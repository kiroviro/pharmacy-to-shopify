#!/usr/bin/env python3
"""OAuth2 flow for Google Ads API - generates a refresh token."""

from typing import Optional

from google_auth_oauthlib.flow import InstalledAppFlow

_SCOPE = "https://www.googleapis.com/auth/adwords"


def get_refresh_token(client_id: str, client_secret: str) -> Optional[str]:
    """Run OAuth2 installed app flow and return a refresh token."""
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    flow = InstalledAppFlow.from_client_config(
        client_config, scopes=[_SCOPE]
    )

    # This opens a browser window for auth and starts a local server to catch the redirect
    flow.run_local_server(port=8080)

    return flow.credentials.refresh_token
