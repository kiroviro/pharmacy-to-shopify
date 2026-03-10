# Promo Campaign System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable recurring promotional campaigns (Phoenix, SoPharmacy) to appear automatically on viapharma.us with a homepage featured section, per-campaign collection cards on `/collections/namaleniya`, and scripts to create and close campaigns.

**Architecture:** Two repos collaborate via a Shopify data contract. `viapharma-pricing` owns all data writes (tags, smart collections, banner image). `viapharma.us-theme` owns display — it reads what viapharma-pricing writes and renders automatically with no manual theme deploys per campaign.

**Tech Stack:** Shopify Liquid (theme JSON templates), Python + Shopify Admin REST/GraphQL API (viapharma-pricing scripts), `push_theme.py` for theme file deployment.

---

## Repo Layout

```
viapharma.us-theme/             (at /Users/kiril/IdeaProjects/viapharma.us-theme)
  templates/
    index.json                  # Homepage — Task 1 modifies this
    collection.namaleniya.json  # New — Task 2 creates this

viapharma-pricing/              (at /Users/kiril/IdeaProjects/viapharma-pricing)
  scripts/
    sync_phoenix_promos.py      # Task 3 extends apply with --campaign-tag
    create_campaign_collection.py   # New — Task 4
    close_campaign.py               # New — Task 5
  tests/scripts/
    test_create_campaign_collection.py  # New — Task 4
    test_close_campaign.py              # New — Task 5
```

**Deploy theme files with:**
```bash
cd /Users/kiril/IdeaProjects/pharmacy-to-shopify
python scripts/push_theme.py templates/index.json
python scripts/push_theme.py templates/collection.namaleniya.json
```
(push_theme.py resolves theme dir as `../../viapharma.us-theme`)

---

## Task 1: Theme — Update index.json (homepage)

**Three changes in one file:**
1. `featured_collection` section: change collection from `grip-i-nastinka` → `namaleniya`, update title/description
2. `collection-tabs` section (key `355af80a-5c77-40fb-83a7-dbff9c1c8ef4`): add "Грип и настинка" as a new tab
3. `homepage_discount_banner` section: enable it (remove `"disabled": true`), update button to link to namaleniya

**File:**
- Modify: `../../viapharma.us-theme/templates/index.json`

No tests for JSON template edits — verify by pushing and viewing the live homepage.

**Step 1: Change featured_collection to point to namaleniya**

In `viapharma.us-theme/templates/index.json`, find the `featured_collection` section and update:

```json
"featured_collection": {
  "type": "featured-collection",
  "settings": {
    "title": "Намаления",
    "heading_size": "h2",
    "description": "<p>Продукти с намалени цени от текущи промоции</p>",
    "text_size_block": "medium",
    "text_color": "secondary",
    "show_description": true,
    "countdown_label": "",
    "countdown_font_weight": "400",
    "numbers_size": "h5",
    "countdown_date": "",
    "countdown_end": "cycle",
    "days_label": "",
    "hours_label": "",
    "mins_label": "",
    "secs_label": "",
    "countdown_label_bg": "#003e52",
    "label_text_color": "secondary",
    "collection": "namaleniya",
    "products_to_show": 8,
    "columns_desktop": 4,
    "full_width": false,
    "show_view_all": true,
    "view_all_style": "solid",
    "enable_desktop_slider": false,
    "color_scheme": "scheme-1",
    "image_ratio": "portrait",
    "show_secondary_image": true,
    "show_vendor": true,
    "show_rating": false,
    "enable_quick_add": true,
    "columns_mobile": "2",
    "swipe_on_mobile": false,
    "padding_top": 60,
    "padding_bottom": 60
  }
}
```

Use the Edit tool to make this change. The old `"collection": "grip-i-nastinka"` is unique in this section.

**Step 2: Add "Грип и настинка" tab to collection-tabs**

The `collection-tabs` section key is `355af80a-5c77-40fb-83a7-dbff9c1c8ef4`. Add a new block `tab_4` after `tab_3`:

