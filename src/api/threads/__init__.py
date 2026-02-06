"""Threads API endpoints"""
from fastapi import APIRouter, Query
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

from src.utils.database import get_db_cursor
from src.models import APIOutput

router = APIRouter(prefix="/threads", tags=["Threads"])


class ThreadSummary(BaseModel):
    """Thread summary for list view"""
    id: int
    mailbox_id: UUID
    root_message_id: str
    subject_normalized: Optional[str]
    created_at: Optional[datetime]
    last_activity: Optional[datetime]
    message_count: int


class EmailInThread(BaseModel):
    """Email within a thread"""
    id: UUID
    mailbox_id: UUID
    direction: str
    status: str
    from_email: str
    to_email: Optional[List[str]]
    cc_email: Optional[List[str]]
    subject: Optional[str]
    body_text: Optional[str]
    body_html: Optional[str]
    message_id: Optional[str]
    in_reply_to: Optional[str]
    imap_uid: Optional[int]
    created_at: Optional[datetime]


class ThreadDetail(BaseModel):
    """Thread with all messages"""
    id: int
    mailbox_id: UUID
    root_message_id: str
    subject_normalized: Optional[str]
    created_at: Optional[datetime]
    messages: List[EmailInThread]


@router.get("")
def get_threads(
    mailbox_id: Optional[str] = Query(None, description="Filter by mailbox ID"),
    limit: int = Query(50, ge=1, le=200, description="Max threads to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """Get all threads with summary info (conversation view)"""
    try:
        with get_db_cursor(commit=False) as cursor:
            query = """
                SELECT 
                    t.id,
                    t.mailbox_id,
                    t.root_message_id,
                    t.subject_normalized,
                    t.created_at,
                    MAX(e.created_at) AS last_activity,
                    COUNT(e.id) AS message_count
                FROM email_threads t
                LEFT JOIN emails e ON e.thread_id = t.id
            """
            params = []
            
            if mailbox_id:
                query += " WHERE t.mailbox_id = %s"
                params.append(mailbox_id)
            
            query += """
                GROUP BY t.id
                ORDER BY last_activity DESC NULLS LAST
                LIMIT %s OFFSET %s
            """
            params.extend([limit, offset])
            
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            
            threads = [
                ThreadSummary(
                    id=row["id"],
                    mailbox_id=row["mailbox_id"],
                    root_message_id=row["root_message_id"],
                    subject_normalized=row["subject_normalized"],
                    created_at=row["created_at"],
                    last_activity=row["last_activity"],
                    message_count=row["message_count"] or 0,
                ).model_dump(mode="json")
                for row in rows
            ]
            
            return APIOutput.success(data=threads)
    except Exception as e:
        return APIOutput.failure(message=str(e))


@router.get("/{thread_id}")
def get_thread_by_id(thread_id: int):
    """Get a single thread with all its messages"""
    try:
        with get_db_cursor(commit=False) as cursor:
            # Get thread info
            cursor.execute(
                """
                SELECT id, mailbox_id, root_message_id, subject_normalized, created_at
                FROM email_threads
                WHERE id = %s
                """,
                (thread_id,)
            )
            thread_row = cursor.fetchone()
            
            if not thread_row:
                return APIOutput.failure(message="Thread not found", status_code=404)
            
            # Get all messages in thread
            cursor.execute(
                """
                SELECT 
                    id, mailbox_id, direction, status,
                    from_email, to_email, cc_email, subject,
                    body_text, body_html, message_id, in_reply_to,
                    imap_uid, created_at
                FROM emails
                WHERE thread_id = %s
                ORDER BY created_at ASC
                """,
                (thread_id,)
            )
            email_rows = cursor.fetchall()
            
            messages = [
                EmailInThread(
                    id=row["id"],
                    mailbox_id=row["mailbox_id"],
                    direction=row["direction"],
                    status=row["status"],
                    from_email=row["from_email"],
                    to_email=row["to_email"],
                    cc_email=row["cc_email"],
                    subject=row["subject"],
                    body_text=row["body_text"],
                    body_html=row["body_html"],
                    message_id=row["message_id"],
                    in_reply_to=row["in_reply_to"],
                    imap_uid=row["imap_uid"],
                    created_at=row["created_at"],
                ).model_dump(mode="json")
                for row in email_rows
            ]
            
            thread = ThreadDetail(
                id=thread_row["id"],
                mailbox_id=thread_row["mailbox_id"],
                root_message_id=thread_row["root_message_id"],
                subject_normalized=thread_row["subject_normalized"],
                created_at=thread_row["created_at"],
                messages=messages,
            ).model_dump(mode="json")
            
            return APIOutput.success(data=thread)
    except Exception as e:
        return APIOutput.failure(message=str(e))
