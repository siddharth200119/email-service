"""
emails
"""

from yoyo import step

__depends__ = {'20260205_01_h519A-mailboxes'}

steps = [
    step(
        """
        CREATE TABLE emails (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            mailbox_id UUID NOT NULL
                REFERENCES mailboxes(id)
                ON DELETE RESTRICT,

            direction VARCHAR(10) NOT NULL DEFAULT 'OUTBOUND',

            from_email TEXT NOT NULL,
            to_email TEXT[] NOT NULL,
            cc_email TEXT[],
            bcc_email TEXT[],

            subject TEXT,
            body_text TEXT,
            body_html TEXT,

            status VARCHAR(20) NOT NULL DEFAULT 'ACKED',

            created_at TIMESTAMP NOT NULL DEFAULT now()
        );
        """,
        "DROP TABLE emails;"
    )
]

