#!/usr/bin/env python3
"""
Single Product Extraction

Extracts a single product with detailed validation report.
Site is auto-detected from URL.

Usage:
    python3 extract_single.py --url https://benu.bg/product-url
    python3 extract_single.py --url https://benu.bg/product-url --verbose
"""

import argparse
import json
import re
import sys
import os
from dataclasses import asdict

from src.extraction import (
    get_extractor_for_url,
    get_site_from_url,
    SpecificationValidator,
)
from src.shopify import ShopifyCSVExporter
from src.models import ExtractedProduct


def remove_source_references(text: str, site: str) -> str:
    """Remove references to source site from text."""
    if not text:
        return text

    # Remove URLs containing the site domain
    text = re.sub(rf'https?://[^\s]*{re.escape(site)}[^\s]*', '', text)

    # Remove mentions of the site (case insensitive)
    site_name = site.replace(".bg", "")
    text = re.sub(rf'\b{re.escape(site)}\b', '', text, flags=re.IGNORECASE)
    text = re.sub(rf'\b{re.escape(site_name)}\b', '', text, flags=re.IGNORECASE)

    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def print_report(product: ExtractedProduct, validation: dict, product_type: str = "unknown", site: str = ""):
    """Print detailed comparison report."""

    print("\n" + "="*80)
    print("EXTRACTION REPORT")
    print("="*80)

    print(f"\nSite: {site}")
    print(f"Product URL: {product.url}")
    print(f"Title: {product.title[:70]}..." if len(product.title) > 70 else f"Title: {product.title}")

    type_label = "Prescription (Rx)" if product_type == "prescription" else "OTC / Regular"
    print(f"Product Type: {type_label}")

    print("\n" + "-"*80)
    print("EXTRACTED DATA")
    print("-"*80)

    # Core fields
    print("\nCORE FIELDS:")
    fields = [
        ("Title", product.title),
        ("Handle", product.handle),
        ("Brand", product.brand),
        ("SKU", product.sku),
        ("Price (BGN)", f"{product.price} лв." if product.price else ""),
        ("Price (EUR)", f"{product.price_eur} €" if product.price_eur else ""),
    ]

    for label, value in fields:
        status = "OK" if value else "MISSING"
        print(f"  [{status:7}] {label:20} {value or 'MISSING'}")

    # Categories
    print(f"\nCATEGORIES ({len(product.category_path)} levels):")
    for idx, category in enumerate(product.category_path, 1):
        print(f"  {idx}. {category}")

    # Tags
    print(f"\nTAGS ({len(product.tags)} items):")
    for idx, tag in enumerate(product.tags, 1):
        print(f"  {idx}. {tag}")

    # Tab sections
    print("\nCONTENT SECTIONS:")
    sections = [
        ("Details", product.details),
        ("Composition", product.composition),
        ("Usage", product.usage),
        ("Contraindications", product.contraindications),
        ("More Info", product.more_info),
    ]

    for name, content in sections:
        status = "OK" if content else "MISSING"
        length = len(content) if content else 0
        print(f"  [{status:7}] {name:25} {length} characters")

    # Images
    print(f"\nIMAGES ({len(product.images)} images):")
    for img in product.images:
        url_short = img.source_url.split('/')[-1] if '/' in img.source_url else img.source_url
        print(f"  {img.position}. {url_short}")

    # Validation results
    print("\n" + "-"*80)
    print("COMPLIANCE")
    print("-"*80)

    compliance = validation["spec_compliance"]
    print(f"\n  Required Fields: {compliance['required_fields']}")
    print(f"  Preferred Fields: {compliance['preferred_fields']}")
    print(f"  Content Sections: {compliance['content_sections']}")
    print(f"  Overall Score: {compliance['overall']}")

    overall_pct = float(compliance['overall'].rstrip('%'))
    if overall_pct >= 95:
        print(f"\n  MEETS TARGET (>=95%)")
    else:
        print(f"\n  BELOW TARGET (95%), Current: {overall_pct:.1f}%")

    if validation["missing_fields"]:
        print("\nMISSING REQUIRED FIELDS:")
        for field in validation["missing_fields"]:
            print(f"  - {field}")

    if validation["warnings"]:
        print("\nWARNINGS:")
        for warning in validation["warnings"]:
            print(f"  - {warning}")

    if not validation["missing_fields"] and not validation["warnings"]:
        print("\nNo issues found!")

    print("\n" + "="*80)


def main():
    parser = argparse.ArgumentParser(
        description="Extract a single product with validation report"
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Product URL"
    )
    parser.add_argument(
        "--output-json",
        help="Output JSON path (default: output/{site}/extraction.json)"
    )
    parser.add_argument(
        "--output-csv",
        help="Output Shopify CSV path (default: output/{site}/product.csv)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show full extracted data"
    )

    args = parser.parse_args()

    # Detect site from URL
    site = get_site_from_url(args.url)
    print(f"Extracting from: {site}")
    print(f"URL: {args.url}")

    # Set default output paths based on site
    output_json = args.output_json or f"output/{site}/extraction.json"
    output_csv = args.output_csv or f"output/{site}/product.csv"

    try:
        # Get appropriate extractor
        ExtractorClass = get_extractor_for_url(args.url)

        # Extract
        extractor = ExtractorClass(args.url)
        extractor.fetch()
        product = extractor.extract()

        # Validate
        validator = SpecificationValidator(product)
        validation = validator.validate()

        # Print report
        print_report(product, validation, extractor.product_type, site)

        # Save JSON
        output_data = {
            "site": site,
            "product": asdict(product),
            "validation": validation,
        }

        os.makedirs(os.path.dirname(output_json), exist_ok=True)
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"\nResults saved to: {output_json}")

        # Clean source references
        product.title = remove_source_references(product.title, site)
        product.description = remove_source_references(product.description, site)
        product.seo_title = remove_source_references(product.seo_title, site)
        product.seo_description = remove_source_references(product.seo_description, site)

        # Save Shopify CSV
        os.makedirs(os.path.dirname(output_csv), exist_ok=True)
        csv_exporter = ShopifyCSVExporter(source_domain=site)
        csv_exporter.export_single(product, output_csv, clean_source_refs=False)
        print(f"Shopify CSV saved to: {output_csv}")

        # Verbose output
        if args.verbose:
            print("\n" + "="*80)
            print("FULL EXTRACTED DATA (JSON)")
            print("="*80)
            print(json.dumps(asdict(product), indent=2, ensure_ascii=False))

        # Exit code
        sys.exit(0 if validation["overall_valid"] else 1)

    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nExtraction failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
