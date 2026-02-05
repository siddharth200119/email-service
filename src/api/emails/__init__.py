from fastapi import APIRouter
from src.models import APIOutput, Email, EmailCreate, EmailUpdate, EmailStatus
from src.utils.database import get_db_cursor
from typing import Optional

router = APIRouter(prefix="/emails", tags=["emails"])


@router.get("")
def get_all_emails(mailbox_id: Optional[str] = None, status: Optional[EmailStatus] = None):
    """Get all emails with optional filters"""
    try:
        with get_db_cursor(commit=False) as cursor:
            query = "SELECT * FROM emails WHERE 1=1"
            params = []

            if mailbox_id:
                query += " AND mailbox_id = %s"
                params.append(mailbox_id)
            if status:
                query += " AND status = %s"
                params.append(status.value)

            query += " ORDER BY created_at DESC"
            cursor.execute(query, params)
            emails = cursor.fetchall()
            return APIOutput.success(
                data=[Email(**row).model_dump(mode="json") for row in emails]
            )
    except Exception as e:
        return APIOutput.failure(message=str(e))


@router.get("/{email_id}")
def get_email(email_id: str):
    """Get an email by ID"""
    try:
        with get_db_cursor(commit=False) as cursor:
            cursor.execute("SELECT * FROM emails WHERE id = %s", (email_id,))
            email = cursor.fetchone()
            if not email:
                return APIOutput.failure(message="Email not found", status_code=404)
            return APIOutput.success(data=Email(**email).model_dump(mode="json"))
    except Exception as e:
        return APIOutput.failure(message=str(e))


@router.post("")
def create_email(email: EmailCreate):
    """Create a new email"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO emails (
                    mailbox_id, direction, from_email, to_email,
                    cc_email, bcc_email, subject, body_text, body_html, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    str(email.mailbox_id),
                    email.direction.value,
                    email.from_email,
                    email.to_email,
                    email.cc_email,
                    email.bcc_email,
                    email.subject,
                    email.body_text,
                    email.body_html,
                    email.status.value,
                ),
            )
            new_email = cursor.fetchone()
            return APIOutput.success(
                data=Email(**new_email).model_dump(mode="json"),
                message="Email acknowledged",
                status_code=202,
            )
    except Exception as e:
        return APIOutput.failure(message=str(e))


@router.put("/{email_id}")
def update_email(email_id: str, email: EmailUpdate):
    """Update an email"""
    try:
        with get_db_cursor() as cursor:
            updates = []
            values = []

            if email.status is not None:
                updates.append("status = %s")
                values.append(email.status.value)
            if email.subject is not None:
                updates.append("subject = %s")
                values.append(email.subject)
            if email.body_text is not None:
                updates.append("body_text = %s")
                values.append(email.body_text)
            if email.body_html is not None:
                updates.append("body_html = %s")
                values.append(email.body_html)

            if not updates:
                return APIOutput.failure(
                    message="No fields to update", status_code=400
                )

            values.append(email_id)
            query = f"UPDATE emails SET {', '.join(updates)} WHERE id = %s RETURNING *"
            cursor.execute(query, values)
            updated_email = cursor.fetchone()

            if not updated_email:
                return APIOutput.failure(message="Email not found", status_code=404)
            return APIOutput.success(
                data=Email(**updated_email).model_dump(mode="json"),
                message="Email updated",
            )
    except Exception as e:
        return APIOutput.failure(message=str(e))


@router.delete("/{email_id}")
def delete_email(email_id: str):
    """Delete an email"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "DELETE FROM emails WHERE id = %s RETURNING id", (email_id,)
            )
            deleted = cursor.fetchone()
            if not deleted:
                return APIOutput.failure(message="Email not found", status_code=404)
            return APIOutput.success(message="Email deleted")
    except Exception as e:
        return APIOutput.failure(message=str(e))
