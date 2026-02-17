# Quality Checklist - Barcode Extraction

**Use this checklist before and after each extraction**

## ✅ Before Extraction

- [ ] Run validation script:
  ```bash
  ./scripts/validate_extraction.sh
  ```
- [ ] Verify all tests pass (23 total: 18 validation + 5 regression)
- [ ] Check for code changes since last extraction
- [ ] Review any warnings in validation output

**If validation fails:** ❌ DO NOT run extraction - fix code first

## ✅ After Extraction

- [ ] Run quality check on results:
  ```bash
  python3 tests/test_extraction_regression.py data/benu.bg/raw/products.csv
  ```
- [ ] Verify quality gates pass:
  - [ ] Barcode coverage ≥ 85%
  - [ ] Invalid barcodes = 0
  - [ ] Missing required fields = 0
- [ ] Compare with previous extraction:
  - [ ] Similar product count (±5%)
  - [ ] Similar barcode coverage (±2%)
  - [ ] Check for unexpected changes

**If quality gates fail:** ❌ DO NOT upload to Shopify - investigate first

## ✅ Before Uploading to Shopify

- [ ] Quality gates passed
- [ ] Spot-check 10 products manually
- [ ] Verify file size is reasonable (~30 MB for 9K products)
- [ ] Check first/last products in CSV look correct
- [ ] Make backup of current Shopify data (if updating)

## Quick Reference

### Current Baseline Metrics (Feb 17, 2026)
- **Total products:** 9,272
- **Barcode coverage:** 88.1%
- **Invalid barcodes:** 0
- **Quality status:** ✅ EXCELLENT

### What Changed (Fixed)
- ✅ Now validates GTIN format (8/12/13/14 digits)
- ✅ Rejects SKUs (3-7 digits)
- ✅ Rejects invalid GTINs (11 digits)
- ✅ Rejects internal IDs (15 digits)
- ✅ Extracts from multiple sources (JSON-LD, meta tags, text)

### Files Created
```
tests/
  ├── test_barcode_validation.py    (18 tests - validates GTIN logic)
  └── test_extraction_regression.py (5 tests + quality gates)

scripts/
  └── validate_extraction.sh        (Pre-extraction validation)

docs/
  └── TESTING_AND_VALIDATION.md     (Complete documentation)

QUALITY_CHECKLIST.md                (This file)
```

### Commands to Remember

```bash
# Before extraction
./scripts/validate_extraction.sh

# After extraction
python3 tests/test_extraction_regression.py data/benu.bg/raw/products.csv

# Run specific tests
python3 tests/test_barcode_validation.py
```

## Emergency: If Tests Fail

1. **Don't panic** - tests are working as designed
2. **Don't run extraction** - you'll get bad data
3. **Review code changes** - what was modified?
4. **Check error messages** - which test failed?
5. **Fix the issue** - revert or correct code
6. **Re-run validation** - tests should pass
7. **Document what happened** - prevent future issues

## Support

- Full documentation: `docs/TESTING_AND_VALIDATION.md`
- Test files: `tests/`
- Validation script: `scripts/validate_extraction.sh`
