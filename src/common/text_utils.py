"""
Text Utilities

Helper functions for text processing and cleanup.
"""

import re


def remove_source_references(text: str, source_domain: str) -> str:
    """
    Remove all references to a source domain from text.

    Args:
        text: Text that may contain source references
        source_domain: Domain to remove (e.g., "benu.bg")

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
