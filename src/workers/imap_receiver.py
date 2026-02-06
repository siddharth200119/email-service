"""
IMAP Receiver Worker - Fetches emails from mailboxes via IMAP.
"""
import dotenv
dotenv.load_dotenv()

import os
import signal
import socket
import time
import imaplib
import email
from email.header import decode_header
from typing import Optional, List, Tuple
from datetime import datetime

from src.utils import logger
from src.utils.database import get_db_cursor
from src.utils.encryption import decrypt
from src.models import MailboxCredentialWithSecrets, EmailDirection


# Worker configuration
WORKER_ID = f"imap-{socket.gethostname()}-{os.getpid()}"
CLAIM_TIMEOUT_MINUTES = int(os.getenv("IMAP_CLAIM_TIMEOUT", "5"))
MAX_MAILBOXES_PER_WORKER = int(os.getenv("IMAP_MAX_MAILBOXES", "10"))
POLL_INTERVAL_SECONDS = int(os.getenv("IMAP_POLL_INTERVAL", "30"))
IDLE_TIMEOUT_SECONDS = int(os.getenv("IMAP_IDLE_TIMEOUT", "300"))

# Graceful shutdown flag
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def claim_mailboxes() -> List[str]:
    """
    Claim available mailboxes for this worker.
    Uses DB lock to prevent race conditions.
    """
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """
                UPDATE mailbox_state
                SET
                    receiver_worker_id = %s,
                    receiver_claimed_at = NOW()
                WHERE mailbox_id IN (
                    SELECT mailbox_id
                    FROM mailbox_state
                    WHERE (receiver_claimed_at IS NULL
                           OR receiver_claimed_at < NOW() - INTERVAL '%s minutes')
                    FOR UPDATE SKIP LOCKED
                    LIMIT %s
                )
                RETURNING mailbox_id;
                """,
                (WORKER_ID, CLAIM_TIMEOUT_MINUTES, MAX_MAILBOXES_PER_WORKER)
            )
            rows = cursor.fetchall()
            mailbox_ids = [str(row["mailbox_id"]) for row in rows]
            if mailbox_ids:
                logger.info(f"Claimed {len(mailbox_ids)} mailboxes: {mailbox_ids}")
            return mailbox_ids
    except Exception as e:
        logger.error(f"Error claiming mailboxes: {e}")
        return []


def release_mailboxes():
    """Release all mailboxes claimed by this worker."""
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """
                UPDATE mailbox_state
                SET
                    receiver_worker_id = NULL,
                    receiver_claimed_at = NULL
                WHERE receiver_worker_id = %s
                RETURNING mailbox_id;
                """,
                (WORKER_ID,)
            )
            rows = cursor.fetchall()
            if rows:
                logger.info(f"Released {len(rows)} mailboxes")
    except Exception as e:
        logger.error(f"Error releasing mailboxes: {e}")


def refresh_claim(mailbox_id: str) -> bool:
    """Refresh the claim on a mailbox to prevent timeout."""
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """
                UPDATE mailbox_state
                SET receiver_claimed_at = NOW()
                WHERE mailbox_id = %s AND receiver_worker_id = %s
                RETURNING mailbox_id;
                """,
                (mailbox_id, WORKER_ID)
            )
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Error refreshing claim for mailbox {mailbox_id}: {e}")
        return False


