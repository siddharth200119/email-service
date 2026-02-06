"""Tests for mail sender utility"""
import pytest
from unittest.mock import patch, MagicMock
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

    @patch("src.utils.mail_sender.smtplib.SMTP")
    def test_send_email_returns_tuple(self, mock_smtp, sample_email, sample_credentials):
        """Test that send_email returns a tuple"""
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        result = send_email(sample_email, sample_credentials)
        
        assert isinstance(result, tuple)
        assert len(result) == 2

    @patch("src.utils.mail_sender.smtplib.SMTP")
    def test_send_email_returns_success(self, mock_smtp, sample_email, sample_credentials):
        """Test that send_email returns success when SMTP works"""
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        success, message = send_email(sample_email, sample_credentials)
        
        assert success is True
        assert "successfully" in message.lower()

    @patch("src.utils.mail_sender.smtplib.SMTP")
    def test_send_email_calls_smtp_methods(self, mock_smtp, sample_email, sample_credentials):
        """Test that send_email calls the correct SMTP methods"""
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        send_email(sample_email, sample_credentials)
        
        # Verify SMTP was initialized with correct host/port
        mock_smtp.assert_called_once_with("smtp.example.com", 587)
        
        # Verify STARTTLS was called (since smtp_secure=True)
        mock_server.starttls.assert_called_once()
        
        # Verify login was called
        mock_server.login.assert_called_once_with("test@example.com", "secret123")
        
        # Verify sendmail was called
        mock_server.sendmail.assert_called_once()
        
        # Verify quit was called
        mock_server.quit.assert_called_once()

    @patch("src.utils.mail_sender.smtplib.SMTP_SSL")
    def test_send_email_uses_ssl_for_port_465(self, mock_smtp_ssl, sample_email):
        """Test that SMTP_SSL is used for port 465"""
        mock_server = MagicMock()
        mock_smtp_ssl.return_value = mock_server
        
        ssl_credentials = MailboxCredentialWithSecrets(
            id=2,
            mailbox_id=str(uuid4()),
            auth_type="password",
            username="test@example.com",
            smtp_host="smtp.example.com",
            smtp_port=465,
            smtp_secure=True,
            imap_host="imap.example.com",
            imap_port=993,
            imap_secure=True,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            password="secret123",
        )
        
        success, message = send_email(sample_email, ssl_credentials)
        
        assert success is True
        mock_smtp_ssl.assert_called_once_with("smtp.example.com", 465)

    @patch("src.utils.mail_sender.smtplib.SMTP")
    def test_send_email_with_oauth2(self, mock_smtp, sample_email):
        """Test sending with OAuth2 credentials"""
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
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
        mock_server.login.assert_called_once_with("oauth@example.com", "ya29.access_token")

    @patch("src.utils.mail_sender.smtplib.SMTP")
    def test_send_email_with_minimal_email(self, mock_smtp, sample_credentials):
        """Test sending with minimal email fields"""
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
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

    @patch("src.utils.mail_sender.smtplib.SMTP")
    def test_send_email_with_multiple_recipients(self, mock_smtp, sample_credentials):
        """Test sending with multiple recipients"""
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        email = Email(
            id=uuid4(),
            mailbox_id=uuid4(),
            direction=EmailDirection.OUTBOUND,
            status=EmailStatus.PROCESSING,
            from_email="sender@example.com",
            to_email=["recipient1@example.com", "recipient2@example.com"],
            cc_email=["cc1@example.com", "cc2@example.com"],
            bcc_email=["bcc@example.com"],
            subject="Multi-recipient test",
            body_text="Test body",
            created_at=datetime.now(),
        )
        
        success, message = send_email(email, sample_credentials)
        assert success is True
        
        # Verify all recipients were included
        call_args = mock_server.sendmail.call_args
        recipients = call_args[0][1]
        assert len(recipients) == 5  # 2 to + 2 cc + 1 bcc

    @patch("src.utils.mail_sender.smtplib.SMTP")
    def test_send_email_handles_auth_error(self, mock_smtp, sample_email, sample_credentials):
        """Test that authentication errors are handled"""
        import smtplib
        
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Authentication failed")
        
        success, message = send_email(sample_email, sample_credentials)
        
        assert success is False
        assert "authentication" in message.lower()

    @patch("src.utils.mail_sender.smtplib.SMTP")
    def test_send_email_handles_connection_error(self, mock_smtp, sample_email, sample_credentials):
        """Test that connection errors are handled"""
        import smtplib
        
        mock_smtp.side_effect = smtplib.SMTPConnectError(421, b"Connection refused")
        
        success, message = send_email(sample_email, sample_credentials)
        
        assert success is False
        assert "smtp" in message.lower() or "error" in message.lower()
