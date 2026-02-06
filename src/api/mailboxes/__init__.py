from fastapi import APIRouter
from src.models import APIOutput, Mailbox, MailboxCreate, MailboxUpdate
from src.utils.database import get_db_cursor

router = APIRouter(prefix="/mailboxes", tags=["mailboxes"])


@router.get("")
def get_all_mailboxes():
    """Get all mailboxes"""
    try:
        with get_db_cursor(commit=False) as cursor:
            cursor.execute("SELECT * FROM mailboxes ORDER BY created_at DESC")
            mailboxes = cursor.fetchall()
            return APIOutput.success(
                data=[Mailbox(**row).model_dump(mode="json") for row in mailboxes]
            )
    except Exception as e:
        return APIOutput.failure(message=str(e))


@router.get("/{mailbox_id}")
def get_mailbox(mailbox_id: str):
    """Get a mailbox by ID"""
    try:
        with get_db_cursor(commit=False) as cursor:
            cursor.execute("SELECT * FROM mailboxes WHERE id = %s", (mailbox_id,))
            mailbox = cursor.fetchone()
            if not mailbox:
                return APIOutput.failure(message="Mailbox not found", status_code=404)
            return APIOutput.success(data=Mailbox(**mailbox).model_dump(mode="json"))
    except Exception as e:
        return APIOutput.failure(message=str(e))


@router.post("")
def create_mailbox(mailbox: MailboxCreate):
    """Create a new mailbox"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO mailboxes (email_address, is_active)
                VALUES (%s, %s)
                RETURNING *
                """,
                (mailbox.email_address, mailbox.is_active),
            )
            new_mailbox = cursor.fetchone()
            
            # Create mailbox_state for IMAP receiver
            cursor.execute(
                """
                INSERT INTO mailbox_state (mailbox_id)
                VALUES (%s)
                """,
                (new_mailbox["id"],)
            )
            
            return APIOutput.success(
                data=Mailbox(**new_mailbox).model_dump(mode="json"),
                message="Mailbox created",
                status_code=201,
            )
    except Exception as e:
        return APIOutput.failure(message=str(e))


@router.put("/{mailbox_id}")
def update_mailbox(mailbox_id: str, mailbox: MailboxUpdate):
    """Update a mailbox"""
    try:
        with get_db_cursor() as cursor:
            updates = []
            values = []
            if mailbox.email_address is not None:
                updates.append("email_address = %s")
                values.append(mailbox.email_address)
            if mailbox.is_active is not None:
                updates.append("is_active = %s")
                values.append(mailbox.is_active)

            if not updates:
                return APIOutput.failure(
                    message="No fields to update", status_code=400
                )

            values.append(mailbox_id)
            query = f"UPDATE mailboxes SET {', '.join(updates)} WHERE id = %s RETURNING *"
            cursor.execute(query, values)
            updated_mailbox = cursor.fetchone()

            if not updated_mailbox:
                return APIOutput.failure(message="Mailbox not found", status_code=404)
            return APIOutput.success(
                data=Mailbox(**updated_mailbox).model_dump(mode="json"),
                message="Mailbox updated",
            )
    except Exception as e:
        return APIOutput.failure(message=str(e))


@router.delete("/{mailbox_id}")
def delete_mailbox(mailbox_id: str):
    """Delete a mailbox"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "DELETE FROM mailboxes WHERE id = %s RETURNING id", (mailbox_id,)
            )
            deleted = cursor.fetchone()
            if not deleted:
                return APIOutput.failure(message="Mailbox not found", status_code=404)
            return APIOutput.success(message="Mailbox deleted")
    except Exception as e:
        return APIOutput.failure(message=str(e))
