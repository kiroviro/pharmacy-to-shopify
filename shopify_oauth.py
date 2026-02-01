#!/usr/bin/env python3
"""
Shopify OAuth Authentication

Gets an Admin API access token using OAuth flow with Client ID and Secret.

Usage:
    python3 shopify_oauth.py --shop YOUR_SHOP --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET
"""

import argparse
import http.server
import json
import os
import secrets
import socketserver
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path

import requests


# Token storage file
TOKEN_FILE = Path(__file__).parent / ".shopify_token.json"


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    """Handle OAuth callback from Shopify."""

    authorization_code = None
    state_received = None

    def do_GET(self):
        """Handle GET request (OAuth callback)."""
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if 'code' in params:
            OAuthCallbackHandler.authorization_code = params['code'][0]
            OAuthCallbackHandler.state_received = params.get('state', [None])[0]

            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"""
                <html>
                <head><title>Authorization Successful</title></head>
                <body style="font-family: Arial, sans-serif; text-align: center; padding-top: 50px;">
                    <h1 style="color: green;">Authorization Successful!</h1>
                    <p>You can close this window and return to the terminal.</p>
                </body>
                </html>
            """)
        else:
            error = params.get('error', ['Unknown error'])[0]
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(f"""
                <html>
                <head><title>Authorization Failed</title></head>
                <body style="font-family: Arial, sans-serif; text-align: center; padding-top: 50px;">
                    <h1 style="color: red;">Authorization Failed</h1>
                    <p>Error: {error}</p>
                </body>
                </html>
            """.encode())

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def get_authorization_url(shop: str, client_id: str, redirect_uri: str, state: str) -> str:
    """Build Shopify authorization URL."""
    scopes = "read_products,write_products,read_product_listings,write_product_listings,read_themes,write_themes,read_online_store_navigation,write_online_store_navigation"

    params = {
        "client_id": client_id,
        "scope": scopes,
        "redirect_uri": redirect_uri,
        "state": state,
    }

    base_url = f"https://{shop}.myshopify.com/admin/oauth/authorize"
    return f"{base_url}?{urllib.parse.urlencode(params)}"


def exchange_code_for_token(shop: str, client_id: str, client_secret: str, code: str) -> dict:
    """Exchange authorization code for access token."""
    url = f"https://{shop}.myshopify.com/admin/oauth/access_token"

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
    }

    response = requests.post(url, json=data)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Token exchange failed: {response.status_code} - {response.text}")


def save_token(shop: str, token_data: dict):
    """Save token to file."""
    data = {
        "shop": shop,
        "access_token": token_data.get("access_token"),
        "scope": token_data.get("scope"),
    }

    with open(TOKEN_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nToken saved to: {TOKEN_FILE}")


def load_token() -> dict:
    """Load token from file."""
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    return {}


def test_token(shop: str, access_token: str) -> bool:
    """Test if token works by fetching shop info."""
    url = f"https://{shop}.myshopify.com/admin/api/2024-01/shop.json"
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        shop_data = response.json().get("shop", {})
        print(f"\n✓ Connected to: {shop_data.get('name', 'Unknown')}")
        print(f"  Shop email: {shop_data.get('email', 'N/A')}")
        print(f"  Plan: {shop_data.get('plan_name', 'N/A')}")
        return True
    else:
        print(f"\n✗ Token test failed: {response.status_code}")
        return False


def run_oauth_flow(shop: str, client_id: str, client_secret: str, port: int = 8888, skip_prompt: bool = False) -> str:
    """Run the complete OAuth flow."""

    redirect_uri = f"http://localhost:{port}/callback"
    state = secrets.token_urlsafe(16)

    print("\n" + "=" * 60)
    print("Shopify OAuth Authentication")
    print("=" * 60)
    print(f"\nShop: {shop}")
    print(f"Redirect URI: {redirect_uri}")

    # Important: User needs to add redirect URI to Shopify app
    print("\n" + "-" * 60)
    print("IMPORTANT: Before continuing, add this redirect URI to your app:")
    print(f"\n  {redirect_uri}")
    print("\nSteps:")
    print("  1. Go to Settings → Apps and sales channels → Develop apps")
    print("  2. Click on your app")
    print("  3. Go to 'Configuration' tab")
    print("  4. Under 'URLs', add the redirect URI above to 'Allowed redirection URL(s)'")
    print("  5. Save the configuration")
    print("-" * 60)

    if not skip_prompt:
        input("\nPress Enter when you've added the redirect URI...")

    # Start local server
    print(f"\nStarting local server on port {port}...")

    server = socketserver.TCPServer(("", port), OAuthCallbackHandler)
    server_thread = threading.Thread(target=server.handle_request)
    server_thread.start()

    # Open browser for authorization
    auth_url = get_authorization_url(shop, client_id, redirect_uri, state)
    print(f"\nOpening browser for authorization...")
    print(f"If browser doesn't open, visit:\n{auth_url}\n")

    webbrowser.open(auth_url)

    # Wait for callback
    print("Waiting for authorization...")
    server_thread.join(timeout=300)  # 5 minute timeout
    server.server_close()

    # Check result
    if not OAuthCallbackHandler.authorization_code:
        raise Exception("No authorization code received. Did you authorize the app?")

    if OAuthCallbackHandler.state_received != state:
        raise Exception("State mismatch - possible CSRF attack")

    print("\n✓ Authorization code received!")

    # Exchange code for token
    print("Exchanging code for access token...")
    token_data = exchange_code_for_token(
        shop, client_id, client_secret,
        OAuthCallbackHandler.authorization_code
    )

    access_token = token_data.get("access_token")
    print(f"\n✓ Access token obtained!")
    print(f"  Token: {access_token[:10]}...{access_token[-4:]}")
    print(f"  Scope: {token_data.get('scope', 'N/A')}")

    # Save token
    save_token(shop, token_data)

    # Test token
    test_token(shop, access_token)

    return access_token


def main():
    parser = argparse.ArgumentParser(description="Shopify OAuth Authentication")

    parser.add_argument(
        "--shop", "-s",
        required=True,
        help="Shopify shop name (e.g., 'my-store' without .myshopify.com)"
    )
    parser.add_argument(
        "--client-id", "-i",
        required=True,
        help="App Client ID (API Key)"
    )
    parser.add_argument(
        "--client-secret", "-c",
        required=True,
        help="App Client Secret"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8888,
        help="Local port for OAuth callback (default: 8888)"
    )
    parser.add_argument(
        "--test-only",
        action="store_true",
        help="Only test existing saved token"
    )
    parser.add_argument(
        "--skip-prompt",
        action="store_true",
        help="Skip the confirmation prompt (for non-interactive use)"
    )

    args = parser.parse_args()

    if args.test_only:
        # Just test existing token
        token_data = load_token()
        if token_data:
            test_token(token_data.get("shop"), token_data.get("access_token"))
        else:
            print("No saved token found.")
        return

    try:
        access_token = run_oauth_flow(
            args.shop,
            args.client_id,
            args.client_secret,
            args.port,
            args.skip_prompt
        )

        print("\n" + "=" * 60)
        print("SUCCESS! You can now run the collection creator:")
        print("=" * 60)
        print(f"\npython3 create_shopify_collections.py \\")
        print(f"  --csv data/benu.bg/raw/products.csv \\")
        print(f"  --shop {args.shop} \\")
        print(f"  --token {access_token[:15]}... \\")
        print(f"  --dry-run")
        print("\n" + "=" * 60)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
