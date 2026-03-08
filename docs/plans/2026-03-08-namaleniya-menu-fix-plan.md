# Намаления Menu Fix — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the "Намаления" smart collection to use Shopify's native `compare_at_price > 0` rule (automatic, zero-maintenance) and fix all mega-menu sub-navigation links to filter within the sale collection by category tag.

**Architecture:** Two independent changes — (1) update the Shopify smart collection rule via Python + REST API, (2) patch `snippets/header-mega-menu.liquid` in the theme to route all Намаления sub-nav links through `/collections/namaleniya?filter.p.tag=<tag>`. The Liquid change introduces `is_sale_context` + `col_sale_tags` variables scoped to the namaleniya `{% when %}` block; no structural changes to how the mega menu renders.

**Tech Stack:** Python 3, Shopify REST API (smart_collections endpoint), Shopify Liquid, `pytest`, `push_theme.py`

---

### Task 1: Update `create_sale_collection()` to use compare_at_price rule

**Files:**
- Modify: `src/shopify/collections.py:155-162`
- Test: `tests/shopify/test_collections.py`

**Step 1: Update the failing test first**

The existing `test_dry_run_prints_preview` asserts `"tag"` and `"Намаление"` appear in output — those will be wrong after the change. Update it now so it fails before implementation:

```python
# tests/shopify/test_collections.py — replace TestCreateSaleCollection.test_dry_run_prints_preview
def test_dry_run_prints_preview(self, capsys):
    creator = _creator(dry_run=True)
    creator.create_sale_collection(title="Намаления")
    captured = capsys.readouterr()
    assert "[DRY RUN]" in captured.out
    assert "Намаления" in captured.out
    assert "variant_compare_at_price" in captured.out
    assert "greater_than" in captured.out
    assert "0" in captured.out
```

**Step 2: Run the test to confirm it fails**

```bash
pytest tests/shopify/test_collections.py::TestCreateSaleCollection::test_dry_run_prints_preview -v
```
Expected: `FAILED` — output still contains `"tag"` not `"variant_compare_at_price"`.

**Step 3: Update `create_sale_collection()` in `collections.py`**

Replace lines 155–162:

```python
def create_sale_collection(self, title: str = "Намаления") -> bool:
    """Create a smart collection for discounted products.

    Uses compare_at_price > 0 so Shopify evaluates membership live on every
    price write — no tagging script needed. viapharma-pricing sends
    compare_at_price=None when removing a discount, which clears the field
    and removes the product from the collection automatically.
    """
    return self._create_collection(
        title=title,
        column="variant_compare_at_price",
        relation="greater_than",
        condition="0",
    )
```

Note: the `tag` parameter is removed — it was only used for the old tag rule.

**Step 4: Run all sale collection tests**

```bash
pytest tests/shopify/test_collections.py::TestCreateSaleCollection -v
```
Expected: all 4 tests pass. (`test_dry_run_returns_true`, `test_dry_run_prints_preview`, `test_dry_run_does_not_call_api`, `test_custom_relation_in_create_collection`)

**Step 5: Commit**

```bash
git add src/shopify/collections.py tests/shopify/test_collections.py
git commit -m "feat: switch sale collection rule to compare_at_price > 0"
```

---

### Task 2: Add `update_sale_collection()` method

The "Намаления" collection already exists in Shopify with the old tag rule. We need to UPDATE it in place (not delete + recreate, which would lose SEO history).

**Files:**
- Modify: `src/shopify/collections.py` (add method after `create_sale_collection`)
- Test: `tests/shopify/test_collections.py` (add `TestUpdateSaleCollection` class)

**Step 1: Write the failing tests**

