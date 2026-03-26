"""Shopify blog post publisher.

Usage:
    python scripts/create_blog_post.py content/blog/spring-cold-2026.html
    python scripts/create_blog_post.py content/blog/spring-cold-2026.html --blog "Промоции"
    python scripts/create_blog_post.py content/blog/spring-cold-2026.html --dry-run
"""
from __future__ import annotations

import sys

import requests

ARTICLE_TITLE = "Пролетна настинка при деца: какво препоръча нашият лекар"
ARTICLE_AUTHOR = "Виафарма"
ARTICLE_TAGS = "настинка, грип, деца, пролет, ибупром, назик, ноктитус, регулат"

SCOPE_ERROR_MSG = (
    "Missing write_content scope. Add it in Shopify Admin → Apps → [app] → "
    "Configuration → Admin API access scopes, then regenerate the token."
)


def find_or_create_blog(session: requests.Session, base_url: str, blog_title: str) -> tuple[int, str]:
    """Return (blog_id, blog_handle) for the named blog, creating it if it doesn't exist."""
    resp = session.get(f"{base_url}/blogs.json")
    if resp.status_code == 403:
        print(SCOPE_ERROR_MSG)
        sys.exit(1)
    resp.raise_for_status()

    blogs = resp.json().get("blogs", [])
    for blog in blogs:
        if blog["title"].lower() == blog_title.lower():
            return blog["id"], blog["handle"]

    # Blog not found — create it
    resp = session.post(f"{base_url}/blogs.json", json={"blog": {"title": blog_title}})
    if resp.status_code == 403:
        print(SCOPE_ERROR_MSG)
        sys.exit(1)
    resp.raise_for_status()
    print(f"Created blog: {blog_title!r}")
    blog = resp.json()["blog"]
    return blog["id"], blog["handle"]


def check_no_duplicate(
    session: requests.Session, base_url: str, blog_id: int, article_title: str
) -> None:
    """Exit with error if an article with the same title already exists."""
    resp = session.get(f"{base_url}/blogs/{blog_id}/articles.json")
    resp.raise_for_status()

    articles = resp.json().get("articles", [])
    for article in articles:
        if article["title"].lower() == article_title.lower():
            print(f"Error: article {article_title!r} already exists in this blog.")
            sys.exit(1)


def publish_article(
    session: requests.Session, base_url: str, blog_id: int, blog_handle: str, article_data: dict
) -> str:
    """POST the article to Shopify and return its URL (uses blog handle, not numeric ID)."""
    resp = session.post(
        f"{base_url}/blogs/{blog_id}/articles.json",
        json={"article": article_data},
    )
    if resp.status_code == 403:
        print(SCOPE_ERROR_MSG)
        sys.exit(1)
    data = resp.json()
    if "errors" in data or resp.status_code >= 400:
        print(f"Error publishing article: {data.get('errors', resp.text)}")
        sys.exit(1)
    article = data["article"]
    return f"https://viapharma.us/blogs/{blog_handle}/{article['handle']}"
