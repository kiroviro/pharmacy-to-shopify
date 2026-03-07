# Anti-Ban Crawl Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the benu.bg crawler indistinguishable from a real browser by rotating User-Agents and sending realistic browser headers, with randomized request delays.

**Architecture:** Four small, isolated changes across existing files — constants, fetcher, discoverer, bulk extractor. No new modules. No new dependencies. All changes are additive except replacing the fixed sleep with a jittered one.

**Tech Stack:** Python stdlib (`random`), `requests`, existing project structure.

---

### Task 1: Add User-Agent list and browser headers to constants

**Files:**
- Modify: `src/common/constants.py`

**Step 1: Write the failing test**

Create `tests/common/test_anti_ban_headers.py`:

```python
"""Tests for anti-ban crawl constants."""
from src.common.constants import USER_AGENTS, BROWSER_HEADERS


def test_user_agents_is_nonempty_list():
    assert isinstance(USER_AGENTS, list)
    assert len(USER_AGENTS) >= 8


def test_user_agents_are_strings():
    for ua in USER_AGENTS:
        assert isinstance(ua, str)
        assert len(ua) > 20  # sanity: real UAs are long


def test_browser_headers_has_required_keys():
    required = {
        "Accept",
        "Accept-Encoding",
        "Accept-Language",
        "Cache-Control",
        "Sec-Fetch-Dest",
        "Sec-Fetch-Mode",
        "Sec-Fetch-Site",
        "Upgrade-Insecure-Requests",
    }
    assert required.issubset(set(BROWSER_HEADERS.keys()))


def test_browser_headers_values_are_strings():
    for k, v in BROWSER_HEADERS.items():
        assert isinstance(v, str), f"{k} value should be a string"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/common/test_anti_ban_headers.py -v
```

Expected: FAIL — `ImportError: cannot import name 'USER_AGENTS'`

**Step 3: Add constants**

Append to `src/common/constants.py`:

```python
# Rotating User-Agents for anti-ban crawling
# Mix of Chrome/Firefox/Safari on Windows/Mac/Linux
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.3; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
]

# Realistic browser headers sent alongside the User-Agent
# User-Agent is NOT included here — it is picked randomly per request
BROWSER_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "bg-BG,bg;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/common/test_anti_ban_headers.py -v
```

Expected: PASS (4 tests)

**Step 5: Run full suite to check nothing broke**

```bash
pytest
```

Expected: same pass/fail counts as before (only new tests added)

**Step 6: Commit**

```bash
git add src/common/constants.py tests/common/test_anti_ban_headers.py
git commit -m "feat: add USER_AGENTS list and BROWSER_HEADERS constants for anti-ban crawling"
```

---

### Task 2: Rotate headers in PharmacyFetcher

**Files:**
- Modify: `src/extraction/fetcher.py`

**Step 1: Write the failing test**

