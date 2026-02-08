#!/usr/bin/env python3
"""Create a new Google Ads client account under the manager (MCC) account.

Usage:
    1. Fill in config/google-ads.yaml with all credentials
    2. Run: python google_ads_create_account.py --name "ViaPharma US"
    3. Optionally pass --update-config to write the new customer ID back to config

This script creates a new Google Ads client account linked to your MCC,
then optionally updates config/google-ads.yaml with the new customer_id.
"""

import argparse
import logging
import sys

import yaml
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from src.common.log_config import setup_logging

logger = logging.getLogger(__name__)


def load_config(config_path: str = "config/google-ads.yaml") -> dict:
    """Load Google Ads config from YAML file."""
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    required = ["developer_token", "client_id", "client_secret",
                 "refresh_token", "login_customer_id"]
    for key in required:
        val = config.get(key, "")
        if not val or "INSERT_" in str(val):
            logger.error("Please fill in '%s' in %s", key, config_path)
            sys.exit(1)

    return config


def get_client(config: dict) -> GoogleAdsClient:
    """Create a GoogleAdsClient from config."""
    client_config = {
        "developer_token": config["developer_token"],
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "refresh_token": config["refresh_token"],
        "login_customer_id": str(config["login_customer_id"]),
        "use_proto_plus": True,
    }
    return GoogleAdsClient.load_from_dict(client_config)


def create_customer_account(
    client: GoogleAdsClient,
    manager_customer_id: str,
    account_name: str,
    currency_code: str,
    time_zone: str,
) -> str:
    """Create a new Google Ads client account under the manager.

    Returns the new customer ID (digits only, no dashes).
    """
    customer_service = client.get_service("CustomerService")
    customer = client.get_type("Customer")

    customer.descriptive_name = account_name
    customer.currency_code = currency_code
    customer.time_zone = time_zone

    response = customer_service.create_customer_client(
        customer_id=manager_customer_id,
        customer_client=customer,
    )

    # resource_name format: "customers/{manager_id}/customerClients/{new_id}"
    new_customer_id = response.resource_name.split("/")[-1]
    logger.info("Created account: %s", response.resource_name)
    return new_customer_id


def update_config_file(config_path: str, new_customer_id: str):
    """Update customer_id in the YAML config file."""
    with open(config_path, "r") as f:
        content = f.read()

    config = yaml.safe_load(content)
    old_id = str(config.get("customer_id", ""))

    # Preserve comments and formatting by doing string replacement
    if old_id:
        content = content.replace(
            f'customer_id: "{old_id}"',
            f'customer_id: "{new_customer_id}"',
        )
    else:
        # Append if not present
        content += f'\ncustomer_id: "{new_customer_id}"\n'

    with open(config_path, "w") as f:
        f.write(content)

    logger.info("Updated %s: customer_id %s → %s", config_path, old_id, new_customer_id)


def main():
    parser = argparse.ArgumentParser(
        description="Create a new Google Ads client account under the MCC"
    )
    parser.add_argument(
        "--name",
        type=str,
        default="ViaPharma",
        help="Descriptive name for the new account (default: ViaPharma)",
    )
    parser.add_argument(
        "--currency",
        type=str,
        default="USD",
        help="Currency code (default: USD)",
    )
    parser.add_argument(
        "--timezone",
        type=str,
        default="America/New_York",
        help="Time zone (default: America/New_York)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/google-ads.yaml",
        help="Path to google-ads.yaml config file",
    )
    parser.add_argument(
        "--update-config",
        action="store_true",
        help="Write the new customer_id back to the config file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config without creating anything",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose (debug) logging",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress info messages, show only warnings and errors",
    )
    args = parser.parse_args()
    setup_logging(verbose=args.verbose, quiet=args.quiet)

    config = load_config(args.config)
    manager_id = str(config["login_customer_id"]).replace("-", "")

    print(f"Manager (MCC) ID: {manager_id}")
    print(f"Account name:     {args.name}")
    print(f"Currency:         {args.currency}")
    print(f"Time zone:        {args.timezone}")
    print()

    if args.dry_run:
        print("Dry run - config is valid. No changes made.")
        return

    client = get_client(config)

    try:
        new_customer_id = create_customer_account(
            client, manager_id, args.name, args.currency, args.timezone
        )

        if args.update_config:
            update_config_file(args.config, new_customer_id)

        print()
        print("=" * 60)
        print("SUCCESS! New Google Ads account created.")
        print()
        print(f"  Customer ID: {new_customer_id}")
        print(f"  Name:        {args.name}")
        print(f"  Currency:    {args.currency}")
        print(f"  Time zone:   {args.timezone}")
        print()
        if not args.update_config:
            print(f"To use this account, update customer_id in {args.config}:")
            print(f'  customer_id: "{new_customer_id}"')
            print()
            print("Or re-run with --update-config to do it automatically.")
            print()
        print("Next steps:")
        print("  1. Set up billing at ads.google.com for the new account")
        print("  2. Run: python google_ads_pmax.py  (to create a PMax campaign)")
        print()
        print("=" * 60)

    except GoogleAdsException as ex:
        logger.error("Google Ads API error: %s", ex.failure.errors[0].message)
        for error in ex.failure.errors:
            logger.error("Error: %s", error.message)
            if error.location:
                for field in error.location.field_path_elements:
                    logger.error("Field: %s", field.field_name)
        sys.exit(1)


if __name__ == "__main__":
    main()
