"""
mailbox_state
"""

from yoyo import step

__depends__ = {'20260206_02_GCuT3-mailbox-credentials'}

steps = [
    step(
        """
        CREATE TABLE mailbox_state (
            mailbox_id UUID PRIMARY KEY,
            last_uid INTEGER DEFAULT 0,
            last_checked_at TIMESTAMP,
            last_success_at TIMESTAMP,
            error_count INTEGER DEFAULT 0,

            FOREIGN KEY (mailbox_id)
                REFERENCES mailboxes(id)
                ON DELETE CASCADE
        );
        """,
        """
        DROP TABLE mailbox_state;
        """
    )
]
