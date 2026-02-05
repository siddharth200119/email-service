from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from enum import Enum


class AuthType(str, Enum):
    PASSWORD = "password"
    OAUTH2 = "oauth2"
    APP_PASSWORD = "app_password"


class MailboxCredentialBase(BaseModel):
    """Base mailbox credential model"""
    mailbox_id: str
    auth_type: AuthType
    username: str
    
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_secure: bool = True
    
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    imap_secure: bool = True
    
    is_active: bool = True


class MailboxCredentialCreate(MailboxCredentialBase):
    """Model for creating a mailbox credential"""
    password: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


class MailboxCredentialUpdate(BaseModel):
    """Model for updating a mailbox credential"""
    auth_type: Optional[AuthType] = None
    username: Optional[str] = None
    password: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_secure: Optional[bool] = None
    
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    imap_secure: Optional[bool] = None
    
    is_active: Optional[bool] = None


class MailboxCredential(MailboxCredentialBase):
    """Full mailbox credential model (without sensitive data)"""
    id: int
    last_verified_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MailboxCredentialWithSecrets(MailboxCredential):
    """Mailbox credential with decrypted secrets (for internal worker use only)"""
    password: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None