In the `blocks` object, add after the `tab_3` block:
```json
"tab_4": {
  "type": "collection",
  "settings": {
    "collection": "grip-i-nastinka",
    "collection_title": "Грип и настинка",
    "show_view_all": true,
    "button_label": "Виж всички",
    "button_style_secondary": false
  }
}
```

And in `block_order`, add `"tab_4"` after `"tab_3"`.

**Step 3: Enable homepage_discount_banner and update button**

The `homepage_discount_banner` section currently has `"disabled": true`. Remove that line. Also update the button to link to namaleniya:

Change `"button_link_1": "shopify://collections/all"` → `"button_link_1": "shopify://collections/namaleniya"`
Change `"button_label_1": "РАЗГЛЕДАЙ КАТАЛОГА"` → `"button_label_1": "РАЗГЛЕДАЙ НАМАЛЕНИЯТА"`

Also update heading and text to be promo-relevant:
- `"heading": "Текущи промоции"`
- `"text": "Продукти с намалени цени от Phoenix, SoPharmacy и наши промоции."`

And remove `"disabled": true` from the section settings.

**Step 4: Push to live**

```bash
cd /Users/kiril/IdeaProjects/pharmacy-to-shopify
python scripts/push_theme.py templates/index.json
```

Expected output: `Pushed templates/index.json` (or similar success message)

**Step 5: Verify**

Open https://viapharma.us in a browser (or take a screenshot after ~2 minutes for CDN propagation).
Confirm:
- Featured collection section shows "Намаления" title with discounted products
- "Популярни продукти" tabs now include "Грип и настинка" as 4th tab
- Homepage discount banner section is visible

**Step 6: Commit**

```bash
cd /Users/kiril/IdeaProjects/viapharma.us-theme
git add templates/index.json
git commit -m "feat: swap homepage featured-collection to namaleniya, add Грип tab, enable discount banner"
```

---

## Task 2: Theme — Create collection.namaleniya.json

This is an **alternate Shopify collection template**. When a collection's template is set to `namaleniya` in Shopify Admin (or via API), Shopify uses this file instead of `collection.json`.

It adds a `collection-list` section above the product grid. The `collection-list` section renders collection cards — the merchant configures which collections to show via Shopify Admin's section editor (no code changes needed per campaign).

**File:**
- Create: `../../viapharma.us-theme/templates/collection.namaleniya.json`

**Step 1: Create the file**

Create `viapharma.us-theme/templates/collection.namaleniya.json` with this content:

```json
{
  "sections": {
    "banner": {
      "type": "main-collection-banner",
      "settings": {
        "color_scheme": "scheme-3",
        "text_secondary_color": false,
        "show_collection_breadcrumbs": true,
        "show_breadcrumbs_top": true,
        "heading_size": "h3",
        "show_collection_description": true,
        "description_text": "{{ collection.description }}",
        "text_size_block": "medium",
        "heading_alignment": "center",
        "show_collection_image": false,
        "banner_height": "small",
        "image_block": false,
        "hide_radius": true,
        "image_size": "60",
        "image_overlay_opacity": 40,
        "content_alignment": "bottom",
        "section_full_width": true,
        "section_background": "#ffffff",
        "padding_top": 10,
        "padding_bottom": 10
      }
    },
    "campaign_cards": {
      "type": "collection-list",
      "blocks": {},
      "block_order": [],
      "settings": {
        "title": "Активни кампании",
        "heading_size": "h2",
        "image_ratio": "square",
        "columns_desktop": 3,
        "color_scheme": "scheme-1",
        "columns_mobile": "1",
        "swipe_on_mobile": false,
        "padding_top": 40,
        "padding_bottom": 20
      }
    },
    "product-grid": {
      "type": "main-collection-product-grid",
      "blocks": {
        "subcollections_z3DaMJ": {
          "type": "subcollections",
          "settings": {
            "color_scheme": "scheme-3",
            "menu": "",
            "show_product_count": true,
            "image_ratio": "landscape",
            "overlay": "",
            "image_overlay_opacity": 50,
            "collections_desktop": 5,
            "heading_size": "h5"
          }
        }
      },
      "block_order": [
        "subcollections_z3DaMJ"
      ],
      "settings": {
        "products_per_page": "96",
        "columns_desktop": 3,
        "color_scheme": "scheme-8",
        "image_ratio": "landscape",
        "show_secondary_image": true,
        "show_vendor": false,
        "show_rating": false,
        "enable_quick_add": true,
        "enable_filtering": true,
        "filter_type": "vertical",
        "swatch_layout": "default",
        "filter_color_scheme": "",
        "enable_sorting": true,
        "sorting_color_scheme": "",
        "sorting_inside_color_scheme": "",
        "show_navigation": true,
        "navigation_label": "Покажи като",
        "label_font_size": "text--small",
        "label_font_weight": "fw-500",
        "label_font_style": "body",
        "summary_font_size": "h6",
        "summary_font_weight": "fw-600",
        "filter_text_font_size": "b-text-sm",
        "filter_text_font_weight": "fw-400",
        "columns_mobile": "2",
        "padding_top": 20,
        "padding_bottom": 40
      }
    }
  },
  "order": [
    "banner",
    "campaign_cards",
    "product-grid"
  ]
}
```

