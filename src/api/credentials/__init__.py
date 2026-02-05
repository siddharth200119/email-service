from fastapi import APIRouter
from src.models import (
    APIOutput,
    MailboxCredential,
    MailboxCredentialCreate,
    MailboxCredentialUpdate,
    AuthType,
)
from src.utils.database import get_db_cursor
from src.utils.encryption import encrypt, decrypt
from typing import Optional

router = APIRouter(prefix="/credentials", tags=["credentials"])


def _serialize_credential(row) -> dict:
    """Serialize credential row to dict (without sensitive decrypted data)"""
    if row is None:
        return None
    return MailboxCredential(
        id=row["id"],
        mailbox_id=str(row["mailbox_id"]),
        auth_type=row["auth_type"],
        username=row["username"],
        smtp_host=row["smtp_host"],
        smtp_port=row["smtp_port"],
        smtp_secure=row["smtp_secure"],
        imap_host=row["imap_host"],
        imap_port=row["imap_port"],
        imap_secure=row["imap_secure"],
        is_active=row["is_active"],
        last_verified_at=row["last_verified_at"],
        expires_at=row["expires_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    ).model_dump(mode="json")


@router.get("")
def get_all_credentials(mailbox_id: Optional[str] = None, is_active: Optional[bool] = None):
    """Get all credentials with optional filters"""
    try:
        with get_db_cursor(commit=False) as cursor:
            query = "SELECT * FROM mailbox_credentials WHERE 1=1"
            params = []

            if mailbox_id:
                query += " AND mailbox_id = %s"
                params.append(mailbox_id)
            if is_active is not None:
                query += " AND is_active = %s"
                params.append(is_active)

            query += " ORDER BY created_at DESC"
            cursor.execute(query, params)
            credentials = cursor.fetchall()
            return APIOutput.success(
                data=[_serialize_credential(row) for row in credentials]
            )
    except Exception as e:
        return APIOutput.failure(message=str(e))


@router.get("/{credential_id}")
def get_credential(credential_id: int):
    """Get a credential by ID"""
    try:
        with get_db_cursor(commit=False) as cursor:
            cursor.execute(
                "SELECT * FROM mailbox_credentials WHERE id = %s", (credential_id,)
            )
            credential = cursor.fetchone()
            if not credential:
                return APIOutput.failure(message="Credential not found", status_code=404)
            return APIOutput.success(data=_serialize_credential(credential))
    except Exception as e:
        return APIOutput.failure(message=str(e))


@router.post("")
def create_credential(credential: MailboxCredentialCreate):
    """Create a new credential with encrypted sensitive fields"""
    try:
        # Encrypt sensitive fields
        password_encrypted = encrypt(credential.password) if credential.password else None
        access_token_encrypted = encrypt(credential.access_token) if credential.access_token else None
        refresh_token_encrypted = encrypt(credential.refresh_token) if credential.refresh_token else None

        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO mailbox_credentials (
                    mailbox_id, auth_type, username,
                    password_encrypted, access_token_encrypted, refresh_token_encrypted,
                    smtp_host, smtp_port, smtp_secure,
                    imap_host, imap_port, imap_secure,
                    is_active
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    credential.mailbox_id,
                    credential.auth_type.value,
                    credential.username,
                    password_encrypted,
                    access_token_encrypted,
                    refresh_token_encrypted,
                    credential.smtp_host,
                    credential.smtp_port,
                    credential.smtp_secure,
                    credential.imap_host,
                    credential.imap_port,
                    credential.imap_secure,
                    credential.is_active,
                ),
            )
            new_credential = cursor.fetchone()
            return APIOutput.success(
                data=_serialize_credential(new_credential),
                message="Credential created",
                status_code=201,
            )
    except Exception as e:
        return APIOutput.failure(message=str(e))


@router.put("/{credential_id}")
def update_credential(credential_id: int, credential: MailboxCredentialUpdate):
    """Update a credential"""
    try:
        with get_db_cursor() as cursor:
            updates = ["updated_at = NOW()"]
            values = []

            if credential.auth_type is not None:
                updates.append("auth_type = %s")
                values.append(credential.auth_type.value)
            if credential.username is not None:
                updates.append("username = %s")
                values.append(credential.username)
            if credential.password is not None:
                updates.append("password_encrypted = %s")
                values.append(encrypt(credential.password))
            if credential.access_token is not None:
                updates.append("access_token_encrypted = %s")
                values.append(encrypt(credential.access_token))
            if credential.refresh_token is not None:
                updates.append("refresh_token_encrypted = %s")
                values.append(encrypt(credential.refresh_token))
            if credential.smtp_host is not None:
                updates.append("smtp_host = %s")
                values.append(credential.smtp_host)
            if credential.smtp_port is not None:
                updates.append("smtp_port = %s")
                values.append(credential.smtp_port)
            if credential.smtp_secure is not None:
                updates.append("smtp_secure = %s")
                values.append(credential.smtp_secure)
            if credential.imap_host is not None:
                updates.append("imap_host = %s")
                values.append(credential.imap_host)
            if credential.imap_port is not None:
                updates.append("imap_port = %s")
                values.append(credential.imap_port)
            if credential.imap_secure is not None:
                updates.append("imap_secure = %s")
                values.append(credential.imap_secure)
            if credential.is_active is not None:
                updates.append("is_active = %s")
                values.append(credential.is_active)

            if len(updates) == 1:  # Only updated_at
                return APIOutput.failure(
                    message="No fields to update", status_code=400
                )

            values.append(credential_id)
            query = f"UPDATE mailbox_credentials SET {', '.join(updates)} WHERE id = %s RETURNING *"
            cursor.execute(query, values)
            updated_credential = cursor.fetchone()

            if not updated_credential:
                return APIOutput.failure(message="Credential not found", status_code=404)
            return APIOutput.success(
                data=_serialize_credential(updated_credential),
                message="Credential updated",
            )
    except Exception as e:
        return APIOutput.failure(message=str(e))


@router.delete("/{credential_id}")
def delete_credential(credential_id: int):
    """Delete a credential"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "DELETE FROM mailbox_credentials WHERE id = %s RETURNING id",
                (credential_id,),
            )
            deleted = cursor.fetchone()
            if not deleted:
                return APIOutput.failure(message="Credential not found", status_code=404)
            return APIOutput.success(message="Credential deleted")
    except Exception as e:
        return APIOutput.failure(message=str(e))