```python
# tests/shopify/test_collections.py — add after TestCreateSaleCollection

class TestUpdateSaleCollection:
    def test_returns_false_when_collection_not_found(self):
        creator = _creator(dry_run=False)
        creator.client.rest_request = lambda method, endpoint, *a, **kw: (
            {"smart_collections": []} if method == "GET" else None
        )
        result = creator.update_sale_collection()
        assert result is False

    def test_calls_put_with_correct_rule(self):
        creator = _creator(dry_run=False)
        put_calls = []

        def fake_rest(method, endpoint, data=None):
            if method == "GET":
                return {"smart_collections": [{"id": 42, "title": "Намаления"}]}
            if method == "PUT":
                put_calls.append((endpoint, data))
                return {"smart_collection": {"id": 42}}
            return None

        creator.client.rest_request = fake_rest
        result = creator.update_sale_collection()

        assert result is True
        assert len(put_calls) == 1
        endpoint, data = put_calls[0]
        assert "42" in endpoint
        rule = data["smart_collection"]["rules"][0]
        assert rule["column"] == "variant_compare_at_price"
        assert rule["relation"] == "greater_than"
        assert rule["condition"] == "0"

    def test_dry_run_does_not_call_api(self):
        creator = _creator(dry_run=True)
        calls = []
        creator.client.rest_request = lambda *a, **kw: calls.append(a)
        creator.update_sale_collection()
        assert len(calls) == 0
```

**Step 2: Run tests to confirm they fail**

```bash
pytest tests/shopify/test_collections.py::TestUpdateSaleCollection -v
```
Expected: `ERROR` — `update_sale_collection` not defined.

**Step 3: Implement `update_sale_collection()`**

Add after `create_sale_collection()` in `collections.py`:

```python
def update_sale_collection(self, title: str = "Намаления") -> bool:
    """Update the existing sale collection rule to compare_at_price > 0.

    Use this when the collection already exists and needs its rule changed
    in place (preserves SEO history and collection ID).
    """
    if self.dry_run:
        print(f"  [DRY RUN] Would update: {title} → variant_compare_at_price > 0")
        return True

    from urllib.parse import quote
    result = self.client.rest_request(
        "GET", f"smart_collections.json?title={quote(title)}&limit=1"
    )
    if not result or not result.get("smart_collections"):
        logger.error("Collection '%s' not found — cannot update", title)
        return False

    collection_id = result["smart_collections"][0]["id"]

    data = {
        "smart_collection": {
            "id": collection_id,
            "rules": [
                {
                    "column": "variant_compare_at_price",
                    "relation": "greater_than",
                    "condition": "0",
                }
            ],
            "disjunctive": False,
        }
    }

    update_result = self.client.rest_request(
        "PUT", f"smart_collections/{collection_id}.json", data
    )
    if update_result and "smart_collection" in update_result:
        logger.info("Updated: %s (ID: %s) → compare_at_price > 0", title, collection_id)
        return True

    logger.error("Failed to update: %s", title)
    return False
```

**Step 4: Run tests**

```bash
pytest tests/shopify/test_collections.py::TestUpdateSaleCollection -v
```
Expected: all 3 tests pass.

**Step 5: Run full test suite**

```bash
pytest tests/shopify/test_collections.py -v
```
Expected: all tests pass.

**Step 6: Commit**

```bash
git add src/shopify/collections.py tests/shopify/test_collections.py
git commit -m "feat: add update_sale_collection() to patch rule in-place via PUT"
```

---

### Task 3: Add `--update` flag to `create_sale_collection.py`

**Files:**
- Modify: `scripts/create_sale_collection.py`

**Step 1: Update the script**

Replace the entire `main()` function:

```python
def main():
    parser = argparse.ArgumentParser(description="Create or update the Намаления smart collection")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't modify Shopify")
    parser.add_argument("--update", action="store_true", help="Update the rule on an existing collection in-place")
    parser.add_argument("--title", default="Намаления", help="Collection title (default: Намаления)")
    parser.add_argument("--verbose", action="store_true", help="Debug logging")

    args = parser.parse_args()
    setup_logging(verbose=args.verbose)

    shop, token = load_shopify_credentials()

    print("=" * 60)
    print("Sale Collection Creator")
    print("=" * 60)
    print(f"  Shop:    {shop}")
    print(f"  Title:   {args.title}")
    print(f"  Mode:    {'update' if args.update else 'create'}")
    print(f"  Dry run: {args.dry_run}")

    creator = ShopifyCollectionCreator(shop=shop, access_token=token, dry_run=args.dry_run)

    if args.update:
        ok = creator.update_sale_collection(title=args.title)
        verb = "Updated" if ok else "Failed to update"
    else:
        if not args.dry_run and creator.collection_exists(args.title):
            print(f"\n  Collection '{args.title}' already exists. Use --update to change its rule.")
            return
        ok = creator.create_sale_collection(title=args.title)
        verb = "Created" if ok else "Failed to create"

    print(f"\n  {verb} collection: {args.title}")
    if not ok:
        sys.exit(1)
```

