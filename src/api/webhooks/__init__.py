"""Webhooks API endpoints"""
import secrets
from fastapi import APIRouter
from typing import Optional, List
from pydantic import BaseModel, HttpUrl
from datetime import datetime

from src.utils.database import get_db_cursor
from src.models import APIOutput

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


class WebhookCreate(BaseModel):
    """Create a new webhook"""
    owner_type: str  # 'mailbox', 'user', etc.
    owner_id: str  # UUID as string
    url: HttpUrl


class WebhookResponse(BaseModel):
    """Webhook response (shown only on create)"""
    id: int
    owner_type: str
    owner_id: str
    url: str
    secret: str  # Only shown once on create
    is_active: bool
    created_at: Optional[datetime]


class WebhookListItem(BaseModel):
    """Webhook in list view (no secret)"""
    id: int
    owner_type: str
    owner_id: str
    url: str
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class WebhookUpdate(BaseModel):
    """Update webhook"""
    url: Optional[HttpUrl] = None
    is_active: Optional[bool] = None


def generate_secret() -> str:
    """Generate a secure webhook secret"""
    return secrets.token_urlsafe(32)


@router.post("")
def create_webhook(webhook: WebhookCreate):
    """
    Create a new webhook.
    
    The secret is returned only once - store it securely!
    """
    try:
        secret = generate_secret()
        
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """
                INSERT INTO webhooks (owner_type, owner_id, url, secret)
                VALUES (%s, %s, %s, %s)
                RETURNING id, owner_type, owner_id, url, secret, is_active, created_at
                """,
                (webhook.owner_type, webhook.owner_id, str(webhook.url), secret)
            )
            row = cursor.fetchone()
            
            return APIOutput.success(
                data=WebhookResponse(
                    id=row["id"],
                    owner_type=row["owner_type"],
                    owner_id=str(row["owner_id"]),
                    url=row["url"],
                    secret=row["secret"],
                    is_active=row["is_active"],
                    created_at=row["created_at"],
                ).model_dump(mode="json"),
                message="Webhook created. Store the secret securely - it won't be shown again!",
                status_code=201,
            )
    except Exception as e:
        return APIOutput.failure(message=str(e))


@router.get("")
def list_webhooks(
    owner_type: Optional[str] = None,
    owner_id: Optional[str] = None,
):
    """List all webhooks (optionally filtered by owner)"""
    try:
        with get_db_cursor(commit=False) as cursor:
            query = "SELECT id, owner_type, owner_id, url, is_active, created_at, updated_at FROM webhooks WHERE 1=1"
            params = []
            
            if owner_type:
                query += " AND owner_type = %s"
                params.append(owner_type)
            
            if owner_id:
                query += " AND owner_id = %s"
                params.append(owner_id)
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            
            webhooks = [
                WebhookListItem(
                    id=row["id"],
                    owner_type=row["owner_type"],
                    owner_id=str(row["owner_id"]),
                    url=row["url"],
                    is_active=row["is_active"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                ).model_dump(mode="json")
                for row in rows
            ]
            
            return APIOutput.success(data=webhooks)
    except Exception as e:
        return APIOutput.failure(message=str(e))


@router.get("/{webhook_id}")
def get_webhook(webhook_id: int):
    """Get a webhook by ID (secret not included)"""
    try:
        with get_db_cursor(commit=False) as cursor:
            cursor.execute(
                "SELECT id, owner_type, owner_id, url, is_active, created_at, updated_at FROM webhooks WHERE id = %s",
                (webhook_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return APIOutput.failure(message="Webhook not found", status_code=404)
            
            return APIOutput.success(
                data=WebhookListItem(
                    id=row["id"],
                    owner_type=row["owner_type"],
                    owner_id=str(row["owner_id"]),
                    url=row["url"],
                    is_active=row["is_active"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                ).model_dump(mode="json")
            )
    except Exception as e:
        return APIOutput.failure(message=str(e))


@router.put("/{webhook_id}")
def update_webhook(webhook_id: int, webhook: WebhookUpdate):
    """Update a webhook (URL or active status)"""
    try:
        with get_db_cursor(commit=True) as cursor:
            updates = []
            values = []
            
            if webhook.url is not None:
                updates.append("url = %s")
                values.append(str(webhook.url))
            
            if webhook.is_active is not None:
                updates.append("is_active = %s")
                values.append(webhook.is_active)
            
            if not updates:
                return APIOutput.failure(message="No fields to update", status_code=400)
            
            updates.append("updated_at = NOW()")
            values.append(webhook_id)
            
            cursor.execute(
                f"UPDATE webhooks SET {', '.join(updates)} WHERE id = %s RETURNING id",
                tuple(values)
            )
            
            if not cursor.fetchone():
                return APIOutput.failure(message="Webhook not found", status_code=404)
            
            return APIOutput.success(message="Webhook updated")
    except Exception as e:
        return APIOutput.failure(message=str(e))


@router.delete("/{webhook_id}")
def delete_webhook(webhook_id: int):
    """Delete a webhook"""
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                "DELETE FROM webhooks WHERE id = %s RETURNING id",
                (webhook_id,)
            )
            
            if not cursor.fetchone():
                return APIOutput.failure(message="Webhook not found", status_code=404)
            
            return APIOutput.success(message="Webhook deleted")
    except Exception as e:
        return APIOutput.failure(message=str(e))


@router.post("/{webhook_id}/regenerate-secret")
def regenerate_secret(webhook_id: int):
    """Regenerate the webhook secret"""
    try:
        new_secret = generate_secret()
        
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                "UPDATE webhooks SET secret = %s, updated_at = NOW() WHERE id = %s RETURNING id, secret",
                (new_secret, webhook_id)
            )
            row = cursor.fetchone()
            
            if not row:
                return APIOutput.failure(message="Webhook not found", status_code=404)
            
            return APIOutput.success(
                data={"secret": row["secret"]},
                message="Secret regenerated. Store it securely - it won't be shown again!"
            )
    except Exception as e:
        return APIOutput.failure(message=str(e))