Add to `tests/extraction/test_parser.py` (or create `tests/extraction/test_fetcher.py` if it doesn't exist):

```python
"""Tests for PharmacyFetcher header building."""
import random
from unittest.mock import patch, MagicMock
from src.extraction.fetcher import PharmacyFetcher
from src.common.constants import USER_AGENTS, BROWSER_HEADERS


def test_build_headers_returns_dict_with_user_agent():
    fetcher = PharmacyFetcher(url="https://benu.bg/test")
    headers = fetcher._build_headers()
    assert "User-Agent" in headers
    assert headers["User-Agent"] in USER_AGENTS


def test_build_headers_includes_all_browser_headers():
    fetcher = PharmacyFetcher(url="https://benu.bg/test")
    headers = fetcher._build_headers()
    for key in BROWSER_HEADERS:
        assert key in headers, f"Missing header: {key}"


def test_build_headers_picks_different_agents():
    fetcher = PharmacyFetcher(url="https://benu.bg/test")
    agents = {fetcher._build_headers()["User-Agent"] for _ in range(50)}
    # With 10 UAs and 50 draws, probability of only 1 unique is astronomically low
    assert len(agents) > 1
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/extraction/test_fetcher.py -v
```

Expected: FAIL — `AttributeError: 'PharmacyFetcher' object has no attribute '_build_headers'`

**Step 3: Update fetcher**

In `src/extraction/fetcher.py`, add the import at the top and replace the `fetch()` method:

```python
import random
from ..common.constants import USER_AGENTS, BROWSER_HEADERS
```

Replace the existing `USER_AGENT` import (was: `from ..common.constants import USER_AGENT`) with the above.

Add the `_build_headers` method and update `fetch()`:

```python
def _build_headers(self) -> dict:
    """Build a randomized but realistic browser header set."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        **BROWSER_HEADERS,
    }

def fetch(self) -> None:
    """Fetch the product page via HTTP GET."""
    requester = self._session or requests
    response = requester.get(self.url, headers=self._build_headers(), timeout=30)
    response.raise_for_status()
    self._load(response.text)
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/extraction/test_fetcher.py -v
```

Expected: PASS (3 tests)

**Step 5: Run full suite**

```bash
pytest
```

Expected: same pass/fail as before

**Step 6: Commit**

```bash
git add src/extraction/fetcher.py tests/extraction/test_fetcher.py
git commit -m "feat: rotate User-Agent and send realistic browser headers in PharmacyFetcher"
```

---

### Task 3: Rotate headers in PharmacyURLDiscoverer

**Files:**
- Modify: `src/discovery/pharmacy_discoverer.py`

**Step 1: Write the failing test**

Create `tests/discovery/__init__.py` (empty) and `tests/discovery/test_discoverer_headers.py`:

```python
"""Tests for PharmacyURLDiscoverer anti-ban headers."""
from src.discovery.pharmacy_discoverer import PharmacyURLDiscoverer
from src.common.constants import USER_AGENTS, BROWSER_HEADERS


def test_discoverer_session_has_realistic_headers():
    discoverer = PharmacyURLDiscoverer()
    session_headers = dict(discoverer.session.headers)
    # User-Agent must be one of our rotating list
    assert session_headers.get("User-Agent") in USER_AGENTS
    # All BROWSER_HEADERS keys must be present
    for key in BROWSER_HEADERS:
        assert key in session_headers, f"Missing session header: {key}"
    discoverer.close()
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/discovery/test_discoverer_headers.py -v
```

Expected: FAIL — User-Agent not in USER_AGENTS (old hardcoded value)

**Step 3: Update discoverer**

In `src/discovery/pharmacy_discoverer.py`, replace the existing imports and `__init__` header setup:

```python
import random
from ..common.constants import USER_AGENTS, BROWSER_HEADERS
```

Replace the `self.session.headers.update(...)` block in `__init__`:

```python
self.session.headers.update({
    "User-Agent": random.choice(USER_AGENTS),
    **BROWSER_HEADERS,
})
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/discovery/test_discoverer_headers.py -v
```

Expected: PASS (1 test)

**Step 5: Run full suite**

```bash
pytest
```

Expected: same pass/fail as before

**Step 6: Commit**

```bash
git add src/discovery/pharmacy_discoverer.py tests/discovery/__init__.py tests/discovery/test_discoverer_headers.py
git commit -m "feat: rotate User-Agent and add browser headers in PharmacyURLDiscoverer"
```

---

### Task 4: Add jitter to request delay in BulkExtractor

**Files:**
- Modify: `src/extraction/bulk_extractor.py`

**Step 1: Write the failing test**

Add to `tests/extraction/test_bulk_extractor.py`:

```python
import random
from unittest.mock import patch


def test_delay_uses_jitter(tmp_path):
    """BulkExtractor sleeps for a random value between delay and delay*3."""
    extractor = BulkExtractor(
        output_csv=str(tmp_path / "out.csv"),
        output_dir=str(tmp_path),
        delay=1.0,
    )
    sleep_calls = []

    with patch("src.extraction.bulk_extractor.time.sleep", side_effect=lambda t: sleep_calls.append(t)):
        with patch("src.extraction.bulk_extractor.random.uniform", return_value=2.5) as mock_uniform:
            # Simulate one completed iteration (the sleep is called at end of loop)
            # We test the arguments passed to random.uniform
            extractor._jitter_sleep()
            mock_uniform.assert_called_once_with(1.0, 3.0)
            assert sleep_calls == [2.5]
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/extraction/test_bulk_extractor.py::test_delay_uses_jitter -v
```

Expected: FAIL — `AttributeError: 'BulkExtractor' object has no attribute '_jitter_sleep'`

**Step 3: Update BulkExtractor**

Add `import random` at the top of `src/extraction/bulk_extractor.py` (after existing imports).

Add the `_jitter_sleep` method to the `BulkExtractor` class:

```python
def _jitter_sleep(self) -> None:
    """Sleep for a random duration between delay and delay*3 seconds."""
    time.sleep(random.uniform(self.delay, self.delay * 3.0))
```

Replace the existing sleep call in `extract_all()`:

```python
# Before (find this line):
time.sleep(self.delay)

# After:
self._jitter_sleep()
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/extraction/test_bulk_extractor.py -v
```

Expected: PASS (all bulk extractor tests including new one)

**Step 5: Run full suite**

```bash
pytest
```

Expected: same pass/fail as before

**Step 6: Commit**

```bash
git add src/extraction/bulk_extractor.py tests/extraction/test_bulk_extractor.py
git commit -m "feat: add jitter to request delay in BulkExtractor (uniform between delay and delay*3)"
```

---

## Verification

After all 4 tasks:

```bash
pytest
```

All existing tests pass. Four new test files/additions cover the new behaviour.

The crawl command is unchanged:

```bash
python scripts/bulk_extract.py --delay 1.0 --resume
```

This will now sleep 1.0–3.0s between requests with a random UA and full browser headers.
