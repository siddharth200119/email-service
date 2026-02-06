"""
Webhook event emission utility.

Usage:
    from src.utils.webhooks import emit_event
    
    emit_event(
        event_type="email.received",
        owner_type="mailbox",
        owner_id="uuid-here",
        payload={"email_id": "...", "subject": "..."}
    )
"""
import json
from typing import Any, Dict, Optional
from src.utils.database import get_db_cursor
from src.utils import logger


def emit_event(
    event_type: str,
    owner_type: str,
    owner_id: str,
    payload: Dict[str, Any],
    cursor=None,
) -> int:
    """
    Emit a webhook event.
    
    This creates webhook_events for all active webhooks matching the owner.
    No HTTP calls are made - delivery is handled by the webhook worker.
    
    Args:
        event_type: Type of event (e.g., "email.received", "email.sent")
        owner_type: Owner type (e.g., "mailbox")
        owner_id: Owner ID (UUID as string)
        payload: Event payload (will be JSON serialized)
        cursor: Optional existing cursor (for transactional consistency)
    
    Returns:
        Number of webhook events created
    """
    def _emit(cur):
        # Fan-out: Insert one event per matching webhook
        cur.execute(
            """
            INSERT INTO webhook_events (webhook_id, event_type, payload)
            SELECT id, %s, %s
            FROM webhooks
            WHERE owner_type = %s
              AND owner_id = %s
              AND is_active = true
            RETURNING id
            """,
            (event_type, json.dumps(payload), owner_type, owner_id)
        )
        rows = cur.fetchall()
        count = len(rows)
        
        if count > 0:
            logger.debug(f"Emitted {count} webhook event(s) for {event_type}")
        
        return count
    
    try:
        if cursor:
            # Use existing cursor (transactional)
            return _emit(cursor)
        else:
            # Create new cursor
            with get_db_cursor(commit=True) as cur:
                return _emit(cur)
    except Exception as e:
        logger.error(f"Error emitting webhook event: {e}")
        return 0


# Event type constants
class EventTypes:
    """Standard webhook event types"""
    # Email events
    EMAIL_RECEIVED = "email.received"
    EMAIL_SENT = "email.sent"
    EMAIL_FAILED = "email.failed"
    EMAIL_QUEUED = "email.queued"
    
    # Thread events
    THREAD_CREATED = "thread.created"
    
    # Mailbox events
    MAILBOX_CREATED = "mailbox.created"
    MAILBOX_DELETED = "mailbox.deleted"
