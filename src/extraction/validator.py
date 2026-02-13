"""
Specification Validator

Validates extracted product data against specification requirements.
"""

from __future__ import annotations

from ..models import ExtractedProduct


class SpecificationValidator:
    """Validates extraction against specification requirements."""

    def __init__(self, product: ExtractedProduct):
        self.product = product

    def validate(self) -> dict:
        """Run all validations."""
        results = {
            "overall_valid": True,
            "field_checks": {},
            "spec_compliance": {},
            "missing_fields": [],
            "warnings": [],
        }

        # Check required fields (per spec)
        required_fields = {
            "title": bool(self.product.title),
            "url": bool(self.product.url),
        }

        # Check preferred fields (per spec)
        preferred_fields = {
            "price": bool(self.product.price),
            "brand": bool(self.product.brand),
            "sku": bool(self.product.sku),
            "images": bool(self.product.images),
            "categories": bool(self.product.category_path),
        }

        # Check content sections (highlights optional - not all sites have them)
        content_fields = {
            "details": bool(self.product.details),
            "composition": bool(self.product.composition),
            "usage": bool(self.product.usage),
        }

        results["field_checks"] = {
            "required": required_fields,
            "preferred": preferred_fields,
            "content": content_fields,
        }

        # Calculate compliance scores
        required_score = sum(required_fields.values()) / len(required_fields) * 100
        preferred_score = sum(preferred_fields.values()) / len(preferred_fields) * 100
        content_score = sum(content_fields.values()) / len(content_fields) * 100

        results["spec_compliance"] = {
            "required_fields": f"{required_score:.0f}%",
            "preferred_fields": f"{preferred_score:.0f}%",
            "content_sections": f"{content_score:.0f}%",
            "overall": f"{(required_score * 0.5 + preferred_score * 0.3 + content_score * 0.2):.1f}%",
        }

        # Check against spec targets
        if required_score < 100:
            results["overall_valid"] = False
            results["missing_fields"].extend([k for k, v in required_fields.items() if not v])

        if preferred_score < 90:
            results["warnings"].append(f"Preferred fields below target: {preferred_score:.0f}% (target: 90%+)")

        return results
