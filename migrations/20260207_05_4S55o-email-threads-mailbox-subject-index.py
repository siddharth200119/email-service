"""
email_threads_mailbox_subject_index
"""

from yoyo import step

__depends__ = {'20260207_04_R3Pvk-email-threads-and-threading-columns'}

steps = [
    step(
        """
        CREATE INDEX idx_threads_mailbox_subject
        ON email_threads (mailbox_id, subject_normalized);
        """,
        """
        DROP INDEX IF EXISTS idx_threads_mailbox_subject;
        """
    )
]