**Step 2: Push to live**

```bash
cd /Users/kiril/IdeaProjects/pharmacy-to-shopify
python scripts/push_theme.py templates/collection.namaleniya.json
```

**Step 3: Assign alternate template in Shopify Admin**

This is a manual step (one-time, no script needed):
1. Go to Shopify Admin → Collections → "Намаления"
2. In the "Theme template" section on the right, select `collection.namaleniya`
3. Save

After this, `/collections/namaleniya` will use the new template with the campaign-list block at the top.

**Step 4: Configure campaign_cards section via Admin**

Each time a new campaign collection is created:
1. Go to Shopify Admin → Online Store → Customize
2. Navigate to `/collections/namaleniya`
3. Click the "Активни кампании" section
4. Add a collection block and select the new campaign collection (e.g. "Phoenix Промоции — Март 2026")
5. Remove old campaign blocks when campaigns close

(The `create_campaign_collection.py` script in Task 4 will print a reminder to do this.)

**Step 5: Commit**

```bash
cd /Users/kiril/IdeaProjects/viapharma.us-theme
git add templates/collection.namaleniya.json
git commit -m "feat: add alternate namaleniya collection template with campaign-cards section"
```

---

## Task 3: viapharma-pricing — extend sync_phoenix_promos.py with --campaign-tag

The `apply` subcommand currently calls `apply_price_updates()`. We need to optionally also apply a tag to each repriced product.

**Files:**
- Modify: `viapharma-pricing/scripts/sync_phoenix_promos.py`
- Modify: `viapharma-pricing/src/shopify/api_client.py` (add `add_tags_to_products` method)
- Test: `viapharma-pricing/tests/shopify/test_api_client.py` (add tag method tests)

**Step 1: Write failing test for add_tags_to_products**

In `viapharma-pricing/tests/shopify/test_api_client.py`, add:

```python
def test_add_tags_to_products_builds_correct_mutation(mocker):
    """add_tags_to_products sends tagsAdd mutation for each product_id."""
    client = ShopifyAPIClient("test-shop", "fake-token")
    mock_gql = mocker.patch.object(client, "graphql_request", return_value={
        "tagsAdd": {"node": {"id": "gid://shopify/Product/123"}, "userErrors": []}
    })

    client.add_tags_to_products(["gid://shopify/Product/123"], ["promo-phoenix-2026-03"])

    mock_gql.assert_called_once()
    call_args = mock_gql.call_args
    assert "tagsAdd" in call_args[0][0]
    assert call_args[0][1]["id"] == "gid://shopify/Product/123"
    assert "promo-phoenix-2026-03" in call_args[0][1]["tags"]
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/kiril/IdeaProjects/viapharma-pricing
pytest tests/shopify/test_api_client.py::test_add_tags_to_products_builds_correct_mutation -v
```
Expected: `AttributeError: 'ShopifyAPIClient' object has no attribute 'add_tags_to_products'`

