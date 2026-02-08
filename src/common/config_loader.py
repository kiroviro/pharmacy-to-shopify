"""
Configuration Loader

Loads YAML configuration files for categories, tag normalization,
vendor defaults, promotional patterns, and known brands.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None


def _get_config_dir() -> Path:
    """Get the config directory path."""
    # Try relative to this file first
    module_dir = Path(__file__).parent.parent.parent
    config_dir = module_dir / 'config'

    if config_dir.exists():
        return config_dir

    # Try current working directory
    cwd_config = Path.cwd() / 'config'
    if cwd_config.exists():
        return cwd_config

    raise FileNotFoundError(
        f"Config directory not found. Tried: {config_dir}, {cwd_config}"
    )


def load_config(filename: str) -> Dict[str, Any]:
    """
    Load a YAML configuration file.

    Args:
        filename: Name of the config file (e.g., 'categories.yaml')

    Returns:
        Parsed YAML content as dictionary

    Raises:
        ImportError: If PyYAML is not installed
        FileNotFoundError: If config file doesn't exist
    """
    if yaml is None:
        raise ImportError(
            "PyYAML is required for config loading. "
            "Install with: pip install pyyaml"
        )

    config_path = _get_config_dir() / filename

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_categories() -> Dict[str, List[str]]:
    """
    Load category configuration.

    Returns:
        Dictionary mapping L1 categories to lists of L2 subcategories

    Example:
        {
            'Козметика': ['Козметика за лице', 'Козметика за тяло', ...],
            'Мама и бебе': ['Бебешка козметика', ...],
            ...
        }
    """
    config = load_config('categories.yaml')
    return config.get('categories', {})


def load_tag_normalization() -> Dict[str, str]:
    """
    Load tag normalization rules.

    Returns:
        Dictionary mapping lowercase tag to canonical form

    Example:
        {
            'abopharma': 'AboPharma',
            'a-derma': 'A-Derma',
            ...
        }
    """
    config = load_config('tag_normalization.yaml')
    return config.get('normalization', {})


def load_vendor_defaults() -> Dict[str, List[str]]:
    """
    Load vendor default tags.

    Returns:
        Dictionary mapping lowercase vendor name to list of default tags

    Example:
        {
            'a-derma': ['Козметика', 'Дермокозметика', 'Медицинска козметика'],
            ...
        }
    """
    config = load_config('vendor_defaults.yaml')
    return config.get('vendor_defaults', {})


def load_promotional_patterns() -> List[str]:
    """
    Load promotional patterns to remove.

    Returns:
        List of patterns (substrings) that identify promotional tags

    Example:
        ['2026', 'black friday', 'промоция', ...]
    """
    config = load_config('promotional_patterns.yaml')
    return config.get('promotional_patterns', [])


def build_subcategory_to_l1_map(categories: Optional[Dict[str, List[str]]] = None) -> Dict[str, str]:
    """
    Build a mapping from L2 subcategories to their L1 parent category.

    Args:
        categories: Category dict (if None, loads from config)

    Returns:
        Dictionary mapping lowercase subcategory name to L1 category name

    Example:
        {
            'козметика за лице': 'Козметика',
            'бебешка козметика': 'Мама и бебе',
            ...
        }
    """
    if categories is None:
        categories = load_categories()

    subcategory_to_l1 = {}
    for l1_category, subcategories in categories.items():
        for subcategory in subcategories:
            subcategory_to_l1[subcategory.lower()] = l1_category

    return subcategory_to_l1


def get_l1_category_names(categories: Optional[Dict[str, List[str]]] = None) -> set:
    """
    Get set of L1 category names (lowercase).

    Args:
        categories: Category dict (if None, loads from config)

    Returns:
        Set of lowercase L1 category names
    """
    if categories is None:
        categories = load_categories()

    return {cat.lower() for cat in categories.keys()}


def load_known_brands() -> set:
    """
    Load known brand names for title prefix matching.

    Returns:
        Set of brand names (canonical capitalization)

    Example:
        {'Boiron', 'Nivea', 'Garnier', 'AboPharma', ...}
    """
    config = load_config('known_brands.yaml')
    brands = config.get('brands', [])
    return set(brands)


def load_seo_settings() -> Dict[str, Any]:
    """
    Load SEO settings configuration.

    Returns:
        Dictionary with SEO settings including store_name, title/description limits,
        Google Shopping default category, and category mapping.
    """
    return load_config('seo_settings.yaml')


def get_brands_lowercase_map(brands: Optional[set] = None) -> Dict[str, str]:
    """
    Get mapping from lowercase brand name to canonical form.

    Args:
        brands: Set of brand names (if None, loads from config)

    Returns:
        Dictionary mapping lowercase brand to canonical form

    Example:
        {
            'abopharma': 'AboPharma',
            'a-derma': 'A-Derma',
            "nature's way": "Nature's Way",
            ...
        }
    """
    if brands is None:
        brands = load_known_brands()

    return {brand.lower(): brand for brand in brands}
