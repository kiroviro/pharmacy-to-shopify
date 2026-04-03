"""Tests for load_google_ads_config()."""

from __future__ import annotations

import pytest
import yaml

from src.common.google_ads_config import load_google_ads_config


def _write_yaml(path, data: dict) -> str:
    """Write a YAML file and return its path as string."""
    f = path / "google-ads.yaml"
    f.write_text(yaml.dump(data))
    return str(f)


VALID_CONFIG = {
    "developer_token": "abc123",
    "client_id": "id-456",
    "client_secret": "secret-789",
    "refresh_token": "refresh-000",
    "login_customer_id": "123-456-7890",
}


class TestLoadValidConfig:
    def test_returns_dict_with_all_fields(self, tmp_path):
        path = _write_yaml(tmp_path, VALID_CONFIG)
        config = load_google_ads_config(path)
        assert config == VALID_CONFIG

    def test_extra_fields_are_preserved(self, tmp_path):
        data = {**VALID_CONFIG, "extra_key": "extra_value"}
        path = _write_yaml(tmp_path, data)
        config = load_google_ads_config(path)
        assert config["extra_key"] == "extra_value"


class TestMissingFile:
    def test_raises_on_nonexistent_path(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_google_ads_config(str(tmp_path / "nonexistent.yaml"))


class TestMissingRequiredFields:
    @pytest.mark.parametrize("missing_field", [
        "developer_token",
        "client_id",
        "client_secret",
        "refresh_token",
    ])
    def test_raises_when_default_required_field_missing(self, tmp_path, missing_field):
        data = {k: v for k, v in VALID_CONFIG.items() if k != missing_field}
        path = _write_yaml(tmp_path, data)
        with pytest.raises(ValueError, match=missing_field):
            load_google_ads_config(path)


class TestPlaceholderValues:
    @pytest.mark.parametrize("placeholder", [
        "INSERT_YOUR_TOKEN",
        "INSERT_CLIENT_ID_HERE",
        "INSERT_",
    ])
    def test_raises_on_placeholder_value(self, tmp_path, placeholder):
        data = {**VALID_CONFIG, "developer_token": placeholder}
        path = _write_yaml(tmp_path, data)
        with pytest.raises(ValueError, match="developer_token"):
            load_google_ads_config(path)

    def test_placeholder_mid_string_still_raises(self, tmp_path):
        data = {**VALID_CONFIG, "client_id": "prefix_INSERT_suffix"}
        path = _write_yaml(tmp_path, data)
        with pytest.raises(ValueError, match="client_id"):
            load_google_ads_config(path)


class TestNoneAndEmptyValues:
    def test_raises_on_none_value(self, tmp_path):
        data = {**VALID_CONFIG, "developer_token": None}
        path = _write_yaml(tmp_path, data)
        with pytest.raises(ValueError, match="developer_token"):
            load_google_ads_config(path)

    def test_raises_on_empty_string(self, tmp_path):
        data = {**VALID_CONFIG, "client_secret": ""}
        path = _write_yaml(tmp_path, data)
        with pytest.raises(ValueError, match="client_secret"):
            load_google_ads_config(path)

    def test_raises_on_zero_value(self, tmp_path):
        """0 is falsy, so it should be rejected as an empty value."""
        data = {**VALID_CONFIG, "refresh_token": 0}
        path = _write_yaml(tmp_path, data)
        with pytest.raises(ValueError, match="refresh_token"):
            load_google_ads_config(path)


class TestCustomRequiredFields:
    def test_custom_required_fields_override_defaults(self, tmp_path):
        data = {"my_field": "my_value"}
        path = _write_yaml(tmp_path, data)
        # Should NOT raise — default fields are absent but not checked
        config = load_google_ads_config(path, required_fields=["my_field"])
        assert config["my_field"] == "my_value"

    def test_custom_required_field_missing_raises(self, tmp_path):
        data = {"other_field": "value"}
        path = _write_yaml(tmp_path, data)
        with pytest.raises(ValueError, match="my_field"):
            load_google_ads_config(path, required_fields=["my_field"])

    def test_empty_required_fields_skips_validation(self, tmp_path):
        data = {"anything": "works"}
        path = _write_yaml(tmp_path, data)
        config = load_google_ads_config(path, required_fields=[])
        assert config["anything"] == "works"