**Step 3: Implement add_tags_to_products in api_client.py**

Add this method to `ShopifyAPIClient` in `viapharma-pricing/src/shopify/api_client.py`:

```python
def add_tags_to_products(self, product_gids: list[str], tags: list[str]) -> dict[str, int]:
    """Apply tags to a list of products via GraphQL tagsAdd mutation.

    Args:
        product_gids: List of Shopify product GIDs (e.g. "gid://shopify/Product/123")
        tags: Tags to add (existing tags are preserved)

    Returns:
        {"tagged": N, "errors": N}
    """
    mutation = """
    mutation tagsAdd($id: ID!, $tags: [String!]!) {
      tagsAdd(id: $id, tags: $tags) {
        node { id }
        userErrors { field message }
      }
    }
    """
    tagged = 0
    errors = 0
    tags_str = list(tags)
    for gid in product_gids:
        result = self.graphql_request(mutation, {"id": gid, "tags": tags_str})
        user_errors = result.get("tagsAdd", {}).get("userErrors", [])
        if user_errors:
            logger.warning("tagsAdd errors for %s: %s", gid, user_errors)
            errors += 1
        else:
            tagged += 1
    return {"tagged": tagged, "errors": errors}
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/shopify/test_api_client.py::test_add_tags_to_products_builds_correct_mutation -v
```
Expected: `PASSED`

**Step 5: Add --campaign-tag to sync_phoenix_promos.py apply subcommand**

In `viapharma-pricing/scripts/sync_phoenix_promos.py`, update `cmd_apply` and add the argparse argument:

In `cmd_apply`:
```python
def cmd_apply(args: argparse.Namespace) -> None:
    """Apply approved promo prices."""
    updates = load_approved_updates(Path(args.csv_path))
    if not updates:
        print("No approved updates found.")
        return

    print(f"Loaded {len(updates)} approved promo updates")

    shop, token = load_shopify_credentials()
    client = ShopifyAPIClient(shop, token)
    results = apply_price_updates(client, updates, dry_run=args.dry_run)

    if args.campaign_tag and not args.dry_run:
        product_gids = [u.product_id for u in updates if u.product_id]
        tag_results = client.add_tags_to_products(product_gids, [args.campaign_tag])
        results["tagged"] = tag_results["tagged"]
        results["tag_errors"] = tag_results["errors"]
        print(f"Campaign tag '{args.campaign_tag}' applied to {tag_results['tagged']} products")

    client.close()

    prefix = "[DRY RUN] " if args.dry_run else ""
    print(f"\n{prefix}Results: {results}")
```

In `main()`, add to the `apply_p` subparser:
```python
apply_p.add_argument(
    "--campaign-tag",
    default=None,
    help="Tag to apply to all repriced products, e.g. promo-phoenix-2026-03",
)
```

**Step 6: Run all api_client tests to confirm nothing broken**

```bash
pytest tests/shopify/test_api_client.py -v
```
Expected: All PASS

**Step 7: Commit**

```bash
git add src/shopify/api_client.py scripts/sync_phoenix_promos.py tests/shopify/test_api_client.py
git commit -m "feat: add add_tags_to_products to ShopifyAPIClient; extend sync_phoenix_promos apply with --campaign-tag"
```

---

## Task 4: viapharma-pricing — create_campaign_collection.py

This script creates a Shopify smart collection filtered by campaign tag, uploads a banner image, and sets it as the collection image.

**Files:**
- Create: `viapharma-pricing/scripts/create_campaign_collection.py`
- Create: `viapharma-pricing/tests/scripts/test_create_campaign_collection.py`

