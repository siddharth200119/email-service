import dotenv
dotenv.load_dotenv()
import os
import time
from typing import Optional, Tuple
from src.utils import logger
from src.utils.database import get_db_cursor
from src.utils.encryption import decrypt
from src.utils.mail_sender import send_email
from src.utils.webhooks import emit_event, EventTypes
from src.models import Email, EmailStatus, MailboxCredentialWithSecrets


# Worker configuration from environment
PROCESSING_TIMEOUT = int(os.getenv("PROCESSING_TIMEOUT", "30"))
WORKER_BREAK_TIME = int(os.getenv("WORKER_BREAK_TIME", "2"))


def recover_stuck_emails() -> int:
    """
    Recover emails that have been stuck in PROCESSING status
    for longer than PROCESSING_TIMEOUT seconds.
    Returns the number of recovered emails.
    """
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """
                UPDATE emails
                SET
                    status = %s,
                    processing_started_at = NULL
                WHERE status = %s
                AND processing_started_at < NOW() - INTERVAL '%s seconds'
                RETURNING id;
                """,
                (EmailStatus.ACKED.value, EmailStatus.PROCESSING.value, PROCESSING_TIMEOUT)
            )
            rows = cursor.fetchall()
            count = len(rows)
            if count > 0:
                logger.warning(f"Recovered {count} stuck emails back to ACKED status")
            return count
    except Exception as e:
        logger.error(f"Error recovering stuck emails: {e}")
        return 0


def claim_pending_email() -> Optional[Email]:
    """
    Atomically claim the oldest pending email (FIFO).
    Uses SELECT FOR UPDATE SKIP LOCKED to prevent multiple workers
    from picking the same email.
    """
    logger.info("Checking for pending emails")
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """
                UPDATE emails
                SET
                    status = %s,
                    processing_started_at = NOW()
                WHERE id = (
                    SELECT id
                    FROM emails
                    WHERE status = %s
                    ORDER BY created_at ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                RETURNING *;
                """,
                (EmailStatus.PROCESSING.value, EmailStatus.ACKED.value)
            )
            row = cursor.fetchone()
            if row:
                return Email(**row)
            return None
    except Exception as e:
        logger.error(f"Error claiming pending email: {e}")
        return None


def get_mailbox_credentials(mailbox_id: str) -> Optional[MailboxCredentialWithSecrets]:
    """
    Get the active credentials for a mailbox with decrypted secrets.
    """
    try:
        with get_db_cursor(commit=False) as cursor:
            cursor.execute(
                """
                SELECT * FROM mailbox_credentials
                WHERE mailbox_id = %s AND is_active = true
                LIMIT 1;
                """,
                (mailbox_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            
            # Decrypt sensitive fields
            password = decrypt(row["password_encrypted"]) if row["password_encrypted"] else None
            access_token = decrypt(row["access_token_encrypted"]) if row["access_token_encrypted"] else None
            refresh_token = decrypt(row["refresh_token_encrypted"]) if row["refresh_token_encrypted"] else None
            
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
                password=password,
                access_token=access_token,
                refresh_token=refresh_token,
            )
    except Exception as e:
        logger.error(f"Error fetching mailbox credentials: {e}")
        return None


def update_email_status(email_id: str, status: EmailStatus) -> bool:
    """
    Update the final status of an email (SENT or FAILED).
    Clears processing_started_at on completion.
    """
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """
                UPDATE emails
                SET status = %s, processing_started_at = NULL
                WHERE id = %s
                RETURNING id;
                """,
                (status.value, email_id)
            )
            row = cursor.fetchone()
            if row:
                logger.info(f"Email {email_id} status updated to {status.value}")
                return True
            return False
    except Exception as e:
        logger.error(f"Error updating email status: {e}")
        return False


def process_email(email: Email) -> bool:
    """
    Process a claimed email: get credentials and send.
    Returns True if successful, False otherwise.
    """
    mailbox_id = str(email.mailbox_id)
    email_id = str(email.id)
    
    # Get credentials for the mailbox
    credentials = get_mailbox_credentials(mailbox_id)
    
    if not credentials:
        logger.warning(f"No active credentials found for mailbox {email.mailbox_id}")
        update_email_status(email_id, EmailStatus.FAILED)
        
        # Emit failure event
        emit_event(
            event_type=EventTypes.EMAIL_FAILED,
            owner_type="mailbox",
            owner_id=mailbox_id,
            payload={
                "email_id": email_id,
                "from_email": email.from_email,
                "to_email": email.to_email,
                "subject": email.subject,
                "error": "No active credentials found",
            }
        )
        return False
    
    # Send the email
    success, message = send_email(email, credentials)
    
    if success:
        update_email_status(email_id, EmailStatus.SENT)
        logger.info(f"Email {email.id} sent successfully")
        
        # Emit sent event
        emit_event(
            event_type=EventTypes.EMAIL_SENT,
            owner_type="mailbox",
            owner_id=mailbox_id,
            payload={
                "email_id": email_id,
                "from_email": email.from_email,
                "to_email": email.to_email,
                "subject": email.subject,
                "direction": "OUTBOUND",
            }
        )
        return True
    else:
        update_email_status(email_id, EmailStatus.FAILED)
        logger.error(f"Email {email.id} failed: {message}")
        
        # Emit failure event
        emit_event(
            event_type=EventTypes.EMAIL_FAILED,
            owner_type="mailbox",
            owner_id=mailbox_id,
            payload={
                "email_id": email_id,
                "from_email": email.from_email,
                "to_email": email.to_email,
                "subject": email.subject,
                "error": message,
            }
        )
        return False


def main():
    logger.info(f"Email sending worker started (timeout={PROCESSING_TIMEOUT}s, break={WORKER_BREAK_TIME}s)")
    
    # Recover stuck emails on startup
    recover_stuck_emails()
    
    while True:
        # Periodically recover stuck emails
        recover_stuck_emails()
        
        # Claim a pending email
        email = claim_pending_email()
        
        if email:
            logger.info(f"Claimed email: {email.id}")
            process_email(email)
        else:
            logger.info("No pending emails found")
        
        time.sleep(WORKER_BREAK_TIME)


if __name__ == "__main__":
    main()