"""
one_active_credential_constraint
"""

from yoyo import step

__depends__ = {'20260206_02_GCuT3-mailbox-credentials'}

steps = [
    step(
        """
        CREATE UNIQUE INDEX one_active_credential_per_mailbox
        ON mailbox_credentials (mailbox_id)
        WHERE is_active = true;
        """,
        "DROP INDEX one_active_credential_per_mailbox;"
    )
]
