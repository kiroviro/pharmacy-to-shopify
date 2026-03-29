# Ликвидация Section — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Ликвидации" homepage section and `/collections/likvidatsii` collection page that show products with ≥15% discount, sorted by biggest discount first, using client-side JS fetch/filter/sort — no scripts, no tags, no cron.

**Architecture:** A new Shopify smart collection (`likvidatsii`, same `compare_at_price > 0` rule as `namaleniya`) provides the collection URL and page. A reusable `sections/liquidation-products.liquid` section (homepage + collection page) renders a Liquid shell; on DOMContentLoaded the shared `assets/liquidation-products.js` fetches all pages of `namaleniya/products.json`, filters to ≥15% discount, sorts descending, and renders product cards. The homepage shows 8 products with a "Виж всички" link; the collection page shows all with load-more.

**Tech Stack:** Python (pytest, `ShopifyCollectionCreator`), Shopify Admin REST API, Liquid, vanilla JS (no build step), `push_theme.py`

---

## File Map

| File | Action | Repo |
|------|--------|------|
| `src/shopify/collections.py` | Modify — add `create_liquidation_collection()` | pharmacy-to-shopify |
| `tests/shopify/test_collections.py` | Modify — add `TestCreateLiquidationCollection` | pharmacy-to-shopify |
| `assets/liquidation-products.js` | Create | viapharma.us-theme |
| `sections/liquidation-products.liquid` | Create | viapharma.us-theme |
| `templates/collection.likvidatsii.json` | Create | viapharma.us-theme |
| `templates/index.json` | Modify — add section before `featured_collection` | viapharma.us-theme |

---

### Task 1: Add `create_liquidation_collection()` to `ShopifyCollectionCreator`

**Files:**
- Modify: `src/shopify/collections.py` (after `create_sale_collection`, ~line 169)
- Modify: `tests/shopify/test_collections.py` (append new test class)

All commands in `/Users/kiril/IdeaProjects/pharmacy-to-shopify/`.

- [ ] **Step 1: Write failing tests**

Append to `tests/shopify/test_collections.py`:

```python
# ---------------------------------------------------------------------------
# Liquidation collection (compare_at_price > 0, handle = likvidatsii)
# ---------------------------------------------------------------------------


class TestCreateLiquidationCollection:
    def test_dry_run_returns_true(self):
        creator = _creator(dry_run=True)
        result = creator.create_liquidation_collection()
        assert result is True

    def test_dry_run_prints_preview(self, capsys):
        creator = _creator(dry_run=True)
        creator.create_liquidation_collection()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "Ликвидации" in captured.out
        assert "variant_compare_at_price" in captured.out
        assert "greater_than" in captured.out

    def test_dry_run_does_not_call_api(self):
        creator = _creator(dry_run=True)
        calls = []
        creator.client.rest_request = lambda *a, **kw: calls.append((a, kw))
        creator.create_liquidation_collection()
        assert len(calls) == 0

    def test_calls_api_with_correct_handle(self):
        creator = _creator(dry_run=False)
        post_calls = []

        def fake_rest(method, endpoint, data=None):
            if method == "POST":
                post_calls.append(data)
                return {"smart_collection": {"id": 99, "title": "Ликвидации"}}
            return None

        creator.client.rest_request = fake_rest
        result = creator.create_liquidation_collection()

        assert result is True
        assert len(post_calls) == 1
        sc = post_calls[0]["smart_collection"]
        assert sc["handle"] == "likvidatsii"
        assert sc["title"] == "Ликвидации"
        rule = sc["rules"][0]
        assert rule["column"] == "variant_compare_at_price"
        assert rule["relation"] == "greater_than"
        assert rule["condition"] == "0"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/shopify/test_collections.py::TestCreateLiquidationCollection -v
```

Expected: `AttributeError: 'ShopifyCollectionCreator' object has no attribute 'create_liquidation_collection'`

- [ ] **Step 3: Add `create_liquidation_collection()` to `src/shopify/collections.py`**

Insert after `create_sale_collection` (~line 168):

