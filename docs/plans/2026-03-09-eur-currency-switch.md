# EUR Currency Switch Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Switch Shopify store base currency from BGN to EUR, re-import all products with EUR prices, and update all theme templates and email notifications so EUR is native and BGN is computed (×1.95583) everywhere.

**Architecture:** Three repos touched in sequence: (1) `pharmacy-to-shopify` — one-line CSV exporter fix + re-chunk + re-import; (2) `viapharma.us-theme` — invert EUR/BGN math in 5 theme files, push; (3) Shopify Admin manual steps (password mode, currency switch, shipping rates, email templates). `viapharma-pricing` is a follow-up session — must happen before the next repricing run.

**Tech Stack:** Python (csv_exporter.py), Shopify Admin REST + GraphQL API, Shopify Liquid (theme), pytest, ruff.

**Fixed rate:** 1 EUR = 1.95583 BGN (ERM II, unchanged after Eurozone accession)

**Pattern change everywhere in theme:**
- Old (BGN base): `price | divided_by: 1.95583 | round: 0` → EUR cents; `price | money` → BGN native
- New (EUR base): `price | money` → EUR native; `price | times: 1.95583 | round: 0` → BGN cents; display as `{{ bgn_cents | money_without_currency }} лв.`

---

## Phase 1 — pharmacy-to-shopify repo

### Task 1: Fix csv_exporter.py to export EUR prices

**Files:**
- Modify: `src/shopify/csv_exporter.py:122`
- Test: `tests/shopify/test_csv_exporter.py` (or nearest exporter test)

**Step 1: Read the current line**

Open `src/shopify/csv_exporter.py` and find line 122 (marked `TODO(EUR-transition)`):
```python
'Price': product.price,
```

**Step 2: Write a failing test first**

Find the existing CSV exporter test. Add:
```python
def test_csv_exports_eur_price():
    """After EUR transition: Price column must use price_eur, not price (BGN)."""
    product = make_test_product(price=11.70, price_eur=5.99)  # adapt to actual factory
    rows = export_product_rows(product)
    price_row = next(r for r in rows if r.get('Title'))
    assert price_row['Price'] == '5.99'
    assert price_row['Price'] != '11.70'
```

Run: `pytest tests/shopify/ -v -k test_csv_exports_eur_price`
Expected: FAIL

**Step 3: Make the one-line fix**

```python
# Before (line 122):
'Price': product.price,

# After:
'Price': product.price_eur,   # EUR transition: store base currency is now EUR
```

**Step 4: Run tests**

```bash
pytest tests/ -v
ruff check src/ tests/
```
Expected: all pass, no lint errors.

**Step 5: Commit**

```bash
git add src/shopify/csv_exporter.py tests/shopify/test_csv_exporter.py
git commit -m "feat: export EUR price in CSV — store base currency switched to EUR"
```

---

### Task 2: Re-chunk the product CSV with EUR prices

**Step 1: Run chunk_csv.py**

```bash
python scripts/chunk_csv.py data/benu.bg/raw/products.csv --chunk-size 1500 --output-dir output/2026.Mar.09.eur
```

Expected output:
```
Total products: ~10173
Expected chunks: 7
output/2026.Mar.09.eur/export_001.csv: 1500 products
...
output/2026.Mar.09.eur/export_007.csv: ~1173 products
Done! Created 7 files
```

**Step 2: Sanity check prices in first chunk**

```bash
python3 -c "
import csv
with open('output/2026.Mar.09.eur/export_001.csv') as f:
    rows = [r for r in csv.DictReader(f) if r.get('Title')][:5]
for r in rows:
    print(r['Title'][:40], '| Price:', r['Price'], '| Price EUR:', r.get('Price EUR',''))
"
```

Expected: `Price` column shows EUR values (e.g. `5.99`), which should match `Price EUR` column.

---

## Phase 2 — Shopify Admin (manual steps)

### Task 3: Enable password mode

1. Go to **Shopify Admin → Online Store → Preferences**
2. Under **Password protection**, enable **Restrict access to visitors with the password**
3. Set a temporary password (e.g. `temp2026`)
4. Click **Save**

> This prevents orders at wrong prices during the currency switch + re-import window (~45 min).

---

### Task 4: Switch store base currency to EUR

1. Go to **Shopify Admin → Settings → Store currency**
2. Click **Change store currency**
3. Select **Euro (EUR) — €**
4. Confirm the warning ("This will affect all your product prices")
5. Click **Save**

