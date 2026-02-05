"""Tests for credentials CRUD API"""
import pytest


class TestCredentialsCRUD:
    """Test credentials API endpoints"""

    @pytest.fixture
    def created_credential(self, client, created_mailbox):
        """Create a credential for testing and clean up after"""
        response = client.post(
            "/api/credentials",
            json={
                "mailbox_id": created_mailbox["id"],
                "auth_type": "password",
                "username": "test@example.com",
                "password": "secret123",
                "smtp_host": "smtp.example.com",
                "smtp_port": 587,
                "imap_host": "imap.example.com",
                "imap_port": 993,
            },
        )
        data = response.json()["data"]
        yield data
        # Cleanup
        client.delete(f"/api/credentials/{data['id']}")

    def test_create_credential(self, client, created_mailbox):
        """Test creating a credential with encrypted password"""
        response = client.post(
            "/api/credentials",
            json={
                "mailbox_id": created_mailbox["id"],
                "auth_type": "password",
                "username": "user@example.com",
                "password": "my_secret_password",
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status_code"] == 201
        assert data["message"] == "Credential created"
        assert data["data"]["username"] == "user@example.com"
        assert data["data"]["auth_type"] == "password"
        # Password should NOT be in response (it's stored encrypted)
        assert "password" not in data["data"]
        assert "password_encrypted" not in data["data"]

        # Cleanup
        client.delete(f"/api/credentials/{data['data']['id']}")

    def test_create_credential_oauth2(self, client, created_mailbox):
        """Test creating an OAuth2 credential"""
        response = client.post(
            "/api/credentials",
            json={
                "mailbox_id": created_mailbox["id"],
                "auth_type": "oauth2",
                "username": "oauth@example.com",
                "access_token": "ya29.access_token_here",
                "refresh_token": "1//refresh_token_here",
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["auth_type"] == "oauth2"
        # Tokens should NOT be in response
        assert "access_token" not in data["data"]
        assert "refresh_token" not in data["data"]

        # Cleanup
        client.delete(f"/api/credentials/{data['data']['id']}")

    def test_get_all_credentials(self, client, created_credential):
        """Test getting all credentials"""
        response = client.get("/api/credentials")

        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= 1

    def test_get_credentials_filter_by_mailbox(self, client, created_mailbox, created_credential):
        """Test filtering credentials by mailbox_id"""
        response = client.get(f"/api/credentials?mailbox_id={created_mailbox['id']}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1
        for cred in data["data"]:
            assert cred["mailbox_id"] == created_mailbox["id"]

    def test_get_credentials_filter_by_active(self, client, created_credential):
        """Test filtering credentials by is_active"""
        response = client.get("/api/credentials?is_active=true")

        assert response.status_code == 200
        data = response.json()
        for cred in data["data"]:
            assert cred["is_active"] is True

    def test_get_credential_by_id(self, client, created_credential):
        """Test getting a credential by ID"""
        response = client.get(f"/api/credentials/{created_credential['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == created_credential["id"]
        assert data["data"]["username"] == created_credential["username"]

    def test_get_credential_not_found(self, client):
        """Test getting a non-existent credential"""
        response = client.get("/api/credentials/99999999")

        assert response.status_code == 404
        data = response.json()
        assert data["message"] == "Credential not found"

    def test_update_credential(self, client, created_credential):
        """Test updating a credential"""
        response = client.put(
            f"/api/credentials/{created_credential['id']}",
            json={
                "username": "updated@example.com",
                "smtp_port": 465,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Credential updated"
        assert data["data"]["username"] == "updated@example.com"
        assert data["data"]["smtp_port"] == 465

    def test_update_credential_password(self, client, created_credential):
        """Test updating a credential password (re-encrypts)"""
        response = client.put(
            f"/api/credentials/{created_credential['id']}",
            json={"password": "new_secret_password"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Credential updated"
        # Password should NOT be returned
        assert "password" not in data["data"]

    def test_update_credential_no_fields(self, client, created_credential):
        """Test updating a credential with no fields"""
        response = client.put(
            f"/api/credentials/{created_credential['id']}",
            json={},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["message"] == "No fields to update"

    def test_update_credential_deactivate(self, client, created_credential):
        """Test deactivating a credential"""
        response = client.put(
            f"/api/credentials/{created_credential['id']}",
            json={"is_active": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["is_active"] is False

    def test_delete_credential(self, client, created_mailbox):
        """Test deleting a credential"""
        # Create a credential to delete
        create_response = client.post(
            "/api/credentials",
            json={
                "mailbox_id": created_mailbox["id"],
                "auth_type": "password",
                "username": "delete@example.com",
                "password": "todelete",
            },
        )
        credential_id = create_response.json()["data"]["id"]

        response = client.delete(f"/api/credentials/{credential_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Credential deleted"

        # Verify it's deleted
        get_response = client.get(f"/api/credentials/{credential_id}")
        assert get_response.status_code == 404

    def test_delete_credential_not_found(self, client):
        """Test deleting a non-existent credential"""
        response = client.delete("/api/credentials/99999999")

        assert response.status_code == 404
        data = response.json()
        assert data["message"] == "Credential not found"