```python
    def create_liquidation_collection(self, title: str = "Ликвидации") -> bool:
        """Create the liquidation smart collection (compare_at_price > 0).

        Uses a hardcoded handle 'likvidatsii' so the URL is always
        /collections/likvidatsii regardless of how the title is transliterated.
        """
        handle = "likvidatsii"

        data = {
            "smart_collection": {
                "title": title,
                "handle": handle,
                "rules": [
                    {
                        "column": "variant_compare_at_price",
                        "relation": "greater_than",
                        "condition": "0",
                    }
                ],
                "disjunctive": False,
                "published": True,
            }
        }

        if self.dry_run:
            print(f"  [DRY RUN] Would create: {title} (variant_compare_at_price: greater_than 0, handle: {handle})")
            return True

        result = self.client.rest_request("POST", "smart_collections.json", data)

        if result and "smart_collection" in result:
            collection_id = result["smart_collection"]["id"]
            logger.info("Created: %s (ID: %s, handle: %s)", title, collection_id, handle)
            return True

        logger.error("Failed to create: %s", title)
        return False
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/shopify/test_collections.py::TestCreateLiquidationCollection -v
```

Expected: all 4 tests PASS

- [ ] **Step 5: Run full test suite — no regressions**

```bash
pytest tests/shopify/test_collections.py -v
```

Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/shopify/collections.py tests/shopify/test_collections.py
git commit -m "feat: add create_liquidation_collection() to ShopifyCollectionCreator"
```

---

### Task 2: Create the Ликвидации Shopify Collection

All commands in `/Users/kiril/IdeaProjects/pharmacy-to-shopify/`.

- [ ] **Step 1: Dry-run first**

```bash
python scripts/create_sale_collection.py --title Ликвидации --dry-run
```

Expected output includes `[DRY RUN]` and `Ликвидации`.

Wait — `create_sale_collection.py` calls `creator.create_sale_collection()`, not `create_liquidation_collection()`. Update the script first.

- [ ] **Step 2: Add `--likvidatsii` flag to `scripts/create_sale_collection.py`**

Replace the `main()` function body in `scripts/create_sale_collection.py`:

```python
def main():
    parser = argparse.ArgumentParser(description="Create or update sale/liquidation smart collections")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't modify Shopify")
    parser.add_argument("--update", action="store_true", help="Update the rule on an existing collection in-place")
    parser.add_argument("--title", default="Намаления", help="Collection title (default: Намаления)")
    parser.add_argument("--likvidatsii", action="store_true", help="Create the Ликвидации collection (handle: likvidatsii)")
    parser.add_argument("--verbose", action="store_true", help="Debug logging")

    args = parser.parse_args()
    setup_logging(verbose=args.verbose)

    shop, token = load_shopify_credentials()

    print("=" * 60)
    print("Sale Collection Creator")
    print("=" * 60)
    print(f"  Shop:    {shop}")
    print(f"  Dry run: {args.dry_run}")

    creator = ShopifyCollectionCreator(shop=shop, access_token=token, dry_run=args.dry_run)

    if args.likvidatsii:
        print("  Mode:    create Ликвидации collection")
        ok = creator.create_liquidation_collection()
        verb = "Created" if ok else "Failed to create"
        print(f"\n  {verb} collection: Ликвидации (handle: likvidatsii)")
    elif args.update:
        print(f"  Title:   {args.title}")
        print("  Mode:    update")
        ok = creator.update_sale_collection(title=args.title)
        verb = "Updated" if ok else "Failed to update"
        print(f"\n  {verb} collection: {args.title}")
    else:
        print(f"  Title:   {args.title}")
        print("  Mode:    create")
        if not args.dry_run and creator.collection_exists(args.title):
            print(f"\n  Collection '{args.title}' already exists. Use --update to change its rule.")
            return
        ok = creator.create_sale_collection(title=args.title)
        verb = "Created" if ok else "Failed to create"
        print(f"\n  {verb} collection: {args.title}")

    if not ok:
        sys.exit(1)
```

- [ ] **Step 3: Dry-run**

```bash
python scripts/create_sale_collection.py --likvidatsii --dry-run
```

Expected:
```
============================================================
Sale Collection Creator
============================================================
  Shop:    61a7bb-4d
  Dry run: True
  Mode:    create Ликвидации collection
  [DRY RUN] Would create: Ликвидации (variant_compare_at_price: greater_than 0, handle: likvidatsii)

  Created collection: Ликвидации (handle: likvidatsii)
