"""Tests for mail sender utility"""
import pytest
from datetime import datetime
from uuid import uuid4
from src.utils.mail_sender import send_email
from src.models import Email, EmailStatus, EmailDirection, MailboxCredentialWithSecrets


class TestMailSender:
    """Test mail sender utility functions"""

    @pytest.fixture
    def sample_email(self):
        """Create a sample email for testing"""
        return Email(
            id=uuid4(),
            mailbox_id=uuid4(),
            direction=EmailDirection.OUTBOUND,
            status=EmailStatus.PROCESSING,
            from_email="sender@example.com",
            to_email=["recipient@example.com"],
            cc_email=["cc@example.com"],
            subject="Test Subject",
            body_text="Test body text",
            body_html="<p>Test body html</p>",
            created_at=datetime.now(),
            processing_started_at=datetime.now(),
        )

    @pytest.fixture
    def sample_credentials(self):
        """Create sample credentials for testing"""
        return MailboxCredentialWithSecrets(
            id=1,
            mailbox_id=str(uuid4()),
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
            access_token=None,
            refresh_token=None,
        )

    def test_send_email_returns_tuple(self, sample_email, sample_credentials):
        """Test that send_email returns a tuple"""
        result = send_email(sample_email, sample_credentials)
        
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_send_email_returns_success(self, sample_email, sample_credentials):
        """Test that send_email returns success (placeholder)"""
        success, message = send_email(sample_email, sample_credentials)
        
        assert success is True
        assert isinstance(message, str)

    def test_send_email_with_different_auth_types(self, sample_email):
        """Test sending with different auth types"""
        # OAuth2 credentials
        oauth_creds = MailboxCredentialWithSecrets(
            id=2,
            mailbox_id=str(uuid4()),
            auth_type="oauth2",
            username="oauth@example.com",
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_secure=True,
            imap_host="imap.gmail.com",
            imap_port=993,
            imap_secure=True,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            password=None,
            access_token="ya29.access_token",
            refresh_token="1//refresh_token",
        )
        
        success, message = send_email(sample_email, oauth_creds)
        assert success is True

    def test_send_email_with_minimal_email(self, sample_credentials):
        """Test sending with minimal email fields"""
        minimal_email = Email(
            id=uuid4(),
            mailbox_id=uuid4(),
            direction=EmailDirection.OUTBOUND,
            status=EmailStatus.PROCESSING,
            from_email="sender@example.com",
            to_email=["recipient@example.com"],
            created_at=datetime.now(),
        )
        
        success, message = send_email(minimal_email, sample_credentials)
        assert success is True

    def test_send_email_with_multiple_recipients(self, sample_credentials):
        """Test sending with multiple recipients"""
        email = Email(
            id=uuid4(),
            mailbox_id=uuid4(),
            direction=EmailDirection.OUTBOUND,
            status=EmailStatus.PROCESSING,
            from_email="sender@example.com",
            to_email=["recipient1@example.com", "recipient2@example.com", "recipient3@example.com"],
            cc_email=["cc1@example.com", "cc2@example.com"],
            bcc_email=["bcc@example.com"],
            subject="Multi-recipient test",
            body_text="Test body",
            created_at=datetime.now(),
        )
        
        success, message = send_email(email, sample_credentials)
        assert success is True
