"""Tests for PharmacyURLDiscoverer anti-ban headers."""
from src.discovery.pharmacy_discoverer import PharmacyURLDiscoverer
from src.common.constants import USER_AGENTS, BROWSER_HEADERS


def test_discoverer_session_has_realistic_headers():
    discoverer = PharmacyURLDiscoverer()
    session_headers = dict(discoverer.session.headers)
    # User-Agent must be one of our rotating list
    assert session_headers.get("User-Agent") in USER_AGENTS
    # All BROWSER_HEADERS keys must be present
    for key in BROWSER_HEADERS:
        assert key in session_headers, f"Missing session header: {key}"
    discoverer.close()


def test_discoverer_uses_different_agents_across_instances():
    agents = set()
    for _ in range(20):
        d = PharmacyURLDiscoverer()
        agents.add(dict(d.session.headers).get("User-Agent"))
        d.close()
    # With 10 UAs and 20 instances, overwhelmingly likely to see >1 unique UA
    assert len(agents) > 1
