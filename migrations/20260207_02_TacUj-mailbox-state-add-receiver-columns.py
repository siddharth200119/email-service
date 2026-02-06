"""
mailbox_state_add_receiver_columns
"""

from yoyo import step

__depends__ = {'20260207_01_jdI0z-mailbox-state'}

steps = [
    step(
        """
        ALTER TABLE mailbox_state
        ADD COLUMN receiver_worker_id VARCHAR(64),
        ADD COLUMN receiver_claimed_at TIMESTAMP;
        """,
        """
        ALTER TABLE mailbox_state
        DROP COLUMN receiver_worker_id,
        DROP COLUMN receiver_claimed_at;
        """
    )
]