> ⚠️ After this step all existing product prices show the wrong amount (e.g. "€11.60" instead of "€5.99"). This is expected — the re-import in Task 5 fixes it.

---

### Task 5: Update shipping rates to EUR

Run this script from `pharmacy-to-shopify` repo:

```bash
python3 << 'EOF'
import requests, json

TOKEN = "<SHOPIFY_ACCESS_TOKEN>"
GRAPHQL_URL = "https://61a7bb-4d.myshopify.com/admin/api/2025-04/graphql.json"
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

PROFILE_ID = "gid://shopify/DeliveryProfile/116719583569"
LOCATION_GROUP_ID = "gid://shopify/DeliveryLocationGroup/118187000145"
ZONE_ID = "gid://shopify/DeliveryZone/547227074897"

# Get current method IDs to delete them
query = """
{
  deliveryProfiles(first: 1) {
    nodes {
      profileLocationGroups {
        locationGroupZones(first: 5) {
          nodes {
            methodDefinitions(first: 10) {
              nodes { id name }
            }
          }
        }
      }
    }
  }
}
"""
r = requests.post(GRAPHQL_URL, headers=HEADERS, json={"query": query})
methods = r.json()["data"]["deliveryProfiles"]["nodes"][0]["profileLocationGroups"][0]["locationGroupZones"]["nodes"][0]["methodDefinitions"]["nodes"]
ids_to_delete = [m["id"] for m in methods]
print("Deleting:", [m["name"] for m in methods])

# EUR equivalents (BGN / 1.95583, rounded to 2 decimal places)
eur_rates = [
    ("Speedy до офис/автомат (промо до 31.03)", "1.52"),
    ("Speedy до офис/автомат", "2.44"),
    ("Econt до офис", "3.40"),
    ("Speedy до адрес", "4.78"),
    ("Econt до адрес", "5.61"),
]

mutation = """
mutation UpdateDeliveryProfile($id: ID!, $profile: DeliveryProfileInput!) {
  deliveryProfileUpdate(id: $id, profile: $profile) {
    profile {
      profileLocationGroups {
        locationGroupZones(first: 5) {
          nodes {
            methodDefinitions(first: 10) {
              nodes { name active rateProvider { ... on DeliveryRateDefinition { price { amount currencyCode } } } }
            }
          }
        }
      }
    }
    userErrors { field message }
  }
}
"""

variables = {
    "id": PROFILE_ID,
    "profile": {
        "methodDefinitionsToDelete": ids_to_delete,
        "locationGroupsToUpdate": [{
            "id": LOCATION_GROUP_ID,
            "zonesToUpdate": [{
                "id": ZONE_ID,
                "methodDefinitionsToCreate": [
                    {"name": name, "active": True, "rateDefinition": {"price": {"amount": price, "currencyCode": "EUR"}}}
                    for name, price in eur_rates
                ]
            }]
        }]
    }
}

r = requests.post(GRAPHQL_URL, headers=HEADERS, json={"query": mutation, "variables": variables})
result = r.json()
errors = result.get("data", {}).get("deliveryProfileUpdate", {}).get("userErrors", [])
if errors:
    print("Errors:", errors)
else:
    methods = result["data"]["deliveryProfileUpdate"]["profile"]["profileLocationGroups"][0]["locationGroupZones"]["nodes"][0]["methodDefinitions"]["nodes"]
    for m in methods:
        price = m["rateProvider"].get("price", {})
        print(f"  ✓ {m['name']} — {price.get('amount')} {price.get('currencyCode')}")
EOF
```

Expected:
```
✓ Speedy до офис/автомат (промо до 31.03) — 1.52 EUR
✓ Speedy до офис/автомат — 2.44 EUR
✓ Econt до офис — 3.40 EUR
✓ Speedy до адрес — 4.78 EUR
✓ Econt до адрес — 5.61 EUR
```

---

### Task 6: Re-import all 7 EUR product chunks

1. Go to **Shopify Admin → Products → Import**
2. Import each file in order, checking **"Overwrite existing products with matching handles"**:
   - `output/2026.Mar.09.eur/export_001.csv`
   - `output/2026.Mar.09.eur/export_002.csv`
   - `output/2026.Mar.09.eur/export_003.csv`
   - `output/2026.Mar.09.eur/export_004.csv`
   - `output/2026.Mar.09.eur/export_005.csv`
   - `output/2026.Mar.09.eur/export_006.csv`
   - `output/2026.Mar.09.eur/export_007.csv`
3. Wait for each import to complete before starting the next one (~5 min each)

