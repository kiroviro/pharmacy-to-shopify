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
    resp = session.get(f"{base_url}/blogs/{blog_id}/articles.json", params={"limit": 250})
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


def main() -> None:
    import argparse
    import os
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv()

    parser = argparse.ArgumentParser(description="Publish a blog post to Shopify.")
    parser.add_argument("html_file", help="Path to the HTML content file")
    parser.add_argument("--blog", default="Здравни съвети", help="Blog title (default: Здравни съвети)")
    parser.add_argument("--dry-run", action="store_true", help="Print metadata without publishing")
    args = parser.parse_args()

    # Load credentials
    shop = os.environ.get("SHOPIFY_SHOP_URL", "")
    token = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
    if not shop or not token:
        print("Error: SHOPIFY_SHOP_URL and SHOPIFY_ACCESS_TOKEN must be set in .env")
        sys.exit(1)
    base_url = f"https://{shop}/admin/api/2025-01"

    # Read HTML file
    html_path = Path(args.html_file)
    try:
        body_html = html_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"File not found: {args.html_file}")
        sys.exit(1)

    article_data = {
        "title": ARTICLE_TITLE,
        "author": ARTICLE_AUTHOR,
        "tags": ARTICLE_TAGS,
        "body_html": body_html,
        "published": True,
    }

    if args.dry_run:
        print("--- DRY RUN ---")
        print(f"Blog:    {args.blog}")
        print(f"Title:   {article_data['title']}")
        print(f"Author:  {article_data['author']}")
        print(f"Tags:    {article_data['tags']}")
        print(f"Body:    {body_html[:200]}...")
        return

    session = requests.Session()
    session.headers["X-Shopify-Access-Token"] = token

    blog_id, blog_handle = find_or_create_blog(session, base_url, args.blog)
    check_no_duplicate(session, base_url, blog_id, ARTICLE_TITLE)
    url = publish_article(session, base_url, blog_id, blog_handle, article_data)
    print(f"Published: {url}")


if __name__ == "__main__":
    main()
