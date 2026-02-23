"""Tests for scripts/push_theme.py"""

import base64
from unittest.mock import MagicMock, patch

from scripts.push_theme import (
    build_asset_payload,
    collect_theme_files,
    push_file,
    theme_key,
)

# ── theme_key ────────────────────────────────────────────────────────────────


class TestThemeKey:
    def test_converts_asset_path(self):
        from scripts.push_theme import THEME_DIR

        file_path = THEME_DIR / "assets" / "component-card.css"
        assert theme_key(file_path) == "assets/component-card.css"

    def test_converts_section_path(self):
        from scripts.push_theme import THEME_DIR

        file_path = THEME_DIR / "sections" / "header.liquid"
        assert theme_key(file_path) == "sections/header.liquid"

    def test_converts_nested_path(self):
        from scripts.push_theme import THEME_DIR

        file_path = THEME_DIR / "templates" / "customers" / "login.json"
        assert theme_key(file_path) == "templates/customers/login.json"


# ── build_asset_payload ──────────────────────────────────────────────────────


class TestBuildAssetPayload:
    def test_text_file_uses_value(self, tmp_path):
        css_file = tmp_path / "test.css"
        css_file.write_text("body { color: red; }", encoding="utf-8")

        with patch("scripts.push_theme.THEME_DIR", tmp_path):
            payload = build_asset_payload(css_file)

        assert payload["key"] == "test.css"
        assert payload["value"] == "body { color: red; }"
        assert "attachment" not in payload

    def test_binary_file_uses_attachment(self, tmp_path):
        png_file = tmp_path / "logo.png"
        png_content = b"\x89PNG\r\n\x1a\n"
        png_file.write_bytes(png_content)

        with patch("scripts.push_theme.THEME_DIR", tmp_path):
            payload = build_asset_payload(png_file)

        assert payload["key"] == "logo.png"
        assert payload["attachment"] == base64.b64encode(png_content).decode("utf-8")
        assert "value" not in payload

    def test_svg_treated_as_binary(self, tmp_path):
        svg_file = tmp_path / "icon.svg"
        svg_file.write_bytes(b"<svg></svg>")

        with patch("scripts.push_theme.THEME_DIR", tmp_path):
            payload = build_asset_payload(svg_file)

        assert "attachment" in payload

    def test_liquid_treated_as_text(self, tmp_path):
        liquid_file = tmp_path / "header.liquid"
        liquid_file.write_text("{{ shop.name }}", encoding="utf-8")

        with patch("scripts.push_theme.THEME_DIR", tmp_path):
            payload = build_asset_payload(liquid_file)

        assert "value" in payload


# ── push_file ────────────────────────────────────────────────────────────────


class TestPushFile:
    def test_missing_file_returns_false(self, tmp_path):
        missing = tmp_path / "nonexistent.css"

        with patch("scripts.push_theme.THEME_DIR", tmp_path):
            result = push_file(missing)

        assert result is False

    def test_dry_run_skips_api_call(self, tmp_path):
        css_file = tmp_path / "test.css"
        css_file.write_text("body {}", encoding="utf-8")

        with patch("scripts.push_theme.THEME_DIR", tmp_path), patch(
            "scripts.push_theme._client"
        ) as mock_client:
            result = push_file(css_file, dry_run=True)

        assert result is True
        mock_client.rest_request.assert_not_called()

    def test_success_returns_true(self, tmp_path):
        css_file = tmp_path / "test.css"
        css_file.write_text("body {}", encoding="utf-8")

        mock_client = MagicMock()
        mock_client.rest_request.return_value = {"asset": {"updated_at": "2026-01-01"}}

        with patch("scripts.push_theme.THEME_DIR", tmp_path), patch(
            "scripts.push_theme._client", mock_client
        ):
            result = push_file(css_file)

        assert result is True
        mock_client.rest_request.assert_called_once()

    def test_api_error_returns_false(self, tmp_path):
        css_file = tmp_path / "test.css"
        css_file.write_text("body {}", encoding="utf-8")

        mock_client = MagicMock()
        mock_client.rest_request.return_value = None

        with patch("scripts.push_theme.THEME_DIR", tmp_path), patch(
            "scripts.push_theme._client", mock_client
        ):
            result = push_file(css_file)

        assert result is False


# ── collect_theme_files ──────────────────────────────────────────────────────


class TestCollectThemeFiles:
    def test_excludes_git_and_node_modules(self, tmp_path):
        # Create theme structure
        (tmp_path / "assets").mkdir()
        (tmp_path / "assets" / "style.css").write_text("body {}")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("gitconfig")
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "pkg.js").write_text("module")

        with patch("scripts.push_theme.THEME_DIR", tmp_path):
            files = collect_theme_files()

        names = [f.name for f in files]
        assert "style.css" in names
        assert "config" not in names
        assert "pkg.js" not in names

    def test_includes_theme_files(self, tmp_path):
        (tmp_path / "assets").mkdir()
        (tmp_path / "sections").mkdir()
        (tmp_path / "assets" / "base.css").write_text("*{}")
        (tmp_path / "sections" / "header.liquid").write_text("<header/>")

        with patch("scripts.push_theme.THEME_DIR", tmp_path):
            files = collect_theme_files()

        names = [f.name for f in files]
        assert "base.css" in names
        assert "header.liquid" in names

    def test_excludes_ds_store(self, tmp_path):
        (tmp_path / "assets").mkdir()
        (tmp_path / "assets" / "style.css").write_text("body {}")
        (tmp_path / ".DS_Store").write_text("")

        with patch("scripts.push_theme.THEME_DIR", tmp_path):
            files = collect_theme_files()

        names = [f.name for f in files]
        assert ".DS_Store" not in names