```

- [ ] **Step 4: Create the collection for real**

```bash
python scripts/create_sale_collection.py --likvidatsii
```

Expected: `Created collection: Ликвидации (handle: likvidatsii)` with no errors.

Verify: open `https://viapharma.us/collections/likvidatsii` in browser — should show 2000+ discounted products (same as namaleniya).

- [ ] **Step 5: Commit**

```bash
git add scripts/create_sale_collection.py
git commit -m "feat: add --likvidatsii flag to create_sale_collection.py"
```

---

### Task 3: Build `assets/liquidation-products.js`

All file edits in `/Users/kiril/IdeaProjects/viapharma.us-theme/`.

This is the shared JS module used by both the homepage section and the collection page.

- [ ] **Step 1: Create `assets/liquidation-products.js`**

```javascript
/**
 * liquidation-products.js
 *
 * Fetches products from a Shopify collection, filters to those with ≥ minDiscount,
 * sorts descending by discount %, and renders product cards into a grid container.
 *
 * Used by sections/liquidation-products.liquid (homepage + collection page).
 * Entry point: window.initLiquidationSection(cfg)
 */

(function () {
  'use strict';

  // ── Pure helpers (exported for console testing) ───────────────────────────

  /**
   * Returns discount fraction [0–1] or null if data is missing/invalid.
   * @param {number} price - sale price in EUR
   * @param {number} compareAt - original price in EUR
   * @returns {number|null}
   */
  function computeDiscount(price, compareAt) {
    if (!compareAt || compareAt <= 0 || price <= 0 || price >= compareAt) return null;
    return (compareAt - price) / compareAt;
  }

  /**
   * Fetches all products from /collections/{handle}/products.json, page by page.
   * @param {string} collectionHandle
   * @returns {Promise<Array>}
   */
  async function fetchAllProducts(collectionHandle) {
    const all = [];
    let page = 1;
    while (true) {
      let res;
      try {
        res = await fetch(`/collections/${collectionHandle}/products.json?limit=250&page=${page}`);
      } catch (e) {
        console.warn('[liquidation] fetch error:', e);
        break;
      }
      if (!res.ok) break;
      const { products } = await res.json();
      if (!products || !products.length) break;
      all.push(...products);
      if (products.length < 250) break;
      page++;
    }
    return all;
  }

  /**
   * Filters products to those with discount ≥ minDiscount and attaches
   * _price, _compareAt, _discount to each qualifying product object.
   * Uses the first variant's price and compare_at_price.
   * @param {Array} products - raw products from products.json
   * @param {number} minDiscount - e.g. 0.15 for 15%
   * @returns {Array} sorted descending by discount
   */
  function filterAndSort(products, minDiscount) {
    const result = [];
    for (const p of products) {
      const v = p.variants && p.variants[0];
      if (!v) continue;
      const price = parseFloat(v.price);
      const compareAt = parseFloat(v.compare_at_price);
      const pct = computeDiscount(price, compareAt);
      if (pct !== null && pct >= minDiscount) {
        result.push(Object.assign({}, p, { _price: price, _compareAt: compareAt, _discount: pct }));
      }
    }
    return result.sort(function (a, b) { return b._discount - a._discount; });
  }

  // ── Formatting ─────────────────────────────────────────────────────────────

  function fmtEur(amount) {
    return '\u20AC' + amount.toFixed(2);
  }

  function fmtBgn(eurAmount) {
    return (eurAmount * 1.95583).toFixed(2) + '\u00A0\u043B\u0432.'; // лв.
  }

  // ── Card renderer ─────────────────────────────────────────────────────────

  /**
   * Returns an <li> HTML string for one product card.
   * Matches the .card-wrapper / .card-information structure used by card-product.liquid.
   * @param {Object} product - enriched product with _price, _compareAt, _discount
   * @returns {string}
   */
  function renderCard(product) {
    const imgSrc = product.featured_image
      ? product.featured_image.src.replace(/(\.[a-zA-Z]+(\?[^?]*)?$)/, '_400x$1')
      : '';
    const pct = Math.round(product._discount * 100);
    const savings = product._compareAt - product._price;
    const title = product.title.replace(/&/g, '&amp;').replace(/"/g, '&quot;');

    return '<li class="grid__item">'
      + '<div class="card-wrapper product-card-wrapper underline-links-hover">'
      + '<div class="card card--standard animate-arrow" tabindex="-1">'
      + '<div class="card__inner">'
      + '<div class="card__media">'
      + '<div class="media media--transparent media--adapt">'
      + '<a href="/products/' + product.handle + '" tabindex="-1">'
      + (imgSrc ? '<img src="' + imgSrc + '" alt="' + title + '" width="400" height="400" loading="lazy">' : '')
      + '</a>'
      + '</div>'
      + '</div>'
      + '<div class="card__badge bottom-left">'
      + '<span class="badge badge--bottom-left" style="color:#fff;background:#cc0000;border-color:#cc0000">'
      + '\u0421\u041f\u0415\u0421\u0422\u0418 ' + fmtEur(savings) + ' / ' + fmtBgn(savings) // СПЕСТИ
      + '</span>'
      + '</div>'
      + '</div>'
      + '<div class="card-information">'
      + '<div class="card-information__wrapper">'
      + '<h3 class="card__heading h6 fw-600">'
      + '<a href="/products/' + product.handle + '" class="full-unstyled-link">' + title + '</a>'
      + '</h3>'
      + '<div class="price">'
      + '<div class="price__container">'
      + '<span class="price-item price-item--sale price-item--eur">' + fmtEur(product._price) + '</span>'
      + '&nbsp;<s class="price-item price-item--regular">' + fmtEur(product._compareAt) + '</s>'
      + '&nbsp;<span class="badge" style="background:#cc0000;color:#fff;border-radius:20px;padding:2px 8px;font-size:0.78em">-' + pct + '%</span>'
      + '</div>'
      + '</div>'
      + '</div>'
      + '</div>'
      + '</div>'
      + '</div>'
      + '</li>';
  }

  // ── Grid renderer (supports load-more) ────────────────────────────────────

  /**
   * Appends a batch of rendered cards to the grid and returns updated offset.
   * @param {HTMLElement} grid
   * @param {Array} products
   * @param {number} offset
   * @param {number} batchSize
   * @returns {number} new offset
   */
  function appendBatch(grid, products, offset, batchSize) {
    var slice = products.slice(offset, offset + batchSize);
    grid.insertAdjacentHTML('beforeend', slice.map(renderCard).join(''));
    return offset + slice.length;
  }

  // ── Entry point ───────────────────────────────────────────────────────────

  /**
   * Called by each section instance via inline <script>.
   * @param {Object} cfg
   * @param {string} cfg.sectionId  - Shopify section.id
   * @param {string} cfg.collection - collection handle to fetch from
   * @param {number} cfg.minDiscount - e.g. 0.15
   * @param {number} cfg.maxDisplay  - max products to show; 0 = show all with load-more
   */
  window.initLiquidationSection = async function (cfg) {
    var sectionEl = document.getElementById('liquidation-section-' + cfg.sectionId);
    var grid = document.getElementById('liquidation-grid-' + cfg.sectionId);
    if (!sectionEl || !grid) return;

    var products = filterAndSort(await fetchAllProducts(cfg.collection), cfg.minDiscount);

    if (!products.length) {
      sectionEl.style.display = 'none';
      return;
    }

    var BATCH = 24;
    var shown = 0;

    if (cfg.maxDisplay > 0) {
      // Homepage mode: show exactly maxDisplay products, no load-more
      appendBatch(grid, products, 0, cfg.maxDisplay);
    } else {
      // Collection page mode: show first batch, then load-more
      shown = appendBatch(grid, products, 0, BATCH);

      if (shown < products.length) {
        var btn = document.createElement('button');
        btn.className = 'button button--secondary';
        btn.textContent = '\u041f\u043e\u043a\u0430\u0436\u0438 \u043e\u0449\u0435'; // Покажи още
        btn.style.cssText = 'display:block;margin:2rem auto 0';
        sectionEl.querySelector('.collection').appendChild(btn);

        btn.addEventListener('click', function () {
          shown = appendBatch(grid, products, shown, BATCH);
          if (shown >= products.length) btn.remove();
        });
      }
    }
  };

  // Expose for browser console testing
  window._liquidationHelpers = { computeDiscount: computeDiscount, filterAndSort: filterAndSort };
})();
```

