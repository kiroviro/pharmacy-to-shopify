#!/usr/bin/env python3
"""
Shopify Filter Configuration (Bulgarian)

Creates metafield definitions for sidebar filters via GraphQL API
and translates built-in filter labels to Bulgarian via theme locale.

Actions:
  1. Creates custom metafield definitions (Форма, За кого) — shown as filter labels
  2. Fetches the active theme and patches its Bulgarian locale file to translate
     built-in filter labels (Availability → Наличност, Price → Цена, etc.)

Requirements:
    pip install requests

Usage:
    # Dry run (preview only)
    python3 configure_shopify_filters.py --shop STORE --token TOKEN --dry-run

    # Create definitions + translate theme
    python3 configure_shopify_filters.py --shop STORE --token TOKEN
"""

import argparse
import json
import logging
import os
import sys
from typing import Optional

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.common.log_config import setup_logging
from src.shopify import ShopifyAPIClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1. Metafield definitions (Bulgarian names → shown as filter labels)
# ---------------------------------------------------------------------------

METAFIELD_DEFINITIONS = [
    {
        "name": "Форма",
        "namespace": "custom",
        "key": "application_form",
        "type": "single_line_text_field",
        "description": "Форма на продукта (Таблетки, Капсули, Крем и др.)",
        "pin": True,
    },
    {
        "name": "За кого",
        "namespace": "custom",
        "key": "target_audience",
        "type": "single_line_text_field",
        "description": "Целева аудитория (Възрастни, Деца, Бебета)",
        "pin": True,
    },
]

METAFIELD_DEFINITION_CREATE_MUTATION = """
mutation metafieldDefinitionCreate($definition: MetafieldDefinitionInput!) {
  metafieldDefinitionCreate(definition: $definition) {
    createdDefinition {
      id
      name
      namespace
      key
    }
    userErrors {
      field
      message
    }
  }
}
"""

# ---------------------------------------------------------------------------
# 2. Bulgarian translations for built-in filter labels
# ---------------------------------------------------------------------------

# These keys cover Dawn-based and most Shopify 2.0 themes.
# The structure mirrors the theme's locales/bg.json file.
FILTER_TRANSLATIONS_BG = {
    "products": {
        "facets": {
            "availability_label": "Наличност",
            "price_label": "Цена",
            "product_type_label": "Категория",
            "vendor_label": "Марка",
            "filter_button": "Филтриране",
            "reset_button": "Изчистване",
            "clear_all": "Изчисти всички",
            "from": "От",
            "to": "До",
            "max_price": "Най-висока цена е {{price}}",
            "filter_and_sort": "Филтриране и сортиране",
            "filter_by_label": "Филтриране по:",
            "sort_by_label": "Сортиране по:",
            "sort_button": "Сортиране",
            "apply": "Приложи",
            "0_results_with_count": "Няма резултати",
            "results_with_count": {
                "one": "{{ count }} резултат",
                "other": "{{ count }} резултата",
            },
            "product_count": {
                "one": "{{ product_count }} продукт",
                "other": "{{ product_count }} продукта",
            },
            "product_count_simple": {
                "one": "{{ count }} продукт",
                "other": "{{ count }} продукта",
            },
        }
    },
    "collections": {
        "sorting": {
            "title": "Сортиране по",
            "featured": "Най-продавани",
            "best_selling": "Най-продавани",
            "title_ascending": "Азбучен ред, А-Я",
            "title_descending": "Азбучен ред, Я-А",
            "price_ascending": "Цена, ниска към висока",
            "price_descending": "Цена, висока към ниска",
            "created_ascending": "Дата, стари към нови",
            "created_descending": "Дата, нови към стари",
        }
    },
}


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


def create_metafield_definitions(client: ShopifyAPIClient, dry_run: bool = False):
    """Create metafield definitions for product filters."""
    print("\n--- Метаполета (Metafield Definitions) ---\n")

    for defn in METAFIELD_DEFINITIONS:
        full_key = f"{defn['namespace']}.{defn['key']}"
        print(f"  {defn['name']} ({full_key})")
        print(f"    Тип: {defn['type']}")
        print(f"    Описание: {defn['description']}")
        print(f"    Закачено: {defn['pin']}")

        if dry_run:
            print("    -> ПРОПУСНАТО (dry run)\n")
            continue

        variables = {
            "definition": {
                "name": defn["name"],
                "namespace": defn["namespace"],
                "key": defn["key"],
                "type": defn["type"],
                "description": defn["description"],
                "ownerType": "PRODUCT",
                "pin": defn["pin"],
            }
        }

        result = client.graphql_request(
            METAFIELD_DEFINITION_CREATE_MUTATION,
            variables=variables,
        )

        if result:
            user_errors = (
                result.get("metafieldDefinitionCreate", {}).get("userErrors", [])
            )
            if user_errors:
                for err in user_errors:
                    print(f"    -> ГРЕШКА: {err['message']}")
            else:
                created = result["metafieldDefinitionCreate"]["createdDefinition"]
                print(f"    -> СЪЗДАДЕНО (id: {created['id']})")
        else:
            print("    -> НЕУСПЕШНО (няма отговор)")

        print()


