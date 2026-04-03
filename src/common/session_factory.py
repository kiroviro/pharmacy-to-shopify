"""
Shared HTTP session factory with anti-ban headers.

Centralizes User-Agent rotation and browser header setup
so all HTTP-using modules get consistent anti-fingerprint behavior.
"""

from __future__ import annotations

import random

import requests

from .constants import BROWSER_HEADERS, USER_AGENTS


def build_headers() -> dict[str, str]:
    """Build a randomized but realistic browser header set.

    Picks a random User-Agent from the rotation pool and
    merges the standard browser headers (Sec-Fetch-*, Accept, etc.).
    """
    return {
        "User-Agent": random.choice(USER_AGENTS),
        **BROWSER_HEADERS,
    }


def create_session(proxy_url: str | None = None) -> requests.Session:
    """Create a requests.Session with anti-ban headers and optional proxy.

    The session's headers are set once; call ``rotate_headers(session)``
    before each request if per-request rotation is needed.

    Args:
        proxy_url: Optional proxy URL (http://user:pass@host:port).

    Returns:
        Configured requests.Session.
    """
    session = requests.Session()
    session.headers.update(build_headers())
    if proxy_url:
        session.proxies = {"http": proxy_url, "https": proxy_url}
    return session


def rotate_headers(session: requests.Session) -> None:
    """Rotate User-Agent on an existing session (call before each request)."""
    session.headers["User-Agent"] = random.choice(USER_AGENTS)
