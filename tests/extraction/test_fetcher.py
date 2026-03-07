"""Tests for PharmacyFetcher header building."""
from src.common.constants import BROWSER_HEADERS, USER_AGENTS
from src.extraction.fetcher import PharmacyFetcher


def test_build_headers_returns_dict_with_user_agent():
    fetcher = PharmacyFetcher(url="https://benu.bg/test")
    headers = fetcher._build_headers()
    assert "User-Agent" in headers
    assert headers["User-Agent"] in USER_AGENTS


def test_build_headers_includes_all_browser_headers():
    fetcher = PharmacyFetcher(url="https://benu.bg/test")
    headers = fetcher._build_headers()
    for key in BROWSER_HEADERS:
        assert key in headers, f"Missing header: {key}"


def test_build_headers_picks_different_agents():
    fetcher = PharmacyFetcher(url="https://benu.bg/test")
    agents = {fetcher._build_headers()["User-Agent"] for _ in range(50)}
    # With 10 UAs and 50 draws, probability of only 1 unique is astronomically low
    assert len(agents) > 1
