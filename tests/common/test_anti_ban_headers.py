"""Tests for anti-ban crawl constants."""
from src.common.constants import USER_AGENTS, BROWSER_HEADERS


def test_user_agents_is_nonempty_list():
    assert isinstance(USER_AGENTS, list)
    assert len(USER_AGENTS) >= 8


def test_user_agents_are_strings():
    for ua in USER_AGENTS:
        assert isinstance(ua, str)
        assert len(ua) > 20  # sanity: real UAs are long


def test_browser_headers_has_required_keys():
    required = {
        "Accept",
        "Accept-Encoding",
        "Accept-Language",
        "Cache-Control",
        "Sec-Fetch-Dest",
        "Sec-Fetch-Mode",
        "Sec-Fetch-Site",
        "Upgrade-Insecure-Requests",
    }
    assert required.issubset(set(BROWSER_HEADERS.keys()))


def test_browser_headers_values_are_strings():
    for k, v in BROWSER_HEADERS.items():
        assert isinstance(v, str), f"{k} value should be a string"


def test_browser_headers_does_not_contain_user_agent():
    # User-Agent must be picked randomly per request, not hardcoded in BROWSER_HEADERS
    assert "User-Agent" not in BROWSER_HEADERS
