import pytest


class TestEmailsCRUD:
    """Test CRUD operations for emails"""

    def test_create_email_returns_acknowledged(self, client, created_mailbox):
        """Test creating an email returns 202 Accepted with ACKED status"""
        response = client.post(
            "/api/emails",
            json={
                "mailbox_id": created_mailbox["id"],
                "from_email": "sender@example.com",
                "to_email": ["recipient@example.com"],
                "subject": "Test Subject",
                "body_text": "Test body"
            }
        )
        
        assert response.status_code == 202
        data = response.json()
        assert data["status_code"] == 202
        assert data["message"] == "Email acknowledged"
        assert data["data"]["status"] == "ACKED"
        assert data["data"]["direction"] == "OUTBOUND"
        assert "id" in data["data"]
        
        # Cleanup
        client.delete(f"/api/emails/{data['data']['id']}")

    def test_create_email_with_cc_bcc(self, client, created_mailbox):
        """Test creating an email with CC and BCC"""
        response = client.post(
            "/api/emails",
            json={
                "mailbox_id": created_mailbox["id"],
                "from_email": "sender@example.com",
                "to_email": ["recipient@example.com"],
                "cc_email": ["cc@example.com"],
                "bcc_email": ["bcc@example.com"],
                "subject": "Test with CC/BCC"
            }
        )
        
        assert response.status_code == 202
        data = response.json()["data"]
        assert data["cc_email"] == ["cc@example.com"]
        assert data["bcc_email"] == ["bcc@example.com"]
        
        # Cleanup
        client.delete(f"/api/emails/{data['id']}")

    def test_get_all_emails(self, client, created_mailbox):
        """Test getting all emails"""
        # Create an email first
        create_response = client.post(
            "/api/emails",
            json={
                "mailbox_id": created_mailbox["id"],
                "from_email": "sender@example.com",
                "to_email": ["recipient@example.com"]
            }
        )
        email_id = create_response.json()["data"]["id"]
        
        response = client.get("/api/emails")
        
        assert response.status_code == 200
        assert isinstance(response.json()["data"], list)
        
        # Cleanup
        client.delete(f"/api/emails/{email_id}")

    def test_get_emails_filter_by_mailbox(self, client, created_mailbox):
        """Test filtering emails by mailbox_id"""
        # Create an email
        create_response = client.post(
            "/api/emails",
            json={
                "mailbox_id": created_mailbox["id"],
                "from_email": "sender@example.com",
                "to_email": ["recipient@example.com"]
            }
        )
        email_id = create_response.json()["data"]["id"]
        
        response = client.get(f"/api/emails?mailbox_id={created_mailbox['id']}")
        
        assert response.status_code == 200
        emails = response.json()["data"]
        assert all(e["mailbox_id"] == created_mailbox["id"] for e in emails)
        
        # Cleanup
        client.delete(f"/api/emails/{email_id}")

    def test_get_emails_filter_by_status(self, client, created_mailbox):
        """Test filtering emails by status"""
        # Create an email
        create_response = client.post(
            "/api/emails",
            json={
                "mailbox_id": created_mailbox["id"],
                "from_email": "sender@example.com",
                "to_email": ["recipient@example.com"]
            }
        )
        email_id = create_response.json()["data"]["id"]
        
        response = client.get("/api/emails?status=ACKED")
        
        assert response.status_code == 200
        emails = response.json()["data"]
        assert all(e["status"] == "ACKED" for e in emails)
        
        # Cleanup
        client.delete(f"/api/emails/{email_id}")

    def test_get_email_by_id(self, client, created_mailbox):
        """Test getting an email by ID"""
        # Create an email
        create_response = client.post(
            "/api/emails",
            json={
                "mailbox_id": created_mailbox["id"],
                "from_email": "sender@example.com",
                "to_email": ["recipient@example.com"],
                "subject": "Get by ID test"
            }
        )
        email_id = create_response.json()["data"]["id"]
        
        response = client.get(f"/api/emails/{email_id}")
        
        assert response.status_code == 200
        assert response.json()["data"]["id"] == email_id
        assert response.json()["data"]["subject"] == "Get by ID test"
        
        # Cleanup
        client.delete(f"/api/emails/{email_id}")

    def test_get_email_not_found(self, client):
        """Test getting a non-existent email"""
        response = client.get("/api/emails/00000000-0000-0000-0000-000000000000")
        
        assert response.status_code == 404
        assert response.json()["message"] == "Email not found"

    def test_update_email_status(self, client, created_mailbox):
        """Test updating an email status"""
        # Create an email
        create_response = client.post(
            "/api/emails",
            json={
                "mailbox_id": created_mailbox["id"],
                "from_email": "sender@example.com",
                "to_email": ["recipient@example.com"]
            }
        )
        email_id = create_response.json()["data"]["id"]
        
        response = client.put(
            f"/api/emails/{email_id}",
            json={"status": "SENT"}
        )
        
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "SENT"
        
        # Cleanup
        client.delete(f"/api/emails/{email_id}")

    def test_update_email_no_fields(self, client, created_mailbox):
        """Test updating an email with no fields"""
        # Create an email
        create_response = client.post(
            "/api/emails",
            json={
                "mailbox_id": created_mailbox["id"],
                "from_email": "sender@example.com",
                "to_email": ["recipient@example.com"]
            }
        )
        email_id = create_response.json()["data"]["id"]
        
        response = client.put(f"/api/emails/{email_id}", json={})
        
        assert response.status_code == 400
        assert "No fields to update" in response.json()["message"]
        
        # Cleanup
        client.delete(f"/api/emails/{email_id}")

    def test_delete_email(self, client, created_mailbox):
        """Test deleting an email"""
        # Create an email
        create_response = client.post(
            "/api/emails",
            json={
                "mailbox_id": created_mailbox["id"],
                "from_email": "sender@example.com",
                "to_email": ["recipient@example.com"]
            }
        )
        email_id = create_response.json()["data"]["id"]
        
        response = client.delete(f"/api/emails/{email_id}")
        
        assert response.status_code == 200
        assert response.json()["message"] == "Email deleted"
        
        # Verify it's gone
        get_response = client.get(f"/api/emails/{email_id}")
        assert get_response.status_code == 404

    def test_delete_email_not_found(self, client):
        """Test deleting a non-existent email"""
        response = client.delete("/api/emails/00000000-0000-0000-0000-000000000000")
        
        assert response.status_code == 404
