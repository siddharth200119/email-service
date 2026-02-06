"""
email_threads_and_threading_columns
"""

from yoyo import step

__depends__ = {'20260207_03_57e4Q-emails-add-imap-uid'}

steps = [
    step(
        """
        -- Create email_threads table
        CREATE TABLE email_threads (
            id BIGSERIAL PRIMARY KEY,
            mailbox_id UUID NOT NULL,
            root_message_id TEXT NOT NULL,
            subject_normalized TEXT,
            created_at TIMESTAMP DEFAULT NOW(),

            FOREIGN KEY (mailbox_id)
                REFERENCES mailboxes(id)
                ON DELETE CASCADE
        );

        -- Add threading columns to emails
        ALTER TABLE emails
        ADD COLUMN message_id TEXT,
        ADD COLUMN in_reply_to TEXT,
        ADD COLUMN "references" TEXT[],
        ADD COLUMN thread_id BIGINT;

        -- Create index for message_id lookups
        CREATE INDEX idx_emails_message_id ON emails (message_id);

        -- Create index for thread lookups
        CREATE INDEX idx_emails_thread_id ON emails (thread_id);
        """,
        """
        -- Rollback
        DROP INDEX IF EXISTS idx_emails_thread_id;
        DROP INDEX IF EXISTS idx_emails_message_id;
        ALTER TABLE emails
        DROP COLUMN IF EXISTS thread_id,
        DROP COLUMN IF EXISTS "references",
        DROP COLUMN IF EXISTS in_reply_to,
        DROP COLUMN IF EXISTS message_id;
        DROP TABLE IF EXISTS email_threads;
        """
    )
]
