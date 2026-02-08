FROM python:3.14-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Service type argument (api, email-sender, imap-receiver, webhook-delivery, migrate)
ARG SERVICE_TYPE=api
ENV SERVICE_TYPE=${SERVICE_TYPE}

# Expose port (only used by API)
EXPOSE 3031

# Entry point script
COPY <<'EOF' /entrypoint.sh
#!/bin/sh
set -e

case "$SERVICE_TYPE" in
    api)
        exec uv run gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:3031
        ;;
    email-sender)
        exec uv run python -m src.workers.email_sender
        ;;
    imap-receiver)
        exec uv run python -m src.workers.imap_receiver
        ;;
    webhook-delivery)
        exec uv run python -m src.workers.webhook_delivery
        ;;
    migrate)
        exec uv run yoyo apply --batch -d "postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
        ;;
    *)
        echo "Unknown SERVICE_TYPE: $SERVICE_TYPE"
        exit 1
        ;;
esac
EOF

RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]