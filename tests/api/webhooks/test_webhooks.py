"""Tests for webhooks API and utilities"""
import pytest
from unittest.mock import patch, MagicMock


class TestWebhooksAPI:
    """Test webhook CRUD operations"""

    def test_create_webhook(self, client, created_mailbox):
        """Test creating a new webhook"""
        response = client.post(
            "/api/webhooks",
            json={
                "owner_type": "mailbox",
                "owner_id": created_mailbox["id"],
                "url": "https://example.com/webhook",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["status_code"] == 201
        assert "secret" in data["data"]
        assert data["data"]["url"] == "https://example.com/webhook"
        
        # Cleanup
        webhook_id = data["data"]["id"]
        client.delete(f"/api/webhooks/{webhook_id}")

    def test_list_webhooks(self, client, created_mailbox):
        """Test listing webhooks"""
        # Create a webhook
        create_response = client.post(
            "/api/webhooks",
            json={
                "owner_type": "mailbox",
                "owner_id": created_mailbox["id"],
                "url": "https://example.com/hook",
            },
        )
        webhook_id = create_response.json()["data"]["id"]
        
        # List webhooks
        response = client.get("/api/webhooks")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)
        
        # Cleanup
        client.delete(f"/api/webhooks/{webhook_id}")

    def test_get_webhook_by_id(self, client, created_mailbox):
        """Test getting a webhook by ID"""
        # Create
        create_response = client.post(
            "/api/webhooks",
            json={
                "owner_type": "mailbox",
                "owner_id": created_mailbox["id"],
                "url": "https://example.com/hook",
            },
        )
        webhook_id = create_response.json()["data"]["id"]
        
        # Get
        response = client.get(f"/api/webhooks/{webhook_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == webhook_id
        # Secret should NOT be included
        assert "secret" not in data["data"]
        
        # Cleanup
        client.delete(f"/api/webhooks/{webhook_id}")

    def test_update_webhook(self, client, created_mailbox):
        """Test updating a webhook"""
        # Create
        create_response = client.post(
            "/api/webhooks",
            json={
                "owner_type": "mailbox",
                "owner_id": created_mailbox["id"],
                "url": "https://example.com/hook",
            },
        )
        webhook_id = create_response.json()["data"]["id"]
        
        # Update
        response = client.put(
            f"/api/webhooks/{webhook_id}",
            json={"is_active": False},
        )
        assert response.status_code == 200
        
        # Verify
        get_response = client.get(f"/api/webhooks/{webhook_id}")
        assert get_response.json()["data"]["is_active"] is False
        
        # Cleanup
        client.delete(f"/api/webhooks/{webhook_id}")

    def test_delete_webhook(self, client, created_mailbox):
        """Test deleting a webhook"""
        # Create
        create_response = client.post(
            "/api/webhooks",
            json={
                "owner_type": "mailbox",
                "owner_id": created_mailbox["id"],
                "url": "https://example.com/hook",
            },
        )
        webhook_id = create_response.json()["data"]["id"]
        
        # Delete
        response = client.delete(f"/api/webhooks/{webhook_id}")
        assert response.status_code == 200
        
        # Verify deleted
        get_response = client.get(f"/api/webhooks/{webhook_id}")
        assert get_response.json()["status_code"] == 404

    def test_regenerate_secret(self, client, created_mailbox):
        """Test regenerating webhook secret"""
        # Create
        create_response = client.post(
            "/api/webhooks",
            json={
                "owner_type": "mailbox",
                "owner_id": created_mailbox["id"],
                "url": "https://example.com/hook",
            },
        )
        webhook_id = create_response.json()["data"]["id"]
        original_secret = create_response.json()["data"]["secret"]
        
        # Regenerate
        response = client.post(f"/api/webhooks/{webhook_id}/regenerate-secret")
        assert response.status_code == 200
        new_secret = response.json()["data"]["secret"]
        
        # Verify secret changed
        assert new_secret != original_secret
        
        # Cleanup
        client.delete(f"/api/webhooks/{webhook_id}")


class TestWebhookEmit:
    """Test webhook event emission"""

    def test_emit_event_no_webhooks(self, client, created_mailbox):
        """Test emitting event when no webhooks exist"""
        from src.utils.webhooks import emit_event, EventTypes
        
        # Should not error even with no webhooks
        count = emit_event(
            event_type=EventTypes.EMAIL_RECEIVED,
            owner_type="mailbox",
            owner_id=created_mailbox["id"],
            payload={"test": "data"},
        )
        
        assert count == 0  # No webhooks to emit to

    def test_emit_event_with_webhook(self, client, created_mailbox):
        """Test emitting event creates webhook_events"""
        from src.utils.webhooks import emit_event, EventTypes
        from src.utils.database import get_db_cursor
        
        # Create webhook
        create_response = client.post(
            "/api/webhooks",
            json={
                "owner_type": "mailbox",
                "owner_id": created_mailbox["id"],
                "url": "https://example.com/hook",
            },
        )
        webhook_id = create_response.json()["data"]["id"]
        
        # Emit event
        count = emit_event(
            event_type=EventTypes.EMAIL_RECEIVED,
            owner_type="mailbox",
            owner_id=created_mailbox["id"],
            payload={"email_id": "123", "subject": "Test"},
        )
        
        assert count == 1
        
        # Verify webhook_events was created
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                "SELECT * FROM webhook_events WHERE webhook_id = %s",
                (webhook_id,)
            )
            events = cursor.fetchall()
            assert len(events) >= 1
            
            # Cleanup
            cursor.execute("DELETE FROM webhook_events WHERE webhook_id = %s", (webhook_id,))
        
        client.delete(f"/api/webhooks/{webhook_id}")


class TestWebhookDelivery:
    """Test webhook delivery worker functions"""

    def test_generate_signature(self):
        """Test HMAC signature generation"""
        from src.workers.webhook_delivery import generate_signature
        
        signature = generate_signature("secret123", '{"test": "data"}')
        
        assert signature.startswith("sha256=")
        assert len(signature) > 10

    @patch("src.workers.webhook_delivery.httpx.Client")
    def test_deliver_webhook_success(self, mock_client_class, client, created_mailbox):
        """Test successful webhook delivery"""
        from src.workers.webhook_delivery import deliver_webhook, claim_pending_event
        from src.utils.webhooks import emit_event, EventTypes
        from src.utils.database import get_db_cursor
        
        # Create webhook
        create_response = client.post(
            "/api/webhooks",
            json={
                "owner_type": "mailbox",
                "owner_id": created_mailbox["id"],
                "url": "https://example.com/hook",
            },
        )
        webhook_id = create_response.json()["data"]["id"]
        
        # Emit event
        emit_event(
            event_type=EventTypes.EMAIL_SENT,
            owner_type="mailbox",
            owner_id=created_mailbox["id"],
            payload={"email_id": "456"},
        )
        
        # Claim the event
        event = claim_pending_event()
        assert event is not None
        
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Deliver
        result = deliver_webhook(event)
        assert result is True
        
        # Cleanup
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM webhook_events WHERE webhook_id = %s", (webhook_id,))
        client.delete(f"/api/webhooks/{webhook_id}")
