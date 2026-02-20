"""
Specification Validator

Validates extracted product data against specification requirements.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from ..models import ExtractedProduct

# EUR/BGN fixed exchange rate (pegged since 1999)
_EUR_TO_BGN = 1.95583

# Exact placeholder hostnames and domain suffixes that mark an image as broken.
# A hostname matches if it IS one of these OR ends with ".<suffix>".
# This catches benu.bg crawl regression: images got pharmacy.example.com base
# domain when source_domain was not forwarded to the extractor (commit a9b6d3b).
_PLACEHOLDER_DOMAINS: frozenset[str] = frozenset({
    "example.com",       # catches pharmacy.example.com, www.example.com, etc.
    "placeholder.com",   # catches via.placeholder.com
    "dummyimage.com",
    "placehold.it",
    "placekitten.com",
    "lorempixel.com",
    "localhost",
})


def _is_placeholder_domain(hostname: str) -> bool:
    """Return True if hostname is or is a subdomain of a known placeholder domain."""
    h = hostname.lower()
    return any(h == d or h.endswith("." + d) for d in _PLACEHOLDER_DOMAINS)

# Barcode lengths valid for EAN-8, UPC-A, EAN-13, ITF-14
_VALID_BARCODE_LENGTHS = frozenset({8, 12, 13, 14})


class SpecificationValidator:
    """Validates extraction against specification requirements."""

    def __init__(self, product: ExtractedProduct):
        self.product = product

    def validate(self) -> dict:
        """
        Run all validations.

        Returns a dict with keys:
          overall_valid  - False if any required field is missing OR any error fires
          field_checks   - presence booleans for required/preferred/content fields
          spec_compliance - percentage compliance scores
          missing_fields  - list of required field names that are absent
          errors          - list of specific error messages (blocking quality issues)
          warnings        - list of warning messages (both specific and high-level)
          issues          - combined list of all specific error + warning messages
        """
        errors: list[str] = []
        specific_warnings: list[str] = []
        p = self.product

        # ── Error checks ─────────────────────────────────────────────────────

        # title: 5–250 chars, not whitespace-only
        if not p.title or not p.title.strip():
            errors.append("title: empty or whitespace-only")
        elif len(p.title) < 5:
            errors.append(f"title: too short ({len(p.title)} chars, min 5)")
        elif len(p.title) > 250:
            errors.append(f"title: too long ({len(p.title)} chars, max 250)")

        # url: starts with https://
        if not p.url or not p.url.startswith("https://"):
            errors.append(f"url: must start with https:// (got {str(p.url)[:50]!r})")

        # price: parseable float, > 0 and < 10 000
        price_float: float | None = None
        if not p.price:
            errors.append("price: missing")
        else:
            try:
                price_float = float(p.price)
                if price_float <= 0:
                    errors.append(f"price: must be > 0 (got {price_float})")
                elif price_float >= 10000:
                    errors.append(f"price: suspiciously high (got {price_float})")
            except (ValueError, TypeError):
                errors.append(f"price: not a valid number ({p.price!r})")

        # brand: non-empty
        if not p.brand or not p.brand.strip():
            errors.append("brand: missing or empty")

        # sku: non-empty
        if not p.sku or not p.sku.strip():
            errors.append("sku: missing or empty")

        # category_path: >= 1 element
        if not p.category_path:
            errors.append("category_path: empty (must have at least 1 category)")

        # handle: non-empty, matches [a-z0-9-]+, <= 200 chars
        if not p.handle or not p.handle.strip():
            errors.append("handle: missing or empty")
        else:
            if not re.fullmatch(r"[a-z0-9-]+", p.handle):
                errors.append(
                    f"handle: invalid format ({p.handle!r}, must match [a-z0-9-]+)"
                )
            if len(p.handle) > 200:
                errors.append(
                    f"handle: too long ({len(p.handle)} chars, max 200)"
                )

        # images: >= 1 image; each URL must start https:// and not be a placeholder domain
        if not p.images:
            errors.append("images: no images found")
        else:
            for img in p.images:
                img_url = img.source_url if hasattr(img, "source_url") else str(img)
                if not img_url.startswith("https://"):
                    errors.append(
                        f"image URL: must start with https:// ({img_url[:60]!r})"
                    )
                else:
                    try:
                        hostname = urlparse(img_url).netloc.lower()
                        if _is_placeholder_domain(hostname):
                            errors.append(
                                f"image URL: placeholder domain ({hostname})"
                            )
                    except Exception:
                        pass

        # price_eur consistency: if both set, deviation must be <= 1%
        if p.price_eur and p.price and price_float is not None:
            try:
                price_eur_f = float(p.price_eur)
                expected_bgn = price_eur_f * _EUR_TO_BGN
                if price_float > 0:
                    deviation = abs(price_float - expected_bgn) / price_float
                    if deviation > 0.01:
                        errors.append(
                            f"price_eur consistency: {p.price} BGN vs {p.price_eur} EUR "
                            f"(expected ~{expected_bgn:.2f} BGN, deviation {deviation:.1%})"
                        )
            except (ValueError, TypeError):
                pass  # price parse error already caught above

        # ── Warning checks ────────────────────────────────────────────────────

        # barcode: if set, must match ^\d{8,14}$ and be a valid length
        if p.barcode:
            if not re.fullmatch(r"\d{8,14}", p.barcode):
                specific_warnings.append(
                    f"barcode: invalid format ({p.barcode!r}, expected 8–14 digits)"
                )
            elif len(p.barcode) not in _VALID_BARCODE_LENGTHS:
                specific_warnings.append(
                    f"barcode: unusual length ({len(p.barcode)}, expected 8/12/13/14)"
                )

        # description: non-empty
        if not p.description or not p.description.strip():
            specific_warnings.append("description: empty (no HTML description)")

        # seo_title: <= 70 chars
        if p.seo_title and len(p.seo_title) > 70:
            specific_warnings.append(
                f"seo_title: too long ({len(p.seo_title)} chars, max 70)"
            )

        # seo_description: <= 155 chars
        if p.seo_description and len(p.seo_description) > 155:
            specific_warnings.append(
                f"seo_description: too long ({len(p.seo_description)} chars, max 155)"
            )

        # ── Backward-compatible field presence checks ─────────────────────────

        required_fields = {
            "title": bool(p.title),
            "url": bool(p.url),
        }
        preferred_fields = {
            "price": bool(p.price),
            "brand": bool(p.brand),
            "sku": bool(p.sku),
            "images": bool(p.images),
            "categories": bool(p.category_path),
        }
        content_fields = {
            "details": bool(p.details),
            "composition": bool(p.composition),
            "usage": bool(p.usage),
        }

        required_score = sum(required_fields.values()) / len(required_fields) * 100
        preferred_score = sum(preferred_fields.values()) / len(preferred_fields) * 100
        content_score = sum(content_fields.values()) / len(content_fields) * 100

        missing_fields = [k for k, v in required_fields.items() if not v]

        # High-level warning kept for backward compat
        all_warnings = list(specific_warnings)
        if preferred_score < 90:
            all_warnings.append(
                f"Preferred fields below target: {preferred_score:.0f}% (target: 90%+)"
            )

        overall_valid = (required_score == 100) and (len(errors) == 0)

        return {
            "overall_valid": overall_valid,
            "field_checks": {
                "required": required_fields,
                "preferred": preferred_fields,
                "content": content_fields,
            },
            "spec_compliance": {
                "required_fields": f"{required_score:.0f}%",
                "preferred_fields": f"{preferred_score:.0f}%",
                "content_sections": f"{content_score:.0f}%",
                "overall": f"{(required_score * 0.5 + preferred_score * 0.3 + content_score * 0.2):.1f}%",
            },
            "missing_fields": missing_fields,
            "errors": errors,
            "warnings": all_warnings,
            "issues": errors + specific_warnings,
        }
