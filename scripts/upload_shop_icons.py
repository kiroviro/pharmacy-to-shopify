#!/usr/bin/env python3
"""
Upload SVG icon files to Shopify Files (shop_images) via the GraphQL Admin API.

Replaces the trust-section icons with clean Apple-style versions.

Usage:
    python scripts/upload_shop_icons.py
"""

import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.common.credentials import load_shopify_credentials
from src.shopify.api_client import ShopifyAPIClient

THEME_DIR = Path(__file__).parent.parent.parent / "viapharma.us-theme"

ICONS = [
    ("icon-original-medicines.svg", THEME_DIR / "assets/icon-trust-shield.svg"),
    ("icon-support.svg",            THEME_DIR / "assets/icon-trust-headset.svg"),
    ("icon-fast-delivery.svg",      THEME_DIR / "assets/icon-trust-truck.svg"),
    ("icon-affordable-healthcare.svg", THEME_DIR / "assets/icon-trust-heart.svg"),
]

# ── GraphQL helpers ───────────────────────────────────────────────────────────

def stage_upload(client: ShopifyAPIClient, filename: str, file_size: int) -> dict:
    """Request a staged upload target from Shopify."""
    mutation = """
    mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
      stagedUploadsCreate(input: $input) {
        stagedTargets {
          url
          resourceUrl
          parameters { name value }
        }
        userErrors { field message }
      }
    }
    """
    variables = {
        "input": [{
            "filename": filename,
            "mimeType": "image/svg+xml",
            "httpMethod": "POST",
            "resource": "FILE",
            "fileSize": str(file_size),
        }]
    }
    data = client.graphql_request(mutation, variables)
    if data is None:
        raise RuntimeError("GraphQL request failed for stagedUploadsCreate")
    errors = data["stagedUploadsCreate"]["userErrors"]
    if errors:
        raise RuntimeError(f"Stage upload errors: {errors}")
    return data["stagedUploadsCreate"]["stagedTargets"][0]


def upload_to_stage(target: dict, content: bytes, filename: str) -> None:
    """POST the file to the Shopify-provided signed URL."""
    params = {p["name"]: p["value"] for p in target["parameters"]}
    files = {"file": (filename, content, "image/svg+xml")}
    resp = requests.post(target["url"], data=params, files=files, timeout=30)
    if resp.status_code not in (200, 201, 204):
        raise RuntimeError(f"Stage upload POST failed: {resp.status_code} {resp.text[:200]}")


def create_file(client: ShopifyAPIClient, resource_url: str, filename: str) -> str:
    """Tell Shopify to create the file from the staged upload."""
    mutation = """
    mutation fileCreate($files: [FileCreateInput!]!) {
      fileCreate(files: $files) {
        files { ... on MediaImage { id } ... on GenericFile { id url } }
        userErrors { field message }
      }
    }
    """
    variables = {
        "files": [{
            "originalSource": resource_url,
            "filename": filename,
            "contentType": "IMAGE",
        }]
    }
    data = client.graphql_request(mutation, variables)
    if data is None:
        raise RuntimeError("GraphQL request failed for fileCreate")
    errors = data["fileCreate"]["userErrors"]
    if errors:
        raise RuntimeError(f"fileCreate errors: {errors}")
    files = data["fileCreate"]["files"]
    return files[0].get("id", "") if files else ""


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    shop, token = load_shopify_credentials()
    client = ShopifyAPIClient(shop, token)

    print(f"Uploading icons to {shop}.myshopify.com\n")

    for shopify_name, local_path in ICONS:
        if not local_path.exists():
            print(f"  [skip] {shopify_name} — source not found: {local_path}")
            continue

        content = local_path.read_bytes()
        print(f"  Uploading {shopify_name} ({len(content)} bytes) …", end=" ", flush=True)

        target = stage_upload(client, shopify_name, len(content))
        upload_to_stage(target, content, shopify_name)
        file_id = create_file(client, target["resourceUrl"], shopify_name)
        print(f"ok  (id: {file_id})")

    print("\nDone. Allow ~30 s for Shopify to process and serve the new files.")


if __name__ == "__main__":
    main()
