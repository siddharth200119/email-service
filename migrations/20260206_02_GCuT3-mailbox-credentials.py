"""
mailbox_credentials
"""

from yoyo import step

__depends__ = {'20260206_01_FQ3Op-add-processing-started-at'}

steps = [
    step(
        """
        CREATE TABLE mailbox_credentials (
            id BIGSERIAL PRIMARY KEY,

            mailbox_id UUID NOT NULL,
            
            auth_type VARCHAR(20) NOT NULL, 
            -- 'password', 'oauth2', 'app_password'

            username VARCHAR(255) NOT NULL,
            password_encrypted TEXT,
            access_token_encrypted TEXT,
            refresh_token_encrypted TEXT,

            smtp_host VARCHAR(255),
            smtp_port INT,
            smtp_secure BOOLEAN DEFAULT TRUE,

            imap_host VARCHAR(255),
            imap_port INT,
            imap_secure BOOLEAN DEFAULT TRUE,

            is_active BOOLEAN DEFAULT TRUE,

            last_verified_at TIMESTAMP,
            expires_at TIMESTAMP,

            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),

            CONSTRAINT fk_mailbox
                FOREIGN KEY (mailbox_id)
                REFERENCES mailboxes(id)
                ON DELETE CASCADE
        );
        """,
        "DROP TABLE mailbox_credentials;"
    )
]
