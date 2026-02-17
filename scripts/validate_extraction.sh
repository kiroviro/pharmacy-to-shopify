#!/bin/bash
#
# Pre-extraction validation script
# Run BEFORE each extraction to ensure code quality
#
# Usage:
#   ./scripts/validate_extraction.sh
#
# Exit codes:
#   0 = All tests passed
#   1 = Tests failed - DO NOT extract
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║              PRE-EXTRACTION VALIDATION - QUALITY GATE CHECK                ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""

cd "$(dirname "$0")/.."

# Check if in correct directory
if [ ! -f "src/extraction/pharmacy_extractor.py" ]; then
    echo -e "${RED}✗ Error: Run this script from pharmacy-to-shopify directory${NC}"
    exit 1
fi

echo "📍 Working directory: $(pwd)"
echo ""

# Step 1: Barcode validation tests
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  Running barcode validation tests..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if python3 tests/test_barcode_validation.py; then
    echo -e "${GREEN}✓ Barcode validation tests PASSED${NC}"
else
    echo -e "${RED}✗ Barcode validation tests FAILED${NC}"
    echo -e "${RED}Fix barcode extraction logic before running extraction${NC}"
    exit 1
fi

echo ""

# Step 2: Regression tests
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  Running regression tests on real product examples..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if python3 tests/test_extraction_regression.py; then
    echo -e "${GREEN}✓ Regression tests PASSED${NC}"
else
    echo -e "${RED}✗ Regression tests FAILED${NC}"
    echo -e "${RED}Fix extraction logic before running extraction${NC}"
    exit 1
fi

echo ""

# Step 3: Check extractor code for known issues
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  Checking extractor code for known issues..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check for dangerous patterns
ISSUES=0

# Check 1: Ensure we validate GTIN length
if ! grep -q "len(candidate) in \[8, 12, 13, 14\]" src/extraction/pharmacy_extractor.py && \
   ! grep -q "len(cleaned) in \[8, 12, 13, 14\]" src/extraction/pharmacy_extractor.py; then
    echo -e "${RED}✗ Missing GTIN length validation (8/12/13/14 digits)${NC}"
    ISSUES=$((ISSUES + 1))
else
    echo -e "${GREEN}✓ GTIN length validation present${NC}"
fi

# Check 2: Ensure we don't accept 'mpn' from JSON-LD (it contains SKUs)
if grep -q "'mpn'" src/extraction/pharmacy_extractor.py | grep -v "# NOT 'mpn'"; then
    echo -e "${YELLOW}⚠ Warning: 'mpn' field may contain SKUs, not GTINs${NC}"
    echo "  Review JSON-LD extraction to ensure it's excluded"
fi

# Check 3: Ensure we use the enhanced pattern
if grep -q "Баркод\\\\s\*:\\\\s\*\\\\d{8,14}" src/extraction/pharmacy_extractor.py; then
    echo -e "${GREEN}✓ Using length-validated barcode pattern${NC}"
else
    echo -e "${YELLOW}⚠ Barcode pattern may not validate length${NC}"
fi

if [ $ISSUES -gt 0 ]; then
    echo ""
    echo -e "${RED}Found $ISSUES critical issues in extractor code${NC}"
    exit 1
fi

echo ""

# Success
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                   ✓ ALL VALIDATION CHECKS PASSED                           ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}✓ Safe to proceed with extraction${NC}"
echo ""
echo "Next steps:"
echo "  1. Run extraction:"
echo "     python3 scripts/bulk_extract.py --urls data/pharmacy.example.com/raw/urls.txt"
echo ""
echo "  2. Validate extraction results:"
echo "     python3 tests/test_extraction_regression.py data/benu.bg/raw/products.csv"
echo ""
echo "  3. Export to Shopify if quality gates pass"
echo ""

exit 0
