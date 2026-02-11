# TODO

## Portfolio & Repo Hygiene

These items are about making the repo presentable as a public portfolio piece on GitHub. They don't change runtime behavior but they're what hiring managers and senior engineers look at first.

| # | Item | Effort | Notes |
|---|------|--------|-------|
| 1 | **Add LICENSE file** — MIT or Apache 2.0. Without a license the repo is legally "all rights reserved" and cannot be forked, evaluated, or referenced properly. This is the single most checked thing on any public repo. | S | |
| 4 | **Add a Makefile** — `make test`, `make lint`, `make install`. Standard developer convenience. Shows you think about onboarding. | S | |
| 5 | **Move CLI scripts into `scripts/`** — 13 `.py` files in the project root (`discover_urls.py`, `bulk_extract.py`, `export_by_brand.py`, etc.) make the repo look cluttered at first glance. Move to `scripts/` or behind a single CLI entry point. | M | |
| 6 | **Add `.env.example` and `config/google-ads.yaml.example`** — credentials are properly gitignored, but there's no template showing what keys are needed. Standard practice for onboarding. | S | |
| 7 | **Trim README, move deep content to `docs/`** — README is 435 lines. The first 30 seconds matter. Keep the hook, quick start, and architecture overview in README. Move theme customization details, Google Ads setup, workflow examples, and SKU/barcode deep-dives into `docs/`. | M | |
| 8 | **Add a screenshot or architecture diagram** — a Mermaid diagram or a screenshot of the live store in the README header gives instant visual context. | S | |
| 9 | **Remove `TODO.md` from repo or rename to `ROADMAP.md`** — once these items are addressed, a public repo shouldn't ship with a raw internal task list. A "Roadmap" section in docs is fine. | S | |

---

## Code Quality

### P2 — Reliability

| # | Item | Effort | Notes |
|---|------|--------|-------|
| 14 | **Close the `requests.Session`** — `api_client.py` creates a `requests.Session()` that's never closed. Add `__enter__`/`__exit__` so scripts can use `with ShopifyAPIClient(...) as client:`. | S | |
| 15 | **Clean up temp file from bulk delete** — `shopify_delete_products.py` creates `shopify_bulk_delete.jsonl` and never removes it. Use `tempfile.NamedTemporaryFile` or delete on completion. | S | |

### P3 — Code hygiene

| # | Item | Effort | Notes |
|---|------|--------|-------|
| 17 | **Add `mypy` in strict mode** — type hints are already used throughout `src/` but nothing enforces them. Add `[tool.mypy]` to `pyproject.toml` and fix incrementally. | M | |
| 18 | **Complete `pyproject.toml`** — missing `authors`, `license`, `readme`, and `dependencies` (currently only in `requirements.txt`). Add `[project.scripts]` entry points so the tool is pip-installable. | S | |
| 19 | **Deduplicate Google Ads `load_config()`** — `google_ads_pmax.py` and `google_ads_create_account.py` both define their own `load_config()` with near-identical logic (differ only in required fields list and error output). Extract to a shared helper. | S | |

---

## Done

Items completed and verified:

| # | Item | Status |
|---|------|--------|
| 2 | **Commit untracked files** — tests, pyproject.toml, log_config | Done — 165 tests committed and passing in CI |
| 3 | **Add GitHub Actions CI** — pytest + ruff on push | Done — `.github/workflows/ci.yml` with Python 3.9/3.11/3.13 matrix |
| 10 | **Fix hardcoded `inventory_quantity = 11`** | Done — uses `product.inventory_quantity or 11` |
| 11 | **Fix image alt text position mismatch** | Done — alt text recalculated post-dedup |
| 12 | **Add timeouts to OAuth HTTP calls** | Done — `timeout=30` added to both calls |
| 13 | **Add retry logic for Shopify API 5xx errors** | Done — bounded retry loop (MAX_RETRIES=5) for 429/502/503/504 |
| 16 | **Finish replacing `print()` with `logging`** | Reviewed — all `print()` is intentionally user-facing (summaries, dry-run, prompts) |

---

## Deferred / Won't Do

Items from the previous TODO that were reviewed and removed, with reasoning:

| Previous Item | Verdict | Why |
|---------------|---------|-----|
| **"Add pytest test suite"** | Already done | 165 tests across 20 files, all passing in <1s. |
| **"Add `pyproject.toml`"** (as P1 blocker) | Already done | File exists with pytest + ruff config. Remaining gap is just metadata completeness (item #18 above). |
| **"Add ruff configuration"** | Already done | Configured in `pyproject.toml` with E/F/W/I rules, line-length 120, target py39. |
| **"Extract duplicated `_load_vendors_from_csv`"** | Already fixed or inaccurate | Function exists only in `collections.py`. `tag_cleaner.py` uses `load_vendor_defaults()` from config_loader. No duplication found. |
| **"Move EUR→BGN rate 1.95583 to config"** | Won't do | This is the legally fixed conversion rate set by the EU Council when Bulgaria adopted the ERM II. It's not a market rate that changes — it's a constant by law, like `pi`. Extracting it to YAML config implies it might change, which is misleading. A code comment explaining this would be sufficient. |
| **"parsers/ (1,050 lines) imported but never used"** | Inaccurate | Parsers have comprehensive test coverage (`test_structured_data.py`, `test_gtm_data.py`, `test_html_parser.py`). They're standalone parsing modules. `BenuExtractor` reimplements extraction inline, but the parsers aren't dead code — they're reusable components for future site extractors. |
| **"Break up BulkExtractor.extract_all() (118 lines)"** | Low value | 118 lines for a batch orchestration method with progress tracking, resume logic, and error handling is not unreasonable. Splitting it would scatter the workflow across methods with no reuse benefit. |
| **"Apply tag normalization during extraction"** | Won't do | The separate `cleanup_tags.py` step is intentional — it keeps extraction pure (extract what's there) and cleanup composable (run independently, idempotent). Coupling them would make the pipeline harder to debug. |
| **"Make `clean_product()` non-mutating"** | Low value | The mutation happens once during CSV export on a product that's about to be serialized. Creating a copy via `dataclasses.replace()` for a write-once path adds allocation with no behavioral benefit. |
| **"Validate price/sku in model `__post_init__`"** | Won't do | Empty price and SKU are valid extraction outcomes (product page may not have them). The model correctly represents incomplete data. Validation belongs in `SpecificationValidator`, which already flags these as warnings. |
| **"Make Shopify API version configurable"** | Low value | The API version is a compatibility contract, not a user preference. Pinning it in code is correct — changing it requires testing against breaking changes, not a config edit. |
| **"Fix OAuth handler shared state"** | Low value | `shopify_oauth.py` is a local dev-only CLI tool. It will never handle concurrent flows. Class variables are fine here. |
| **"Guard `_extract_categories` default path"** | Low value | Defensive coding against hypothetical future misuse. The function is only called from `extract()` where `product_title` is always set. |
| **"Add `pre-commit` config"** | Optional | CI catches the same issues. Pre-commit is nice but not a gap — it's preference. |
| **Storefront images (brand logos, testimonial avatars)** | Removed | Shopify Admin operational tasks, not code TODOs. Doesn't belong in a code repository's task list. |

---

Effort: **S** = small (< 1 hour), **M** = medium (1-4 hours)
