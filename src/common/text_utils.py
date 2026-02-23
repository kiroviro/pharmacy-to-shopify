"""
Text Utilities

Helper functions for text processing and cleanup.
"""

from __future__ import annotations

import re

# Exact placeholder hostnames and domain suffixes that mark an image as broken.
# A hostname matches if it IS one of these OR ends with ".<suffix>".
# This catches benu.bg crawl regression: images got pharmacy.example.com base
# domain when source_domain was not forwarded to the extractor (commit a9b6d3b).
PLACEHOLDER_DOMAINS: frozenset[str] = frozenset({
    "example.com",       # catches pharmacy.example.com, www.example.com, etc.
    "placeholder.com",   # catches via.placeholder.com
    "dummyimage.com",
    "placehold.it",
    "placekitten.com",
    "lorempixel.com",
    "localhost",
})


def is_placeholder_domain(hostname: str) -> bool:
    """Return True if hostname is or is a subdomain of a known placeholder domain."""
    h = hostname.lower()
    return any(h == d or h.endswith("." + d) for d in PLACEHOLDER_DOMAINS)


def remove_source_references(text: str | None, source_domain: str) -> str | None:
    """
    Remove all references to a source domain from text.

    Args:
        text: Text that may contain source references
        source_domain: Domain to remove (e.g., "pharmacy.example.com")

    Returns:
        Cleaned text without source references
    """
    if not text:
        return text

    # Remove URLs containing the domain
    text = re.sub(rf'https?://[^\s]*{re.escape(source_domain)}[^\s]*', '', text)

    # Remove mentions of the domain (case insensitive)
    text = re.sub(rf'\b{re.escape(source_domain)}\b', '', text, flags=re.IGNORECASE)

    # Remove the domain name without TLD
    domain_name = source_domain.split('.')[0]
    text = re.sub(rf'\b{re.escape(domain_name)}\b', '', text, flags=re.IGNORECASE)

    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text