> If any chunk times out again, re-chunk at 1000 products: `--chunk-size 1000`

---

## Phase 3 — viapharma.us-theme repo

> Work in `/Users/kiril/IdeaProjects/viapharma.us-theme`. Pull latest before starting:
> ```bash
> cd /Users/kiril/IdeaProjects/viapharma.us-theme && git pull
> ```

**Key transformation pattern (apply to all files below):**

| Old (BGN base) | New (EUR base) |
|---|---|
| `assign eur_cents = price \| divided_by: 1.95583 \| round: 0` | *(remove — EUR is native)* |
| `€{{ eur_cents \| money_without_currency }}` | `{{ price \| money }}` |
| `{{ price \| money }}` *(was BGN native)* | `{%- assign bgn_cents = price \| times: 1.95583 \| round: 0 -%}{{ bgn_cents \| money_without_currency }} лв.` |

---

### Task 7: Fix snippets/price.liquid

**File:** `snippets/price.liquid`

Key lines to change (find by content, not hardcoded line numbers):

**Block 1 — regular price:**
```liquid
<!-- BEFORE -->
{%- assign eur_cents = price | divided_by: 1.95583 | round: 0 -%}
{%- assign compare_at_eur_cents = compare_at_price | divided_by: 1.95583 | round: 0 -%}
...
<span class="price-item price-item--regular price-item--eur">
  €{{ eur_cents | money_without_currency }}
</span>
<span class="price-item price-item--bgn">
  {{ price | money }}
</span>

<!-- AFTER -->
{%- assign bgn_cents = price | times: 1.95583 | round: 0 -%}
{%- assign compare_at_bgn_cents = compare_at_price | times: 1.95583 | round: 0 -%}
...
<span class="price-item price-item--regular price-item--eur">
  {{ price | money }}
</span>
<span class="price-item price-item--bgn">
  {{ bgn_cents | money_without_currency }} лв.
</span>
```

**Block 2 — sale price (struck-through compare_at):**
```liquid
<!-- BEFORE -->
<span class="price-item price-item--sale price-item--eur">
  €{{ eur_cents | money_without_currency }}
</span>
<s class="price-item price-item--regular price-item--eur">
  €{{ compare_at_eur_cents | money_without_currency }}
</s>
<span class="price-item price-item--bgn">
  {{ price | money }}  (and compare_at equivalent)
</span>

<!-- AFTER -->
<span class="price-item price-item--sale price-item--eur">
  {{ price | money }}
</span>
<s class="price-item price-item--regular price-item--eur">
  {{ compare_at_price | money }}
</s>
<span class="price-item price-item--bgn">
  {{ bgn_cents | money_without_currency }} лв.  (and compare_at_bgn_cents equivalent)
</span>
```

After editing, push:
```bash
cd /Users/kiril/IdeaProjects/pharmacy-to-shopify
python scripts/push_theme.py snippets/price.liquid
```

---

### Task 8: Fix snippets/cart-drawer.liquid

**File:** `snippets/cart-drawer.liquid`

Find all occurrences of `divided_by: 1.95583` (there are ~6). Apply pattern:

```liquid
<!-- BEFORE (example — line item price) -->
{%- assign drawer_orig_eur = item.original_price | divided_by: 1.95583 | round: 0 -%}
{%- assign drawer_final_eur = item.final_price | divided_by: 1.95583 | round: 0 -%}
...
€{{ drawer_final_eur | money_without_currency }}
<span class="price-item--bgn">{{ item.final_price | money }}</span>

<!-- AFTER -->
{%- assign drawer_orig_bgn = item.original_price | times: 1.95583 | round: 0 -%}
{%- assign drawer_final_bgn = item.final_price | times: 1.95583 | round: 0 -%}
...
{{ item.final_price | money }}
<span class="price-item--bgn">{{ drawer_final_bgn | money_without_currency }} лв.</span>
```

Apply same pattern to all 6 occurrences (line prices, line totals, cart total).

**Cart total block (around line 527):**
```liquid
<!-- BEFORE -->
{%- assign cart_eur_cents = cart.total_price | divided_by: 1.95583 | round: 0 -%}
<p class="totals__total-value h5">€{{ cart_eur_cents | money_without_currency }}</p>
<p class="totals__bgn-note">{{ cart.total_price | money_with_currency }}</p>

<!-- AFTER -->
{%- assign cart_bgn_cents = cart.total_price | times: 1.95583 | round: 0 -%}
<p class="totals__total-value h5">{{ cart.total_price | money }}</p>
<p class="totals__bgn-note">{{ cart_bgn_cents | money_without_currency }} лв.</p>
```

