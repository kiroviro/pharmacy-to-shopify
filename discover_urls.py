#!/usr/bin/env python3
"""
URL Discovery Script

Discovers all product URLs from pharmacy sites using sitemaps.

Usage:
    python3 discover_urls.py --site benu.bg --output data/benu.bg/raw/urls.txt
    python3 discover_urls.py --site benu.bg --limit 100
"""

import argparse
import os

from src.discovery import get_discoverer_for_site, get_supported_sites, BenuURLDiscoverer


def main():
    supported = get_supported_sites()

    parser = argparse.ArgumentParser(
        description=f"Discover product URLs (supports: {', '.join(supported)})"
    )
    parser.add_argument(
        "--site", "-s",
        required=True,
        choices=supported,
        help=f"Site to crawl ({', '.join(supported)})"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file for product URLs (default: data/{site}/raw/urls.txt)"
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

    args = parser.parse_args()

    # Set default output path based on site
    output_path = args.output or f"data/{args.site}/raw/urls.txt"

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print("=" * 60)
    print(f"{args.site} URL Discovery")
    print("=" * 60)
    print(f"  Site:   {args.site}")
    print(f"  Output: {output_path}")
    print(f"  Limit:  {args.limit if args.limit else 'none'}")

    # Get appropriate discoverer for the site
    DiscovererClass = get_discoverer_for_site(args.site)

    print("  Method: Sitemap")
    discoverer = DiscovererClass(verbose=args.verbose)
    discoverer.discover_all_products(limit=args.limit, output_file=output_path)

    # Summary
    stats = discoverer.get_stats()
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"  Site:             {args.site}")
    if "categories_found" in stats:
        print(f"  Categories found: {stats['categories_found']}")
    print(f"  Products found:   {stats['products_found']}")
    if stats.get("failed_urls"):
        print(f"  Failed URLs:      {stats['failed_urls']}")
    print(f"  Output file:      {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
