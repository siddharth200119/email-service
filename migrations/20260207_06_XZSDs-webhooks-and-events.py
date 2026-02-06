"""
webhooks_and_events
"""

from yoyo import step

__depends__ = {'20260207_05_4S55o-email-threads-mailbox-subject-index'}

steps = [
    step(
        """
        -- Webhooks table
        CREATE TABLE webhooks (
            id BIGSERIAL PRIMARY KEY,
            owner_type VARCHAR(50) NOT NULL,  -- 'mailbox', 'user', etc.
            owner_id UUID NOT NULL,
            url TEXT NOT NULL,
            secret TEXT NOT NULL,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );

        -- Index for looking up webhooks by owner
        CREATE INDEX idx_webhooks_owner ON webhooks (owner_type, owner_id);

        -- Webhook events table
        CREATE TYPE webhook_event_status AS ENUM ('PENDING', 'PROCESSING', 'DELIVERED', 'FAILED');

        CREATE TABLE webhook_events (
            id BIGSERIAL PRIMARY KEY,
            webhook_id BIGINT NOT NULL REFERENCES webhooks(id) ON DELETE CASCADE,
            event_type VARCHAR(100) NOT NULL,
            payload JSONB NOT NULL,
            status webhook_event_status DEFAULT 'PENDING',
            attempts INTEGER DEFAULT 0,
            next_attempt_at TIMESTAMP DEFAULT NOW(),
            last_attempt_at TIMESTAMP,
            last_error TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );

        -- Index for delivery worker to claim pending events
        CREATE INDEX idx_webhook_events_pending 
        ON webhook_events (status, next_attempt_at) 
        WHERE status = 'PENDING';

        -- Index for webhook_id lookups
        CREATE INDEX idx_webhook_events_webhook_id ON webhook_events (webhook_id);
        """,
        """
        -- Rollback
        DROP INDEX IF EXISTS idx_webhook_events_webhook_id;
        DROP INDEX IF EXISTS idx_webhook_events_pending;
        DROP TABLE IF EXISTS webhook_events;
        DROP TYPE IF EXISTS webhook_event_status;
        DROP INDEX IF EXISTS idx_webhooks_owner;
        DROP TABLE IF EXISTS webhooks;
        """
    )
]
