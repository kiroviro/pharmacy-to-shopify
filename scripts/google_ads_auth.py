#!/usr/bin/env python3
"""Generate a Google Ads API refresh token via OAuth2 flow.

Usage:
    1. Fill in client_id and client_secret in config/google-ads.yaml
    2. Run: python google_ads_auth.py
    3. Open the URL in your browser, authorize, paste the code back
    4. Copy the refresh_token into config/google-ads.yaml
"""

import logging
import os
import sys

# Add project root and scripts dir to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import yaml
from google_ads_auth_flow import get_refresh_token

from src.common.log_config import setup_logging

logger = logging.getLogger(__name__)


def main():
    setup_logging()

    with open("config/google-ads.yaml", "r") as f:
        config = yaml.safe_load(f)

    client_id = config.get("client_id", "")
    client_secret = config.get("client_secret", "")

    if "INSERT_" in client_id or "INSERT_" in client_secret:
        print("ERROR: Please fill in client_id and client_secret in config/google-ads.yaml first.")
        print()
        print("Steps:")
        print("  1. Go to https://console.cloud.google.com")
        print("  2. Select your project")
        print("  3. APIs & Services → Credentials → Create OAuth 2.0 Client ID")
        print("  4. Application type: Desktop app")
        print("  5. Copy Client ID and Client Secret into config/google-ads.yaml")
        return

    refresh_token = get_refresh_token(client_id, client_secret)

    if refresh_token:
        print()
        print("=" * 60)
        print("SUCCESS! Your refresh token:")
        print()
        print(f"  {refresh_token}")
        print()
        print("Paste this into config/google-ads.yaml as refresh_token")
        print("=" * 60)


if __name__ == "__main__":
    main()
