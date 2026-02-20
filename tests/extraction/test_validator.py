"""Tests for src/extraction/validator.py"""


from src.extraction.validator import SpecificationValidator


class TestValidate:
    def test_full_product_is_valid(self, full_product):
        validator = SpecificationValidator(full_product)
        result = validator.validate()
        assert result["overall_valid"] is True

    def test_minimal_product_has_content_errors(self, minimal_product):
        """Minimal product lacks images, handle, and category_path — all hard errors."""
        validator = SpecificationValidator(minimal_product)
        result = validator.validate()
        assert result["overall_valid"] is False
        assert len(result["errors"]) > 0

    def test_result_structure(self, full_product):
        validator = SpecificationValidator(full_product)
        result = validator.validate()
        assert "overall_valid" in result
        assert "field_checks" in result
        assert "spec_compliance" in result
        assert "missing_fields" in result
        assert "warnings" in result
        assert "errors" in result
        assert "issues" in result

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
        # Minimal product is missing description and preferred fields
        assert len(result["warnings"]) > 0

    def test_full_product_no_missing_fields(self, full_product):
        validator = SpecificationValidator(full_product)
        result = validator.validate()
        assert result["missing_fields"] == []

    def test_full_product_no_errors(self, full_product):
        result = SpecificationValidator(full_product).validate()
        assert result["errors"] == []

    def test_full_product_empty_issues(self, full_product):
        result = SpecificationValidator(full_product).validate()
        assert result["issues"] == []

    def test_minimal_product_issues_contain_error_messages(self, minimal_product):
        result = SpecificationValidator(minimal_product).validate()
        for err in result["errors"]:
            assert err in result["issues"]
