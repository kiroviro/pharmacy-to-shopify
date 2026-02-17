"""
URL Discovery modules for pharmacy sites.

Modules:
    pharmacy_discoverer - PharmacyURLDiscoverer for pharmacy.example.com
"""

from .pharmacy_discoverer import PharmacyURLDiscoverer

# Site to discoverer mapping
SITE_DISCOVERERS = {
    'pharmacy.example.com': PharmacyURLDiscoverer,
    'benu.bg': PharmacyURLDiscoverer,
}


def get_discoverer_for_site(site: str):
    """
    Get the appropriate URL discoverer class for a site.

    Args:
        site: Site identifier (e.g., "pharmacy.example.com")

    Returns:
        Discoverer class

    Raises:
        ValueError: If site is not supported
    """
    site = site.lower().strip()

    if site in SITE_DISCOVERERS:
        return SITE_DISCOVERERS[site]

    # Try partial match
    for key, discoverer in SITE_DISCOVERERS.items():
        if key in site or site in key:
            return discoverer

    raise ValueError(f"Unsupported site: {site}. Supported: {', '.join(SITE_DISCOVERERS.keys())}")


def get_supported_sites() -> list:
    """Return list of supported sites for discovery."""
    return list(SITE_DISCOVERERS.keys())


__all__ = [
    'PharmacyURLDiscoverer',
    'get_discoverer_for_site',
    'get_supported_sites',
    'SITE_DISCOVERERS',
]
