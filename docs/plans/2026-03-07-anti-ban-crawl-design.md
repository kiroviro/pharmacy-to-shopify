# Anti-Ban Crawl Design

**Date:** 2026-03-07
**Status:** Approved

## Problem

Fresh crawl of benu.bg (~10,500 products) with a fixed 1s delay and single User-Agent is detectable as a bot. Precautionary measure before starting the crawl.

## Approach

Sequential crawling with jitter + realistic browser headers. No new dependencies (stdlib only). No proxy service required.

## Changes

### 1. `src/common/constants.py`

Add:
- `USER_AGENTS` — list of 8–10 real Chrome/Firefox/Safari UAs (Windows, Mac, Linux)
- `BROWSER_HEADERS` — dict of realistic static headers: `Accept`, `Accept-Encoding`, `Accept-Language`, `Cache-Control`, `Sec-Fetch-Dest`, `Sec-Fetch-Mode`, `Sec-Fetch-Site`, `Sec-Fetch-User`, `Upgrade-Insecure-Requests`

### 2. `src/extraction/fetcher.py`

- Replace hardcoded `headers` dict in `fetch()` with a `_build_headers()` helper
- `_build_headers()` picks a random UA from `USER_AGENTS` and merges with `BROWSER_HEADERS`

### 3. `src/discovery/pharmacy_discoverer.py`

- Replace hardcoded UA in `__init__` with a randomly chosen one from `USER_AGENTS`
- Add full `BROWSER_HEADERS` to the session headers

### 4. `src/extraction/bulk_extractor.py`

- Replace `time.sleep(self.delay)` with `time.sleep(random.uniform(self.delay, self.delay * 3.0))`
- Existing `--delay` CLI arg becomes the minimum delay (default 1.0 → range 1.0–3.0s)

## What Does Not Change

- No new dependencies
- No changes to extraction logic, CSV output, or CLI interface
- Resume/state behavior unchanged
- All existing tests pass (fetcher tests use `load_html()`, bypassing network)

## Testing

- Unit test: `_build_headers()` returns a UA from `USER_AGENTS` and includes all required header keys
- `pytest` — all existing tests pass unchanged

## Expected Crawl Duration

~10,500 products × avg 2.0s delay = ~5.8 hours (comfortable overnight run)
