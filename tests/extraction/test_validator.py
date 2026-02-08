"""Tests for src/extraction/validator.py"""


from src.extraction.validator import SpecificationValidator


class TestValidate:
    def test_full_product_is_valid(self, full_product):
        validator = SpecificationValidator(full_product)
        result = validator.validate()
        assert result["overall_valid"] is True

    def test_minimal_product_is_valid(self, minimal_product):
        validator = SpecificationValidator(minimal_product)
        result = validator.validate()
        assert result["overall_valid"] is True

    def test_result_structure(self, full_product):
        validator = SpecificationValidator(full_product)
        result = validator.validate()
        assert "overall_valid" in result
        assert "field_checks" in result
        assert "spec_compliance" in result
        assert "missing_fields" in result
        assert "warnings" in result

    def test_compliance_scores_present(self, full_product):
        validator = SpecificationValidator(full_product)
        result = validator.validate()
        compliance = result["spec_compliance"]
        assert "required_fields" in compliance
        assert "preferred_fields" in compliance
        assert "content_sections" in compliance
        assert "overall" in compliance

    def test_minimal_product_has_warnings(self, minimal_product):
        validator = SpecificationValidator(minimal_product)
        result = validator.validate()
        # Minimal product is missing preferred fields (images, categories)
        assert len(result["warnings"]) > 0

    def test_full_product_no_missing_fields(self, full_product):
        validator = SpecificationValidator(full_product)
        result = validator.validate()
        assert result["missing_fields"] == []
