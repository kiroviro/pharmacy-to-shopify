"""
Shopify API Client

Shared client for Shopify Admin API (REST and GraphQL).
Handles authentication, rate limiting, and error handling.
"""

import logging
import time
from typing import Dict, Optional
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)


class ShopifyAPIClient:
    """
    Shared client for Shopify Admin API.

    Handles:
    - Authentication
    - Rate limiting (2 requests/second)
    - Error handling and retries
    - Both REST and GraphQL endpoints

    Usage:
        client = ShopifyAPIClient(shop="my-store", access_token="shpat_xxx")

        # REST request
        result = client.rest_request("GET", "products.json")

        # GraphQL request
        result = client.graphql_request(query, variables)
    """

    API_VERSION = "2025-01"
    MAX_RETRIES = 5
    RETRYABLE_STATUS_CODES = {429, 502, 503, 504}

    def __init__(self, shop: str, access_token: str):
        """
        Initialize the API client.

        Args:
            shop: Shop name (without .myshopify.com) or full domain
            access_token: Shopify Admin API access token
        """
        # Normalize shop name
        if ".myshopify.com" in shop:
            self.shop = shop.replace("https://", "").replace("http://", "").split(".myshopify.com")[0]
        else:
            self.shop = shop

        self.access_token = access_token
        self.base_url = f"https://{self.shop}.myshopify.com/admin/api/{self.API_VERSION}"
        self.graphql_url = f"{self.base_url}/graphql.json"

        self.session = requests.Session()
        self.session.headers.update({
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json",
        })

        # Rate limiting
        self.requests_made = 0
        self.last_request_time = 0.0
        self.min_request_interval = 0.5  # 2 req/sec

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.session.close()

    def close(self):
        self.session.close()

    def _rate_limit(self):
        """Implement rate limiting (2 requests/second max)."""
        now = time.time()
        elapsed = now - self.last_request_time

        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)

        self.last_request_time = time.time()
        self.requests_made += 1

    def rest_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        timeout: int = 30
    ) -> Optional[Dict]:
        """
        Make REST API request with rate limiting and error handling.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., "products.json")
            data: Request body for POST/PUT
            timeout: Request timeout in seconds

        Returns:
            Response JSON or None on error
        """
        url = urljoin(self.base_url + "/", endpoint)

        for attempt in range(self.MAX_RETRIES):
            self._rate_limit()

            try:
                if method == "GET":
                    response = self.session.get(url, timeout=timeout)
                elif method == "POST":
                    response = self.session.post(url, json=data, timeout=timeout)
                elif method == "PUT":
                    response = self.session.put(url, json=data, timeout=timeout)
                elif method == "DELETE":
                    response = self.session.delete(url, timeout=timeout)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                # Retry on rate limiting or server errors
                if response.status_code in self.RETRYABLE_STATUS_CODES:
                    retry_after = int(response.headers.get("Retry-After", 2 ** attempt))
                    logger.warning("HTTP %d on %s, retry %d/%d in %ds...",
                                   response.status_code, endpoint, attempt + 1,
                                   self.MAX_RETRIES, retry_after)
                    time.sleep(retry_after)
                    continue

                # Check for errors
                if response.status_code >= 400:
                    error_msg = response.text[:200]
                    logger.error("API Error %d: %s", response.status_code, error_msg)
                    return None

                return response.json()

            except requests.exceptions.Timeout:
                logger.error("Request timeout: %s", endpoint)
                return None
            except requests.exceptions.RequestException as e:
                logger.error("Request failed: %s", e)
                return None

        logger.error("Max retries (%d) exceeded for %s %s", self.MAX_RETRIES, method, endpoint)
        return None

    def graphql_request(
        self,
        query: str,
        variables: Optional[Dict] = None,
        timeout: int = 30
    ) -> Optional[Dict]:
        """
        Make GraphQL API request with rate limiting and error handling.

        Args:
            query: GraphQL query or mutation
            variables: Query variables
            timeout: Request timeout in seconds

        Returns:
            Response data (without 'data' wrapper) or None on error
        """
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        for attempt in range(self.MAX_RETRIES):
            self._rate_limit()

            try:
                response = self.session.post(
                    self.graphql_url,
                    json=payload,
                    timeout=timeout
                )

                # Retry on rate limiting or server errors
                if response.status_code in self.RETRYABLE_STATUS_CODES:
                    retry_after = int(response.headers.get("Retry-After", 2 ** attempt))
                    logger.warning("HTTP %d on GraphQL, retry %d/%d in %ds...",
                                   response.status_code, attempt + 1,
                                   self.MAX_RETRIES, retry_after)
                    time.sleep(retry_after)
                    continue

                # Check for HTTP errors
                if response.status_code >= 400:
                    logger.error("API Error %d: %s", response.status_code, response.text[:200])
                    return None

                result = response.json()

                # Check for GraphQL errors
                if "errors" in result:
                    logger.error("GraphQL Errors: %s", result['errors'])
                    return None

                return result.get("data")

            except requests.exceptions.Timeout:
                logger.error("GraphQL request timeout")
                return None
            except requests.exceptions.RequestException as e:
                logger.error("Request failed: %s", e)
                return None

        logger.error("Max retries (%d) exceeded for GraphQL request", self.MAX_RETRIES)
        return None

    def test_connection(self) -> bool:
        """
        Test API connection by fetching shop info.

        Returns:
            True if connection successful
        """
        result = self.rest_request("GET", "shop.json")
        if result and "shop" in result:
            shop_name = result["shop"].get("name", "Unknown")
            logger.info("Connected to: %s", shop_name)
            return True
        return False
