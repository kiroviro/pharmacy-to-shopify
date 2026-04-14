#!/usr/bin/env python3
"""Add images to IVF products that were created without them.

Usage:
    python scripts/add_ivf_images.py --dry-run
    python scripts/add_ivf_images.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.common.cli import base_parser, init_logging, shopify_client_from_env

# SKU → image URL mapping
IVF_IMAGES: dict[str, str] = {
    "PERGOVERIS-900-450": "https://www.dockpharmacy.com/wp-content/uploads/2021/10/Pergoveris-900-450iu-Pen-Follitropin-alfa-Lutropin-alfa-1-pack.jpg",
    "PERGOVERIS-300-150": "https://www.dockpharmacy.com/wp-content/uploads/2021/10/Pergoveris-Pen-300-150iu-Follitropin-alfa-Lutropin-alfa-Injection-1-pack-1.jpg",
    "MERIOFERT-150": "https://fastivf.com/wp-content/uploads/2017/02/meriofert-150-iu.jpg",
    "CETROTIDE-025": "https://fastivf.com/wp-content/uploads/2017/02/cetrorelix-0-25-mg.jpg",
    "GONAL-F-300": "https://fastivf.com/wp-content/uploads/2017/02/gonal-f-300iu-pen-e1763110580854.jpg",
    "GONAL-F-450": "https://fastivf.com/wp-content/uploads/2017/02/gonal-f-450iu-pen-e1763110632623.jpg",
    "OVITRELLE-250": "https://fastivf.com/wp-content/uploads/2017/02/ovitrelle.jpg",
    "CHORIOMON-5000": "https://ivfsmart.com/wp-content/uploads/2022/09/CHORIOMON-5000-IU-IM-SC.jpg",
}


def main() -> None:
    parser = base_parser("Add images to IVF products")
    args = parser.parse_args()
    init_logging(args)

    client, shop, _token = shopify_client_from_env()
    if not client.test_connection():
        print("Error: Could not connect to Shopify")
        sys.exit(1)

    # Find IVF products by tag
    print("Fetching IVF products...")
    products = []
    page = client.rest_request("GET", "products.json?limit=50&collection_id=&status=active&fields=id,title,variants,images")
    # Paginate through all products to find IVF ones by SKU
    all_products = []
    page = client.rest_request("GET", "products.json?limit=250&fields=id,title,variants,images")
    while page and "products" in page:
        all_products.extend(page["products"])
        if len(page["products"]) == 250:
            last_id = page["products"][-1]["id"]
            page = client.rest_request("GET", f"products.json?limit=250&since_id={last_id}&fields=id,title,variants,images")
        else:
            break

    # Build SKU → product mapping
    sku_to_product: dict[str, dict] = {}
    for p in all_products:
        for v in p.get("variants", []):
            if v.get("sku") in IVF_IMAGES:
                sku_to_product[v["sku"]] = p

    print(f"Found {len(sku_to_product)} IVF products needing images")

    added = 0
    for sku, image_url in IVF_IMAGES.items():
        product = sku_to_product.get(sku)
        if not product:
            print(f"  [SKIP] {sku}: product not found")
            continue

        # Skip if product already has images
        if product.get("images"):
            print(f"  [SKIP] {sku}: already has {len(product['images'])} image(s)")
            continue

        if args.dry_run:
            print(f"  [DRY RUN] Would add image to {product['title'][:60]}...")
            continue

        result = client.rest_request(
            "POST",
            f"products/{product['id']}/images.json",
            data={"image": {"src": image_url}},
        )
        if result and "image" in result:
            print(f"  [OK] {product['title'][:60]}...")
            added += 1
        else:
            print(f"  [FAIL] {product['title'][:60]}...")

        time.sleep(0.5)

    print(f"\nDone. Added images to {added} products.")
    missing = set(IVF_IMAGES.keys()) - set(sku_to_product.keys())
    if missing:
        print(f"Products not found for SKUs: {missing}")


if __name__ == "__main__":
    main()
