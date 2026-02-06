"""
Webhook Delivery Worker - Delivers webhook events via HTTP.
"""
import dotenv
dotenv.load_dotenv()

import os
import signal
import socket
import time
import hmac
import hashlib
import json
import httpx
from typing import Optional, Dict, Any

from src.utils import logger
from src.utils.database import get_db_cursor


# Worker configuration
WORKER_ID = f"webhook-{socket.gethostname()}-{os.getpid()}"
POLL_INTERVAL_SECONDS = int(os.getenv("WEBHOOK_POLL_INTERVAL", "5"))
DELIVERY_TIMEOUT_SECONDS = int(os.getenv("WEBHOOK_TIMEOUT", "5"))
MAX_ATTEMPTS = int(os.getenv("WEBHOOK_MAX_ATTEMPTS", "5"))
RETRY_DELAY_MINUTES = int(os.getenv("WEBHOOK_RETRY_DELAY", "5"))

# Graceful shutdown flag
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def claim_pending_event() -> Optional[Dict[str, Any]]:
    """
    Claim a single pending webhook event for delivery.
    Uses FOR UPDATE SKIP LOCKED to prevent double delivery.
    """
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """
                UPDATE webhook_events
                SET status = 'PROCESSING'
                WHERE id = (
                    SELECT id
                    FROM webhook_events
                    WHERE status = 'PENDING'
                      AND next_attempt_at <= NOW()
                    ORDER BY next_attempt_at
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                RETURNING id, webhook_id, event_type, payload, attempts
                """
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    except Exception as e:
        logger.error(f"Error claiming event: {e}")
        return None


def get_webhook_config(webhook_id: int) -> Optional[Dict[str, Any]]:
    """Get webhook URL and secret."""
    try:
        with get_db_cursor(commit=False) as cursor:
            cursor.execute(
                "SELECT id, url, secret, is_active FROM webhooks WHERE id = %s",
                (webhook_id,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    except Exception as e:
        logger.error(f"Error getting webhook config: {e}")
        return None


def generate_signature(secret: str, payload: str) -> str:
    """Generate HMAC-SHA256 signature for the payload."""
    signature = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


def deliver_webhook(event: Dict[str, Any]) -> bool:
    """
    Deliver a webhook event via HTTP POST.
    
    Returns True if delivered successfully, False otherwise.
    """
    event_id = event["id"]
    webhook_id = event["webhook_id"]
    attempts = event["attempts"]
    
    # Get webhook config
    webhook = get_webhook_config(webhook_id)
    if not webhook:
        logger.error(f"Webhook {webhook_id} not found for event {event_id}")
        mark_event_failed(event_id, "Webhook not found")
        return False
    
    if not webhook["is_active"]:
        logger.warning(f"Webhook {webhook_id} is inactive, marking event failed")
        mark_event_failed(event_id, "Webhook inactive")
        return False
    
    url = webhook["url"]
    secret = webhook["secret"]
    
    # Prepare payload
    payload_dict = event["payload"]
    if isinstance(payload_dict, str):
        payload_dict = json.loads(payload_dict)
    
    # Add event metadata
    body = {
        "event_type": event["event_type"],
        "payload": payload_dict,
        "timestamp": time.time(),
    }
    body_json = json.dumps(body)
    
    # Generate signature
    signature = generate_signature(secret, body_json)
    
    # Prepare headers
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
        "X-Webhook-Event": event["event_type"],
    }
    
    logger.info(f"Delivering event {event_id} to {url}")
    
    try:
        with httpx.Client(timeout=DELIVERY_TIMEOUT_SECONDS) as client:
            response = client.post(url, content=body_json, headers=headers)
        
        if 200 <= response.status_code < 300:
            logger.info(f"Event {event_id} delivered successfully (status {response.status_code})")
            mark_event_delivered(event_id)
            return True
        else:
            error = f"HTTP {response.status_code}: {response.text[:200]}"
            logger.warning(f"Event {event_id} delivery failed: {error}")
            handle_delivery_failure(event_id, webhook_id, attempts, error)
            return False
            
    except httpx.TimeoutException:
        error = "Request timeout"
        logger.warning(f"Event {event_id} delivery timeout")
        handle_delivery_failure(event_id, webhook_id, attempts, error)
        return False
    except Exception as e:
        error = str(e)
        logger.error(f"Event {event_id} delivery error: {error}")
        handle_delivery_failure(event_id, webhook_id, attempts, error)
        return False


def mark_event_delivered(event_id: int):
    """Mark an event as successfully delivered."""
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """
                UPDATE webhook_events
                SET status = 'DELIVERED', last_attempt_at = NOW()
                WHERE id = %s
                """,
                (event_id,)
            )
    except Exception as e:
        logger.error(f"Error marking event delivered: {e}")


def mark_event_failed(event_id: int, error: str):
    """Mark an event as permanently failed."""
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """
                UPDATE webhook_events
                SET status = 'FAILED', last_attempt_at = NOW(), last_error = %s
                WHERE id = %s
                """,
                (error, event_id)
            )
    except Exception as e:
        logger.error(f"Error marking event failed: {e}")


def handle_delivery_failure(event_id: int, webhook_id: int, attempts: int, error: str):
    """
    Handle a delivery failure - either retry or fail permanently.
    """
    new_attempts = attempts + 1
    
    if new_attempts >= MAX_ATTEMPTS:
        # Max attempts reached - fail permanently and deactivate webhook
        logger.warning(f"Event {event_id} failed after {new_attempts} attempts")
        mark_event_failed(event_id, error)
        
        # Deactivate the webhook
        try:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute(
                    "UPDATE webhooks SET is_active = false, updated_at = NOW() WHERE id = %s",
                    (webhook_id,)
                )
                logger.warning(f"Webhook {webhook_id} deactivated after {MAX_ATTEMPTS} failures")
        except Exception as e:
            logger.error(f"Error deactivating webhook: {e}")
    else:
        # Schedule retry
        try:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute(
                    """
                    UPDATE webhook_events
                    SET 
                        status = 'PENDING',
                        attempts = %s,
                        next_attempt_at = NOW() + INTERVAL '%s minutes',
                        last_attempt_at = NOW(),
                        last_error = %s
                    WHERE id = %s
                    """,
                    (new_attempts, RETRY_DELAY_MINUTES, error, event_id)
                )
                logger.info(f"Event {event_id} scheduled for retry (attempt {new_attempts}/{MAX_ATTEMPTS})")
        except Exception as e:
            logger.error(f"Error scheduling retry: {e}")


def main():
    global shutdown_requested
    
    logger.info(f"Webhook Delivery Worker started (worker_id={WORKER_ID})")
    logger.info(f"Config: poll_interval={POLL_INTERVAL_SECONDS}s, timeout={DELIVERY_TIMEOUT_SECONDS}s, max_attempts={MAX_ATTEMPTS}")
    
    try:
        while not shutdown_requested:
            # Claim and deliver events
            event = claim_pending_event()
            
            if event:
                deliver_webhook(event)
            else:
                # No events to process, wait before polling again
                time.sleep(POLL_INTERVAL_SECONDS)
    
    finally:
        logger.info("Webhook Delivery Worker stopped")


if __name__ == "__main__":
    main()
