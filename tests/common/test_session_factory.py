"""Tests for src/common/session_factory.py"""

import requests

from src.common.constants import BROWSER_HEADERS, USER_AGENTS
from src.common.session_factory import build_headers, create_session, rotate_headers


class TestBuildHeaders:
    def test_returns_dict(self):
        headers = build_headers()
        assert isinstance(headers, dict)

    def test_contains_user_agent(self):
        headers = build_headers()
        assert "User-Agent" in headers

    def test_user_agent_from_pool(self):
        headers = build_headers()
        assert headers["User-Agent"] in USER_AGENTS

    def test_contains_all_browser_headers(self):
        headers = build_headers()
        for key, value in BROWSER_HEADERS.items():
            assert headers[key] == value, f"Missing or wrong value for {key}"

    def test_does_not_contain_extra_keys(self):
        headers = build_headers()
        expected_keys = {"User-Agent"} | set(BROWSER_HEADERS.keys())
        assert set(headers.keys()) == expected_keys

    def test_randomness_across_calls(self):
        """Over many calls, at least 2 different User-Agents should appear."""
        agents = {build_headers()["User-Agent"] for _ in range(50)}
        assert len(agents) >= 2, "Expected User-Agent rotation across calls"


class TestCreateSession:
    def test_returns_session(self):
        session = create_session()
        assert isinstance(session, requests.Session)

    def test_session_has_user_agent(self):
        session = create_session()
        assert session.headers["User-Agent"] in USER_AGENTS

    def test_session_has_browser_headers(self):
        session = create_session()
        for key in BROWSER_HEADERS:
            assert key in session.headers, f"Session missing header: {key}"

    def test_no_proxy_by_default(self):
        session = create_session()
        assert session.proxies == {}

    def test_proxy_set_when_provided(self):
        proxy = "http://user:pass@proxy.example.com:8080"
        session = create_session(proxy_url=proxy)
        assert session.proxies["http"] == proxy
        assert session.proxies["https"] == proxy

    def test_proxy_none_explicitly(self):
        session = create_session(proxy_url=None)
        assert session.proxies == {}


class TestRotateHeaders:
    def test_changes_user_agent(self):
        session = create_session()
        original_ua = session.headers["User-Agent"]
        # Rotate many times — at least one should differ
        changed = False
        for _ in range(50):
            rotate_headers(session)
            if session.headers["User-Agent"] != original_ua:
                changed = True
                break
        assert changed, "Expected User-Agent to change after rotation"

    def test_new_user_agent_from_pool(self):
        session = create_session()
        rotate_headers(session)
        assert session.headers["User-Agent"] in USER_AGENTS

    def test_preserves_other_headers(self):
        session = create_session()
        rotate_headers(session)
        for key, value in BROWSER_HEADERS.items():
            assert session.headers[key] == value, f"Header {key} was modified by rotation"