**Remove the EUR notice paragraph** (no longer needed — checkout shows EUR natively):
```liquid
<!-- REMOVE this line entirely -->
<p class="cart__eur-notice">💳 Плащането се извършва в евро (EUR). 1 € = 1.9558 лв.</p>
```

Push:
```bash
python scripts/push_theme.py snippets/cart-drawer.liquid
```

---

### Task 9: Fix sections/main-cart-footer.liquid

**File:** `sections/main-cart-footer.liquid`

Around line 123:
```liquid
<!-- BEFORE -->
{%- assign cart_eur_cents = cart.total_price | divided_by: 1.95583 | round: 0 -%}
<p class="totals__total-value">€{{ cart_eur_cents | money_without_currency }}</p>
<p class="totals__bgn-note">{{ cart.total_price | money_with_currency }}</p>

<!-- AFTER -->
{%- assign cart_bgn_cents = cart.total_price | times: 1.95583 | round: 0 -%}
<p class="totals__total-value">{{ cart.total_price | money }}</p>
<p class="totals__bgn-note">{{ cart_bgn_cents | money_without_currency }} лв.</p>
```

Remove the EUR notice paragraph (~line 163):
```liquid
<!-- REMOVE -->
<p class="cart__eur-notice">💳 Плащането се извършва в евро (EUR). 1 € = 1.9558 лв.</p>
```

Push:
```bash
python scripts/push_theme.py sections/main-cart-footer.liquid
```

---

### Task 10: Fix sections/main-cart-items.liquid

**File:** `sections/main-cart-items.liquid`

Same pattern as cart-drawer. Find all `divided_by: 1.95583` occurrences (~6) and apply:
- Remove EUR computation assignments
- Change `€{{ eur_var | money_without_currency }}` → `{{ item.price | money }}` (or appropriate price variable)
- Change `{{ item.price | money }}` (was BGN) → `{%- assign bgn = item.price | times: 1.95583 | round: 0 -%}{{ bgn | money_without_currency }} лв.`

Push:
```bash
python scripts/push_theme.py sections/main-cart-items.liquid
```

---

### Task 11: Fix savings badge in snippets/card-product.liquid

**File:** `snippets/card-product.liquid` (~line 158)

```liquid
<!-- BEFORE -->
{%- assign savings_raw = card_product.compare_at_price | minus: card_product.price -%}
{%- assign savings_eur = savings_raw | divided_by: 1.95583 | round: 0 -%}
{%- assign savings_bgn = savings_raw | money_without_trailing_zeros -%}
<!-- badge shows: €X.XX / Y.YY лв -->

<!-- AFTER -->
{%- assign savings_raw = card_product.compare_at_price | minus: card_product.price -%}
{%- assign savings_bgn_cents = savings_raw | times: 1.95583 | round: 0 -%}
{%- assign savings_bgn = savings_bgn_cents | money_without_currency -%}
<!-- badge shows: €X.XX / Y.YY лв  (savings_raw is now EUR cents natively) -->
```

The EUR part of the badge: replace `€{{ savings_eur | money_without_currency }}` with `{{ savings_raw | money_without_currency | prepend: '€' }}` or simply `{{ savings_raw | money }}`.

Push:
```bash
python scripts/push_theme.py snippets/card-product.liquid
```

---

### Task 12: Commit theme changes

```bash
cd /Users/kiril/IdeaProjects/viapharma.us-theme
git add snippets/price.liquid snippets/cart-drawer.liquid snippets/card-product.liquid \
        sections/main-cart-footer.liquid sections/main-cart-items.liquid
git commit -m "feat: invert EUR/BGN math after store currency switch to EUR

EUR is now native (price | money). BGN computed as price × 1.95583.
Remove cart EUR notices — checkout now shows EUR natively."
git push
```

---

## Phase 4 — Email notification templates (Shopify Admin, manual)

> Go to **Shopify Admin → Settings → Notifications**

The current email templates compute EUR via `divided_by: 1.95583`. After the currency switch, all price variables (`line_item.final_price`, `subtotal_price`, `total_price`, etc.) are already EUR. The pattern inverts exactly as in the theme.

**Pattern for each price field in emails:**

