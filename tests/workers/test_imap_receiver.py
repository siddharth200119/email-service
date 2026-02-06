"""Tests for IMAP receiver worker"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from uuid import uuid4
import email
from email.message import EmailMessage


class TestIMAPReceiverWorker:
    """Test IMAP receiver worker functions"""

    def test_claim_mailboxes_empty(self, client):
        """Test claiming when no mailboxes with state exist"""
        from src.workers.imap_receiver import claim_mailboxes
        
        # Should return empty list when no mailbox_state entries exist
        result = claim_mailboxes()
        assert isinstance(result, list)

    def test_release_mailboxes(self, client):
        """Test releasing mailboxes runs without error"""
        from src.workers.imap_receiver import release_mailboxes
        
        # Should run without error even if nothing to release
        release_mailboxes()

    def test_get_mailbox_state_not_found(self, client):
        """Test getting state for non-existent mailbox"""
        from src.workers.imap_receiver import get_mailbox_state
        
        fake_id = str(uuid4())
        last_uid, last_checked = get_mailbox_state(fake_id)
        
        assert last_uid == 0
        assert last_checked is None

    def test_get_mailbox_state_found(self, client, created_mailbox):
        """Test getting state for existing mailbox"""
        from src.workers.imap_receiver import get_mailbox_state
        
        last_uid, last_checked = get_mailbox_state(created_mailbox["id"])
        
        assert last_uid == 0  # Default value
        assert last_checked is None  # Not checked yet

    def test_update_mailbox_state_success(self, client, created_mailbox):
        """Test updating mailbox state after success"""
        from src.workers.imap_receiver import (
            update_mailbox_state_success,
            get_mailbox_state,
        )
        
        # Update state
        update_mailbox_state_success(created_mailbox["id"], 100)
        
        # Verify state was updated
        last_uid, _ = get_mailbox_state(created_mailbox["id"])
        assert last_uid == 100

    def test_update_mailbox_state_failure(self, client, created_mailbox):
        """Test updating mailbox state after failure"""
        from src.workers.imap_receiver import update_mailbox_state_failure
        from src.utils.database import get_db_cursor
        
        # Update state on failure
        update_mailbox_state_failure(created_mailbox["id"])
        
        # Verify error count was incremented
        with get_db_cursor(commit=False) as cursor:
            cursor.execute(
                "SELECT error_count FROM mailbox_state WHERE mailbox_id = %s",
                (created_mailbox["id"],)
            )
            row = cursor.fetchone()
            assert row["error_count"] == 1

    def test_decode_mime_header_plain(self):
        """Test decoding plain header"""
        from src.workers.imap_receiver import decode_mime_header
        
        result = decode_mime_header("Simple Subject")
        assert result == "Simple Subject"

    def test_decode_mime_header_empty(self):
        """Test decoding empty header"""
        from src.workers.imap_receiver import decode_mime_header
        
        assert decode_mime_header(None) == ""
        assert decode_mime_header("") == ""

    def test_parse_email_addresses_simple(self):
        """Test parsing simple email address"""
        from src.workers.imap_receiver import parse_email_addresses
        
        result = parse_email_addresses("test@example.com")
        assert result == ["test@example.com"]

    def test_parse_email_addresses_with_name(self):
        """Test parsing email with display name"""
        from src.workers.imap_receiver import parse_email_addresses
        
        result = parse_email_addresses("John Doe <john@example.com>")
        assert result == ["john@example.com"]

    def test_parse_email_addresses_multiple(self):
        """Test parsing multiple email addresses"""
        from src.workers.imap_receiver import parse_email_addresses
        
        result = parse_email_addresses("a@example.com, b@example.com")
        assert len(result) == 2
        assert "a@example.com" in result
        assert "b@example.com" in result

    def test_parse_email_addresses_empty(self):
        """Test parsing empty/None header"""
        from src.workers.imap_receiver import parse_email_addresses
        
        assert parse_email_addresses(None) == []
        assert parse_email_addresses("") == []

    def test_get_mailbox_credentials_not_found(self, client):
        """Test getting credentials for non-existent mailbox"""
        from src.workers.imap_receiver import get_mailbox_credentials
        
        fake_id = str(uuid4())
        credentials = get_mailbox_credentials(fake_id)
        
        assert credentials is None

    def test_get_mailbox_credentials_found(self, client, created_mailbox):
        """Test getting credentials for mailbox with credentials"""
        from src.workers.imap_receiver import get_mailbox_credentials
        
        # Create credentials
        cred_response = client.post(
            "/api/credentials",
            json={
                "mailbox_id": created_mailbox["id"],
                "auth_type": "password",
                "username": "test@example.com",
                "password": "secret123",
                "smtp_host": "smtp.example.com",
                "smtp_port": 587,
                "imap_host": "imap.example.com",
                "imap_port": 993,
                "imap_secure": True,
            },
        )
        cred_id = cred_response.json()["data"]["id"]
        
        # Get credentials
        credentials = get_mailbox_credentials(created_mailbox["id"])
        
        assert credentials is not None
        assert credentials.username == "test@example.com"
        assert credentials.password == "secret123"  # Decrypted
        assert credentials.imap_host == "imap.example.com"
        assert credentials.imap_port == 993
        
        # Cleanup
        client.delete(f"/api/credentials/{cred_id}")

    @patch("src.workers.imap_receiver.imaplib.IMAP4_SSL")
    def test_connect_imap_success(self, mock_imap_class, client, created_mailbox):
        """Test successful IMAP connection"""
        from src.workers.imap_receiver import connect_imap
        from src.models import MailboxCredentialWithSecrets
        
        mock_imap = MagicMock()
        mock_imap_class.return_value = mock_imap
        
        credentials = MailboxCredentialWithSecrets(
            id=1,
            mailbox_id=created_mailbox["id"],
            auth_type="password",
            username="test@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_secure=True,
            imap_host="imap.example.com",
            imap_port=993,
            imap_secure=True,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            password="secret123",
        )
        
        result = connect_imap(credentials)
        
        assert result is not None
        mock_imap_class.assert_called_once_with("imap.example.com", 993)
        mock_imap.login.assert_called_once_with("test@example.com", "secret123")

    @patch("src.workers.imap_receiver.imaplib.IMAP4_SSL")
    def test_connect_imap_auth_failure(self, mock_imap_class, client, created_mailbox):
        """Test IMAP connection with auth failure"""
        from src.workers.imap_receiver import connect_imap
        from src.models import MailboxCredentialWithSecrets
        import imaplib
        
        mock_imap = MagicMock()
        mock_imap_class.return_value = mock_imap
        mock_imap.login.side_effect = imaplib.IMAP4.error("Auth failed")
        
        credentials = MailboxCredentialWithSecrets(
            id=1,
            mailbox_id=created_mailbox["id"],
            auth_type="password",
            username="test@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_secure=True,
            imap_host="imap.example.com",
            imap_port=993,
            imap_secure=True,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            password="wrong_password",
        )
        
        result = connect_imap(credentials)
        
        assert result is None

    def test_store_email(self, client, created_mailbox):
        """Test storing an email from IMAP"""
        from src.workers.imap_receiver import store_email
        from src.utils.database import get_db_cursor
        
        # Create a test email message
        msg = EmailMessage()
        msg["From"] = "sender@example.com"
        msg["To"] = "recipient@example.com"
        msg["Subject"] = "Test Email"
        msg.set_content("This is the body")
        
        # Store the email
        result = store_email(created_mailbox["id"], 999, msg)
        
        assert result is True
        
        # Verify it was stored via direct DB query
        with get_db_cursor(commit=False) as cursor:
            cursor.execute(
                "SELECT * FROM emails WHERE mailbox_id = %s AND imap_uid = %s",
                (created_mailbox["id"], 999)
            )
            row = cursor.fetchone()
            assert row is not None
            assert row["subject"] == "Test Email"
            assert row["direction"] == "INBOUND"
            email_id = row["id"]
        
        # Cleanup - delete the email so mailbox can be deleted
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM emails WHERE id = %s", (email_id,))

    def test_store_email_duplicate(self, client, created_mailbox):
        """Test that duplicate emails are not stored"""
        from src.workers.imap_receiver import store_email
        from src.utils.database import get_db_cursor
        
        msg = EmailMessage()
        msg["From"] = "sender@example.com"
        msg["To"] = "recipient@example.com"
        msg["Subject"] = "Duplicate Test"
        msg.set_content("Body")
        
        # Store first time - should succeed
        result1 = store_email(created_mailbox["id"], 888, msg)
        assert result1 is True
        
        # Store second time - should return False (duplicate)
        result2 = store_email(created_mailbox["id"], 888, msg)
        assert result2 is False
        
        # Cleanup - delete the email so mailbox can be deleted
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                "DELETE FROM emails WHERE mailbox_id = %s AND imap_uid = %s",
                (created_mailbox["id"], 888)
            )

    @patch("src.workers.imap_receiver.connect_imap")
    @patch("src.workers.imap_receiver.get_mailbox_credentials")
    def test_process_mailbox_no_credentials(
        self, mock_get_creds, mock_connect, client, created_mailbox
    ):
        """Test processing mailbox with no credentials"""
        from src.workers.imap_receiver import process_mailbox
        
        mock_get_creds.return_value = None
        
        result = process_mailbox(created_mailbox["id"])
        
        assert result is False
        mock_connect.assert_not_called()

    @patch("src.workers.imap_receiver.fetch_new_emails")
    @patch("src.workers.imap_receiver.connect_imap")
    @patch("src.workers.imap_receiver.get_mailbox_credentials")
    def test_process_mailbox_success(
        self, mock_get_creds, mock_connect, mock_fetch, client, created_mailbox
    ):
        """Test successful mailbox processing"""
        from src.workers.imap_receiver import process_mailbox
        from src.models import MailboxCredentialWithSecrets
        
        # Setup mocks
        mock_get_creds.return_value = MailboxCredentialWithSecrets(
            id=1,
            mailbox_id=created_mailbox["id"],
            auth_type="password",
            username="test@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_secure=True,
            imap_host="imap.example.com",
            imap_port=993,
            imap_secure=True,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            password="secret",
        )
        
        mock_imap = MagicMock()
        mock_connect.return_value = mock_imap
        mock_fetch.return_value = 10  # New last_uid
        
        result = process_mailbox(created_mailbox["id"])
        
        assert result is True
        mock_fetch.assert_called_once()
        mock_imap.logout.assert_called_once()

    def test_claim_and_refresh_mailbox(self, client, created_mailbox):
        """Test claiming and refreshing a mailbox"""
        from src.workers.imap_receiver import claim_mailboxes, refresh_claim, WORKER_ID
        
        # Claim mailboxes
        claimed = claim_mailboxes()
        
        # Should have claimed the created mailbox
        assert created_mailbox["id"] in claimed
        
        # Refresh the claim
        result = refresh_claim(created_mailbox["id"])
        assert result is True
