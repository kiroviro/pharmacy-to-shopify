# Discount Visibility Design

**Date:** 2026-03-02
**Context:** ~4,691 of ~10,500 products are getting price decreases. Pricing is managed by a separate project that sets `compare_at_price` on Shopify variants. This design covers the visibility layer only.

## Changes

### 1. Smart Collection "Намаления"

Create a Shopify smart collection via Admin API:

- **Title:** Намаления
- **Handle:** `namaleniya`
- **Rule:** `variant_compare_at_price > 0` (auto-includes any product with compare_at_price set)
- **Fully automatic:** Products appear/disappear as compare_at_price changes — no maintenance needed

Implementation: standalone script or addition to `create_shopify_collections.py`.

### 2. Top-Level Menu Item "Намаления"

Add "Намаления" as a top-level item in the main navigation menu, linking to `/collections/namaleniya`.

Implementation: Shopify GraphQL `menuItemCreate` via existing menu API patterns.

### 3. Tagging Script

New script that queries all Shopify products and adds/removes a `Намаление` tag based on discount status:

- **Add tag** when `variant.compare_at_price > variant.price`
- **Remove tag** when product is no longer discounted
- **Idempotent:** Skip products already correctly tagged
- **Scope:** All ~10,500 products; ~4,691 expected to be tagged

Enables storefront filtering by discount status.

### 4. Badge Style Change

Config-only change in `settings_data.json`:

- `sale_badge_style`: `"sale"` → `"saving"`
- Add `saving_badge_text`: `"Спести"`

Result: badges show "Спести 5.40 лв" instead of generic "On Sale". Theme Liquid already calculates `compare_at_price - price` and formats with `money_without_trailing_zeros`.

## Out of Scope

- Setting/managing `compare_at_price` (handled by separate pricing project)
- Announcement bar or additional promotional banners
- Tiered discount tags (e.g., "10-20%", "20-50%")
