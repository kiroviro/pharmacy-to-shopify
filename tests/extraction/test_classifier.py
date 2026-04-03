"""Tests for src/extraction/classifier.py"""

import pytest

from src.extraction.classifier import (
    determine_google_age_group,
    determine_google_category,
    extract_application_form,
    extract_target_audience,
)


class TestExtractApplicationForm:
    def test_empty_title(self):
        assert extract_application_form("") == ""

    def test_no_match(self):
        assert extract_application_form("Витамин D3 1000 IU") == ""

    @pytest.mark.parametrize(
        "title, expected",
        [
            ("Аспирин таблетки 500мг x20", "Таблетки"),
            ("Омега-3 капсули 1000мг", "Капсули"),
            ("Витамин C сашета 10бр", "Сашета"),
            ("Пастили за гърло", "Пастили"),
            ("Драже витамини", "Драже"),
            ("Детски крем за лице", "Крем"),
            ("Мехлем за рани", "Мехлем"),
            ("Обезболяващ гел 50мл", "Гел"),
            ("Хидратираща маска", "Маска"),
            ("Хиалуронов серум", "Серум"),
            ("Лосион за тяло", "Лосион"),
            ("Балсам за устни", "Балсам"),
            ("Пяна за бръснене", "Пяна"),
            ("Тоник за лице", "Тоник"),
            ("Паста за зъби", "Паста"),
            ("Бебешка пудра", "Пудра"),
            ("Назален спрей", "Спрей"),
            ("Очни капки 10мл", "Капки"),
            ("Разтвор за лещи", "Разтвор"),
            ("Сироп за кашлица", "Сироп"),
            ("Суспензия 100мл", "Суспензия"),
            ("Бебешко олио", "Олио"),
            ("Масло от жожоба", "Масло"),
            ("Шампоан против пърхот", "Шампоан"),
        ],
        ids=lambda t: t if isinstance(t, str) and len(t) < 20 else None,
    )
    def test_exact_keyword_match(self, title, expected):
        assert extract_application_form(title) == expected

    def test_stem_match_sashe(self):
        """'саше' is a stem pattern — should match 'сашета' too."""
        assert extract_application_form("Витамин саше 5г") == "Сашета"

    def test_stem_match_plastir(self):
        """'пластир' is a stem — matches 'пластири', 'пластира', etc."""
        assert extract_application_form("Пластири за мазоли") == "Пластири"

    def test_stem_match_supozitori(self):
        """'супозитори' is a stem — matches 'супозитории', 'супозиториите', etc."""
        assert extract_application_form("Супозитории за деца") == "Супозитории"

    def test_case_insensitive(self):
        assert extract_application_form("ТАБЛЕТКИ ЗА ГЛАВОБОЛИЕ") == "Таблетки"

    def test_first_match_wins(self):
        """When multiple forms appear, the first in pattern order wins."""
        # 'таблетки' appears before 'капсули' in patterns
        assert extract_application_form("таблетки и капсули комплект") == "Таблетки"

    def test_word_boundary_prevents_partial_match(self):
        """Non-stem patterns require word boundary — partial match should fail."""
        # 'гел' should not match inside 'ангел'
        assert extract_application_form("Ангел крем") == "Крем"

    def test_stem_pattern_matches_longer_words(self):
        """Stem patterns (is_stem=True) match words that start with the keyword."""
        assert extract_application_form("Пластирите са удобни") == "Пластири"

    def test_keyword_at_start_of_title(self):
        assert extract_application_form("Крем за ръце 50мл") == "Крем"

    def test_keyword_at_end_of_title(self):
        assert extract_application_form("Витамин C 1000мг таблетки") == "Таблетки"


