"""Shared Google Ads configuration loading and client creation."""

import logging

import yaml
from google.ads.googleads.client import GoogleAdsClient

logger = logging.getLogger(__name__)


def load_google_ads_config(config_path: str = "config/google-ads.yaml", required_fields: list = None) -> dict:
    """Load and validate Google Ads config from YAML file.

    Args:
        config_path: Path to the YAML config file.
        required_fields: List of field names that must be present and filled in.

    Returns:
        Validated config dictionary.

    Raises:
        ValueError: If a required field is missing or contains a placeholder.
    """
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    if required_fields is None:
        required_fields = ["developer_token", "client_id", "client_secret", "refresh_token"]

    for key in required_fields:
        val = config.get(key, "")
        if not val or "INSERT_" in str(val):
            raise ValueError(f"Please fill in '{key}' in {config_path}")

    return config


def get_google_ads_client(config: dict) -> GoogleAdsClient:
    """Create a GoogleAdsClient from config dictionary.

    Args:
        config: Config dict with developer_token, client_id, client_secret, refresh_token,
                and optionally login_customer_id.

    Returns:
        Configured GoogleAdsClient instance.
    """
    client_config = {
        "developer_token": config["developer_token"],
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "refresh_token": config["refresh_token"],
        "use_proto_plus": True,
    }
    if config.get("login_customer_id"):
        client_config["login_customer_id"] = str(config["login_customer_id"])

    return GoogleAdsClient.load_from_dict(client_config)