- [ ] **Step 2: Push the JS asset**

```bash
# From pharmacy-to-shopify repo
python scripts/push_theme.py assets/liquidation-products.js
```

Expected: `✓ Uploaded assets/liquidation-products.js`

- [ ] **Step 3: Verify `computeDiscount` in browser console**

Open any page on `viapharma.us`, open DevTools console, run:

```javascript
const { computeDiscount } = window._liquidationHelpers;

// Normal discount
console.assert(Math.abs(computeDiscount(21, 26.25) - 0.2) < 0.001, 'FAIL: 20% off');

// Exactly at threshold
console.assert(Math.abs(computeDiscount(85, 100) - 0.15) < 0.001, 'FAIL: 15% off');

// No compare_at → null
console.assert(computeDiscount(21, 0) === null, 'FAIL: zero compareAt');
console.assert(computeDiscount(21, null) === null, 'FAIL: null compareAt');

// Price >= compareAt → null
console.assert(computeDiscount(100, 100) === null, 'FAIL: equal prices');
console.assert(computeDiscount(110, 100) === null, 'FAIL: price > compareAt');

// Zero price → null
console.assert(computeDiscount(0, 100) === null, 'FAIL: zero price');

console.log('All computeDiscount tests passed ✓');
```

Expected: `All computeDiscount tests passed ✓`