class TestExtractTargetAudience:
    def test_defaults_to_adults(self):
        assert extract_target_audience([], "") == "Възрастни"

    def test_empty_categories_and_title(self):
        assert extract_target_audience([], "") == "Възрастни"

    @pytest.mark.parametrize(
        "keyword",
        ["бебе", "бебета", "бебешк", "новородено", "кърмач"],
    )
    def test_baby_keywords_in_title(self, keyword):
        assert extract_target_audience([], f"Продукт за {keyword}") == "Бебета"

    @pytest.mark.parametrize(
        "keyword",
        ["бебе", "бебета", "бебешки", "новородено", "кърмачета"],
    )
    def test_baby_keywords_in_categories(self, keyword):
        assert extract_target_audience([f"Грижа за {keyword}"], "") == "Бебета"

    @pytest.mark.parametrize(
        "keyword",
        ["дете", "деца", "детск"],
    )
    def test_child_keywords_in_title(self, keyword):
        assert extract_target_audience([], f"Сироп за {keyword}") == "Деца"

    @pytest.mark.parametrize(
        "keyword",
        ["деца", "детски"],
    )
    def test_child_keywords_in_categories(self, keyword):
        assert extract_target_audience([f"Витамини за {keyword}"], "") == "Деца"

    def test_baby_takes_priority_over_child(self):
        """Baby keywords are checked first, so 'бебе' wins over 'деца'."""
        assert extract_target_audience(["деца"], "бебешко олио") == "Бебета"

    def test_adult_when_no_keywords(self):
        assert extract_target_audience(["Лекарства", "Аналгетици"], "Аспирин 500мг") == "Възрастни"

    def test_case_insensitive(self):
        assert extract_target_audience([], "БЕБЕШКО мляко") == "Бебета"

    def test_keyword_in_both_sources(self):
        """Keyword found in categories and title — still returns correctly."""
        assert extract_target_audience(["Бебета"], "Бебешки крем") == "Бебета"


class TestDetermineGoogleCategory:
    def test_empty_categories_returns_config_default(self):
        seo = {"google_shopping": {"default_category": "Custom Default"}}
        assert determine_google_category([], seo) == "Custom Default"

    def test_empty_categories_returns_hardcoded_default(self):
        assert determine_google_category([], {}) == "Health & Beauty > Health Care > Pharmacy"

    def test_exact_match(self):
        seo = {
            "google_shopping_category_map": {
                "Витамини": "Health > Vitamins & Supplements",
            }
        }
        assert determine_google_category(["Витамини"], seo) == "Health > Vitamins & Supplements"

    def test_prefix_match(self):
        seo = {
            "google_shopping_category_map": {
                "Козметика": "Health & Beauty > Personal Care",
            }
        }
        assert determine_google_category(["Козметика за лице"], seo) == "Health & Beauty > Personal Care"

    def test_prefix_match_case_insensitive(self):
        seo = {
            "google_shopping_category_map": {
                "козметика": "Health & Beauty > Personal Care",
            }
        }
        assert determine_google_category(["Козметика"], seo) == "Health & Beauty > Personal Care"

    def test_first_category_wins(self):
        seo = {
            "google_shopping_category_map": {
                "Витамини": "Vitamins",
                "Лекарства": "Pharmacy",
            }
        }
        assert determine_google_category(["Витамини", "Лекарства"], seo) == "Vitamins"

    def test_second_category_matches_when_first_doesnt(self):
        seo = {
            "google_shopping_category_map": {
                "Лекарства": "Pharmacy",
            }
        }
        assert determine_google_category(["Непознато", "Лекарства"], seo) == "Pharmacy"

    def test_no_match_returns_default(self):
        seo = {
            "google_shopping_category_map": {
                "Витамини": "Vitamins",
            },
            "google_shopping": {"default_category": "Fallback"},
        }
        assert determine_google_category(["Непознато"], seo) == "Fallback"

    def test_empty_seo_settings(self):
        assert determine_google_category(["Нещо"], {}) == "Health & Beauty > Health Care > Pharmacy"


class TestDetermineGoogleAgeGroup:
    def test_empty_categories(self):
        assert determine_google_age_group([]) == "adult"

    def test_adult_by_default(self):
        assert determine_google_age_group(["Лекарства", "Аналгетици"]) == "adult"

    @pytest.mark.parametrize(
        "keyword",
        ["дете", "бебе", "деца", "бебета", "детски", "бебешки"],
    )
    def test_kids_keywords(self, keyword):
        assert determine_google_age_group([f"Грижа за {keyword}"]) == "kids"

    def test_keyword_in_second_category(self):
        assert determine_google_age_group(["Витамини", "За деца"]) == "kids"

    def test_case_insensitive(self):
        assert determine_google_age_group(["БЕБЕШКИ продукти"]) == "kids"

    def test_no_partial_false_positive(self):
        """Categories without child keywords should return adult."""
        assert determine_google_age_group(["Козметика", "Парфюми"]) == "adult"
