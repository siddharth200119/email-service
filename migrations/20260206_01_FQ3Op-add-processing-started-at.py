"""
add_processing_started_at
"""

from yoyo import step

__depends__ = {'20260205_02_WBRpG-emails'}

steps = [
    step(
        """
        ALTER TABLE emails 
        ADD COLUMN processing_started_at TIMESTAMP;
        """,
        """
        ALTER TABLE emails 
        DROP COLUMN processing_started_at;
        """
    )
]
