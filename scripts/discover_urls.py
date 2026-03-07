#!/usr/bin/env python3
"""
URL Discovery Script

Discovers all product URLs from benu.bg using sitemaps.

Usage:
    python3 discover_urls.py --output data/benu.bg/raw/urls.txt
    python3 discover_urls.py --limit 100
"""

import argparse
import logging
import os
import random
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.common.log_config import setup_logging
from src.discovery import PharmacyURLDiscoverer

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Discover product URLs from benu.bg"
    )
    parser.add_argument(
        "--output", "-o",
        default="data/benu.bg/raw/urls.txt",
        help="Output file for product URLs (default: data/benu.bg/raw/urls.txt)"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=0,
        help="Limit number of URLs to discover (0 = no limit)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress info messages, show only warnings and errors"
    )
    parser.add_argument(
        "--proxies",
        help="Path to file with proxy URLs (one per line). A random one will be used.",
    )

    args = parser.parse_args()
    setup_logging(verbose=args.verbose, quiet=args.quiet)

    output_path = args.output

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print("=" * 60)
    print("benu.bg URL Discovery")
    print("=" * 60)
    print(f"  Output: {output_path}")
    print(f"  Limit:  {args.limit if args.limit else 'none'}")

    proxy_url = None
    if args.proxies:
        with open(args.proxies) as f:
            proxy_list = [
                line.strip() for line in f
                if line.strip() and not line.strip().startswith("#")
            ]
        if proxy_list:
            proxy_url = random.choice(proxy_list)
            print(f"  Proxy:  {proxy_url.split('@')[-1]}")  # log host:port only, not credentials
        else:
            print(f"  Proxy:  file empty, running without proxy")

    print("  Method: Sitemap")
    discoverer = PharmacyURLDiscoverer(
        verbose=args.verbose,
        base_url="https://benu.bg",
        sitemap_url="https://benu.bg/sitemap.products.xml",
        proxy_url=proxy_url,
    )
    discoverer.discover_all_products(limit=args.limit, output_file=output_path)

    # Summary
    stats = discoverer.get_stats()
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    if "categories_found" in stats:
        print(f"  Categories found: {stats['categories_found']}")
    print(f"  Products found:   {stats['products_found']}")
    if stats.get("failed_urls"):
        print(f"  Failed URLs:      {stats['failed_urls']}")
    print(f"  Output file:      {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
