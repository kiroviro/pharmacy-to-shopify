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

import argparse
import json
import os
import sys
import tempfile
import time

import requests

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from src.shopify import ShopifyAPIClient


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
            print(f"  Error fetching products at page {page}")
            break

        edges = data["products"]["edges"]
        for edge in edges:
            product_ids.append(edge["node"]["id"])

        page_info = data["products"]["pageInfo"]
        if page_info["hasNextPage"]:
            cursor = page_info["endCursor"]
            if page % 10 == 0:
                print(f"  Fetched {len(product_ids)} product IDs ({page} pages)...")
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
        print(f"  Staged upload errors: {errors}")
        return None

    targets = result.get("stagedTargets", [])
    if not targets:
        print("  No staged upload targets returned")
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
    else:
        print(f"  Upload failed: HTTP {response.status_code}")
        print(f"  Response: {response.text[:500]}")
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
        print(f"  Bulk operation errors: {errors}")
        return None

    op = result.get("bulkOperation")
    if not op:
        print("  No bulk operation returned")
        return None

    print(f"  Bulk operation started: {op['id']} (status: {op['status']})")
    return op["id"]


def poll_bulk_operation(client: ShopifyAPIClient, poll_interval: int = 10) -> dict | None:
    """Poll the current bulk mutation operation until it completes."""
    while True:
        data = client.graphql_request(BULK_OPERATION_STATUS)
        if not data or "currentBulkOperation" not in data:
            print("  Could not fetch bulk operation status")
            return None

        op = data["currentBulkOperation"]
        if op is None:
            print("  No active bulk mutation operation found")
            return None

        status = op["status"]
        object_count = op.get("objectCount", "?")
        print(f"  Status: {status} | Objects processed: {object_count}")

        if status == "COMPLETED":
            return op
        elif status in ("FAILED", "CANCELED", "EXPIRED"):
            print(f"  Bulk operation ended with status: {status}")
            if op.get("errorCode"):
                print(f"  Error code: {op['errorCode']}")
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

    args = parser.parse_args()
    client = ShopifyAPIClient(args.shop, args.token)

    # Test connection
    print("Connecting to Shopify...")
    if not client.test_connection():
        print("Failed to connect. Check shop name and token.")
        sys.exit(1)

    # Step 1: Count products
    print("\nCounting products...")
    count = get_product_count(client)
    print(f"  Total products: {count}")

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
        print(f"\nProceeding to delete {count} products (--yes flag set)")

    # Step 2: Fetch all product IDs
    print("\nFetching all product IDs...")
    product_ids = fetch_all_product_ids(client)
    print(f"  Fetched {len(product_ids)} product IDs")

    if not product_ids:
        print("No product IDs fetched. Aborting.")
        return

    # Step 3: Write JSONL file
    jsonl_path = os.path.join(tempfile.gettempdir(), "shopify_bulk_delete.jsonl")
    print(f"\nWriting JSONL to {jsonl_path}...")
    write_jsonl(product_ids, jsonl_path)
    jsonl_size = os.path.getsize(jsonl_path)
    print(f"  Written {len(product_ids)} lines ({jsonl_size:,} bytes)")

    # Step 4: Stage upload
    print("\nCreating staged upload...")
    target = stage_upload(client)
    if not target:
        print("Failed to create staged upload. Aborting.")
        sys.exit(1)
    print(f"  Upload URL obtained")

    # Step 5: Upload JSONL
    print("\nUploading JSONL file...")
    if not upload_jsonl(target, jsonl_path):
        print("Failed to upload JSONL. Aborting.")
        sys.exit(1)
    print("  Upload complete")

    # Step 6: Start bulk delete
    print("\nStarting bulk delete operation...")
    # Extract the "key" parameter — this is the staged upload path Shopify expects
    staged_upload_path = next(
        p["value"] for p in target["parameters"] if p["name"] == "key"
    )
    op_id = run_bulk_delete(client, staged_upload_path)
    if not op_id:
        print("Failed to start bulk delete. Aborting.")
        sys.exit(1)

    # Step 7: Poll for completion
    print(f"\nPolling for completion (every {args.poll_interval}s)...")
    result = poll_bulk_operation(client, args.poll_interval)

    if result and result["status"] == "COMPLETED":
        print(f"\nDeletion complete. Objects processed: {result.get('objectCount', '?')}")
    else:
        status = result["status"] if result else "UNKNOWN"
        print(f"\nBulk operation finished with status: {status}")
        sys.exit(1)

    # Verify
    print("\nVerifying...")
    remaining = get_product_count(client)
    print(f"  Products remaining: {remaining}")

    if remaining == 0:
        print("\nAll products deleted successfully.")
    else:
        print(f"\n{remaining} products still remain. You may need to run again.")


if __name__ == "__main__":
    main()