- [ ] **Step 4: Commit to theme repo**

```bash
# From viapharma.us-theme repo
git add assets/liquidation-products.js
git commit -m "feat: add liquidation-products.js — fetch/filter/sort/render"
```

---

### Task 4: Build `sections/liquidation-products.liquid`

All file edits in `/Users/kiril/IdeaProjects/viapharma.us-theme/`.

- [ ] **Step 1: Create `sections/liquidation-products.liquid`**

```liquid
{{ 'component-card.css' | asset_url | stylesheet_tag }}
{{ 'component-price.css' | asset_url | stylesheet_tag }}

{%- style -%}
  @media screen and (max-width: 749px) {
    .section-{{ section.id }}-padding {
      padding-top: {{ section.settings.padding_top | times: 0.57 | round: 0 }}px;
      padding-bottom: {{ section.settings.padding_bottom | times: 0.57 | round: 0 }}px;
    }
  }
  @media screen and (min-width: 750px) {
    .section-{{ section.id }}-padding {
      padding-top: {{ section.settings.padding_top }}px;
      padding-bottom: {{ section.settings.padding_bottom }}px;
    }
  }
{%- endstyle -%}

<div id="liquidation-section-{{ section.id }}" class="color-{{ section.settings.color_scheme }} isolate gradient">
  <div class="collection section-{{ section.id }}-padding">

    <div class="section-heading page-width">
      <div class="section-title-wrapp">
        {%- if section.settings.title != blank -%}
          <h2 class="section-title inline-richtext {{ section.settings.heading_size }}">
            {{ section.settings.title }}
          </h2>
        {%- endif -%}
      </div>
      {%- if section.settings.show_view_all and section.settings.view_all_label != blank -%}
        <a href="/collections/likvidatsii" class="button button--secondary">
          {{ section.settings.view_all_label }}
        </a>
      {%- endif -%}
    </div>

    <div class="collection-wrapp page-width page-width-desktop">
      <ul id="liquidation-grid-{{ section.id }}"
          class="grid product-grid contains-card contains-card--product grid--4-col-desktop grid--2-col-tablet-down"
          role="list"
          aria-label="{{ section.settings.title }}">
      </ul>
    </div>

  </div>
</div>

<script src="{{ 'liquidation-products.js' | asset_url }}" defer="defer"></script>
<script>
  document.addEventListener('DOMContentLoaded', function () {
    if (typeof window.initLiquidationSection === 'function') {
      window.initLiquidationSection({
        sectionId: '{{ section.id }}',
        collection: '{{ section.settings.collection.handle | default: "namaleniya" }}',
        minDiscount: 0.15,
        maxDisplay: {% if section.settings.show_all %}0{% else %}{{ section.settings.products_to_show }}{% endif %}
      });
    }
  });
</script>

{% schema %}
{
  "name": "Ликвидации",
  "tag": "section",
  "class": "section",
  "settings": [
    {
      "type": "inline_richtext",
      "id": "title",
      "default": "Ликвидации",
      "label": "Заглавие"
    },
    {
      "type": "select",
      "id": "heading_size",
      "options": [
        { "value": "h1", "label": "H1" },
        { "value": "h2", "label": "H2" },
        { "value": "h3", "label": "H3" }
      ],
      "default": "h2",
      "label": "Размер на заглавието"
    },
    {
      "type": "collection",
      "id": "collection",
      "label": "Колекция (данни)"
    },
    {
      "type": "range",
      "id": "products_to_show",
      "min": 4,
      "max": 24,
      "step": 4,
      "default": 8,
      "label": "Брой продукти (начална страница)"
    },
    {
      "type": "checkbox",
      "id": "show_all",
      "default": false,
      "label": "Покажи всички с пагинация (за страница на колекция)"
    },
    {
      "type": "checkbox",
      "id": "show_view_all",
      "default": true,
      "label": "Покажи бутон „Виж всички""
    },
    {
      "type": "text",
      "id": "view_all_label",
      "default": "Виж всички ликвидации →",
      "label": "Текст на бутона"
    },
    {
      "type": "color_scheme",
      "id": "color_scheme",
      "label": "Цветова схема",
      "default": "scheme-1"
    },
    {
      "type": "range",
      "id": "padding_top",
      "min": 0,
      "max": 100,
      "step": 4,
      "unit": "px",
      "label": "Отстъп горе",
      "default": 60
    },
    {
      "type": "range",
      "id": "padding_bottom",
      "min": 0,
      "max": 100,
      "step": 4,
      "unit": "px",
      "label": "Отстъп долу",
      "default": 60
    }
  ],
  "presets": [
    {
      "name": "Ликвидации",
      "settings": {
        "title": "Ликвидации",
        "products_to_show": 8,
        "show_all": false,
        "show_view_all": true,
        "view_all_label": "Виж всички ликвидации →"
      }
    }
  ]
}
{% endschema %}
```

