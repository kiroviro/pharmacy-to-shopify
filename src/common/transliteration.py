"""
Bulgarian Transliteration Utilities

Converts Bulgarian Cyrillic text to Latin characters for URL handles.
"""

import re

# Bulgarian Cyrillic to Latin transliteration map
TRANSLIT_MAP = {
    # Lowercase
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l',
    'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's',
    'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch',
    'ш': 'sh', 'щ': 'sht', 'ъ': 'a', 'ь': '', 'ю': 'yu', 'я': 'ya',
    # Uppercase
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E',
    'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L',
    'М': 'M', 'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S',
    'Т': 'T', 'У': 'U', 'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch',
    'Ш': 'Sh', 'Щ': 'Sht', 'Ъ': 'A', 'Ь': '', 'Ю': 'Yu', 'Я': 'Ya',
}


def transliterate(text: str) -> str:
    """
    Transliterate Bulgarian Cyrillic text to Latin characters.

    Args:
        text: Text containing Bulgarian characters

    Returns:
        Transliterated text with Latin characters

    Example:
        >>> transliterate("Козметика")
        'Kozmetika'
    """
    result = []
    for char in text:
        if char in TRANSLIT_MAP:
            result.append(TRANSLIT_MAP[char])
        else:
            result.append(char)
    return ''.join(result)


def generate_handle(title: str, prefix: str = '') -> str:
    """
    Generate URL-friendly handle from title.

    Converts title to lowercase, transliterates Bulgarian characters,
    and replaces spaces/special characters with hyphens.

    Args:
        title: Product or collection title
        prefix: Optional prefix (e.g., 'brand-' for brand collections)

    Returns:
        URL-friendly handle

    Example:
        >>> generate_handle("Козметика за лице")
        'kozmetika-za-litse'
        >>> generate_handle("Nivea", prefix="brand-")
        'brand-nivea'
    """
    # Add prefix if provided
    if prefix:
        text = f"{prefix}{title}"
    else:
        text = title

    result = []
    for char in text.lower():
        if char in TRANSLIT_MAP:
            # Use lowercase version of transliteration
            result.append(TRANSLIT_MAP[char].lower())
        elif char.isalnum():
            result.append(char)
        elif char in ' -_':
            result.append('-')
        # Skip other characters

    handle = ''.join(result)

    # Clean up multiple consecutive hyphens
    handle = re.sub(r'-+', '-', handle)

    # Remove leading/trailing hyphens
    return handle.strip('-')
