"""
Mail sending utility for sending emails via SMTP.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple
from src.models import Email, MailboxCredentialWithSecrets
from src.utils import logger


def send_email(email: Email, credentials: MailboxCredentialWithSecrets) -> Tuple[bool, str]:
    """
    Send an email using the provided credentials via SMTP.
    
    Args:
        email: The Email object to send
        credentials: The mailbox credentials with decrypted secrets
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    logger.info(f"Sending email {email.id} via {credentials.smtp_host}:{credentials.smtp_port}")
    logger.debug(f"From: {email.from_email}, To: {email.to_email}, Subject: {email.subject}")
    
    try:
        # Build the email message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = email.subject or ""
        msg["From"] = email.from_email
        msg["To"] = ", ".join(email.to_email)
        
        if email.cc_email:
            msg["Cc"] = ", ".join(email.cc_email)
        
        # Add text body
        if email.body_text:
            text_part = MIMEText(email.body_text, "plain")
            msg.attach(text_part)
        
        # Add HTML body
        if email.body_html:
            html_part = MIMEText(email.body_html, "html")
            msg.attach(html_part)
        
        # Build recipient list
        recipients = list(email.to_email)
        if email.cc_email:
            recipients.extend(email.cc_email)
        if email.bcc_email:
            recipients.extend(email.bcc_email)
        
        # Connect to SMTP server
        smtp_port = credentials.smtp_port or 587
        
        if credentials.smtp_secure and smtp_port == 465:
            # SSL connection
            server = smtplib.SMTP_SSL(credentials.smtp_host, smtp_port)
        else:
            # Regular connection with optional STARTTLS
            server = smtplib.SMTP(credentials.smtp_host, smtp_port)
            if credentials.smtp_secure:
                server.starttls()
        
        # Authenticate
        if credentials.password:
            server.login(credentials.username, credentials.password)
        elif credentials.access_token:
            # OAuth2 authentication (if supported by the server)
            # This is a simplified implementation - production would need proper OAuth2
            server.login(credentials.username, credentials.access_token)
        
        # Send the email
        server.sendmail(email.from_email, recipients, msg.as_string())
        server.quit()
        
        logger.info(f"Email {email.id} sent successfully")
        return True, "Email sent successfully"
        
    except smtplib.SMTPAuthenticationError as e:
        error_msg = f"SMTP authentication failed: {e}"
        logger.error(f"Email {email.id} failed: {error_msg}")
        return False, error_msg
        
    except smtplib.SMTPRecipientsRefused as e:
        error_msg = f"Recipients refused: {e}"
        logger.error(f"Email {email.id} failed: {error_msg}")
        return False, error_msg
        
    except smtplib.SMTPException as e:
        error_msg = f"SMTP error: {e}"
        logger.error(f"Email {email.id} failed: {error_msg}")
        return False, error_msg
        
    except Exception as e:
        error_msg = f"Failed to send email: {e}"
        logger.error(f"Email {email.id} failed: {error_msg}")
        return False, error_msg
