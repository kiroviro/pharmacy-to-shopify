# Testing and Validation Framework

**Prevents barcode extraction regressions and ensures data quality**

## Overview

This framework ensures that product extraction maintains high quality standards and prevents regressions like the one discovered on Feb 17, 2026, where we initially thought barcode coverage decreased, but it actually improved by correctly rejecting invalid GTINs.

## Key Concepts

### GTIN vs SKU - Critical Distinction

**GTIN (Global Trade Item Number)** = Barcode
- Standardized global identifier
- Must be exactly 8, 12, 13, or 14 digits
- Required by Google Merchant Center
- Examples: `3352710009079` (EAN-13), `123456789012` (UPC-A)

**SKU (Stock Keeping Unit)**
- Internal retailer identifier
- Can be any length/format
- NOT accepted by Google Merchant Center
- Examples: `559` (3 digits), `5909` (4 digits)

**The Problem:** benu.bg labels both as "Баркод" (Barcode), but only GTINs are valid for Google Shopping.

**Our Solution:** Validate length and reject SKUs/invalid codes.

## Test Suite Components

### 1. Barcode Validation Tests

**File:** `tests/test_barcode_validation.py`

**Purpose:** Ensures GTIN validation logic is correct

**Tests:**
- ✓ Accepts valid GTINs (8, 12, 13, 14 digits)
- ✓ Rejects SKUs (3-7 digits)
- ✓ Rejects invalid GTINs (9-11 digits)
- ✓ Rejects internal IDs (15+ digits)

**Run:**
```bash
python3 tests/test_barcode_validation.py
```

**Expected output:**
```
18 passed, 0 failed
```

### 2. Regression Test Suite

**File:** `tests/test_extraction_regression.py`

**Purpose:** Prevents quality regressions with real product examples and quality gates

**Tests:**
- Real BOIRON products (valid 13-digit barcodes)
- Real SOLGAR products (invalid 11-digit codes - should reject)
- Real Duphalac products (3-digit SKUs - should reject)
- Overall extraction quality metrics

**Quality Gates:**
- Barcode coverage ≥ 85%
- Invalid barcodes ≤ 5
- Missing required fields = 0

**Run:**
```bash
# Test real product examples only
python3 tests/test_extraction_regression.py

# Test real products + validate CSV extraction
python3 tests/test_extraction_regression.py data/benu.bg/raw/products.csv
```

**Expected output:**
```
✓ ALL QUALITY GATES PASSED
```

### 3. Pre-Extraction Validation Script

**File:** `scripts/validate_extraction.sh`

**Purpose:** Run BEFORE each extraction to ensure code is safe

**Checks:**
1. Barcode validation logic (18 tests)
2. Real product regression tests (5 tests)
3. Code review for known issues

**Run:**
```bash
./scripts/validate_extraction.sh
```

**Expected output:**
```
✓ ALL VALIDATION CHECKS PASSED
✓ Safe to proceed with extraction
```

## Workflow: How to Prevent Regressions

### Before Making Code Changes

1. **Run validation to establish baseline:**
   ```bash
   ./scripts/validate_extraction.sh
   ```

2. **All tests should pass** before making changes

### After Making Code Changes

1. **Run validation again:**
   ```bash
   ./scripts/validate_extraction.sh
   ```

2. **If tests fail:**
   - ✗ DO NOT run extraction
   - Fix the code until tests pass
   - Review what changed

3. **If tests pass:**
   - ✓ Safe to run extraction
   - Run a test extraction on a small sample first

### After Running Extraction

1. **Validate extraction results:**
   ```bash
   python3 tests/test_extraction_regression.py data/benu.bg/raw/products.csv
   ```

2. **Check quality gates:**
   - Barcode coverage should be ≥ 85%
   - Should have 0 invalid barcodes
   - All required fields present

3. **Compare to previous extraction:**
   ```bash
   # Create comparison script if needed
   python3 scripts/compare_extractions.py \
     output/benu.bg/products_001.csv \
     data/benu.bg/raw/products.csv
   ```

## Known Issues & Solutions

### Issue 1: SOLGAR 11-Digit Codes

