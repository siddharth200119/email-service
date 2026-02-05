"""Tests for email sender worker"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from uuid import uuid4


class TestEmailSenderWorker:
    """Test email sender worker functions"""

    def test_recover_stuck_emails(self, client, created_mailbox):
        """Test that stuck emails are recovered"""
        from src.workers.email_sender import recover_stuck_emails
        
        # This should run without error
        count = recover_stuck_emails()
        assert isinstance(count, int)
        assert count >= 0

    def test_claim_pending_email_no_emails(self, client):
        """Test claiming when no pending emails exist"""
        from src.workers.email_sender import claim_pending_email
        
        # Claim all pending emails first to clear the queue
        while True:
            email = claim_pending_email()
            if email is None:
                break
        
        # Now there should be no pending emails
        email = claim_pending_email()
        assert email is None

    def test_claim_pending_email_returns_email(self, client, created_mailbox):
        """Test claiming a pending email"""
        from src.workers.email_sender import claim_pending_email
        from src.models import EmailStatus
        
        # Create a new email
        response = client.post(
            "/api/emails",
            json={
                "mailbox_id": created_mailbox["id"],
                "from_email": "sender@example.com",
                "to_email": ["recipient@example.com"],
                "subject": "Test claim",
                "body_text": "Test body",
            },
        )
        assert response.status_code == 202
        email_id = response.json()["data"]["id"]
        
        # Claim the email
        email = claim_pending_email()
        assert email is not None
        assert str(email.id) == email_id
        assert email.status == EmailStatus.PROCESSING
        
        # Cleanup
        client.delete(f"/api/emails/{email_id}")

    def test_update_email_status_to_sent(self, client, created_mailbox):
        """Test updating email status to SENT"""
        from src.workers.email_sender import update_email_status
        from src.models import EmailStatus
        
        # Create a new email
        response = client.post(
            "/api/emails",
            json={
                "mailbox_id": created_mailbox["id"],
                "from_email": "sender@example.com",
                "to_email": ["recipient@example.com"],
                "subject": "Test status update",
                "body_text": "Test body",
            },
        )
        email_id = response.json()["data"]["id"]
        
        # Update status to SENT
        result = update_email_status(email_id, EmailStatus.SENT)
        assert result is True
        
        # Verify status changed
        get_response = client.get(f"/api/emails/{email_id}")
        assert get_response.json()["data"]["status"] == "SENT"
        
        # Cleanup
        client.delete(f"/api/emails/{email_id}")

    def test_update_email_status_to_failed(self, client, created_mailbox):
        """Test updating email status to FAILED"""
        from src.workers.email_sender import update_email_status
        from src.models import EmailStatus
        
        # Create a new email
        response = client.post(
            "/api/emails",
            json={
                "mailbox_id": created_mailbox["id"],
                "from_email": "sender@example.com",
                "to_email": ["recipient@example.com"],
                "subject": "Test status update",
                "body_text": "Test body",
            },
        )
        email_id = response.json()["data"]["id"]
        
        # Update status to FAILED
        result = update_email_status(email_id, EmailStatus.FAILED)
        assert result is True
        
        # Verify status changed
        get_response = client.get(f"/api/emails/{email_id}")
        assert get_response.json()["data"]["status"] == "FAILED"
        
        # Cleanup
        client.delete(f"/api/emails/{email_id}")

    def test_get_mailbox_credentials_not_found(self, client):
        """Test getting credentials for non-existent mailbox"""
        from src.workers.email_sender import get_mailbox_credentials
        
        fake_mailbox_id = str(uuid4())
        credentials = get_mailbox_credentials(fake_mailbox_id)
        assert credentials is None

    def test_get_mailbox_credentials_found(self, client, created_mailbox):
        """Test getting credentials for a mailbox with credentials"""
        from src.workers.email_sender import get_mailbox_credentials
        
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
            },
        )
        cred_id = cred_response.json()["data"]["id"]
        
        # Get credentials
        credentials = get_mailbox_credentials(created_mailbox["id"])
        assert credentials is not None
        assert credentials.username == "test@example.com"
        assert credentials.password == "secret123"  # Should be decrypted
        assert credentials.smtp_host == "smtp.example.com"
        
        # Cleanup
        client.delete(f"/api/credentials/{cred_id}")

    def test_process_email_no_credentials(self, client, created_mailbox):
        """Test processing an email with no credentials fails"""
        from src.workers.email_sender import process_email
        from src.models import Email, EmailStatus, EmailDirection
        
        # Create an email without setting up credentials
        email = Email(
            id=uuid4(),
            mailbox_id=uuid4(),  # Non-existent mailbox
            direction=EmailDirection.OUTBOUND,
            status=EmailStatus.PROCESSING,
            from_email="sender@example.com",
            to_email=["recipient@example.com"],
            created_at=datetime.now(),
        )
        
        result = process_email(email)
        assert result is False

    def test_process_email_with_credentials(self, client, created_mailbox):
        """Test processing an email with credentials succeeds"""
        from src.workers.email_sender import process_email, claim_pending_email
        from src.models import EmailStatus
        
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
            },
        )
        cred_id = cred_response.json()["data"]["id"]
        
        # Create an email
        email_response = client.post(
            "/api/emails",
            json={
                "mailbox_id": created_mailbox["id"],
                "from_email": "sender@example.com",
                "to_email": ["recipient@example.com"],
                "subject": "Test process email",
                "body_text": "Test body",
            },
        )
        email_id = email_response.json()["data"]["id"]
        
        # Claim the email
        email = claim_pending_email()
        assert email is not None
        
        # Process the email
        result = process_email(email)
        assert result is True
        
        # Verify status is SENT
        get_response = client.get(f"/api/emails/{email_id}")
        assert get_response.json()["data"]["status"] == "SENT"
        
        # Cleanup
        client.delete(f"/api/credentials/{cred_id}")
        client.delete(f"/api/emails/{email_id}")
