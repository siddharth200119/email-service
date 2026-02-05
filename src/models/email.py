from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class EmailDirection(str, Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class EmailStatus(str, Enum):
    ACKED = "ACKED"
    PROCESSING = "PROCESSING"
    QUEUED = "QUEUED"
    SENT = "SENT"
    FAILED = "FAILED"


class EmailBase(BaseModel):
    """Base email model with common fields"""
    mailbox_id: UUID
    direction: EmailDirection = EmailDirection.OUTBOUND
    from_email: str
    to_email: List[str]
    cc_email: Optional[List[str]] = None
    bcc_email: Optional[List[str]] = None
    subject: Optional[str] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None


class EmailCreate(EmailBase):
    """Model for creating an email"""
    status: EmailStatus = EmailStatus.ACKED


class EmailUpdate(BaseModel):
    """Model for updating an email"""
    status: Optional[EmailStatus] = None
    subject: Optional[str] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None


class Email(EmailBase):
    """Full email model with all fields"""
    id: UUID
    status: EmailStatus
    created_at: datetime
    processing_started_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
