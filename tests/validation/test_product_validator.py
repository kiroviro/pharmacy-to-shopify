"""Tests for content-quality checks added to SpecificationValidator."""

import pytest

from src.extraction.validator import SpecificationValidator
from src.models import ExtractedProduct, ProductImage


def _make_product(**overrides) -> ExtractedProduct:
    """Return a fully valid product with optional field overrides."""
    defaults = dict(
        title="Some Valid Product Name",
        url="https://benu.bg/product/some-valid-product",
        brand="TestBrand",
        sku="TST-001",
        price="12.50",
        category_path=["Vitamins"],
        handle="some-valid-product",
        images=[ProductImage(source_url="https://cdn.benu.bg/img1.jpg", position=1)],
        description="<p>Some description.</p>",
    )
    defaults.update(overrides)
    return ExtractedProduct(**defaults)


class TestTitleChecks:
    def test_title_too_short(self):
        p = _make_product(title="Hi")
        result = SpecificationValidator(p).validate()
        assert result["overall_valid"] is False
        assert any("title" in e and "short" in e for e in result["errors"])

    def test_title_too_long(self):
        p = _make_product(title="A" * 251)
        result = SpecificationValidator(p).validate()
        assert result["overall_valid"] is False
        assert any("title" in e and "long" in e for e in result["errors"])

    def test_title_minimum_valid_length(self):
        p = _make_product(title="ABCDE")
        result = SpecificationValidator(p).validate()
        assert not any("title" in e for e in result["errors"])

    def test_title_maximum_valid_length(self):
        p = _make_product(title="A" * 250)
        result = SpecificationValidator(p).validate()
        assert not any("title" in e for e in result["errors"])


class TestUrlChecks:
    def test_url_without_https(self):
        p = _make_product(url="http://benu.bg/product")
        result = SpecificationValidator(p).validate()
        assert result["overall_valid"] is False
        assert any("url" in e for e in result["errors"])

    def test_url_with_https(self):
        p = _make_product(url="https://benu.bg/product")
        result = SpecificationValidator(p).validate()
        assert not any("url" in e for e in result["errors"])


class TestPriceChecks:
    def test_price_zero(self):
        p = _make_product(price="0.00")
        result = SpecificationValidator(p).validate()
        assert any("price" in e and "> 0" in e for e in result["errors"])

    def test_price_negative(self):
        p = _make_product(price="-5.00")
        result = SpecificationValidator(p).validate()
        assert any("price" in e for e in result["errors"])

    def test_price_not_a_number(self):
        p = _make_product(price="not-a-price")
        result = SpecificationValidator(p).validate()
        assert any("price" in e and "number" in e for e in result["errors"])

    def test_price_suspiciously_high(self):
        p = _make_product(price="15000.00")
        result = SpecificationValidator(p).validate()
        assert any("price" in e and "high" in e for e in result["errors"])

    def test_valid_price(self):
        p = _make_product(price="9.99")
        result = SpecificationValidator(p).validate()
        assert not any("price" in e for e in result["errors"])


class TestHandleFormat:
    def test_handle_with_uppercase(self):
        p = _make_product(handle="Invalid-Handle")
        result = SpecificationValidator(p).validate()
        assert any("handle" in e and "format" in e for e in result["errors"])

    def test_handle_with_spaces(self):
        p = _make_product(handle="invalid handle")
        result = SpecificationValidator(p).validate()
        assert any("handle" in e and "format" in e for e in result["errors"])

    def test_handle_too_long(self):
        p = _make_product(handle="a" * 201)
        result = SpecificationValidator(p).validate()
        assert any("handle" in e and "long" in e for e in result["errors"])

    def test_valid_handle(self):
        p = _make_product(handle="vitamin-c-500mg")
        result = SpecificationValidator(p).validate()
        assert not any("handle" in e for e in result["errors"])

    def test_handle_with_numbers(self):
        p = _make_product(handle="product-123")
        result = SpecificationValidator(p).validate()
        assert not any("handle" in e for e in result["errors"])

    def test_handle_missing(self):
        p = _make_product(handle="")
        result = SpecificationValidator(p).validate()
        assert any("handle" in e and "missing" in e for e in result["errors"])


