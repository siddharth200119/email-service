import dotenv
dotenv.load_dotenv()

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def created_mailbox(client):
    """Create a mailbox for testing and clean up after"""
    response = client.post(
        "/api/mailboxes",
        json={"email_address": "test-fixture@example.com", "is_active": True}
    )
    data = response.json()["data"]
    yield data
    # Cleanup
    client.delete(f"/api/mailboxes/{data['id']}")
