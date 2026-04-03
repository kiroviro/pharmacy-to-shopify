"""
Product classifier — classification logic extracted from PharmacyParser.

Pure functions for determining pharmaceutical form, target audience,
Google Shopping category, and Google age group. No I/O or state.
"""

from __future__ import annotations

import re


def extract_application_form(title: str) -> str:
    """Extract pharmaceutical application form from product title."""
    if not title:
        return ""

    title_lower = title.lower()
    form_patterns = [
        ("таблетки", "Таблетки", False),
        ("капсули", "Капсули", False),
        ("сашета", "Сашета", False),
        ("саше", "Сашета", True),
        ("пастили", "Пастили", False),
        ("драже", "Драже", False),
        ("крем", "Крем", False),
        ("мехлем", "Мехлем", False),
        ("гел", "Гел", False),
        ("маска", "Маска", False),
        ("серум", "Серум", False),
        ("лосион", "Лосион", False),
        ("балсам", "Балсам", False),
        ("пяна", "Пяна", False),
        ("тоник", "Тоник", False),
        ("паста", "Паста", False),
        ("пудра", "Пудра", False),
        ("спрей", "Спрей", False),
        ("капки", "Капки", False),
        ("разтвор", "Разтвор", False),
        ("сироп", "Сироп", False),
        ("суспензия", "Суспензия", False),
        ("олио", "Олио", False),
        ("масло", "Масло", False),
        ("шампоан", "Шампоан", False),
        ("пластир", "Пластири", True),
        ("супозитори", "Супозитории", True),
    ]
    for keyword, label, is_stem in form_patterns:
        pattern = rf'\b{keyword}' if is_stem else rf'\b{keyword}\b'
        if re.search(pattern, title_lower):
            return label

    return ""


def extract_target_audience(categories: list[str], title: str) -> str:
    """Derive target audience from categories and title."""
    text = " ".join(categories).lower() + " " + title.lower()

    baby_keywords = ["бебе", "бебета", "бебешк", "новородено", "кърмач"]
    for kw in baby_keywords:
        if kw in text:
            return "Бебета"

    child_keywords = ["дете", "деца", "детск"]
    for kw in child_keywords:
        if kw in text:
            return "Деца"

    return "Възрастни"


def determine_google_category(categories: list[str], seo_settings: dict) -> str:
    """Map product categories to Google Shopping taxonomy via config."""
    category_map = seo_settings.get("google_shopping_category_map", {})
    default = seo_settings.get("google_shopping", {}).get(
        "default_category", "Health & Beauty > Health Care > Pharmacy"
    )
    for cat in categories:
        if cat in category_map:
            return category_map[cat]
        for config_key, google_cat in category_map.items():
            if cat.lower().startswith(config_key.lower()):
                return google_cat

    return default


def determine_google_age_group(categories: list[str]) -> str:
    """Determine Google Shopping age group from categories."""
    child_keywords = ["дете", "бебе", "деца", "бебета", "детски", "бебешки"]
    categories_lower = " ".join(categories).lower()
    for keyword in child_keywords:
        if keyword in categories_lower:
            return "kids"
    return "adult"
