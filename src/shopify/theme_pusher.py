"""
ThemePusher — push Shopify theme assets via the Admin API.

Encapsulates file reading, binary/text detection, asset key generation,
and API calls. Accepts all dependencies via constructor for testability.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path

from .api_client import ShopifyAPIClient

logger = logging.getLogger(__name__)

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".eot",
}


class ThemePusher:
    """Push theme files to Shopify via the Admin API."""

    def __init__(
        self,
        client: ShopifyAPIClient,
        theme_id: str,
        theme_dir: Path,
    ) -> None:
        self.client = client
        self.theme_id = theme_id
        self.theme_dir = theme_dir

    def theme_key(self, file_path: Path) -> str:
        """Convert absolute path to Shopify asset key, e.g. 'assets/component-card.css'."""
        return str(file_path.relative_to(self.theme_dir))

    def build_asset_payload(self, file_path: Path) -> dict:
        """Build the asset dict for the API PUT request."""
        key = self.theme_key(file_path)
        if file_path.suffix.lower() in BINARY_EXTENSIONS:
            encoded = base64.b64encode(file_path.read_bytes()).decode("utf-8")
            return {"key": key, "attachment": encoded}
        return {"key": key, "value": file_path.read_text(encoding="utf-8")}

    def push_file(self, file_path: Path, dry_run: bool = False) -> bool:
        """
        Push a single theme file to Shopify.

        Returns True on success (or dry run), False on error or missing file.
        """
        key = self.theme_key(file_path)

        if not file_path.exists():
            print(f"  [skip]  {key}  (file not found)")
            return False

        if dry_run:
            size = file_path.stat().st_size
            print(f"  [dry]   {key}  ({size:,} bytes)")
            return True

        asset = self.build_asset_payload(file_path)
        result = self.client.rest_request(
            "PUT", f"themes/{self.theme_id}/assets.json", data={"asset": asset}
        )
        if result is not None:
            updated_at = result.get("asset", {}).get("updated_at", "")
            print(f"  [ok]    {key}  ({updated_at})")
            return True

        print(f"  [error] {key}  (see log for details)")
        return False

    def collect_theme_files(self) -> list[Path]:
        """Return all text/binary theme files, excluding non-theme artifacts."""
        exclude = {".git", "node_modules", ".DS_Store", "THEME_INFO.json", "README.md"}
        return [
            f
            for f in sorted(self.theme_dir.rglob("*"))
            if f.is_file() and not any(part in exclude for part in f.parts)
        ]