```liquid
<!-- BEFORE -->
{%- assign li_eur = line_item.final_price | divided_by: 1.95583 | round: 0 -%}
€{{ li_eur | money_without_currency }} <small style="color:#999;">({{ line_item.final_price | money }} лв.)</small>

<!-- AFTER -->
{%- assign li_bgn = line_item.final_price | times: 1.95583 | round: 0 -%}
{{ line_item.final_price | money }} <small style="color:#999;">({{ li_bgn | money_without_currency }} лв.)</small>
```

Apply to these templates:

### Task 13: Update Order confirmation email
- Edit in Admin → Settings → Notifications → Order confirmation
- Apply pattern to: line item price, line item total, subtotal, discounts, shipping, total
- The ready-to-paste originals are in `docs/plans/order-confirmation-original.liquid` — use as reference for structure, then apply the new pattern
- Save

### Task 14: Update Shipping confirmation email
- Edit in Admin → Settings → Notifications → Shipping confirmation
- Same pattern, fewer price fields
- Reference: `docs/plans/shipping-confirmation-eur.liquid` (adapt pattern direction)
- Save

### Task 15: Update Order edited email
- Edit in Admin → Settings → Notifications → Order edited
- Same pattern
- Reference: `docs/plans/order-edited-original.liquid`
- Save

---

## Phase 5 — Re-enable store

### Task 16: Disable password mode

1. Go to **Shopify Admin → Online Store → Preferences**
2. Disable password protection
3. Save

### Task 17: Verify end-to-end

1. Visit [viapharma.us](https://viapharma.us) — product cards should show EUR primary, лв secondary
2. Open a product page — same
3. Add to cart, open drawer — EUR total + лв note
4. Proceed to checkout — EUR prices natively in Shopify checkout (no manual computation)
5. Check a product with compare_at — savings badge shows `€X.XX / Y.YY лв`

Quick price sanity check via API:
```bash
python3 -c "
import requests
TOKEN = '<SHOPIFY_ACCESS_TOKEN>'
r = requests.get(
    'https://61a7bb-4d.myshopify.com/admin/api/2025-04/products.json?limit=5',
    headers={'X-Shopify-Access-Token': TOKEN}
)
for p in r.json()['products']:
    v = p['variants'][0]
    print(p['title'][:40], '| price:', v['price'])
"
```
Expected: prices are EUR values (e.g. `5.99`, not `11.70`).

---

## Phase 6 — viapharma-pricing (SEPARATE SESSION — before next repricing run)

> ⚠️ Do NOT run any repricing until this is done. If repricing runs before this fix, it will push BGN values as EUR prices (wrong by factor of ~2).

**Files to change in `viapharma-pricing` repo:**

1. `price_calculator.py` — remove `× BGN_PER_EUR` (or `× 1.95583`) conversions; keep prices in EUR throughout
2. `reprice_competitive.py` / `benu_catalog.py` — swap benu price source from `Price` (BGN column) to `Price EUR` column
3. Run full test suite after changes: `pytest`
4. Do a `--sample 10 --dry-run` repricing pass to verify EUR values look correct before applying

---

## Summary Checklist

```
Phase 1 — pharmacy-to-shopify
[ ] Task 1: Fix csv_exporter.py:122 (price → price_eur) + test + commit
[ ] Task 2: Re-chunk CSV to output/2026.Mar.09.eur/ (7 files, 1500 products each)

Phase 2 — Shopify Admin
[ ] Task 3: Enable password mode
[ ] Task 4: Switch store currency BGN → EUR
[ ] Task 5: Update shipping rates to EUR (script provided above)
[ ] Task 6: Re-import all 7 EUR CSV chunks

Phase 3 — viapharma.us-theme
[ ] Task 7: Fix snippets/price.liquid + push
[ ] Task 8: Fix snippets/cart-drawer.liquid + push
[ ] Task 9: Fix sections/main-cart-footer.liquid + push
[ ] Task 10: Fix sections/main-cart-items.liquid + push
[ ] Task 11: Fix snippets/card-product.liquid savings badge + push
[ ] Task 12: Commit theme changes

Phase 4 — Email templates (Shopify Admin)
[ ] Task 13: Update Order confirmation email
[ ] Task 14: Update Shipping confirmation email
[ ] Task 15: Update Order edited email

Phase 5 — Re-enable
[ ] Task 16: Disable password mode
[ ] Task 17: Verify end-to-end (storefront + checkout + prices sanity check)

Phase 6 — viapharma-pricing (separate session)
[ ] Fix price_calculator.py — remove BGN conversion
[ ] Fix benu price source to use Price EUR column
[ ] Run pytest
[ ] Dry-run repricing sample before applying
```
