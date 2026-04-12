#!/usr/bin/env python3
"""
Create the WELCOME10 discount code in Shopify.

10% off entire order, once per customer — for newsletter subscribers.
Uses GraphQL discountCodeBasicCreate (requires write_discounts scope).

Usage:
    python scripts/create_welcome_discount.py
    python scripts/create_welcome_discount.py --dry-run
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.common.credentials import load_shopify_credentials
from src.shopify.api_client import ShopifyAPIClient

logger = logging.getLogger(__name__)

MUTATION = """
mutation discountCodeBasicCreate($basicCodeDiscount: DiscountCodeBasicInput!) {
  discountCodeBasicCreate(basicCodeDiscount: $basicCodeDiscount) {
    codeDiscountNode {
      id
      codeDiscount {
        ... on DiscountCodeBasic {
          title
          codes(first: 1) {
            nodes {
              code
            }
          }
        }
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""


def main():
    parser = argparse.ArgumentParser(description="Create WELCOME10 discount code")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    variables = {
        "basicCodeDiscount": {
            "title": "WELCOME10 - 10% за абонати на бюлетина",
            "code": "WELCOME10",
            "startsAt": "2026-03-30T00:00:00Z",
            "customerSelection": {
                "all": True,
            },
            "customerGets": {
                "value": {
                    "percentage": 0.10,
                },
                "items": {
                    "all": True,
                },
            },
            "appliesOncePerCustomer": True,
        }
    }

    if args.dry_run:
        logger.info("DRY RUN — would create discount:")
        logger.info("  Title: WELCOME10 - 10%% за абонати на бюлетина")
        logger.info("  Code: WELCOME10")
        logger.info("  Value: 10%% off entire order")
        logger.info("  Once per customer: True")
        return

    shop, token = load_shopify_credentials()
    client = ShopifyAPIClient(shop=shop, access_token=token)

    logger.info("Creating discount code WELCOME10 via GraphQL...")
    result = client.graphql_request(MUTATION, variables)

    if not result:
        logger.error("Failed — no response from API.")
        sys.exit(1)

    data = result.get("discountCodeBasicCreate", {})
    errors = data.get("userErrors", [])

    if errors:
        for err in errors:
            logger.error("Error: %s — %s", err["field"], err["message"])
        sys.exit(1)

    node = data.get("codeDiscountNode", {})
    discount = node.get("codeDiscount", {})
    code = discount.get("codes", {}).get("nodes", [{}])[0].get("code", "?")

    logger.info("Done! Discount code created successfully.")
    logger.info("  ID: %s", node.get("id"))
    logger.info("  Code: %s", code)
    logger.info("  Discount: 10%% off entire order")
    logger.info("  Limit: once per customer")


if __name__ == "__main__":
    main()
