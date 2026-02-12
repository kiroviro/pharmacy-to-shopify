# Configuration

## Adding Support for a New Vendor Site

The tool is designed to support multiple vendor sites. To add a new site:

1. **Create an extractor** in `src/extraction/` (e.g., `newsite_extractor.py`)
   - Implement `fetch()` and `extract()` methods that return `ExtractedProduct`
   - Use JSON-LD, HTML parsing, or other strategies appropriate for the site

2. **Create a discoverer** in `src/discovery/` (e.g., `newsite_discoverer.py`)
   - Implement `discover_all_products()` to find product URLs (sitemap, crawling, etc.)

3. **Register in `__init__.py`** files:
   - Add to `SITE_EXTRACTORS` in `src/extraction/__init__.py`
   - Add to `SITE_DISCOVERERS` in `src/discovery/__init__.py`

4. **Create data directories**: `data/{new-site}/raw/` and `data/{new-site}/processed/`

The CLI scripts auto-detect the site from URLs, so no changes are needed there.

## Category and Tag Configuration

All category and tag settings are in YAML files under `config/`:

- **`categories.yaml`** -- L1/L2 category hierarchy (83 subcategories for benu.bg)
- **`tag_normalization.yaml`** -- canonical brand name casing (e.g., "AboPharma")
- **`promotional_patterns.yaml`** -- patterns to strip from tags (e.g., "Black Friday")
- **`vendor_defaults.yaml`** -- default tags for specific vendors
- **`seo_settings.yaml`** -- SEO title/description limits, store name, Google Shopping category mapping

After editing config files, re-run `scripts/cleanup_tags.py` to apply changes.