**Understanding the Shopify APIs used:**
- **Create smart collection (REST):** `POST /admin/api/2025-01/smart_collections.json` with `rules: [{column: "tag", relation: "equals", condition: "promo-phoenix-2026-03"}]`
- **Staged upload + fileCreate (GraphQL):** Two-step image upload to Shopify CDN. Step 1: `stagedUploadsCreate` mutation gets a PUT URL. Step 2: PUT the file. Step 3: `fileCreate` mutation registers it in Shopify Files.
- **Set collection image (REST):** `PUT /admin/api/2025-01/smart_collections/{id}.json` with `image: {src: <cdn_url>}`

**Step 1: Write failing tests**

Create `viapharma-pricing/tests/scripts/__init__.py` (empty).

Create `viapharma-pricing/tests/scripts/test_create_campaign_collection.py`:

```python
"""Tests for create_campaign_collection.py (unit tests — no live API calls)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_build_collection_payload():
    """build_collection_payload returns correct smart collection structure."""
    from scripts.create_campaign_collection import build_collection_payload

    payload = build_collection_payload(
        source="phoenix",
        month="2026-03",
        title="Phoenix Промоции — Март 2026",
    )

    assert payload["smart_collection"]["title"] == "Phoenix Промоции — Март 2026"
    assert payload["smart_collection"]["rules"] == [
        {"column": "tag", "relation": "equals", "condition": "promo-phoenix-2026-03"}
    ]
    assert payload["smart_collection"]["published"] is True


def test_build_collection_payload_tag_format():
    """Campaign tag is always promo-{source}-{month}."""
    from scripts.create_campaign_collection import build_collection_payload

    payload = build_collection_payload("sopharmacy", "2026-04", "SoPharmacy April")
    rules = payload["smart_collection"]["rules"]
    assert rules[0]["condition"] == "promo-sopharmacy-2026-04"


def test_create_smart_collection_calls_rest():
    """create_smart_collection calls REST POST and returns collection id."""
    from scripts.create_campaign_collection import create_smart_collection

    mock_client = MagicMock()
    mock_client.rest_request.return_value = {
        "smart_collection": {"id": 987654321, "title": "Phoenix Промоции — Март 2026"}
    }

    collection_id = create_smart_collection(mock_client, "phoenix", "2026-03", "Phoenix Промоции — Март 2026")

    mock_client.rest_request.assert_called_once()
    call_method, call_endpoint = mock_client.rest_request.call_args[0][:2]
    assert call_method == "POST"
    assert "smart_collections" in call_endpoint
    assert collection_id == 987654321
```

**Step 2: Run tests to verify they fail**

```bash
cd /Users/kiril/IdeaProjects/viapharma-pricing
pytest tests/scripts/test_create_campaign_collection.py -v
```
Expected: `ModuleNotFoundError: No module named 'scripts.create_campaign_collection'`

**Step 3: Implement create_campaign_collection.py**

Create `viapharma-pricing/scripts/create_campaign_collection.py`:

