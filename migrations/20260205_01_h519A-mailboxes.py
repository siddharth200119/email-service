"""
mailboxes
"""

from yoyo import step

__depends__ = {}

steps = [
    step(
        """
        CREATE TABLE mailboxes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email_address TEXT NOT NULL UNIQUE,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP NOT NULL DEFAULT now()
        );
        """,
        "DROP TABLE mailboxes;"
    )
]

