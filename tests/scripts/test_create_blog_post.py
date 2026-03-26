"""Tests for scripts/create_blog_post.py"""
import sys
from unittest.mock import MagicMock, patch

import pytest

# Import the functions we're about to write
from scripts.create_blog_post import (
    check_no_duplicate,
    find_or_create_blog,
    publish_article,
)

BASE_URL = "https://test-store.myshopify.com/admin/api/2025-01"


def _mock_session(get_json=None, post_json=None, status_code=200):
    """Build a mock requests.Session with controllable GET/POST responses."""
    session = MagicMock()
    get_resp = MagicMock()
    get_resp.status_code = status_code
    get_resp.json.return_value = get_json or {}
    session.get.return_value = get_resp

    post_resp = MagicMock()
    post_resp.status_code = 201
    post_resp.json.return_value = post_json or {}
    session.post.return_value = post_resp

    return session


# ---------------------------------------------------------------------------
# find_or_create_blog
# ---------------------------------------------------------------------------

class TestFindOrCreateBlog:
    def test_returns_existing_blog_id_and_handle(self):
        session = _mock_session(get_json={"blogs": [{"id": 42, "handle": "zdravni-saveti", "title": "Здравни съвети"}]})
        blog_id, blog_handle = find_or_create_blog(session, BASE_URL, "Здравни съвети")
        assert blog_id == 42
        assert blog_handle == "zdravni-saveti"
        session.post.assert_not_called()

    def test_creates_blog_when_missing(self):
        session = _mock_session(
            get_json={"blogs": []},
            post_json={"blog": {"id": 99, "handle": "zdravni-saveti", "title": "Здравни съвети"}},
        )
        blog_id, blog_handle = find_or_create_blog(session, BASE_URL, "Здравни съвети")
        assert blog_id == 99
        assert blog_handle == "zdravni-saveti"
        session.post.assert_called_once()

    def test_title_match_is_case_insensitive(self):
        session = _mock_session(get_json={"blogs": [{"id": 7, "handle": "zdravni-saveti", "title": "здравни съвети"}]})
        blog_id, blog_handle = find_or_create_blog(session, BASE_URL, "Здравни съвети")
        assert blog_id == 7

    def test_exits_on_403(self):
        session = _mock_session(status_code=403)
        with pytest.raises(SystemExit):
            find_or_create_blog(session, BASE_URL, "Здравни съвети")


# ---------------------------------------------------------------------------
# check_no_duplicate
# ---------------------------------------------------------------------------

class TestCheckNoDuplicate:
    def test_passes_when_no_articles(self):
        session = _mock_session(get_json={"articles": []})
        check_no_duplicate(session, BASE_URL, 42, "Пролетна настинка при деца")
        # should not raise

    def test_exits_when_duplicate_title_exists(self):
        session = _mock_session(
            get_json={"articles": [{"title": "Пролетна настинка при деца"}]}
        )
        with pytest.raises(SystemExit):
            check_no_duplicate(session, BASE_URL, 42, "Пролетна настинка при деца")

    def test_duplicate_check_is_case_insensitive(self):
        session = _mock_session(
            get_json={"articles": [{"title": "пролетна настинка при деца"}]}
        )
        with pytest.raises(SystemExit):
            check_no_duplicate(session, BASE_URL, 42, "Пролетна настинка при деца")

    def test_passes_when_different_title_exists(self):
        session = _mock_session(
            get_json={"articles": [{"title": "Друга статия"}]}
        )
        check_no_duplicate(session, BASE_URL, 42, "Пролетна настинка при деца")
        # should not raise


# ---------------------------------------------------------------------------
# publish_article
# ---------------------------------------------------------------------------

class TestPublishArticle:
    def test_returns_article_url_with_blog_handle(self):
        session = _mock_session(
            post_json={"article": {"id": 123, "handle": "prolетna-nastinka"}}
        )
        url = publish_article(
            session,
            BASE_URL,
            blog_id=42,
            blog_handle="zdravni-saveti",
            article_data={"title": "Test", "body_html": "<p>body</p>", "published": True},
        )
        assert "zdravni-saveti" in url
        assert "prolетna-nastinka" in url

    def test_exits_on_api_error(self):
        resp = MagicMock()
        resp.status_code = 422
        resp.json.return_value = {"errors": "Title can't be blank"}
        session = MagicMock()
        session.post.return_value = resp
        with pytest.raises(SystemExit):
            publish_article(session, BASE_URL, 42, "zdravni-saveti", {"title": "", "body_html": ""})

    def test_exits_on_403(self):
        session = _mock_session(status_code=403)
        session.post.return_value.status_code = 403
        session.post.return_value.json.return_value = {"errors": "[API] scope error"}
        with pytest.raises(SystemExit):
            publish_article(session, BASE_URL, 42, "zdravni-saveti", {"title": "T", "body_html": "<p/>"})