```python
#!/usr/bin/env python3
"""Create a campaign smart collection in Shopify.

Usage:
    python scripts/create_campaign_collection.py \
        --source phoenix \
        --month 2026-03 \
        --title "Phoenix Промоции — Март 2026" \
        [--image campaign_banner.jpg]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.credentials import load_shopify_credentials
from src.shopify.api_client import ShopifyAPIClient

logger = logging.getLogger(__name__)


def build_collection_payload(source: str, month: str, title: str) -> dict:
    """Build REST payload for creating a smart collection."""
    tag = f"promo-{source}-{month}"
    return {
        "smart_collection": {
            "title": title,
            "rules": [{"column": "tag", "relation": "equals", "condition": tag}],
            "published": True,
        }
    }


def create_smart_collection(client: ShopifyAPIClient, source: str, month: str, title: str) -> int:
    """Create smart collection via REST API. Returns collection id."""
    payload = build_collection_payload(source, month, title)
    result = client.rest_request("POST", "smart_collections.json", json=payload)
    collection_id = result["smart_collection"]["id"]
    logger.info("Created smart collection id=%d: %s", collection_id, title)
    return collection_id


def upload_image_and_set(client: ShopifyAPIClient, collection_id: int, image_path: Path) -> None:
    """Upload image to Shopify Files via staged upload, then set as collection image."""
    # Step 1: Staged upload — get PUT URL
    stage_mutation = """
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
    stage_vars = {
        "input": [{
            "filename": image_path.name,
            "mimeType": "image/jpeg",
            "resource": "IMAGE",
            "httpMethod": "PUT",
        }]
    }
    stage_result = client.graphql_request(stage_mutation, stage_vars)
    targets = stage_result["stagedUploadsCreate"]["stagedTargets"]
    if not targets:
        raise RuntimeError("Staged upload returned no targets")

    target = targets[0]
    put_url = target["url"]
    resource_url = target["resourceUrl"]

    # Step 2: PUT the file
    import requests
    with open(image_path, "rb") as f:
        resp = requests.put(put_url, data=f, headers={"Content-Type": "image/jpeg"})
    resp.raise_for_status()
    logger.info("Uploaded image to CDN: %s", resource_url)

    # Step 3: Set collection image via REST
    image_payload = {"smart_collection": {"image": {"src": resource_url}}}
    client.rest_request("PUT", f"smart_collections/{collection_id}.json", json=image_payload)
    logger.info("Set collection image for id=%d", collection_id)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Create a campaign smart collection")
    parser.add_argument("--source", required=True, help="Campaign source: phoenix, sopharmacy, etc.")
    parser.add_argument("--month", required=True, help="Campaign month: YYYY-MM")
    parser.add_argument("--title", required=True, help='Collection title, e.g. "Phoenix Промоции — Март 2026"')
    parser.add_argument("--image", help="Path to campaign banner JPG (optional)")
    args = parser.parse_args()

    shop, token = load_shopify_credentials()
    client = ShopifyAPIClient(shop, token)

    collection_id = create_smart_collection(client, args.source, args.month, args.title)
    print(f"Collection created: id={collection_id}")
    print(f"Tag rule: promo-{args.source}-{args.month}")

    if args.image:
        image_path = Path(args.image)
        if not image_path.exists():
            print(f"Error: image not found: {image_path}")
            sys.exit(1)
        upload_image_and_set(client, collection_id, image_path)
        print("Banner image uploaded and set.")

    client.close()

    print("\nNext steps:")
    print(f"1. Apply --campaign-tag promo-{args.source}-{args.month} when running sync_phoenix_promos.py apply")
    print("2. In Shopify Admin → Online Store → Customize → /collections/namaleniya:")
    print(f"   Add a collection block pointing to the new campaign collection")


if __name__ == "__main__":
    main()
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/scripts/test_create_campaign_collection.py -v
```
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add scripts/create_campaign_collection.py tests/scripts/__init__.py tests/scripts/test_create_campaign_collection.py
git commit -m "feat: add create_campaign_collection.py with unit tests"
```

---

## Task 5: viapharma-pricing — close_campaign.py

This script removes the campaign tag from all products and archives the smart collection.

**Files:**
- Create: `viapharma-pricing/scripts/close_campaign.py`
- Create: `viapharma-pricing/tests/scripts/test_close_campaign.py`

**Understanding the Shopify APIs:**
- **List products with tag (GraphQL):** `query { products(first: 250, query: "tag:promo-phoenix-2026-03") { edges { node { id } } } }` — paginate with cursor
- **Remove tags (GraphQL):** `tagsRemove(id: $id, tags: $tags)` mutation
- **Archive collection (REST):** `PUT /admin/api/2025-01/smart_collections/{id}.json` with `{"smart_collection": {"published": false}}`

**Step 1: Write failing tests**

Create `viapharma-pricing/tests/scripts/test_close_campaign.py`:

```python
"""Tests for close_campaign.py (unit tests — no live API calls)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_build_campaign_tag():
    """Campaign tag follows promo-{source}-{month} format."""
    from scripts.close_campaign import build_campaign_tag

    assert build_campaign_tag("phoenix", "2026-03") == "promo-phoenix-2026-03"
    assert build_campaign_tag("sopharmacy", "2026-04") == "promo-sopharmacy-2026-04"


def test_fetch_tagged_product_ids_returns_ids():
    """fetch_tagged_product_ids returns list of GIDs from paginated GraphQL."""
    from scripts.close_campaign import fetch_tagged_product_ids

    mock_client = MagicMock()
    mock_client.graphql_request.return_value = {
        "products": {
            "edges": [
                {"node": {"id": "gid://shopify/Product/1"}},
                {"node": {"id": "gid://shopify/Product/2"}},
            ],
            "pageInfo": {"hasNextPage": False, "endCursor": None},
        }
    }

    ids = fetch_tagged_product_ids(mock_client, "promo-phoenix-2026-03")

    assert ids == ["gid://shopify/Product/1", "gid://shopify/Product/2"]
    mock_client.graphql_request.assert_called_once()


def test_remove_tag_from_products_calls_mutation():
    """remove_tag_from_products calls tagsRemove for each product."""
    from scripts.close_campaign import remove_tag_from_products

    mock_client = MagicMock()
    mock_client.graphql_request.return_value = {
        "tagsRemove": {"node": {"id": "gid://shopify/Product/1"}, "userErrors": []}
    }

    result = remove_tag_from_products(
        mock_client,
        ["gid://shopify/Product/1", "gid://shopify/Product/2"],
        "promo-phoenix-2026-03",
    )

    assert mock_client.graphql_request.call_count == 2
    assert result["untagged"] == 2
    assert result["errors"] == 0


def test_archive_collection_calls_rest():
    """archive_collection sends PUT with published=false."""
    from scripts.close_campaign import archive_collection

    mock_client = MagicMock()
    mock_client.rest_request.return_value = {"smart_collection": {"id": 111, "published_at": None}}

    archive_collection(mock_client, 111)

    mock_client.rest_request.assert_called_once()
    call_args = mock_client.rest_request.call_args
    assert call_args[0][0] == "PUT"
    assert "smart_collections/111" in call_args[0][1]
    assert call_args[1]["json"]["smart_collection"]["published"] is False
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/scripts/test_close_campaign.py -v
```
Expected: `ModuleNotFoundError: No module named 'scripts.close_campaign'`

**Step 3: Implement close_campaign.py**

Create `viapharma-pricing/scripts/close_campaign.py`:

```python
#!/usr/bin/env python3
"""Close a campaign: remove tag from products and archive the smart collection.

