#!/usr/bin/env python3
"""Create a Performance Max campaign for ViaPharma via Google Ads API.

Usage:
    1. Fill in config/google-ads.yaml with all credentials
    2. Run: python google_ads_pmax.py

This script creates:
    - A campaign budget
    - A Performance Max campaign linked to Merchant Center
    - An asset group with text and image assets
    - Listing group filters for product targeting
"""

import argparse
import logging
import sys
import uuid
from datetime import datetime, timedelta

import yaml
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from src.common.log_config import setup_logging

logger = logging.getLogger(__name__)


def load_config(config_path: str = "config/google-ads.yaml") -> dict:
    """Load Google Ads config from YAML file."""
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    required = ["developer_token", "client_id", "client_secret", "refresh_token",
                 "customer_id", "merchant_center_id"]
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
        "use_proto_plus": True,
    }
    if config.get("login_customer_id"):
        client_config["login_customer_id"] = str(config["login_customer_id"])

    return GoogleAdsClient.load_from_dict(client_config)


def create_campaign_budget(client, customer_id: str, budget_amount_micros: int) -> str:
    """Create a campaign budget and return its resource name."""
    budget_service = client.get_service("CampaignBudgetService")
    budget_operation = client.get_type("CampaignBudgetOperation")

    budget = budget_operation.create
    budget.name = f"ViaPharma PMax Budget #{uuid.uuid4().hex[:8]}"
    budget.amount_micros = budget_amount_micros
    budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
    # Performance Max requires explicitly_shared = False
    budget.explicitly_shared = False

    response = budget_service.mutate_campaign_budgets(
        customer_id=customer_id, operations=[budget_operation]
    )
    budget_resource = response.results[0].resource_name
    logger.info("Created budget: %s", budget_resource)
    return budget_resource


def create_pmax_campaign(
    client, customer_id: str, budget_resource: str, merchant_center_id: int
) -> str:
    """Create a Performance Max campaign and return its resource name."""
    campaign_service = client.get_service("CampaignService")
    campaign_operation = client.get_type("CampaignOperation")

    campaign = campaign_operation.create
    campaign.name = f"ViaPharma PMax #{uuid.uuid4().hex[:8]}"
    campaign.advertising_channel_type = (
        client.enums.AdvertisingChannelTypeEnum.PERFORMANCE_MAX
    )
    campaign.status = client.enums.CampaignStatusEnum.PAUSED  # Start paused for review
    campaign.campaign_budget = budget_resource

    # Bidding: Maximize Conversion Value (best for e-commerce)
    campaign.bidding_strategy_type = (
        client.enums.BiddingStrategyTypeEnum.MAXIMIZE_CONVERSION_VALUE
    )
    campaign.maximize_conversion_value.target_roas = 0  # No target ROAS initially; let Google optimize

    # Link Merchant Center shopping feed
    campaign.shopping_setting.merchant_id = merchant_center_id
    # Empty feed_label = use all products; set to filter specific products if needed
    campaign.shopping_setting.feed_label = ""

    # Start and end dates
    start_date = datetime.now() + timedelta(days=1)
    campaign.start_date = start_date.strftime("%Y%m%d")
    # No end date = runs indefinitely

    # URL expansion: let Google find relevant landing pages
    campaign.url_expansion_opt_out = False

    response = campaign_service.mutate_campaigns(
        customer_id=customer_id, operations=[campaign_operation]
    )
    campaign_resource = response.results[0].resource_name
    logger.info("Created PMax campaign: %s", campaign_resource)
    return campaign_resource


def create_asset_group(
    client,
    customer_id: str,
    campaign_resource: str,
) -> str:
    """Create an asset group for the PMax campaign."""
    asset_group_service = client.get_service("AssetGroupService")
    operation = client.get_type("AssetGroupOperation")

    asset_group = operation.create
    asset_group.name = f"ViaPharma All Products #{uuid.uuid4().hex[:8]}"
    asset_group.campaign = campaign_resource
    asset_group.status = client.enums.AssetGroupStatusEnum.PAUSED

    # Final URL — your main landing page
    asset_group.final_urls.append("https://viapharma.us")
    asset_group.final_mobile_urls.append("https://viapharma.us")

    response = asset_group_service.mutate_asset_groups(
        customer_id=customer_id, operations=[operation]
    )
    asset_group_resource = response.results[0].resource_name
    logger.info("Created asset group: %s", asset_group_resource)
    return asset_group_resource


