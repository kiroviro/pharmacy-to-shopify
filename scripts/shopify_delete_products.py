#!/usr/bin/env python3
"""
Shopify Product Bulk Deleter

Deletes all products from a Shopify store using the GraphQL Bulk Operations API.
Products are deleted asynchronously in a single background job on Shopify's side.

Requirements:
    pip install requests

Usage:
    # Dry run — count products, don't delete
    python3 shopify_delete_products.py --shop STORE --token TOKEN --dry-run

    # Delete all products (with confirmation prompt)
    python3 shopify_delete_products.py --shop STORE --token TOKEN
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
import time

import requests

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.common.log_config import setup_logging
from src.shopify import ShopifyAPIClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# GraphQL queries / mutations
# ---------------------------------------------------------------------------

PRODUCTS_QUERY = """
query ($cursor: String) {
  products(first: 250, after: $cursor) {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        id
      }
    }
  }
}
"""

PRODUCT_COUNT_QUERY = """
query {
  productsCount {
    count
  }
}
"""

STAGED_UPLOADS_CREATE = """
mutation {
  stagedUploadsCreate(input: [{
    resource: BULK_MUTATION_VARIABLES,
    filename: "bulk_delete.jsonl",
    mimeType: "text/jsonl",
    httpMethod: POST
  }]) {
    stagedTargets {
      url
      resourceUrl
      parameters {
        name
        value
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""

BULK_MUTATION_RUN = """
mutation bulkOperationRunMutation($mutation: String!, $stagedUploadPath: String!) {
  bulkOperationRunMutation(
    mutation: $mutation,
    stagedUploadPath: $stagedUploadPath
  ) {
    bulkOperation {
      id
      url
      status
    }
    userErrors {
      field
      message
    }
  }
}
"""

BULK_OPERATION_STATUS = """
query {
  currentBulkOperation(type: MUTATION) {
    id
    status
    errorCode
    objectCount
    url
  }
}
"""

PRODUCT_DELETE_MUTATION = """
mutation productDelete($input: ProductDeleteInput!) {
  productDelete(input: $input) {
    deletedProductId
    userErrors {
      field
      message
    }
  }
}
"""


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def get_product_count(client: ShopifyAPIClient) -> int:
    """Get total product count via GraphQL."""
    data = client.graphql_request(PRODUCT_COUNT_QUERY)
    if data and "productsCount" in data:
        return data["productsCount"]["count"]
    return -1


def fetch_all_product_ids(client: ShopifyAPIClient) -> list[str]:
    """Fetch all product GIDs via paginated GraphQL query."""
    product_ids = []
    cursor = None
    page = 0

    while True:
        page += 1
        variables = {"cursor": cursor} if cursor else {}
        data = client.graphql_request(PRODUCTS_QUERY, variables)

        if not data or "products" not in data:
            logger.error("Error fetching products at page %d", page)
            break

        edges = data["products"]["edges"]
        for edge in edges:
            product_ids.append(edge["node"]["id"])

        page_info = data["products"]["pageInfo"]
        if page_info["hasNextPage"]:
            cursor = page_info["endCursor"]
            if page % 10 == 0:
                logger.info("Fetched %d product IDs (%d pages)...", len(product_ids), page)
        else:
            break

    return product_ids


def write_jsonl(product_ids: list[str], path: str) -> None:
    """Write product IDs to a JSONL file for bulk mutation."""
    with open(path, "w") as f:
        for gid in product_ids:
            line = json.dumps({"input": {"id": gid}})
            f.write(line + "\n")


def stage_upload(client: ShopifyAPIClient) -> dict | None:
    """Create a staged upload target and return target info."""
    data = client.graphql_request(STAGED_UPLOADS_CREATE)
    if not data:
        return None

    result = data.get("stagedUploadsCreate", {})
    errors = result.get("userErrors", [])
    if errors:
        logger.error("Staged upload errors: %s", errors)
        return None

    targets = result.get("stagedTargets", [])
    if not targets:
        logger.error("No staged upload targets returned")
        return None

    return targets[0]


def upload_jsonl(target: dict, jsonl_path: str) -> bool:
    """Upload JSONL file to the staged upload URL."""
    url = target["url"]
    params = {p["name"]: p["value"] for p in target["parameters"]}

    with open(jsonl_path, "rb") as f:
        # POST as multipart form data
        files = {"file": ("bulk_delete.jsonl", f, "text/jsonl")}
        response = requests.post(url, data=params, files=files, timeout=60)

    if response.status_code in (200, 201):
        return True

    logger.error("Upload failed: HTTP %d", response.status_code)
    logger.error("Response: %s", response.text[:500])
    return False


def run_bulk_delete(client: ShopifyAPIClient, staged_upload_path: str) -> str | None:
    """Start the bulk delete mutation and return the operation ID."""
    variables = {
        "mutation": PRODUCT_DELETE_MUTATION,
        "stagedUploadPath": staged_upload_path,
    }
    data = client.graphql_request(BULK_MUTATION_RUN, variables)
    if not data:
        return None

    result = data.get("bulkOperationRunMutation", {})
    errors = result.get("userErrors", [])
    if errors:
        logger.error("Bulk operation errors: %s", errors)
        return None

    op = result.get("bulkOperation")
    if not op:
        logger.error("No bulk operation returned")
        return None

    logger.info("Bulk operation started: %s (status: %s)", op['id'], op['status'])
    return op["id"]


def poll_bulk_operation(client: ShopifyAPIClient, poll_interval: int = 10) -> dict | None:
    """Poll the current bulk mutation operation until it completes."""
    while True:
        data = client.graphql_request(BULK_OPERATION_STATUS)
        if not data or "currentBulkOperation" not in data:
            logger.error("Could not fetch bulk operation status")
            return None

        op = data["currentBulkOperation"]
        if op is None:
            logger.error("No active bulk mutation operation found")
            return None

        status = op["status"]
        object_count = op.get("objectCount", "?")
        logger.info("Status: %s | Objects processed: %s", status, object_count)

        if status == "COMPLETED":
            return op
        elif status in ("FAILED", "CANCELED", "EXPIRED"):
            logger.error("Bulk operation ended with status: %s", status)
            if op.get("errorCode"):
                logger.error("Error code: %s", op['errorCode'])
            return op

        time.sleep(poll_interval)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Delete all products from a Shopify store using bulk operations"
    )
    parser.add_argument(
        "--shop", "-s",
        required=True,
        help="Shopify shop name (e.g., 'my-store' or 'my-store.myshopify.com')"
    )
    parser.add_argument(
        "--token", "-t",
        required=True,
        help="Shopify Admin API access token"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count products without deleting"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt"
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=10,
        help="Seconds between status polls (default: 10)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose (debug) logging"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress info messages, show only warnings and errors"
    )

    args = parser.parse_args()
    setup_logging(verbose=args.verbose, quiet=args.quiet)
    client = ShopifyAPIClient(args.shop, args.token)

    # Test connection
    logger.info("Connecting to Shopify...")
    if not client.test_connection():
        logger.error("Failed to connect. Check shop name and token.")
        sys.exit(1)

    # Step 1: Count products
    logger.info("Counting products...")
    count = get_product_count(client)
    logger.info("Total products: %d", count)

    if count == 0:
        print("No products to delete.")
        return

    if args.dry_run:
        print("\n[DRY RUN] Would delete all products. No changes made.")
        return

    # Confirmation prompt
    if not args.yes:
        print(f"\n*** WARNING: This will permanently delete {count} products ***")
        confirm = input(f"Delete {count} products? Type YES to confirm: ")
        if confirm != "YES":
            print("Aborted.")
            return
    else:
        logger.info("Proceeding to delete %d products (--yes flag set)", count)

    # Step 2: Fetch all product IDs
    logger.info("Fetching all product IDs...")
    product_ids = fetch_all_product_ids(client)
    logger.info("Fetched %d product IDs", len(product_ids))

    if not product_ids:
        logger.error("No product IDs fetched. Aborting.")
        return

    # Step 3: Write JSONL file
    jsonl_path = os.path.join(tempfile.gettempdir(), "shopify_bulk_delete.jsonl")
    logger.info("Writing JSONL to %s...", jsonl_path)
    write_jsonl(product_ids, jsonl_path)
    jsonl_size = os.path.getsize(jsonl_path)
    logger.info("Written %d lines (%s bytes)", len(product_ids), f"{jsonl_size:,}")

    # Step 4: Stage upload
    logger.info("Creating staged upload...")
    target = stage_upload(client)
    if not target:
        logger.error("Failed to create staged upload. Aborting.")
        sys.exit(1)
    logger.info("Upload URL obtained")

    # Step 5: Upload JSONL
    logger.info("Uploading JSONL file...")
    if not upload_jsonl(target, jsonl_path):
        logger.error("Failed to upload JSONL. Aborting.")
        sys.exit(1)
    logger.info("Upload complete")

    # Step 6: Start bulk delete
    logger.info("Starting bulk delete operation...")
    # Extract the "key" parameter — this is the staged upload path Shopify expects
    staged_upload_path = next(
        p["value"] for p in target["parameters"] if p["name"] == "key"
    )
    op_id = run_bulk_delete(client, staged_upload_path)
    if not op_id:
        logger.error("Failed to start bulk delete. Aborting.")
        sys.exit(1)

    # Step 7: Poll for completion
    logger.info("Polling for completion (every %ds)...", args.poll_interval)
    result = poll_bulk_operation(client, args.poll_interval)

    if result and result["status"] == "COMPLETED":
        print(f"\nDeletion complete. Objects processed: {result.get('objectCount', '?')}")
    else:
        status = result["status"] if result else "UNKNOWN"
        logger.error("Bulk operation finished with status: %s", status)
        sys.exit(1)

    # Verify
    logger.info("Verifying...")
    remaining = get_product_count(client)
    logger.info("Products remaining: %d", remaining)

    if remaining == 0:
        print("\nAll products deleted successfully.")
    else:
        print(f"\n{remaining} products still remain. You may need to run again.")


if __name__ == "__main__":
    main()