def get_mailbox_credentials(mailbox_id: str) -> Optional[MailboxCredentialWithSecrets]:
    """Get credentials for a mailbox with decrypted secrets."""
    try:
        with get_db_cursor(commit=False) as cursor:
            cursor.execute(
                """
                SELECT c.* FROM mailbox_credentials c
                WHERE c.mailbox_id = %s AND c.is_active = true
                LIMIT 1;
                """,
                (mailbox_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None

            return MailboxCredentialWithSecrets(
                id=row["id"],
                mailbox_id=str(row["mailbox_id"]),
                auth_type=row["auth_type"],
                username=row["username"],
                smtp_host=row["smtp_host"],
                smtp_port=row["smtp_port"],
                smtp_secure=row["smtp_secure"],
                imap_host=row["imap_host"],
                imap_port=row["imap_port"],
                imap_secure=row["imap_secure"],
                is_active=row["is_active"],
                last_verified_at=row["last_verified_at"],
                expires_at=row["expires_at"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                password=decrypt(row["password_encrypted"]) if row["password_encrypted"] else None,
                access_token=decrypt(row["access_token_encrypted"]) if row["access_token_encrypted"] else None,
                refresh_token=decrypt(row["refresh_token_encrypted"]) if row["refresh_token_encrypted"] else None,
            )
    except Exception as e:
        logger.error(f"Error getting credentials for mailbox {mailbox_id}: {e}")
        return None


def get_mailbox_state(mailbox_id: str) -> Tuple[int, Optional[datetime]]:
    """Get the current state (last_uid, last_checked_at) for a mailbox."""
    try:
        with get_db_cursor(commit=False) as cursor:
            cursor.execute(
                "SELECT last_uid, last_checked_at FROM mailbox_state WHERE mailbox_id = %s",
                (mailbox_id,)
            )
            row = cursor.fetchone()
            if row:
                return row["last_uid"] or 0, row["last_checked_at"]
            return 0, None
    except Exception as e:
        logger.error(f"Error getting state for mailbox {mailbox_id}: {e}")
        return 0, None


def update_mailbox_state_success(mailbox_id: str, last_uid: int):
    """Update mailbox state after successful fetch."""
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """
                UPDATE mailbox_state
                SET
                    last_uid = %s,
                    last_checked_at = NOW(),
                    last_success_at = NOW(),
                    error_count = 0
                WHERE mailbox_id = %s;
                """,
                (last_uid, mailbox_id)
            )
    except Exception as e:
        logger.error(f"Error updating success state for mailbox {mailbox_id}: {e}")


def update_mailbox_state_failure(mailbox_id: str):
    """Update mailbox state after failure."""
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """
                UPDATE mailbox_state
                SET
                    error_count = error_count + 1,
                    last_checked_at = NOW()
                WHERE mailbox_id = %s;
                """,
                (mailbox_id,)
            )
    except Exception as e:
        logger.error(f"Error updating failure state for mailbox {mailbox_id}: {e}")


def decode_mime_header(header_value: Optional[str]) -> str:
    """Decode MIME encoded header value."""
    if not header_value:
        return ""
    decoded_parts = decode_header(header_value)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            try:
                result.append(part.decode(charset or "utf-8", errors="replace"))
            except Exception:
                result.append(part.decode("utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)


def parse_email_addresses(header_value: Optional[str]) -> List[str]:
    """Parse email addresses from a header value."""
    if not header_value:
        return []
    # Simple parsing - split by comma and clean up
    addresses = []
    for addr in header_value.split(","):
        addr = addr.strip()
        # Extract email from "Name <email>" format
        if "<" in addr and ">" in addr:
            start = addr.index("<") + 1
            end = addr.index(">")
            addr = addr[start:end]
        if addr:
            addresses.append(addr)
    return addresses


def store_email(mailbox_id: str, imap_uid: int, msg: email.message.Message) -> bool:
    """Store an email in the database."""
    try:
        # Parse email headers
        from_email = parse_email_addresses(msg.get("From"))
        from_email = from_email[0] if from_email else "unknown@unknown.com"
        to_email = parse_email_addresses(msg.get("To"))
        cc_email = parse_email_addresses(msg.get("Cc"))
        bcc_email = parse_email_addresses(msg.get("Bcc"))
        subject = decode_mime_header(msg.get("Subject"))

        # Parse body
        body_text = None
        body_html = None
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain" and not body_text:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_text = payload.decode("utf-8", errors="replace")
                elif content_type == "text/html" and not body_html:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_html = payload.decode("utf-8", errors="replace")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                content_type = msg.get_content_type()
                decoded = payload.decode("utf-8", errors="replace")
                if content_type == "text/html":
                    body_html = decoded
                else:
                    body_text = decoded

        with get_db_cursor(commit=True) as cursor:
            # Check if email already exists (deduplication)
            cursor.execute(
                "SELECT id FROM emails WHERE mailbox_id = %s AND imap_uid = %s",
                (mailbox_id, imap_uid)
            )
            if cursor.fetchone():
                logger.debug(f"Email UID {imap_uid} already exists (duplicate)")
                return False
            
            # Insert new email
            cursor.execute(
                """
                INSERT INTO emails (
                    mailbox_id, direction, status, imap_uid,
                    from_email, to_email, cc_email, bcc_email,
                    subject, body_text, body_html
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    mailbox_id,
                    EmailDirection.INBOUND.value,
                    "RECEIVED",
                    imap_uid,
                    from_email,
                    to_email,
                    cc_email if cc_email else None,
                    bcc_email if bcc_email else None,
                    subject,
                    body_text,
                    body_html,
                )
            )
            result = cursor.fetchone()
            if result:
                logger.debug(f"Stored email UID {imap_uid} as {result['id']}")
                return True
            return False
    except Exception as e:
        logger.error(f"Error storing email UID {imap_uid}: {e}")
        return False


def connect_imap(credentials: MailboxCredentialWithSecrets) -> Optional[imaplib.IMAP4_SSL]:
    """Connect to IMAP server and authenticate."""
    try:
        imap_host = credentials.imap_host
        imap_port = credentials.imap_port or 993

        if not imap_host:
            logger.error("No IMAP host configured")
            return None

        logger.info(f"Connecting to IMAP server {imap_host}:{imap_port}")
        
        if credentials.imap_secure:
            imap = imaplib.IMAP4_SSL(imap_host, imap_port)
        else:
            imap = imaplib.IMAP4(imap_host, imap_port)

        # Authenticate
        if credentials.password:
            imap.login(credentials.username, credentials.password)
        elif credentials.access_token:
            # OAuth2 authentication
            auth_string = f"user={credentials.username}\x01auth=Bearer {credentials.access_token}\x01\x01"
            imap.authenticate("XOAUTH2", lambda x: auth_string.encode())

        logger.info(f"Successfully authenticated as {credentials.username}")
        return imap

    except imaplib.IMAP4.error as e:
        logger.error(f"IMAP authentication failed: {e}")
        return None
    except Exception as e:
        logger.error(f"IMAP connection error: {e}")
        return None


def fetch_new_emails(imap: imaplib.IMAP4_SSL, mailbox_id: str, last_uid: int) -> int:
    """Fetch new emails since last_uid. Returns the new last_uid."""
    try:
        # Select INBOX
        status, data = imap.select("INBOX")
        if status != "OK":
            logger.error(f"Failed to select INBOX: {data}")
            return last_uid

        # Search for messages with UID greater than last_uid
        if last_uid > 0:
            search_criteria = f"UID {last_uid + 1}:*"
        else:
            search_criteria = "ALL"

        status, data = imap.uid("search", None, search_criteria)
        if status != "OK":
            logger.error(f"IMAP search failed: {data}")
            return last_uid

        uids = data[0].split()
        if not uids:
            logger.debug("No new messages")
            return last_uid

        # Filter out UIDs <= last_uid (can happen with UID 1:* search)
        uids = [int(uid) for uid in uids if int(uid) > last_uid]
        
        if not uids:
            logger.debug("No new messages after filtering")
            return last_uid

        logger.info(f"Found {len(uids)} new messages")

        max_uid = last_uid
        for uid in uids:
            if shutdown_requested:
                break

            try:
                status, data = imap.uid("fetch", str(uid), "(RFC822)")
                if status != "OK":
                    logger.error(f"Failed to fetch UID {uid}")
                    continue

                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                if store_email(mailbox_id, uid, msg):
                    max_uid = max(max_uid, uid)
                else:
                    max_uid = max(max_uid, uid)  # Still update UID even for duplicates

            except Exception as e:
                logger.error(f"Error processing UID {uid}: {e}")
                continue

        return max_uid

    except Exception as e:
        logger.error(f"Error fetching emails: {e}")
        return last_uid


def process_mailbox(mailbox_id: str) -> bool:
    """Process a single mailbox - connect, fetch, store."""
    logger.info(f"Processing mailbox {mailbox_id}")

    # Get credentials
    credentials = get_mailbox_credentials(mailbox_id)
    if not credentials:
        logger.warning(f"No active credentials for mailbox {mailbox_id}")
        update_mailbox_state_failure(mailbox_id)
        return False

    # Check IMAP config
    if not credentials.imap_host:
        logger.warning(f"No IMAP host configured for mailbox {mailbox_id}")
        update_mailbox_state_failure(mailbox_id)
        return False

    # Get current state
    last_uid, _ = get_mailbox_state(mailbox_id)
    logger.debug(f"Last UID for mailbox {mailbox_id}: {last_uid}")

    # Connect to IMAP
    imap = connect_imap(credentials)
    if not imap:
        update_mailbox_state_failure(mailbox_id)
        return False

    try:
        # Refresh claim
        refresh_claim(mailbox_id)

        # Fetch new emails
        new_last_uid = fetch_new_emails(imap, mailbox_id, last_uid)

        # Update state
        if new_last_uid > last_uid:
            update_mailbox_state_success(mailbox_id, new_last_uid)
            logger.info(f"Mailbox {mailbox_id}: processed UIDs {last_uid + 1} to {new_last_uid}")
        else:
            update_mailbox_state_success(mailbox_id, last_uid)
            logger.debug(f"Mailbox {mailbox_id}: no new emails")

        return True

    except Exception as e:
        logger.error(f"Error processing mailbox {mailbox_id}: {e}")
        update_mailbox_state_failure(mailbox_id)
        return False
    finally:
        try:
            imap.logout()
        except Exception:
            pass


def main():
    global shutdown_requested
    
    logger.info(f"IMAP Receiver Worker started (worker_id={WORKER_ID})")
    logger.info(f"Config: claim_timeout={CLAIM_TIMEOUT_MINUTES}min, max_mailboxes={MAX_MAILBOXES_PER_WORKER}, poll_interval={POLL_INTERVAL_SECONDS}s")

    try:
        while not shutdown_requested:
            # Claim mailboxes
            mailbox_ids = claim_mailboxes()

            if not mailbox_ids:
                logger.debug("No mailboxes to process, waiting...")
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            # Process each mailbox
            for mailbox_id in mailbox_ids:
                if shutdown_requested:
                    break
                process_mailbox(mailbox_id)

            # Wait before next cycle
            if not shutdown_requested:
                time.sleep(POLL_INTERVAL_SECONDS)

    finally:
        # Graceful shutdown - release all claimed mailboxes
        logger.info("Shutting down, releasing mailboxes...")
        release_mailboxes()
        logger.info("IMAP Receiver Worker stopped")


if __name__ == "__main__":
    main()
