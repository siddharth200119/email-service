from fastapi import FastAPI
from src.api import main_router as APIRouter
from src.middlewares.logger import LoggingMiddleware
import os
from src.events import startup, shutdown
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

DESCRIPTION = """
## Email Service API

A complete email service for sending and receiving emails via SMTP/IMAP with webhooks support.

### Features
- 📬 **Mailboxes**: Manage email accounts
- 🔑 **Credentials**: Store SMTP/IMAP credentials securely (encrypted)
- 📧 **Emails**: Send and receive emails
- 🧵 **Threads**: View email conversations grouped by thread
- 🔔 **Webhooks**: Get notified when emails are sent/received

---

### Getting Started

1. **Create a mailbox**:
   ```
   POST /api/mailboxes
   {"email_address": "your@email.com", "is_active": true}
   ```

2. **Add credentials** (for Gmail, use an App Password):
   ```
   POST /api/credentials
   {
     "mailbox_id": "<mailbox_id>",
     "auth_type": "app_password",
     "username": "your@gmail.com",
     "password": "your-app-password",
     "smtp_host": "smtp.gmail.com", "smtp_port": 587,
     "imap_host": "imap.gmail.com", "imap_port": 993
   }
   ```

3. **Send an email**:
   ```
   POST /api/emails
   {
     "mailbox_id": "<mailbox_id>",
     "from_email": "your@email.com",
     "to_email": ["recipient@example.com"],
     "subject": "Hello",
     "body_text": "Hello World!"
   }
   ```

4. **Run the workers** to send/receive:
   ```bash
   uv run python -m src.workers.email_sender   # Send pending emails
   uv run python -m src.workers.imap_receiver  # Receive emails via IMAP
   uv run python -m src.workers.webhook_delivery  # Deliver webhooks
   ```

---

### Webhooks

Register a webhook to receive notifications when events occur:

1. **Create a webhook**:
   ```
   POST /api/webhooks
   {
     "owner_type": "mailbox",
     "owner_id": "<mailbox_id>",
     "url": "https://your-server.com/webhook"
   }
   ```
   
   Response includes a `secret` (shown only once) - store it securely!

2. **Webhook payload** (sent to your URL):
   ```json
   {
     "event_type": "email.received",
     "payload": {
       "email_id": "...",
       "thread_id": 123,
       "from_email": "sender@example.com",
       "subject": "Hello"
     },
     "timestamp": 1707123456.789
   }
   ```

3. **Verify webhook signature**:
   ```python
   import hmac, hashlib
   signature = request.headers["X-Webhook-Signature"]
   expected = "sha256=" + hmac.new(
       secret.encode(), request.body, hashlib.sha256
   ).hexdigest()
   assert hmac.compare_digest(signature, expected)
   ```

**Event types**: `email.received`, `email.sent`, `email.failed`

---

### Workers
| Worker | Command | Description |
|--------|---------|-------------|
| Email Sender | `python -m src.workers.email_sender` | Sends queued emails via SMTP |
| IMAP Receiver | `python -m src.workers.imap_receiver` | Fetches emails via IMAP |
| Webhook Delivery | `python -m src.workers.webhook_delivery` | Delivers webhook events |
"""

app = FastAPI(
    title="Email Service",
    description=DESCRIPTION,
    version="1.0.0",
    contact={
        "name": "Email Service",
    },
    license_info={
        "name": "MIT",
    },
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup(app)
    try:
        yield
    finally:
        await shutdown(app)


app.add_middleware(LoggingMiddleware)

app.include_router(APIRouter)

if __name__ == "__main__":
    import uvicorn

    DEFAULT_PORT = "3030"
    try:
        port = int(os.environ.get("PORT", DEFAULT_PORT))
    except Exception:
        port = int(DEFAULT_PORT)

    uvicorn.run(
        "main:app",
        port=port,
        host=os.environ.get("HOST", "127.0.0.1"),
        reload=os.environ.get("ENV", "DEV") == "DEV",
    )
