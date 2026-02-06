"""
emails_add_imap_uid
"""

from yoyo import step

__depends__ = {'20260207_02_TacUj-mailbox-state-add-receiver-columns'}

steps = [
    step(
        """
        ALTER TABLE emails
        ADD COLUMN IF NOT EXISTS imap_uid INTEGER;

        CREATE UNIQUE INDEX IF NOT EXISTS uniq_mailbox_uid
        ON emails (mailbox_id, imap_uid)
        WHERE imap_uid IS NOT NULL;
        """,
        """
        DROP INDEX IF EXISTS uniq_mailbox_uid;
        ALTER TABLE emails DROP COLUMN IF EXISTS imap_uid;
        """
    )
]