**Problem:** SOLGAR products have 11-digit codes like `33984007536`
**Status:** Invalid GTIN (GTINs are 8/12/13/14 digits only)
**Solution:** Correctly rejected by validator
**Impact:** 174 products won't sync to Google Merchant Center (expected)

### Issue 2: SKUs Labeled as Barcodes

**Problem:** benu.bg labels SKUs as "Баркод" (e.g., `559`, `5909`)
**Status:** Not valid GTINs
**Solution:** Correctly rejected by validator
**Impact:** 43 products won't sync to Google Merchant Center (expected)

### Issue 3: 'mpn' Field Contains SKUs

**Problem:** JSON-LD `mpn` field contains SKUs, not GTINs
**Status:** Fixed - removed from extraction sources
**Solution:** Only extract from `gtin`, `gtin13`, `gtin8`, `gtin12`, `gtin14`, `ean`
**Impact:** Prevents extracting SKUs as barcodes

## Continuous Integration

### Add to CI/CD Pipeline

If using GitHub Actions, GitLab CI, etc.:

```yaml
test:
  script:
    - ./scripts/validate_extraction.sh
  only:
    - merge_requests
    - main
```

### Pre-commit Hook (Optional)

Add to `.git/hooks/pre-commit`:
```bash
#!/bin/bash
./scripts/validate_extraction.sh
if [ $? -ne 0 ]; then
    echo "❌ Validation failed - commit rejected"
    exit 1
fi
```

## Metrics to Track

### Current Baseline (Feb 17, 2026)

| Metric | Value | Target |
|--------|-------|--------|
| Total products | 9,272 | - |
| Valid barcode coverage | 88.1% | ≥85% |
| Invalid barcodes | 0 | ≤5 |
| Missing required fields | 0 | 0 |

### Track Over Time

Create a metrics log:
```bash
# After each extraction
echo "$(date +%Y-%m-%d),$TOTAL_PRODUCTS,$BARCODE_COVERAGE,$INVALID_BARCODES" \
  >> metrics/extraction_quality.csv
```

## Troubleshooting

### Test Failures

**If barcode validation tests fail:**
```
✗ FAIL | EAN-13: 13 digits (BOIRON product)
```
- Check `src/extraction/pharmacy_extractor.py`
- Ensure `len(candidate) in [8, 12, 13, 14]` validation exists
- Review regex patterns

**If regression tests fail:**
```
✗ FAIL | SOLGAR product (invalid 11-digit - should reject)
       Expected: '' | Got: '33984007536'
```
- The extractor is NOT rejecting invalid barcodes
- Check validation logic in `_extract_barcode()`
- Ensure length validation happens AFTER extraction

**If quality gates fail:**
```
✗ FAIL | Barcode coverage >= 85%: 82.3%
```
- Extraction quality decreased
- Review recent code changes
- Compare with previous extraction
- Check for new extraction bugs

### Debugging Barcode Extraction

Test extraction on a single URL:
```bash
python3 scripts/test_single_url.py "https://benu.bg/some-product"
```

Add debug logging:
```python
# In pharmacy_extractor.py
import logging
logging.basicConfig(level=logging.DEBUG)
logger.debug(f"Barcode extracted: {barcode} (length: {len(barcode)})")
```

## Adding New Tests

### Add a Real Product Test

Edit `tests/test_extraction_regression.py`:

```python
REAL_PRODUCT_TESTS.append({
    "name": "Brand X Product (description)",
    "html": '<h3>Допълнителна информация</h3><p>Баркод : 1234567890123</p>',
    "expected_barcode": "1234567890123",
    "should_extract": True,
})
```

### Adjust Quality Gates

Edit `tests/test_extraction_regression.py`:

```python
# Adjust thresholds if needed
MIN_BARCODE_COVERAGE = 85.0  # Percentage
MAX_INVALID_BARCODES = 5     # Count
```

## Summary

This framework ensures:
1. ✓ Code changes don't break barcode extraction
2. ✓ Only valid GTINs are extracted (not SKUs)
3. ✓ Quality stays above 85% barcode coverage
4. ✓ Regressions are caught before extraction runs

**Always run `./scripts/validate_extraction.sh` before extracting!**
