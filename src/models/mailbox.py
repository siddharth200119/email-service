from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID


class MailboxBase(BaseModel):
    """Base mailbox model with common fields"""
    email_address: str
    is_active: bool = True


class MailboxCreate(MailboxBase):
    """Model for creating a mailbox"""
    pass


class MailboxUpdate(BaseModel):
    """Model for updating a mailbox"""
    email_address: Optional[str] = None
    is_active: Optional[bool] = None


class Mailbox(MailboxBase):
    """Full mailbox model with all fields"""
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