**Step 2: Dry-run test**

```bash
python scripts/create_sale_collection.py --update --dry-run
```
Expected output:
```
Sale Collection Creator
  Shop:    61a7bb-4d.myshopify.com
  Title:   Намаления
  Mode:    update
  Dry run: True
  [DRY RUN] Would update: Намаления → variant_compare_at_price > 0

  Updated collection: Намаления
```

**Step 3: Apply to live Shopify collection**

```bash
python scripts/create_sale_collection.py --update
```
Expected output:
```
  Updated collection: Намаления
```

Verify in Shopify Admin → Collections → Намаления → the rule shows "Compare at price is greater than 0".

**Step 4: Commit**

```bash
git add scripts/create_sale_collection.py
git commit -m "feat: add --update flag to create_sale_collection.py for rule migration"
```

---

### Task 4: Fix mega-menu Liquid template

The `{% when '/collections/namaleniya' %}` block currently has `col_urls` pointing to full category collections. We add `is_sale_context = true` and a `col_sale_tags` array so L2 and L3 links route through the sale collection filtered by tag. "Медицински и спорт" is split into two proper columns.

**Files:**
- Modify: `viapharma.us-theme/snippets/header-mega-menu.liquid`

**Step 1: Update the namaleniya `{% when %}` block (lines 59–63)**

Replace:
```liquid
  {% when '/collections/namaleniya' %}
    {% assign has_mega_columns = true %}
    {% assign col_titles  = 'Лечение и здраве,Козметика,Майка и дете,Медицински и спорт' | split: ',' %}
    {% assign col_handles = 'mega-col-lechenie-1,mega-col-kozmetika-1,mega-col-mayka-1,mega-col-med-1' | split: ',' %}
    {% assign col_urls    = '/collections/lechenie-i-zdrave,/collections/kozmetika,/collections/mayka-i-dete,/collections/meditsinski-izdeliya-i-konsumativi' | split: ',' %}
```

With:
```liquid
  {% when '/collections/namaleniya' %}
    {% assign has_mega_columns = true %}
    {% assign is_sale_context = true %}
    {% assign col_titles    = 'Лечение и здраве,Козметика,Майка и дете,Медицински изделия,Спорт' | split: ',' %}
    {% assign col_sale_tags = 'Лечение и здраве,Козметика,Майка и дете,Медицински изделия и консумативи,Спорт' | split: ',' %}
    {% assign col_handles   = 'mega-col-lechenie-1,mega-col-kozmetika-1,mega-col-mayka-1,mega-col-med-1,mega-col-sport-1' | split: ',' %}
    {% assign col_urls      = '/collections/lechenie-i-zdrave,/collections/kozmetika,/collections/mayka-i-dete,/collections/meditsinski-izdeliya-i-konsumativi,/collections/sport' | split: ',' %}
```

Notes:
- `is_sale_context` signals the rendering loop below to use sale-filtered URLs
- `col_sale_tags` holds the exact product tag values (different from display titles for the medical column)
- "Медицински и спорт" → split into "Медицински изделия" (tag: `Медицински изделия и консумативи`) and "Спорт" (tag: `Спорт`) — each using its own existing linklist

**Step 2: Update the column rendering loop (lines 101–119)**

