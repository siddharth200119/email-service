import dotenv
dotenv.load_dotenv()

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def created_mailbox(client):
    """Create a mailbox for testing and clean up after"""
    # Use unique email to avoid conflicts
    unique_email = f"test-fixture-{uuid4().hex[:8]}@example.com"
    response = client.post(
        "/api/mailboxes",
        json={"email_address": unique_email, "is_active": True}
    )
    data = response.json()["data"]
    yield data
    # Cleanup
    client.delete(f"/api/mailboxes/{data['id']}")
