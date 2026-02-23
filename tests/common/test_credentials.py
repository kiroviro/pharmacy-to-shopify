"""Tests for src/common/credentials.py"""

import json

import pytest

from src.common.credentials import load_shopify_credentials


class TestLoadShopifyCredentials:
    def test_loads_from_env_vars(self, monkeypatch, tmp_path):
        """Returns shop/token directly from SHOPIFY_SHOP_URL and SHOPIFY_ACCESS_TOKEN."""
        monkeypatch.setenv("SHOPIFY_SHOP_URL", "my-store")
        monkeypatch.setenv("SHOPIFY_ACCESS_TOKEN", "shpat_abc123")
        # Point project root to tmp_path so no real token file interferes
        monkeypatch.setattr("src.common.credentials._PROJECT_ROOT", tmp_path)

        shop, token = load_shopify_credentials()

        assert shop == "my-store"
        assert token == "shpat_abc123"

    def test_strips_myshopify_com_suffix(self, monkeypatch, tmp_path):
        """Full .myshopify.com domain is normalized to bare shop name."""
        monkeypatch.setenv("SHOPIFY_SHOP_URL", "my-store.myshopify.com")
        monkeypatch.setenv("SHOPIFY_ACCESS_TOKEN", "shpat_abc123")
        monkeypatch.setattr("src.common.credentials._PROJECT_ROOT", tmp_path)

        shop, token = load_shopify_credentials()

        assert shop == "my-store"

    def test_strips_https_protocol(self, monkeypatch, tmp_path):
        """https://my-store.myshopify.com is normalized to bare shop name."""
        monkeypatch.setenv("SHOPIFY_SHOP_URL", "https://my-store.myshopify.com")
        monkeypatch.setenv("SHOPIFY_ACCESS_TOKEN", "shpat_abc123")
        monkeypatch.setattr("src.common.credentials._PROJECT_ROOT", tmp_path)

        shop, token = load_shopify_credentials()

        assert shop == "my-store"

    def test_falls_back_to_token_file(self, monkeypatch, tmp_path):
        """Reads shop/token from .shopify_token.json when env vars are absent."""
        monkeypatch.delenv("SHOPIFY_SHOP_URL", raising=False)
        monkeypatch.delenv("SHOPIFY_ACCESS_TOKEN", raising=False)
        monkeypatch.setattr("src.common.credentials._PROJECT_ROOT", tmp_path)

        token_file = tmp_path / ".shopify_token.json"
        token_file.write_text(json.dumps({
            "shop": "file-store",
            "access_token": "file_token_xyz",
        }))

        shop, token = load_shopify_credentials()

        assert shop == "file-store"
        assert token == "file_token_xyz"

    def test_env_vars_override_token_file(self, monkeypatch, tmp_path):
        """Env vars take priority over values in .shopify_token.json."""
        monkeypatch.setenv("SHOPIFY_SHOP_URL", "env-store")
        monkeypatch.setenv("SHOPIFY_ACCESS_TOKEN", "env_token")
        monkeypatch.setattr("src.common.credentials._PROJECT_ROOT", tmp_path)

        token_file = tmp_path / ".shopify_token.json"
        token_file.write_text(json.dumps({
            "shop": "file-store",
            "access_token": "file_token",
        }))

        shop, token = load_shopify_credentials()

        assert shop == "env-store"
        assert token == "env_token"

    def test_partial_fallback_env_shop_file_token(self, monkeypatch, tmp_path):
        """Shop from env, token from file when SHOPIFY_ACCESS_TOKEN is absent."""
        monkeypatch.setenv("SHOPIFY_SHOP_URL", "env-store")
        monkeypatch.delenv("SHOPIFY_ACCESS_TOKEN", raising=False)
        monkeypatch.setattr("src.common.credentials._PROJECT_ROOT", tmp_path)

        token_file = tmp_path / ".shopify_token.json"
        token_file.write_text(json.dumps({
            "shop": "file-store",
            "access_token": "file_token",
        }))

        shop, token = load_shopify_credentials()

        assert shop == "env-store"
        assert token == "file_token"

    def test_raises_system_exit_when_no_credentials(self, monkeypatch, tmp_path):
        """SystemExit(1) is raised when neither env vars nor token file exist."""
        monkeypatch.delenv("SHOPIFY_SHOP_URL", raising=False)
        monkeypatch.delenv("SHOPIFY_ACCESS_TOKEN", raising=False)
        monkeypatch.setattr("src.common.credentials._PROJECT_ROOT", tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            load_shopify_credentials()

        assert exc_info.value.code == 1
