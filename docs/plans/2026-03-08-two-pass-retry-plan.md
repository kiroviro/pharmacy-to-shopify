# Two-Pass Retry Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `--output-dir` CLI flag to `bulk_extract.py`, then execute the two-pass retry to recover as many of the 1,516 failed crawl URLs as possible.

**Architecture:** One small code change (expose `output_dir` to CLI), then two sequential `bulk_extract.py` runs with separate output directories, followed by a merge. No new scripts needed — merge is a one-liner.

**Tech Stack:** Python, pandas, pytest, `src/extraction/bulk_extractor.py`, `scripts/bulk_extract.py`

---

### Task 1: Add `--output-dir` CLI flag to `bulk_extract.py`

**Files:**
- Modify: `scripts/bulk_extract.py` (around line 137 for arg, line 202 for BulkExtractor init)
- Test: `tests/scripts/test_bulk_extract_cli.py` (create if it doesn't exist, or add to existing)

**Step 1: Write the failing test**

Add to `tests/extraction/test_bulk_extractor.py`:

```python
def test_output_dir_flag_passed_to_extractor(tmp_path):
    """--output-dir sets the state/failed_urls directory, not the CSV path."""
    custom_dir = tmp_path / "my_output"
    bulk = BulkExtractor(
        output_csv=str(tmp_path / "out.csv"),
        output_dir=str(custom_dir),
        validate=False,
    )
    bulk.extract_all(
        urls=["https://benu.bg/product-1"],
        extractor_class=FakeExtractor,
    )
    # State file and failed_urls.txt should be in custom_dir, not "output/"
    assert (custom_dir / "extraction_state.json").exists()
```

**Step 2: Run test to verify it passes already (BulkExtractor already supports output_dir)**

```bash
pytest tests/extraction/test_bulk_extractor.py::test_output_dir_flag_passed_to_extractor -v
```

Expected: PASS (the param already works in BulkExtractor — we just need to wire it to CLI).

**Step 3: Add `--output-dir` argument to `scripts/bulk_extract.py`**

After the `--retries` argument block (line ~142):

```python
parser.add_argument(
    "--output-dir",
    default="output",
    help="Directory for state files and failed_urls.txt (default: output)",
)
```

Then update the `BulkExtractor(...)` call (line ~202):

```python
extractor = BulkExtractor(
    output_csv=output_csv,
    output_dir=args.output_dir,
    delay=args.delay,
    save_failed_html=args.save_failed_html,
    proxies=proxies,
    retries=args.retries,
)
```

**Step 4: Run full test suite**

```bash
pytest tests/ -q --ignore=tests/validation/test_real_data_regressions.py
```

Expected: all pass.

**Step 5: Commit and push**

```bash
git add scripts/bulk_extract.py tests/extraction/test_bulk_extractor.py
git commit -m "feat: add --output-dir flag to bulk_extract.py"
git push
```

---

### Task 2: Execute Pass 1 — retry without proxies

No code changes. Just run the command and let it complete.

**Step 1: Verify failed_urls.txt exists and has content**

```bash
wc -l output/failed_urls.txt
```

Expected: 1516

**Step 2: Run Pass 1**

```bash
python scripts/bulk_extract.py \
  --urls output/failed_urls.txt \
  --output data/benu.bg/raw/products_retry1.csv \
  --output-dir output/retry1 \
  --delay 1.5 \
  --retries 3
```

Let it run to completion. Monitor for quality gate PASS/FAIL in the summary.

**Step 3: Note how many recovered and how many still failed**

```bash
wc -l data/benu.bg/raw/products_retry1.csv
wc -l output/retry1/failed_urls.txt
```

---

### Task 3: Execute Pass 2 — retry remaining failures with proxies

**Step 1: Verify retry1 failed_urls.txt exists**

```bash
wc -l output/retry1/failed_urls.txt
```

If 0 — all recovered in Pass 1, skip to Task 4 (merge).

**Step 2: Run Pass 2**

```bash
python scripts/bulk_extract.py \
  --urls output/retry1/failed_urls.txt \
  --output data/benu.bg/raw/products_retry2.csv \
  --output-dir output/retry2 \
  --delay 2.0 \
  --retries 3 \
  --proxies proxies.txt
```

**Step 3: Note permanent failures**

```bash
wc -l output/retry2/failed_urls.txt
```

These are accepted as dead benu.bg pages.

---

### Task 4: Merge all CSVs into products.csv

**Step 1: Run merge**

```python
import pandas as pd
from pathlib import Path

frames = [pd.read_csv('data/benu.bg/raw/products.csv')]
for path in ['data/benu.bg/raw/products_retry1.csv', 'data/benu.bg/raw/products_retry2.csv']:
    p = Path(path)
    if p.exists() and p.stat().st_size > 200:  # >200 bytes means more than just a header
        df = pd.read_csv(path)
        if len(df) > 0:
            frames.append(df)
            print(f'  + {len(df)} rows from {path}')

merged = pd.concat(frames).drop_duplicates(subset=['URL handle'], keep='first')
merged.to_csv('data/benu.bg/raw/products.csv', index=False)
print(f'Final: {len(merged)} products')
```

Run with:
```bash
python3 -c "
import pandas as pd
from pathlib import Path

frames = [pd.read_csv('data/benu.bg/raw/products.csv')]
for path in ['data/benu.bg/raw/products_retry1.csv', 'data/benu.bg/raw/products_retry2.csv']:
    p = Path(path)
    if p.exists() and p.stat().st_size > 200:
        df = pd.read_csv(path)
        if len(df) > 0:
            frames.append(df)
            print(f'  + {len(df)} rows from {path}')
merged = pd.concat(frames).drop_duplicates(subset=['URL handle'], keep='first')
merged.to_csv('data/benu.bg/raw/products.csv', index=False)
print(f'Final: {len(merged)} products')
"
```

Expected: final count significantly higher than 8,687.

**Step 2: Verify**

```bash
wc -l data/benu.bg/raw/products.csv
```

---

### Task 5: Update CLAUDE.md and commit final state

**Step 1: Note permanent failure count**

```bash
python3 -c "
with open('output/retry2/failed_urls.txt') as f:
    lines = [l for l in f if l.strip()]
print(f'Permanent failures: {len(lines)}')
"
```

**Step 2: Commit final products.csv and docs**

```bash
git add docs/plans/2026-03-08-two-pass-retry-plan.md
git commit -m "docs: add two-pass retry implementation plan"
git push
```