- [ ] **Step 2: Push the section**

```bash
python scripts/push_theme.py sections/liquidation-products.liquid
```

Expected: `✓ Uploaded sections/liquidation-products.liquid`

- [ ] **Step 3: Commit**

```bash
git add sections/liquidation-products.liquid
git commit -m "feat: add liquidation-products section (Liquid shell + JS init)"
```

---

### Task 5: Add Liquidation Section to Homepage (`templates/index.json`)

All file edits in `/Users/kiril/IdeaProjects/viapharma.us-theme/`.

- [ ] **Step 1: Add section entry to `templates/index.json`**

Find the `"featured_collection"` key in `templates/index.json` and add the new section entry **before** it. Also add `"likvidatsii-homepage"` **before** `"featured_collection"` in the `"order"` array.

Add this new section block (before `"featured_collection": { ... }`):

```json
"likvidatsii-homepage": {
  "type": "liquidation-products",
  "settings": {
    "title": "Ликвидации",
    "heading_size": "h2",
    "collection": "namaleniya",
    "products_to_show": 8,
    "show_all": false,
    "show_view_all": true,
    "view_all_label": "Виж всички ликвидации →",
    "color_scheme": "scheme-1",
    "padding_top": 60,
    "padding_bottom": 60
  }
},
```

In the `"order"` array, insert `"likvidatsii-homepage"` before `"featured_collection"`:

```json
"order": [
  "likvidatsii-homepage",
  "featured_collection",
  ...
]
```

- [ ] **Step 2: Push `templates/index.json`**

```bash
python scripts/push_theme.py templates/index.json
```

Expected: `✓ Uploaded templates/index.json`

- [ ] **Step 3: Visual verification**

Open `https://viapharma.us` in browser. Wait ~30 seconds for CDN propagation.

Check:
- "Ликвидации" section appears above "Намаления"
- Product cards load (JS fetch completes)
- Biggest discount card is first
- "Виж всички ликвидации →" button is visible
- Section hides gracefully on slow connections (no broken layout)

