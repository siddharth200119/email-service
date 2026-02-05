import pytest


class TestMailboxesCRUD:
    """Test CRUD operations for mailboxes"""

    def test_create_mailbox(self, client):
        """Test creating a new mailbox"""
        response = client.post(
            "/api/mailboxes",
            json={"email_address": "create-test@example.com", "is_active": True}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["status_code"] == 201
        assert data["message"] == "Mailbox created"
        assert data["data"]["email_address"] == "create-test@example.com"
        assert data["data"]["is_active"] is True
        assert "id" in data["data"]
        assert "created_at" in data["data"]
        
        # Cleanup
        client.delete(f"/api/mailboxes/{data['data']['id']}")

    def test_get_all_mailboxes(self, client, created_mailbox):
        """Test getting all mailboxes"""
        response = client.get("/api/mailboxes")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= 1

    def test_get_mailbox_by_id(self, client, created_mailbox):
        """Test getting a mailbox by ID"""
        mailbox_id = created_mailbox["id"]
        response = client.get(f"/api/mailboxes/{mailbox_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == mailbox_id
        assert data["data"]["email_address"] == "test-fixture@example.com"

    def test_get_mailbox_not_found(self, client):
        """Test getting a non-existent mailbox"""
        response = client.get("/api/mailboxes/00000000-0000-0000-0000-000000000000")
        
        assert response.status_code == 404
        assert response.json()["message"] == "Mailbox not found"

    def test_update_mailbox(self, client, created_mailbox):
        """Test updating a mailbox"""
        mailbox_id = created_mailbox["id"]
        response = client.put(
            f"/api/mailboxes/{mailbox_id}",
            json={"is_active": False}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Mailbox updated"
        assert data["data"]["is_active"] is False

    def test_update_mailbox_no_fields(self, client, created_mailbox):
        """Test updating a mailbox with no fields"""
        mailbox_id = created_mailbox["id"]
        response = client.put(
            f"/api/mailboxes/{mailbox_id}",
            json={}
        )
        
        assert response.status_code == 400
        assert "No fields to update" in response.json()["message"]

    def test_delete_mailbox(self, client):
        """Test deleting a mailbox"""
        # Create a mailbox to delete
        create_response = client.post(
            "/api/mailboxes",
            json={"email_address": "delete-test@example.com"}
        )
        mailbox_id = create_response.json()["data"]["id"]
        
        # Delete it
        response = client.delete(f"/api/mailboxes/{mailbox_id}")
        
        assert response.status_code == 200
        assert response.json()["message"] == "Mailbox deleted"
        
        # Verify it's gone
        get_response = client.get(f"/api/mailboxes/{mailbox_id}")
        assert get_response.status_code == 404

    def test_delete_mailbox_not_found(self, client):
        """Test deleting a non-existent mailbox"""
        response = client.delete("/api/mailboxes/00000000-0000-0000-0000-000000000000")
        
        assert response.status_code == 404