def create_text_assets(client, customer_id: str, asset_group_resource: str):
    """Create text assets (headlines, descriptions) and link them to the asset group."""
    asset_service = client.get_service("AssetService")
    asset_group_asset_service = client.get_service("AssetGroupAssetService")

    # Define text assets (Bulgarian market - prices in BGN, free shipping over 68 лв / ~€35)
    headlines = [
        "ViaPharma - Онлайн Аптека",
        "Витамини и Добавки",
        "Вашата онлайн аптека",
        "Безплатна доставка над 68лв",
        "10000+ Здравни Продукти",
    ]

    long_headlines = [
        "Вашата доверена онлайн аптека в България",
        "Витамини, добавки и козметика с доставка до вратата",
    ]

    descriptions = [
        "Пазарувайте витамини, добавки, козметика и здравни продукти. Бърза доставка в България.",
        "Доверена онлайн аптека с 10000+ продукта. Безплатна доставка над 68 лв.",
        "Качествени здравни продукти за цялото семейство. Лекарства, витамини и козметика.",
        "Вашата онлайн аптека за здраве и красота с европейско качество.",
    ]

    business_name = "ViaPharma"

    all_operations = []

    # Create headline assets
    for text in headlines:
        op = client.get_type("AssetOperation")
        op.create.text_asset.text = text
        op.create.name = f"headline_{uuid.uuid4().hex[:8]}"
        all_operations.append(("HEADLINE", op))

    # Create long headline assets
    for text in long_headlines:
        op = client.get_type("AssetOperation")
        op.create.text_asset.text = text
        op.create.name = f"long_headline_{uuid.uuid4().hex[:8]}"
        all_operations.append(("LONG_HEADLINE", op))

    # Create description assets
    for text in descriptions:
        op = client.get_type("AssetOperation")
        op.create.text_asset.text = text
        op.create.name = f"desc_{uuid.uuid4().hex[:8]}"
        all_operations.append(("DESCRIPTION", op))

    # Create business name asset
    op = client.get_type("AssetOperation")
    op.create.text_asset.text = business_name
    op.create.name = f"biz_{uuid.uuid4().hex[:8]}"
    all_operations.append(("BUSINESS_NAME", op))

    # Batch create all text assets
    asset_ops = [op for _, op in all_operations]
    response = asset_service.mutate_assets(
        customer_id=customer_id, operations=asset_ops
    )

    # Link each asset to the asset group with its field type
    link_operations = []
    for i, result in enumerate(response.results):
        field_type_name = all_operations[i][0]
        field_type = getattr(
            client.enums.AssetFieldTypeEnum, field_type_name
        )

        link_op = client.get_type("AssetGroupAssetOperation")
        link_op.create.asset = result.resource_name
        link_op.create.asset_group = asset_group_resource
        link_op.create.field_type = field_type
        link_operations.append(link_op)

    asset_group_asset_service.mutate_asset_group_assets(
        customer_id=customer_id, operations=link_operations
    )
    logger.info("Created and linked %d text assets", len(link_operations))


def create_listing_group_filter(
    client, customer_id: str, asset_group_resource: str
):
    """Create a listing group filter to include all products from the feed."""
    service = client.get_service("AssetGroupListingGroupFilterService")
    operation = client.get_type("AssetGroupListingGroupFilterOperation")

    listing_filter = operation.create
    listing_filter.asset_group = asset_group_resource
    listing_filter.type_ = (
        client.enums.ListingGroupFilterTypeEnum.UNIT_INCLUDED
    )
    # Root node with no parent = all products
    listing_filter.listing_source = (
        client.enums.ListingGroupFilterListingSourceEnum.SHOPPING
    )

    response = service.mutate_asset_group_listing_group_filters(
        customer_id=customer_id, operations=[operation]
    )
    logger.info("Created listing group filter: %s", response.results[0].resource_name)


def main():
    parser = argparse.ArgumentParser(
        description="Create a Performance Max campaign for ViaPharma"
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=20.0,
        help="Daily budget in USD (default: 20.00)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/google-ads.yaml",
        help="Path to google-ads.yaml config file",
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
    customer_id = str(config["customer_id"]).replace("-", "")
    merchant_center_id = int(config["merchant_center_id"])
    budget_micros = int(args.budget * 1_000_000)  # Convert USD to micros

    print(f"Customer ID:      {customer_id}")
    print(f"Merchant Center:  {merchant_center_id}")
    print(f"Daily Budget:     ${args.budget:.2f}")
    print()

    if args.dry_run:
        print("Dry run - config is valid. No changes made.")
        return

    client = get_client(config)

    try:
        # Step 1: Create budget
        logger.info("Step 1/5: Creating campaign budget...")
        budget_resource = create_campaign_budget(client, customer_id, budget_micros)

        # Step 2: Create PMax campaign
        logger.info("Step 2/5: Creating Performance Max campaign...")
        campaign_resource = create_pmax_campaign(
            client, customer_id, budget_resource, merchant_center_id
        )

        # Step 3: Create asset group
        logger.info("Step 3/5: Creating asset group...")
        asset_group_resource = create_asset_group(
            client, customer_id, campaign_resource
        )

        # Step 4: Create and link text assets
        logger.info("Step 4/5: Creating text assets (headlines, descriptions)...")
        create_text_assets(client, customer_id, asset_group_resource)

        # Step 5: Create listing group filter (include all products)
        logger.info("Step 5/5: Creating product listing group filter...")
        create_listing_group_filter(client, customer_id, asset_group_resource)

        print()
        print("=" * 60)
        print("SUCCESS! Performance Max campaign created.")
        print()
        print("Campaign is PAUSED by default. To activate:")
        print("  1. Go to ads.google.com")
        print("  2. Review the campaign and asset group")
        print("  3. Add image assets (logo, marketing images)")
        print("  4. Enable the campaign when ready")
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