Usage:
    python scripts/close_campaign.py --source phoenix --month 2026-03 --collection-id 987654321
    python scripts/close_campaign.py --source phoenix --month 2026-03 --collection-id 987654321 --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.credentials import load_shopify_credentials
from src.shopify.api_client import ShopifyAPIClient

logger = logging.getLogger(__name__)


def build_campaign_tag(source: str, month: str) -> str:
    return f"promo-{source}-{month}"


def fetch_tagged_product_ids(client: ShopifyAPIClient, tag: str) -> list[str]:
    """Fetch all product GIDs tagged with the campaign tag (paginated)."""
    query = """
    query getTaggedProducts($query: String!, $cursor: String) {
      products(first: 250, query: $query, after: $cursor) {
        edges { node { id } }
        pageInfo { hasNextPage endCursor }
      }
    }
    """
    ids = []
    cursor = None
    while True:
        result = client.graphql_request(query, {"query": f"tag:{tag}", "cursor": cursor})
        products = result["products"]
        for edge in products["edges"]:
            ids.append(edge["node"]["id"])
        page_info = products["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]
    return ids


def remove_tag_from_products(
    client: ShopifyAPIClient, product_gids: list[str], tag: str
) -> dict[str, int]:
    """Remove tag from each product via tagsRemove mutation."""
    mutation = """
    mutation tagsRemove($id: ID!, $tags: [String!]!) {
      tagsRemove(id: $id, tags: $tags) {
        node { id }
        userErrors { field message }
      }
    }
    """
    untagged = 0
    errors = 0
    for gid in product_gids:
        result = client.graphql_request(mutation, {"id": gid, "tags": [tag]})
        user_errors = result.get("tagsRemove", {}).get("userErrors", [])
        if user_errors:
            logger.warning("tagsRemove errors for %s: %s", gid, user_errors)
            errors += 1
        else:
            untagged += 1
    return {"untagged": untagged, "errors": errors}


def archive_collection(client: ShopifyAPIClient, collection_id: int) -> None:
    """Archive (unpublish) the smart collection."""
    client.rest_request(
        "PUT",
        f"smart_collections/{collection_id}.json",
        json={"smart_collection": {"published": False}},
    )
    logger.info("Archived collection id=%d", collection_id)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Close a promotional campaign")
    parser.add_argument("--source", required=True, help="Campaign source: phoenix, sopharmacy, etc.")
    parser.add_argument("--month", required=True, help="Campaign month: YYYY-MM")
    parser.add_argument("--collection-id", required=True, type=int, help="Shopify smart collection id to archive")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    args = parser.parse_args()

    tag = build_campaign_tag(args.source, args.month)
    print(f"Closing campaign: {tag}")
    print(f"Collection id to archive: {args.collection_id}")

    if args.dry_run:
        shop, token = load_shopify_credentials()
        client = ShopifyAPIClient(shop, token)
        ids = fetch_tagged_product_ids(client, tag)
        client.close()
        print(f"[DRY RUN] Would remove tag '{tag}' from {len(ids)} products")
        print(f"[DRY RUN] Would archive collection id={args.collection_id}")
        return

    shop, token = load_shopify_credentials()
    client = ShopifyAPIClient(shop, token)

    ids = fetch_tagged_product_ids(client, tag)
    print(f"Found {len(ids)} products tagged '{tag}'")

    if ids:
        result = remove_tag_from_products(client, ids, tag)
        print(f"Tag removed from {result['untagged']} products ({result['errors']} errors)")

    archive_collection(client, args.collection_id)
    print(f"Collection {args.collection_id} archived.")

    client.close()
    print("\nDone. Remember to remove the campaign block from /collections/namaleniya in Shopify Admin.")


if __name__ == "__main__":
    main()
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/scripts/test_close_campaign.py -v
```
Expected: All 4 tests PASS

**Step 5: Run all tests to confirm nothing broken**

```bash
pytest tests/ -v --tb=short 2>&1 | tail -20
```
Expected: All tests pass (same count as before + 7 new tests)

**Step 6: Commit**

```bash
git add scripts/close_campaign.py tests/scripts/test_close_campaign.py
git commit -m "feat: add close_campaign.py to remove campaign tags and archive collection"
```

---

## Final: Campaign Lifecycle Reference

After all tasks are implemented, the full campaign workflow is:

**START a campaign:**
```bash
# 1. Price + tag products (in viapharma-pricing):
python scripts/sync_phoenix_promos.py review
python scripts/sync_phoenix_promos.py apply output/phoenix_promos_review.csv \
    --campaign-tag promo-phoenix-2026-03

# 2. Sync discount tag (in pharmacy-to-shopify):
python scripts/tag_discounted_products.py

# 3. Create collection + upload banner (in viapharma-pricing):
python scripts/create_campaign_collection.py \
    --source phoenix --month 2026-03 \
    --title "Phoenix Промоции — Март 2026" \
    --image campaign_banner.jpg
# Note the collection id printed in output

# 4. Add campaign card in Shopify Admin:
#    Online Store → Customize → /collections/namaleniya
#    → "Активни кампании" section → Add block → select new collection
```

**END a campaign:**
```bash
# 1. Remove tag + archive (in viapharma-pricing):
python scripts/close_campaign.py \
    --source phoenix --month 2026-03 \
    --collection-id <id from create step>

# 2. Remove campaign card in Shopify Admin:
#    Online Store → Customize → /collections/namaleniya
#    → "Активни кампании" section → Remove the campaign block
```
