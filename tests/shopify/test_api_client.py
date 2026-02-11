"""Tests for src/shopify/api_client.py"""

from unittest.mock import MagicMock, patch

import pytest

from src.shopify.api_client import ShopifyAPIClient


@pytest.fixture
def client():
    """Create a client with rate limiting disabled for fast tests."""
    c = ShopifyAPIClient(shop="test-store", access_token="shpat_test")
    c.min_request_interval = 0  # Disable rate limiting in tests
    return c


class TestInit:
    def test_normalizes_shop_name(self):
        c = ShopifyAPIClient(shop="test-store", access_token="tok")
        assert c.shop == "test-store"

    def test_normalizes_full_domain(self):
        c = ShopifyAPIClient(shop="test-store.myshopify.com", access_token="tok")
        assert c.shop == "test-store"

    def test_normalizes_full_url(self):
        c = ShopifyAPIClient(shop="https://test-store.myshopify.com", access_token="tok")
        assert c.shop == "test-store"

    def test_base_url(self, client):
        assert "test-store.myshopify.com" in client.base_url
        assert client.API_VERSION in client.base_url

    def test_session_headers(self, client):
        assert client.session.headers["X-Shopify-Access-Token"] == "shpat_test"


class TestRestRequest:
    def test_successful_get(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"shop": {"name": "Test"}}

        with patch.object(client.session, "get", return_value=mock_response):
            result = client.rest_request("GET", "shop.json")

        assert result == {"shop": {"name": "Test"}}

    def test_successful_post(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"smart_collection": {"id": 123}}

        with patch.object(client.session, "post", return_value=mock_response):
            result = client.rest_request("POST", "smart_collections.json", {"data": "test"})

        assert result == {"smart_collection": {"id": 123}}

    def test_returns_none_on_400(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        with patch.object(client.session, "get", return_value=mock_response):
            result = client.rest_request("GET", "nonexistent.json")

        assert result is None

    def test_returns_none_on_timeout(self, client):
        import requests

        with patch.object(client.session, "get", side_effect=requests.exceptions.Timeout):
            result = client.rest_request("GET", "shop.json")

        assert result is None

    def test_unsupported_method_raises(self, client):
        with pytest.raises(ValueError, match="Unsupported method"):
            client.rest_request("PATCH", "shop.json")

    def test_retries_on_429(self, client):
        rate_limited = MagicMock()
        rate_limited.status_code = 429
        rate_limited.headers = {"Retry-After": "0"}

        success = MagicMock()
        success.status_code = 200
        success.json.return_value = {"ok": True}

        with patch.object(client.session, "get", side_effect=[rate_limited, success]):
            result = client.rest_request("GET", "shop.json")

        assert result == {"ok": True}

    def test_retries_on_502(self, client):
        server_error = MagicMock()
        server_error.status_code = 502
        server_error.headers = {}

        success = MagicMock()
        success.status_code = 200
        success.json.return_value = {"ok": True}

        with patch.object(client.session, "get", side_effect=[server_error, success]):
            result = client.rest_request("GET", "shop.json")

        assert result == {"ok": True}

    def test_max_retries_exceeded(self, client):
        error_response = MagicMock()
        error_response.status_code = 503
        error_response.headers = {"Retry-After": "0"}

        with patch.object(client.session, "get", return_value=error_response):
            result = client.rest_request("GET", "shop.json")

        assert result is None


class TestGraphqlRequest:
    def test_successful_query(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"shop": {"name": "Test"}}}

        with patch.object(client.session, "post", return_value=mock_response):
            result = client.graphql_request("{ shop { name } }")

        assert result == {"shop": {"name": "Test"}}

    def test_returns_none_on_graphql_errors(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errors": [{"message": "bad query"}]}

        with patch.object(client.session, "post", return_value=mock_response):
            result = client.graphql_request("{ invalid }")

        assert result is None

    def test_retries_on_429(self, client):
        rate_limited = MagicMock()
        rate_limited.status_code = 429
        rate_limited.headers = {"Retry-After": "0"}

        success = MagicMock()
        success.status_code = 200
        success.json.return_value = {"data": {"ok": True}}

        with patch.object(client.session, "post", side_effect=[rate_limited, success]):
            result = client.graphql_request("{ ok }")

        assert result == {"ok": True}

    def test_max_retries_exceeded(self, client):
        error_response = MagicMock()
        error_response.status_code = 504
        error_response.headers = {"Retry-After": "0"}

        with patch.object(client.session, "post", return_value=error_response):
            result = client.graphql_request("{ shop { name } }")

        assert result is None


class TestTestConnection:
    def test_success(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"shop": {"name": "Test Store"}}

        with patch.object(client.session, "get", return_value=mock_response):
            assert client.test_connection() is True

    def test_failure(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch.object(client.session, "get", return_value=mock_response):
            assert client.test_connection() is False
