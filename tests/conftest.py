"""
Test fixtures and configuration.

Uses transaction-based isolation: each test runs in a transaction
that is rolled back after the test, ensuring no test pollution.
"""
import dotenv
dotenv.load_dotenv()

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from unittest.mock import patch

from main import app
from src.utils.database import get_db_config, LoggingCursor


# Global connection for the test session
_test_connection = None
_test_savepoint_counter = 0


def get_test_connection():
    """Get or create a persistent test connection."""
    global _test_connection
    if _test_connection is None or _test_connection.closed:
        config = get_db_config()
        _test_connection = psycopg2.connect(**config)
        _test_connection.autocommit = False
    return _test_connection


@contextmanager
def get_test_db_cursor(commit=True):
    """
    Test version of get_db_cursor that uses savepoints for isolation.
    This allows nested transactions that can be rolled back independently.
    """
    global _test_savepoint_counter
    conn = get_test_connection()
    
    savepoint_name = f"test_savepoint_{_test_savepoint_counter}"
    _test_savepoint_counter += 1
    
    raw_cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor = LoggingCursor(raw_cursor)
    
    try:
        # Create a savepoint (nested transaction)
        raw_cursor.execute(f"SAVEPOINT {savepoint_name}")
        yield cursor
        # If commit requested, release savepoint (keep changes within test)
        if commit:
            raw_cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
    except Exception as e:
        # Rollback to savepoint on error
        raw_cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
        raise
    finally:
        cursor.close()


@pytest.fixture(scope="function", autouse=True)
def db_transaction():
    """
    Wrap each test in a transaction that gets rolled back.
    This ensures complete isolation between tests.
    """
    conn = get_test_connection()
    cursor = conn.cursor()
    
    # Start a new savepoint for this test
    cursor.execute("SAVEPOINT test_isolation")
    
    yield
    
    # Rollback everything done in this test
    cursor.execute("ROLLBACK TO SAVEPOINT test_isolation")
    cursor.close()


@pytest.fixture(scope="function")
def client(db_transaction):
    """
    Test client with database transaction isolation.
    All database operations will be rolled back after the test.
    """
    # Patch get_db_cursor to use our test version
    with patch("src.utils.database.get_db_cursor", get_test_db_cursor):
        with patch("src.api.mailboxes.get_db_cursor", get_test_db_cursor):
            with patch("src.api.emails.get_db_cursor", get_test_db_cursor):
                with patch("src.api.threads.get_db_cursor", get_test_db_cursor):
                    with patch("src.api.webhooks.get_db_cursor", get_test_db_cursor):
                        with patch("src.api.credentials.get_db_cursor", get_test_db_cursor):
                            yield TestClient(app)


@pytest.fixture(scope="function")
def created_mailbox(client):
    """
    Create a mailbox for testing.
    Will be automatically rolled back after test due to db_transaction.
    """
    unique_email = f"test-fixture-{uuid4().hex[:8]}@example.com"
    response = client.post(
        "/api/mailboxes",
        json={"email_address": unique_email, "is_active": True}
    )
    data = response.json()["data"]
    yield data
    # No explicit cleanup needed - transaction rollback handles it


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_connection():
    """Clean up the test connection at the end of the session."""
    yield
    global _test_connection
    if _test_connection and not _test_connection.closed:
        _test_connection.rollback()
        _test_connection.close()
