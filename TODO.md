# TODO: Storefront Images

## Homepage Theme Images (DONE)

Uploaded as shop images in Shopify Admin > Content > Files, referenced in Theme Customizer.

| # | Section | Status |
|---|---------|--------|
| 1 | Hero banner | Done |
| 2 | Promo: Витамини | Done |
| 3 | Promo: Козметика | Done |
| 4 | Collage: Грижа за лице | Done |
| 5 | Collage: Майка и дете | Done |
| 6 | Collage: Медицински изделия | Done |

## Collection Card Images (DONE)

Uploaded via Shopify Admin > Products > Collections > select collection > edit image.

| # | Collection | Status |
|---|-----------|--------|
| 7 | Лечение и здраве | Done |
| 8 | Козметика | Done |
| 9 | Майка и дете | Done |
| 10 | Медицински изделия | Done |
| 11 | Спорт | Done |
| 12 | Здравословно хранене | Done |

## Collection Page Images (DONE)

| # | Image | Section | Status |
|---|-------|---------|--------|
| 13 | Promo Card 1 (Горещи оферти) | `promo_yaghg4` in product-grid | Done -- `Promo_card_1.png` |
| 14 | Promo Card 2 (ВИЖ ПОВЕЧЕ) | `promo_zj3gnd` in product-grid | Done -- `Promo_card_11.png` |
| 15 | Discount Banner (Спестете до 50%) | `collection_discount_banner` | Done -- `Discount_banner.png` |

## Trust Badge Icons (DONE)

Created as SVG line icons matching theme palette (#1DA1D4 / #0A3244 / #EBF6FB). Uploaded via GraphQL staged uploads and wired into `multicolumn_xFpxpe` (collection) and `multicolumn_TPpXaJ` (product) sections.

| # | Badge | File | Status |
|---|-------|------|--------|
| 16 | Оригинални лекарства | `icon-original-medicines.svg` | Done |
| 17 | Поддръжка след покупка | `icon-support.svg` | Done |
| 18 | Бърза и сигурна доставка | `icon-fast-delivery.svg` | Done |
| 19 | Достъпно здравеопазване | `icon-affordable-healthcare.svg` | Done |

## Remaining

| # | Image | Location | Status |
|---|-------|----------|--------|
| 20-29 | Brand logos (10) | Homepage brand slider/grid | Pending |
| 30-32 | Testimonial avatars (3) | Collection page: Мария К., Георги П., Елена Д. | Pending |

---

# TODO: Code Quality & Engineering

## P1 — Foundational (blocks everything else)

| # | Item | Effort | Status |
|---|------|--------|--------|
| 1 | **Add pytest test suite** — start with pure functions (`remove_source_references`, `transliterate`, `generate_handle`, `_extract_application_form`, `_extract_target_audience`, `_parse_weight`, price regex). Then integration tests for `ShopifyCSVExporter` and `BenuExtractor` with fixture HTML. Target ~80% coverage on `src/`. | L | Pending |
| 2 | **Replace `print()` with `logging` module** — add `import logging` in all `src/` modules, keep `print()` only for user-facing CLI output (progress, summaries). Add `--verbose`/`--quiet` flags mapping to log levels. | M | Pending |
| 3 | **Add `pyproject.toml` with packaging** — project metadata, pinned dependencies, `[project.scripts]` entry points for CLI commands. Add `requirements.lock` via `pip-compile` for reproducible builds. | M | Pending |

## P2 — Production reliability (causes real bugs)

| # | Item | Effort | Status |
|---|------|--------|--------|
| 4 | **Fix hardcoded inventory=11** in `csv_exporter.py:126` — use `product.inventory_quantity` or make configurable via `ShopifyCSVExporter` constructor. | S | Pending |
| 5 | **Move EUR→BGN rate to config** — `benu_extractor.py:200` hardcodes `1.95583`. Move to `config/seo_settings.yaml` or dedicated currency config. | S | Pending |
| 6 | **Add retry logic for transient API errors** — `api_client.py` returns `None` silently on 5xx/timeout. Add 2-3 retries with exponential backoff (use `tenacity` or `urllib3.util.Retry`). | M | Pending |
| 7 | **Add context manager to `ShopifyAPIClient`** — `requests.Session` at `api_client.py:55` is never closed. Add `__enter__`/`__exit__` and use `with` pattern in scripts. | S | Pending |
| 8 | **Add timeouts to all HTTP calls** — missing on: `shopify_delete_products.py:208` (file upload), `shopify_oauth.py:102,140` (token exchange/test). Also consider making image HEAD validation optional via `--skip-image-check` flag. | S | Pending |

## P3 — Code quality (slows you down over time)

| # | Item | Effort | Status |
|---|------|--------|--------|
| 9 | **Extract duplicated CSV reading to shared utils** — `_load_vendors_from_csv` duplicated in `collections.py`, `menus.py`, `tag_cleaner.py`. Same for tag counting. Move to `src/common/csv_utils.py`. | S | Pending |
| 10 | **Deduplicate Google Ads config loading** — `google_ads_pmax.py:25-38` and `google_ads_create_account.py:21-34` have identical `load_config()`. Extract to shared module. | S | Pending |
| 11 | **Break up large functions** — `BulkExtractor.extract_all()` (118 lines), `BrandExporter.export()` (119 lines), `shopify_delete_products.py:main()` (128 lines). Extract loop bodies and sub-steps into named methods. | M | Pending |
| 12 | **Apply tag normalization during extraction or document gap** — `config/tag_normalization.yaml` defines canonical casing but `BenuExtractor` copies categories to tags with no normalization. Only applied by the separate `cleanup_tags.py` step. | S | Pending |

## P4 — Engineering hygiene (shows maturity)

| # | Item | Effort | Status |
|---|------|--------|--------|
| 13 | **Add GitHub Actions CI** — `.github/workflows/ci.yml` running `pytest`, `ruff check`, `mypy` on push. Add `pre-commit` config. | S | Pending |
| 14 | **Add ruff + mypy configuration** — `ruff.toml` for linting/formatting, `mypy.ini` in strict mode on `src/`. Fix errors incrementally. | M | Pending |
| 15 | **Validate price/sku in model `__post_init__`** — `product.py:107-112` only validates `title` and `url`. Products with `price=""` and `sku=""` pass silently. Either validate or give explicit defaults. | S | Pending |
| 16 | **Make `clean_product()` non-mutating** — `csv_exporter.py:64-78` modifies the product in-place. Use `dataclasses.replace()` or document the mutation clearly. | S | Pending |
| 17 | **Make Shopify API version configurable** — `api_client.py:35` pins `2024-01`. Move to config or constructor parameter. | S | Pending |

## P5 — Polish

| # | Item | Effort | Status |
|---|------|--------|--------|
| 18 | **Remove or integrate unused parsers** — `src/extraction/parsers/` (1,050 lines) imported but never used by `BenuExtractor`. | S | Pending |
| 19 | **Clean up temp files** — `shopify_delete_products.py` creates `shopify_bulk_delete.jsonl` but never deletes it. | S | Pending |
| 20 | **Fix OAuth handler shared state** — `shopify_oauth.py` uses class variables for `authorization_code`/`state_received`, would break with concurrent flows. | S | Pending |
| 21 | **Fix image position sync after deduplication** — alt text says "Снимка 1 от 3" when only 2 images survive dedup. | S | Pending |
| 22 | **Guard `_extract_categories` default path** — default `product_title=""` triggers redundant `_extract_title()` if called without argument from new code. | S | Pending |

Effort: **S** = small (< 1h), **M** = medium (1-4h), **L** = large (4h+)