If cards don't appear within 5 seconds, open DevTools → Console and check for errors.

- [ ] **Step 4: Commit**

```bash
git add templates/index.json
git commit -m "feat: add Ликвидации section to homepage above Намаления"
```

---

### Task 6: Collection Page (`templates/collection.likvidatsii.json`)

All file edits in `/Users/kiril/IdeaProjects/viapharma.us-theme/`.

- [ ] **Step 1: Create `templates/collection.likvidatsii.json`**

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
        "section_full_width": true,
        "section_background": "#ffffff",
        "padding_top": 10,
        "padding_bottom": 10
      }
    },
    "liquidation-grid": {
      "type": "liquidation-products",
      "settings": {
        "title": "",
        "collection": "namaleniya",
        "products_to_show": 8,
        "show_all": true,
        "show_view_all": false,
        "view_all_label": "",
        "color_scheme": "scheme-8",
        "padding_top": 20,
        "padding_bottom": 40
      }
    }
  },
  "order": ["banner", "liquidation-grid"]
}
```

> Note: `"collection": "namaleniya"` — both `namaleniya` and `likvidatsii` have the same `compare_at_price > 0` rule. Using `namaleniya` as the data source is fine since handles are equivalent. The collection page URL `/collections/likvidatsii` is provided by the Shopify smart collection created in Task 2.

- [ ] **Step 2: Assign the template to the collection in Shopify Admin**

The template must be assigned in Shopify Admin → Collections → Ликвидации → Theme template → `likvidatsii`.

Alternatively, set it via API:

```bash
python3 - <<'EOF'
import sys, os
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
from src.shopify.api_client import ShopifyAPIClient

client = ShopifyAPIClient("61a7bb-4d", os.getenv('SHOPIFY_ACCESS_TOKEN'))

# Find the collection
result = client.rest_request("GET", "smart_collections.json?handle=likvidatsii&limit=1")
col = result["smart_collections"][0]
col_id = col["id"]
print(f"Found collection: {col['title']} (ID: {col_id})")

# Assign template
update = {"smart_collection": {"id": col_id, "template_suffix": "likvidatsii"}}
result = client.rest_request("PUT", f"smart_collections/{col_id}.json", update)
print("Template assigned:", result["smart_collection"].get("template_suffix"))
client.close()
EOF
```

Expected: `Template assigned: likvidatsii`

- [ ] **Step 3: Push the template**

```bash
python scripts/push_theme.py templates/collection.likvidatsii.json
```

Expected: `✓ Uploaded templates/collection.likvidatsii.json`

- [ ] **Step 4: Visual verification**

Open `https://viapharma.us/collections/likvidatsii` in browser. Wait ~30 seconds.

Check:
- Banner shows "Ликвидации" title
- All qualifying products load (JS fetches all pages)
- Sorted biggest discount first
- "Покажи още" button appears if >24 products qualify
- Products below 15% discount do NOT appear

- [ ] **Step 5: Commit**

```bash
git add templates/collection.likvidatsii.json
git commit -m "feat: add collection.likvidatsii template (all products, load-more)"
```

---

## Self-Review Checklist

- [x] Spec: homepage section → Task 4 + Task 5
- [x] Spec: `/collections/likvidatsii` URL → Task 2 (smart collection) + Task 6 (template)
- [x] Spec: ≥15% filter → `filterAndSort` in Task 3 JS
- [x] Spec: sort by discount % descending → `filterAndSort` sort in Task 3 JS
- [x] Spec: "Виж всички" link → Task 4 Liquid, Task 5 JSON settings
- [x] Spec: load-more on collection page → Task 3 JS `appendBatch` + button, Task 6 `show_all: true`
- [x] Spec: section hidden if 0 products → `sectionEl.style.display = 'none'` in Task 3
- [x] Spec: JS fetch fails gracefully → try/catch in `fetchAllProducts`, Task 3
- [x] Spec: no backend scripts or cron → confirmed, Tasks 1–2 are one-time setup only
- [x] Type consistency: `initLiquidationSection` called identically in Task 4 Liquid and Task 6 uses same section
- [x] `computeDiscount` tested in Task 3 Step 3 (browser console)
- [x] Python `create_liquidation_collection` tested in Task 1 (pytest)
