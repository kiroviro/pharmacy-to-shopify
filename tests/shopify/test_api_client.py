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


class TestPaginateRest:
    def test_single_page(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "orders": [{"id": 1}, {"id": 2}]
        }

        with patch.object(client.session, "get", return_value=mock_response):
            result = client.paginate_rest("orders.json?status=any", "orders")

        assert result == [{"id": 1}, {"id": 2}]

    def test_multi_page(self, client):
        page1 = MagicMock()
        page1.status_code = 200
        page1.json.return_value = {"items": [{"id": i} for i in range(250)]}

        page2 = MagicMock()
        page2.status_code = 200
        page2.json.return_value = {"items": [{"id": 300}, {"id": 301}]}

        with patch.object(client.session, "get", side_effect=[page1, page2]):
            result = client.paginate_rest("items.json", "items")

        assert len(result) == 252
        assert result[0]["id"] == 0
        assert result[-1]["id"] == 301

    def test_empty_response(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"orders": []}

        with patch.object(client.session, "get", return_value=mock_response):
            result = client.paginate_rest("orders.json", "orders")

        assert result == []

    def test_none_response(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.headers = {"Retry-After": "0"}

        with patch.object(client.session, "get", return_value=mock_response):
            result = client.paginate_rest("orders.json", "orders")

        assert result == []

    def test_endpoint_without_query_params(self, client):
        """Endpoint without ? gets ?limit=250 appended."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"collections": [{"id": 1}]}

        with patch.object(client.session, "get", return_value=mock_response) as mock_get:
            client.paginate_rest("smart_collections.json", "collections")

        called_url = mock_get.call_args[0][0]
        assert "?limit=250" in called_url

    def test_endpoint_with_query_params(self, client):
        """Endpoint with ? gets &limit=250 appended."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"orders": [{"id": 1}]}

        with patch.object(client.session, "get", return_value=mock_response) as mock_get:
            client.paginate_rest("orders.json?status=any", "orders")

        called_url = mock_get.call_args[0][0]
        assert "&limit=250" in called_url
        assert "status=any" in called_url


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
