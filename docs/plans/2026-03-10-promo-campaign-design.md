# Recurring Promotional Campaign System — Design

**Date:** 2026-03-10
**Status:** Approved

## Goal

Surface recurring promotional campaigns (Phoenix, SoPharmacy, email-based) with maximum visual impact on viapharma.us — homepage hero banner + per-campaign collection pages + unified "Намаления" page — all self-updating when viapharma-pricing runs, with no manual theme deploys per campaign.

## Architecture

Two repos collaborate via a data contract:

- **viapharma-pricing** owns: setting prices, tagging products, creating/closing campaign collections, uploading banners
- **viapharma.us-theme** owns: displaying everything automatically based on what viapharma-pricing writes to Shopify

After one-time theme setup, every future campaign requires only running scripts in viapharma-pricing.

## Data Contract (viapharma-pricing → Shopify → theme)

For each campaign batch, viapharma-pricing must:

1. `compare_at_price` set on variants → products auto-join `namaleniya` smart collection *(already done)*
2. Campaign tag applied to products: `promo-{source}-{YYYY-MM}` (e.g. `promo-phoenix-2026-03`)
3. Smart collection created with rule `tag = promo-phoenix-2026-03`, title "Phoenix Промоции — Март 2026"
4. Banner image uploaded to Shopify Files; `homepage_discount_banner` section updated via Assets API
5. At campaign end: campaign tag removed from products, collection archived

## Section 1: Theme Changes (one-time setup)

### Homepage (`templates/index.json`)

| Change | Detail |
|--------|--------|
| `featured_collection` section | Point to `namaleniya` instead of "Грип и настинка" |
| "Грип и настинка" | Move as a new tab in existing `collection-tabs` ("Популярни продукти") |
| `homepage_discount_banner` | Already on homepage; image updated via Assets API each campaign |

### `/collections/namaleniya` — alternate template

- Create `templates/collection.namaleniya.json` (Shopify alternate collection template)
- Add `collection-list` block at the top → shows current per-campaign collection cards
- Standard product grid below (existing, unchanged)
- The main `templates/collection.json` is NOT modified (shared by all other collections)

## Section 2: viapharma-pricing New Scripts

### `scripts/create_campaign_collection.py`

Run once per campaign batch after repricing:

```bash
python scripts/create_campaign_collection.py \
  --source phoenix \
  --month 2026-03 \
  --title "Phoenix Промоции — Март 2026" \
  --image campaign_banner.jpg
```

Steps performed:
1. Creates Shopify smart collection with rule `tag = promo-{source}-{YYYY-MM}`
2. Uploads `campaign_banner.jpg` via Shopify staged uploads + `fileCreate` mutation
3. Sets collection image to the uploaded file
4. Patches `templates/index.json` via Assets API to update `homepage_discount_banner` image

### `scripts/close_campaign.py`

Run when campaign period ends:

```bash
python scripts/close_campaign.py --source phoenix --month 2026-03
```

Steps performed:
1. Removes `promo-phoenix-2026-03` tag from all products (GraphQL batch mutations)
2. Archives (or deletes) the campaign collection

### Tagging wired into existing workflow

`sync_phoenix_promos.py apply` extended to accept `--campaign-tag promo-phoenix-2026-03`
and apply it to each repriced product alongside the existing `compare_at_price` write.

## Section 3: Campaign Lifecycle

```
CAMPAIGN START:
  python scripts/sync_phoenix_promos.py review
  python scripts/sync_phoenix_promos.py apply --campaign-tag promo-phoenix-2026-03
  python pharmacy-to-shopify/scripts/tag_discounted_products.py
  python scripts/create_campaign_collection.py --source phoenix --month 2026-03 \
    --title "Phoenix Промоции — Март 2026" --image banner.jpg

CAMPAIGN END (next month before new campaign):
  python scripts/close_campaign.py --source phoenix --month 2026-03
```

Multiple concurrent campaigns (Phoenix + SoPharmacy) are fully supported — each has its own tag and collection, both show as cards on the namaleniya page.

## Section 4: AI Image Prompt Template

Generate campaign banner images with this DALL-E prompt (fill in `[ ]` fields):

```
A clean, modern pharmacy promotional banner for a Bulgarian online pharmacy.
Wide landscape format (1600×900px), white or very light background.
Prominently feature [PRODUCT CATEGORY, e.g. "vitamins and supplements" or "cold & flu remedies"].
Bold headline space on the left third for text: "[CAMPAIGN HEADLINE, e.g. 'До 30% отстъпка']".
Use teal (#0096C7) and green (#10B981) as accent colors.
Professional, trustworthy medical aesthetic. No AI-generated text or letters visible.
Soft product imagery on the right two thirds. Minimalist, Apple-inspired design.
High resolution, suitable for a hero banner.
```

Upload the result as `campaign_banner.jpg` and pass to `create_campaign_collection.py --image`.

## Implementation Scope by Repo

| Repo | Work |
|------|------|
| `viapharma.us-theme` | 1. Update `index.json` (swap featured-collection + add Грип tab) <br> 2. Create `templates/collection.namaleniya.json` with collection-list block |
| `viapharma-pricing` | 1. Extend `sync_phoenix_promos.py` with `--campaign-tag` <br> 2. New `create_campaign_collection.py` <br> 3. New `close_campaign.py` |
| `pharmacy-to-shopify` | No changes needed |

## Key Constraints

- Shopify non-Plus: no Checkout UI Extensions, no custom storefront
- Theme: Liquid + vanilla JS, no build step; deploy via `push_theme.py`
- `templates/collection.json` must NOT be modified (shared by all collections)
- Assets API write is the same mechanism as `push_theme.py` — safe to use
- Per-campaign collections must be cleanly deletable (no orphan data)