class TestImageUrlChecks:
    def test_image_http_not_https(self):
        p = _make_product(images=[
            ProductImage(source_url="http://cdn.benu.bg/img.jpg", position=1)
        ])
        result = SpecificationValidator(p).validate()
        assert any("image URL" in e and "https" in e for e in result["errors"])

    def test_image_placeholder_domain(self):
        p = _make_product(images=[
            ProductImage(source_url="https://via.placeholder.com/300x300", position=1)
        ])
        result = SpecificationValidator(p).validate()
        assert any("placeholder domain" in e for e in result["errors"])

    def test_image_example_com_domain(self):
        p = _make_product(images=[
            ProductImage(source_url="https://example.com/img.jpg", position=1)
        ])
        result = SpecificationValidator(p).validate()
        assert any("placeholder domain" in e for e in result["errors"])

    def test_image_subdomain_of_example_com_is_flagged(self):
        """
        pharmacy.example.com must be flagged — it's the actual domain used in the
        benu.bg image URL regression (commit a9b6d3b): when source_domain was not
        forwarded to the extractor, image URLs were built with 'pharmacy.example.com'
        instead of 'benu.bg', causing Shopify "Media processing failed" on import.
        """
        p = _make_product(images=[
            ProductImage(source_url="https://pharmacy.example.com/img.jpg", position=1)
        ])
        result = SpecificationValidator(p).validate()
        assert any("placeholder domain" in e for e in result["errors"])

    def test_image_any_example_com_subdomain_is_flagged(self):
        """Any subdomain of example.com in an image URL is a placeholder signal."""
        for subdomain in ["cdn.example.com", "static.example.com", "www.example.com"]:
            p = _make_product(images=[
                ProductImage(source_url=f"https://{subdomain}/img.jpg", position=1)
            ])
            result = SpecificationValidator(p).validate()
            assert any("placeholder domain" in e for e in result["errors"]), \
                f"Expected {subdomain!r} to be flagged"

    def test_valid_image_url(self):
        p = _make_product(images=[
            ProductImage(source_url="https://cdn.benu.bg/products/img.jpg", position=1)
        ])
        result = SpecificationValidator(p).validate()
        assert not any("image URL" in e for e in result["errors"])

    def test_no_images_is_error(self):
        p = _make_product(images=[])
        result = SpecificationValidator(p).validate()
        assert any("images: no images" in e for e in result["errors"])


class TestPriceEurConsistency:
    def test_consistent_eur_price(self):
        # 6.39 EUR × 1.95583 = 12.488 BGN, within 1% of 12.50
        p = _make_product(price="12.50", price_eur="6.39")
        result = SpecificationValidator(p).validate()
        assert not any("price_eur" in e for e in result["errors"])

    def test_inconsistent_eur_price(self):
        # 10.00 EUR × 1.95583 = 19.56 BGN — very far from 12.50
        p = _make_product(price="12.50", price_eur="10.00")
        result = SpecificationValidator(p).validate()
        assert any("price_eur consistency" in e for e in result["errors"])

    def test_no_eur_price_skips_check(self):
        p = _make_product(price="12.50", price_eur="")
        result = SpecificationValidator(p).validate()
        assert not any("price_eur" in e for e in result["errors"])


class TestBarcodeWarning:
    def test_valid_ean13(self):
        p = _make_product(barcode="3800123456789")
        result = SpecificationValidator(p).validate()
        assert not any("barcode" in w for w in result["warnings"])

    def test_valid_ean8(self):
        p = _make_product(barcode="12345678")
        result = SpecificationValidator(p).validate()
        assert not any("barcode" in w for w in result["warnings"])

    def test_barcode_with_letters(self):
        p = _make_product(barcode="ABC123456789")
        result = SpecificationValidator(p).validate()
        assert any("barcode" in w for w in result["warnings"])

    def test_barcode_wrong_length(self):
        # 11 digits is not a valid EAN/UPC length
        p = _make_product(barcode="12345678901")
        result = SpecificationValidator(p).validate()
        assert any("barcode" in w for w in result["warnings"])

    def test_barcode_valid_lengths(self):
        for barcode in ["12345678", "123456789012", "1234567890123", "12345678901234"]:
            p = _make_product(barcode=barcode)
            result = SpecificationValidator(p).validate()
            assert not any("barcode" in w for w in result["warnings"]), \
                f"Expected no barcode warning for {barcode!r}"

    def test_no_barcode_no_warning(self):
        p = _make_product(barcode="")
        result = SpecificationValidator(p).validate()
        assert not any("barcode" in w for w in result["warnings"])


class TestSeoWarnings:
    def test_seo_title_too_long(self):
        p = _make_product(seo_title="A" * 71)
        result = SpecificationValidator(p).validate()
        assert any("seo_title" in w for w in result["warnings"])

    def test_seo_title_at_limit(self):
        p = _make_product(seo_title="A" * 70)
        result = SpecificationValidator(p).validate()
        assert not any("seo_title" in w for w in result["warnings"])

    def test_seo_description_too_long(self):
        p = _make_product(seo_description="A" * 156)
        result = SpecificationValidator(p).validate()
        assert any("seo_description" in w for w in result["warnings"])

    def test_seo_description_at_limit(self):
        p = _make_product(seo_description="A" * 155)
        result = SpecificationValidator(p).validate()
        assert not any("seo_description" in w for w in result["warnings"])


class TestIssuesKey:
    def test_issues_key_present(self):
        p = _make_product()
        result = SpecificationValidator(p).validate()
        assert "issues" in result

    def test_issues_contains_errors_and_specific_warnings(self):
        # Product with both errors and a warning
        p = _make_product(
            handle="",         # error
            seo_title="A" * 80,  # warning
        )
        result = SpecificationValidator(p).validate()
        assert len(result["errors"]) > 0
        # issues must contain the error messages
        for err in result["errors"]:
            assert err in result["issues"]

    def test_valid_product_has_empty_issues(self):
        p = _make_product()
        result = SpecificationValidator(p).validate()
        assert result["issues"] == []
        assert result["overall_valid"] is True