Replace:
```liquid
				{% for col_handle in col_handles %}
					{% assign col_title = col_titles[forloop.index0] %}
					{% assign col_url   = col_urls[forloop.index0] %}
					<li>
						<a href="{{ col_url }}" class="mega-menu__link mega-menu__link--level-2 link{% if col_url == request.path %} mega-menu__link--active{% endif %}">
							{{ col_title | escape }}
						</a>
						<ul class="list-unstyled" role="list">
							{% for col_link in linklists[col_handle].links %}
								<li>
									<a href="{{ col_link.url }}"
										class="mega-menu__link link{% if col_link.current %} mega-menu__link--active{% endif %}"
										{% if col_link.current %} aria-current="page"{% endif %}>
										{{ col_link.title | escape }}
									</a>
								</li>
							{% endfor %}
						</ul>
					</li>
				{% endfor %}
```

With:
```liquid
				{% for col_handle in col_handles %}
					{% assign col_title = col_titles[forloop.index0] %}
					{% assign col_url   = col_urls[forloop.index0] %}
					{% if is_sale_context %}
						{% assign _sale_tag = col_sale_tags[forloop.index0] %}
						{% assign _sale_tag_enc = _sale_tag | url_encode %}
						{% assign col_url = '/collections/namaleniya?filter.p.tag=' | append: _sale_tag_enc %}
					{% endif %}
					<li>
						<a href="{{ col_url }}" class="mega-menu__link mega-menu__link--level-2 link{% if col_url == request.path %} mega-menu__link--active{% endif %}">
							{{ col_title | escape }}
						</a>
						<ul class="list-unstyled" role="list">
							{% for col_link in linklists[col_handle].links %}
								{% if is_sale_context %}
									{% assign _l3_enc = col_link.title | url_encode %}
									{% assign _l3_url = '/collections/namaleniya?filter.p.tag=' | append: _l3_enc %}
								{% else %}
									{% assign _l3_url = col_link.url %}
								{% endif %}
								<li>
									<a href="{{ _l3_url }}"
										class="mega-menu__link link{% if col_link.current %} mega-menu__link--active{% endif %}"
										{% if col_link.current %} aria-current="page"{% endif %}>
										{{ col_link.title | escape }}
									</a>
								</li>
							{% endfor %}
						</ul>
					</li>
				{% endfor %}
```

**Step 3: Push the theme file**

```bash
cd /Users/kiril/IdeaProjects/pharmacy-to-shopify
python scripts/push_theme.py snippets/header-mega-menu.liquid
```
Expected:
```
[ok]    snippets/header-mega-menu.liquid
```

**Step 4: Commit the theme file**

```bash
cd /Users/kiril/IdeaProjects/viapharma.us-theme
git add snippets/header-mega-menu.liquid
git commit -m "fix: route Намаления sub-nav links through sale collection tag filter"
```

---

### Task 5: Verify storefront filters are enabled

**Manual step — do this before or after Task 4.**

1. Go to Shopify Admin → Sales channels → Online Store → Navigation
2. Find the `namaleniya` collection in Collections list
3. Click the collection → Filters tab
4. Confirm "Tag" filter is enabled (add it if missing)

If the tag filter is not enabled, the `?filter.p.tag=` URL parameter will be silently ignored and ALL sale products will show regardless of category.

---

### Task 6: End-to-end verification

**Step 1: Check the collection rule**
```bash
python scripts/create_sale_collection.py --update --dry-run
```
Should show `compare_at_price > 0` in output.

**Step 2: Visual check in browser**

1. Open `https://viapharma.us` in an incognito window
2. Hover over "Намаления" in the top nav — mega menu should show 5 columns: Лечение и здраве, Козметика, Майка и дете, Медицински изделия, Спорт
3. Click "Лечение и здраве" (L2) → URL should be `/collections/namaleniya?filter.p.tag=Лечение%20и%20здраве` → only discounted products in that category
4. Click any L3 item → URL should be `/collections/namaleniya?filter.p.tag=<L3-tag>` → only discounted products matching that subcategory
5. Confirm no non-discounted products appear (all visible products should show a strikethrough original price)

**Step 3: Optional — clean up stale "Намаление" tags**

The tags are no longer used to drive the collection but may still be on products. Safe to clean up:
```bash
python scripts/tag_discounted_products.py --dry-run   # Preview
python scripts/tag_discounted_products.py             # Apply
```
This is optional and does not affect the new collection rule.