def get_active_theme_id(client: ShopifyAPIClient) -> Optional[str]:
    """Get the ID of the currently active (published) theme."""
    result = client.rest_request("GET", "themes.json")
    if not result or "themes" not in result:
        return None

    for theme in result["themes"]:
        if theme.get("role") == "main":
            return str(theme["id"])

    return None


def deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base, preserving existing keys."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def translate_theme_filters(client: ShopifyAPIClient, dry_run: bool = False):
    """Translate filter labels in the active theme's Bulgarian locale."""
    print("\n--- Превод на филтри в темата ---\n")

    # Step 1: Get active theme
    theme_id = get_active_theme_id(client)
    if not theme_id:
        print("  ГРЕШКА: Не може да се намери активната тема")
        return

    logger.info("Активна тема ID: %s", theme_id)

    # Step 2: Try to read existing Bulgarian locale file
    # Shopify themes use locales/bg.json or locales/bg.default.json
    locale_key = None
    existing_locale = {}

    for candidate_key in ["locales/bg.default.json", "locales/bg.json"]:
        result = client.rest_request(
            "GET",
            f"themes/{theme_id}/assets.json?asset[key]={candidate_key}",
        )
        if result and "asset" in result:
            locale_key = candidate_key
            try:
                existing_locale = json.loads(result["asset"].get("value", "{}"))
            except (json.JSONDecodeError, TypeError):
                existing_locale = {}
            logger.info("Намерен локал файл: %s", locale_key)
            break

    if not locale_key:
        # No Bulgarian locale exists yet — create one
        locale_key = "locales/bg.json"
        logger.info("Български локал не е намерен, ще се създаде: %s", locale_key)

    # Step 3: Merge translations (preserve any existing keys)
    updated_locale = deep_merge(existing_locale, FILTER_TRANSLATIONS_BG)

    # Show what's being translated
    facets = FILTER_TRANSLATIONS_BG.get("products", {}).get("facets", {})
    label_keys = [k for k in facets if k.endswith("_label")]
    for k in label_keys:
        print(f"    {k}: {facets[k]}")

    if dry_run:
        print("\n  -> ПРОПУСНАТО (dry run)")
        print(f"     Щеше да се обнови: {locale_key}")
        return

    # Step 4: Write updated locale back to theme
    result = client.rest_request(
        "PUT",
        f"themes/{theme_id}/assets.json",
        data={
            "asset": {
                "key": locale_key,
                "value": json.dumps(updated_locale, ensure_ascii=False, indent=2),
            }
        },
    )

    if result and "asset" in result:
        print(f"\n  -> ОБНОВЕНО: {locale_key}")
    else:
        print(f"\n  -> НЕУСПЕШНО: не можа да се обнови {locale_key}")


def print_manual_steps():
    """Print instructions for enabling filters in Shopify Admin."""
    print("\n--- Ръчни стъпки (Shopify Admin) ---\n")
    print("  Следните филтри трябва да се включат ръчно:\n")
    print("  1. Отидете на: Online Store > Navigation > Collection and search filters")
    print("  2. Натиснете 'Add filter' и включете:")
    print("     - Product vendor  (ще се показва като 'Марка')")
    print("     - Product type    (ще се показва като 'Категория')")
    print("     - Форма           (custom metafield — създадено по-горе)")
    print("     - За кого         (custom metafield — създадено по-горе)")
    print("  3. Подредете филтрите по желание")
    print("  4. Натиснете Save\n")
    print("  Забележка: Преводите на 'Availability' и 'Price' идват от")
    print("  локализацията на темата (обновена автоматично по-горе).\n")


def main():
    parser = argparse.ArgumentParser(
        description="Конфигуриране на филтри в Shopify (метаполета + превод)"
    )
    parser.add_argument(
        "--shop",
        "-s",
        required=True,
        help="Shopify shop name (e.g., 'viapharma' or 'viapharma.myshopify.com')",
    )
    parser.add_argument(
        "--token",
        "-t",
        required=True,
        help="Shopify Admin API access token",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Преглед без промени",
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

    print("=" * 60)
    print("Конфигуриране на филтри в Shopify")
    print("=" * 60)
    print(f"  Магазин: {args.shop}")
    print(f"  Dry run: {args.dry_run}")

    client = ShopifyAPIClient(shop=args.shop, access_token=args.token)

    # 1. Create custom metafield definitions (Форма, За кого)
    create_metafield_definitions(client, dry_run=args.dry_run)

    # 2. Translate built-in filter labels in theme locale
    translate_theme_filters(client, dry_run=args.dry_run)

    # 3. Print remaining manual steps
    print_manual_steps()

    print("=" * 60)
    print("Готово.")
    print("=" * 60)


if __name__ == "__main__":
    main()
