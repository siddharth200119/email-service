# Email Service

A complete email service for sending and receiving emails via SMTP/IMAP with webhooks support.

## Features

- 📬 **Mailboxes** - Manage email accounts
- 🔑 **Credentials** - Store SMTP/IMAP credentials securely (encrypted)
- 📧 **Emails** - Send and receive emails
- 🧵 **Threads** - View email conversations grouped by thread
- 🔔 **Webhooks** - Get notified when emails are sent/received

## Quick Start

### 1. Setup

```bash
# Install dependencies
uv sync

# Setup environment
cp .env.example .env
# Edit .env with your database credentials

# Run migrations
make migrate-apply
```

### 2. Start the Server

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 3031 --reload
```

### 3. API Documentation

Visit http://localhost:3031/docs for interactive API documentation.

## API Endpoints

### Mailboxes
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/mailboxes` | Create a mailbox |
| GET | `/api/mailboxes` | List mailboxes |
| GET | `/api/mailboxes/{id}` | Get mailbox |
| PUT | `/api/mailboxes/{id}` | Update mailbox |
| DELETE | `/api/mailboxes/{id}` | Delete mailbox |

### Credentials
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/credentials` | Add credentials |
| GET | `/api/credentials` | List credentials |
| PUT | `/api/credentials/{id}` | Update credentials |
| DELETE | `/api/credentials/{id}` | Delete credentials |

### Emails
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/emails` | Queue email for sending |
| GET | `/api/emails` | List emails |
| GET | `/api/emails/{id}` | Get email |

### Threads
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/threads` | List threads |
| GET | `/api/threads/{id}` | Get thread with messages |

### Webhooks
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/webhooks` | Create webhook |
| GET | `/api/webhooks` | List webhooks |
| GET | `/api/webhooks/{id}` | Get webhook |
| PUT | `/api/webhooks/{id}` | Update webhook |
| DELETE | `/api/webhooks/{id}` | Delete webhook |
| POST | `/api/webhooks/{id}/regenerate-secret` | Regenerate secret |

## Workers

| Worker | Command | Description |
|--------|---------|-------------|
| Email Sender | `uv run python -m src.workers.email_sender` | Sends queued emails via SMTP |
| IMAP Receiver | `uv run python -m src.workers.imap_receiver` | Fetches emails via IMAP |
| Webhook Delivery | `uv run python -m src.workers.webhook_delivery` | Delivers webhook events |

## Webhooks

### Creating a Webhook

```bash
curl -X POST http://localhost:3031/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "owner_type": "mailbox",
    "owner_id": "<mailbox_id>",
    "url": "https://your-server.com/webhook"
  }'
```

**Response** (secret shown only once):
```json
{
  "data": {
    "id": 1,
    "secret": "your-secret-here",
    "url": "https://your-server.com/webhook"
  }
}
```

### Webhook Payload

Your webhook URL will receive POST requests:

```json
{
  "event_type": "email.received",
  "payload": {
    "email_id": "uuid",
    "thread_id": 123,
    "from_email": "sender@example.com",
    "to_email": ["recipient@example.com"],
    "subject": "Hello"
  },
  "timestamp": 1707123456.789
}
```

### Verifying Webhook Signatures

```python
import hmac
import hashlib

signature = request.headers["X-Webhook-Signature"]
expected = "sha256=" + hmac.new(
    secret.encode(),
    request.body,
    hashlib.sha256
).hexdigest()

if hmac.compare_digest(signature, expected):
    # Signature valid
    pass
```

### Event Types

| Event | Description |
|-------|-------------|
| `email.received` | Email received via IMAP |
| `email.sent` | Email sent successfully via SMTP |
| `email.failed` | Email failed to send |

## Gmail Setup

For Gmail, you need an **App Password**:

1. Enable 2-Factor Authentication on your Google account
2. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
3. Generate a new app password for "Mail"
4. Use this password in your credentials

```bash
curl -X POST http://localhost:3031/api/credentials \
  -H "Content-Type: application/json" \
  -d '{
    "mailbox_id": "<mailbox_id>",
    "auth_type": "app_password",
    "username": "your@gmail.com",
    "password": "your-16-char-app-password",
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "imap_host": "imap.gmail.com",
    "imap_port": 993
  }'
```

## Testing

```bash
uv run pytest tests/ -v
```

## License

MIT
