# Two-Pass Retry Strategy for Failed Crawl URLs

**Date:** 2026-03-08
**Context:** Main crawl completed with 1,516 failures (1,295 HTTP 500, 219 ProxyError, 2 ReadTimeout) out of 10,393 URLs. Previous crawls yielded ~10,500 products vs 8,687 this run — the failures likely account for the discrepancy. All failures occurred with Oxylabs datacenter proxies active; hypothesis is benu.bg returned 500s to proxy IPs rather than genuine missing pages.

---

## Goal

Recover as many of the 1,516 failed products as possible before proceeding to pipeline stage 3 (cleanup → export → Shopify import).

## Data Flow

```
output/failed_urls.txt  (1,516 URLs)
        │
        ▼  Pass 1: no proxy, --retries 3, --delay 1.5
        │  output: data/benu.bg/raw/products_retry1.csv
        │  state:  output/retry1/failed_urls.txt  (~X remaining)
        │
        ▼  Pass 2: --proxies proxies.txt, --retries 3, --delay 2.0
        │  output: data/benu.bg/raw/products_retry2.csv
        │  state:  output/retry2/failed_urls.txt  (permanent failures)
        │
        ▼  Merge + deduplicate by URL handle
        products.csv  (final, replaces original)
```

## What Gets Built

### 1. `--output-dir` CLI flag on `bulk_extract.py`

`BulkExtractor` already accepts `output_dir` as a constructor param but the CLI hardcodes `"output"`. Add a `--output-dir` flag so each retry pass can write its state and `failed_urls.txt` to a separate directory without colliding.

```bash
python scripts/bulk_extract.py \
  --urls output/failed_urls.txt \
  --output data/benu.bg/raw/products_retry1.csv \
  --output-dir output/retry1 \
  --delay 1.5 --retries 3
```

### 2. Execution commands

**Pass 1 — no proxy:**
```bash
python scripts/bulk_extract.py \
  --urls output/failed_urls.txt \
  --output data/benu.bg/raw/products_retry1.csv \
  --output-dir output/retry1 \
  --delay 1.5 --retries 3
```

**Pass 2 — with proxies (for remaining failures):**
```bash
python scripts/bulk_extract.py \
  --urls output/retry1/failed_urls.txt \
  --output data/benu.bg/raw/products_retry2.csv \
  --output-dir output/retry2 \
  --delay 2.0 --retries 3 \
  --proxies proxies.txt
```

**Merge:**
```python
import pandas as pd
from pathlib import Path

frames = [pd.read_csv('data/benu.bg/raw/products.csv')]
for path in ['data/benu.bg/raw/products_retry1.csv', 'data/benu.bg/raw/products_retry2.csv']:
    if Path(path).exists() and Path(path).stat().st_size > 0:
        frames.append(pd.read_csv(path))

merged = pd.concat(frames).drop_duplicates(subset=['URL handle'], keep='first')
merged.to_csv('data/benu.bg/raw/products.csv', index=False)
print(f'Final: {len(merged)} products')
```

## Error Handling

- Empty retry CSV (all failed in that pass) → skipped gracefully via `Path.exists()` + size check
- Permanent failures in `output/retry2/failed_urls.txt` → accepted as dead benu.bg pages, not retried further
- Deduplication by `URL handle` (keep first) prevents duplicate rows if a URL somehow appears in multiple passes

## Testing

- `--output-dir` flag: unit test that `BulkExtractor` is instantiated with the correct `output_dir`
- Merge: verify row count = sum of unique handles across all three CSVs
