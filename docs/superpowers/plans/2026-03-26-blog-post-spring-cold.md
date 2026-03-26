# Blog Post Publisher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a reusable script that publishes a Bulgarian-language blog post to viapharma.us via the Shopify API, alongside the first blog post content file.

**Architecture:** Two deliverables — `scripts/create_blog_post.py` (standalone Shopify publisher using direct `requests` calls) and `content/blog/spring-cold-2026.html` (the HTML body). The script finds or creates a blog, checks for duplicate articles client-side, then publishes. Core logic lives in three pure functions so they can be unit-tested without hitting a real API.

**Tech Stack:** Python 3.12, `requests`, `python-dotenv`, `pytest`, `unittest.mock`

---

## File Map

| Action | Path | Purpose |
|--------|------|---------|
| Create | `content/blog/spring-cold-2026.html` | Bulgarian blog post body (HTML, UTF-8) |
| Create | `scripts/create_blog_post.py` | Shopify blog post publisher script |
| Create | `tests/scripts/test_create_blog_post.py` | Unit tests for publisher functions |

---

## Prerequisites (manual step — do before any code)

The current `SHOPIFY_ACCESS_TOKEN` in `.env` lacks `read_content` / `write_content` scopes.

- [ ] In Shopify Admin → Apps → Develop apps → select your app → Configuration → Admin API access scopes, add **`read_content`** and **`write_content`**
- [ ] Click **Save** then **Rotate token** — copy the new token into `.env` as `SHOPIFY_ACCESS_TOKEN`

You cannot test the live publish step until this is done.

---

## Task 1: Blog post HTML content

**Files:**
- Create: `content/blog/spring-cold-2026.html`

- [ ] **Step 1: Create the content directory**

```bash
mkdir -p content/blog
```

- [ ] **Step 2: Write the HTML file**

Save the following to `content/blog/spring-cold-2026.html` (UTF-8):

```html
<p>Като родители, всички сме минавали през онези неспокойни нощи, когато детето ни е болно — треска, запушен нос, суха кашлица. Особено напролет, когато времето се сменя бързо, децата са по-уязвими към вируси и настинки. Тази статия споделя какво препоръча нашият лекар при пролетна настинка — и защо всеки от тези продукти има своята роля.</p>

<h2>Кога да потърсите лекар?</h2>

<p>При пролетна настинка или грип типичните симптоми при деца включват хрема, запушен нос, суха кашлица, лека температура и отпадналост. Ако температурата надхвърли 38.5°C, не спада след 3 дни, или детето отказва да пие течности — потърсете лекар. Информацията по-долу не заменя лекарска консултация.</p>

<h2><a href="https://viapharma.us/products/ibuprom-sinus-tabletki-200mg-30mg-h-12">Ибупром Синус</a> — срещу болка, температура и запушен нос</h2>

<p>Ибупром Синус съдържа ибупрофен (болкоуспокояващ и антипиретик) и псевдоефедрин (деконгестант). Действа едновременно срещу главоболието, температурата и запушения нос — три от най-честите симптоми при пролетния грип. Подходящ е за кратковременна употреба при остри симптоми. Следвайте препоръчаната от лекаря дозировка.</p>

<h2><a href="https://viapharma.us/products/nazik-nazalen-sprej-za-deca-10ml">Назик назален спрей за деца</a> — бързо облекчение на конгестията</h2>

<p>Когато носът е запушен, децата не могат да спят и ядат добре. Назик за деца съдържа оксиметазолин в детска доза и действа бързо — в рамките на минути. Препоръчва се 3–4 пъти на ден. Важно: не се прилага повече от 5–7 последователни дни, за да се избегне ефект на рикошет.</p>

<h2><a href="https://viapharma.us/products/noktitus-sirop-za-suha-kaslica-200-ml">Ноктитус сироп</a> — при суха, дразнеща кашлица</h2>

<p>Сухата кашлица е особено изтощителна — не дава на детето да спи и дразни гърлото. Ноктитус сироп действа успокояващо върху рефлекса на кашлица. Дозировката е по 1 супена лъжица на 5–6 часа според препоръката на лекаря. Приемайте само при суха (непродуктивна) кашлица.</p>

<h2><a href="https://viapharma.us/products/regulatpro-bio-solucio-350ml">Регулатпро Био</a> — имунна подкрепа и чревен баланс</h2>

<p>При вирусно заболяване (особено ако детето е приемало антибиотици), пробиотикът помага за възстановяване на чревната микрофлора и поддържа имунната система. Регулатпро Био е ферментирален продукт с висока бионаличност. Препоръчва се 3 пъти по 1 супена лъжица дневно по времето на заболяването.</p>

<hr>

<p><em>Тази статия е с информационна цел. Консултирайте се с Вашия лекар или фармацевт преди употреба на всяко лекарство. Дозировките, посочени тук, са примерни и могат да се различават в зависимост от възрастта и теглото на детето.</em></p>

<p>Всички препоръчани продукти ще намерите в нашата онлайн аптека <a href="https://viapharma.us">viapharma.us</a> — с бърза доставка до вкъщи.</p>
```

- [ ] **Step 3: Open the file in a browser to proof-read**

```bash
open content/blog/spring-cold-2026.html
```

Verify: all four product links are clickable, text reads naturally, no Cyrillic encoding issues.

- [ ] **Step 4: Commit**

```bash
git add content/blog/spring-cold-2026.html
git commit -m "content: add spring cold blog post (Bulgarian)"
```

---

## Task 2: Publisher script — core functions + tests

**Files:**
- Create: `tests/scripts/__init__.py`
- Create: `tests/scripts/test_create_blog_post.py`
- Create: `scripts/create_blog_post.py` (functions only, no `main()` yet)

The script exposes three pure functions that the tests target:
- `find_or_create_blog(session, base_url, blog_title) -> tuple[int, str]` — returns `(blog_id, blog_handle)`
- `check_no_duplicate(session, base_url, blog_id, article_title) -> None` — raises `SystemExit` if duplicate found
- `publish_article(session, base_url, blog_id, blog_handle, article_data) -> str` — returns article URL using blog handle (not numeric ID)

Note: `tests/scripts/` already exists with `__init__.py` — no setup needed.

- [ ] **Step 1: Write the failing tests**

Create `tests/scripts/test_create_blog_post.py`:

```python
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
```

- [ ] **Step 3: Run the tests — verify they all fail**

```bash
pytest tests/scripts/test_create_blog_post.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` — `create_blog_post` doesn't exist yet.

- [ ] **Step 4: Write the script functions (no `main()` yet)**

Create `scripts/create_blog_post.py`:

```python
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
```

- [ ] **Step 5: Run the tests — verify they all pass**

```bash
pytest tests/scripts/test_create_blog_post.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/create_blog_post.py tests/scripts/test_create_blog_post.py
git commit -m "feat: add blog post publisher functions with tests"
```

---

## Task 3: Publisher script — `main()` + CLI

**Files:**
- Modify: `scripts/create_blog_post.py` (add `main()` and `if __name__ == "__main__"`)

No new tests needed for `main()` — it's thin argparse glue that delegates to the already-tested functions.

- [ ] **Step 1: Add `main()` to the script**

Append to `scripts/create_blog_post.py`:

```python
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
```

- [ ] **Step 2: Test dry-run locally (no token scope change needed)**

```bash
python scripts/create_blog_post.py content/blog/spring-cold-2026.html --dry-run
```

Expected output:
```
--- DRY RUN ---
Blog:    Здравни съвети
Title:   Пролетна настинка при деца: какво препоръча нашият лекар
Author:  Виафарма
Tags:    настинка, грип, деца, пролет, ибупром, назик, ноктитус, регулат
Body:    <p>Като родители...
```

- [ ] **Step 3: Test missing file error**

```bash
python scripts/create_blog_post.py nonexistent.html --dry-run
```

Expected: `File not found: nonexistent.html` and exit code 1.

- [ ] **Step 4: Run full test suite to confirm nothing broken**

```bash
pytest tests/scripts/test_create_blog_post.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/create_blog_post.py
git commit -m "feat: add CLI main() to blog post publisher"
```

---

## Task 4: Live publish

**Prerequisites:** Token scope update must be complete (see Prerequisites section above).

- [ ] **Step 1: Test with --dry-run against live credentials**

```bash
python scripts/create_blog_post.py content/blog/spring-cold-2026.html --dry-run
```

This doesn't hit the API — just verifies the file reads correctly.

- [ ] **Step 2: Publish**

```bash
python scripts/create_blog_post.py content/blog/spring-cold-2026.html
```

Expected:
```
Created blog: 'Здравни съвети'    # (first time only)
Published: https://viapharma.us/blogs/zdravni-saveti/prole...
```

- [ ] **Step 3: Open the published URL and verify**

Check: all four product links work, Cyrillic text renders correctly, disclaimer is present.

- [ ] **Step 4: Optional — add SEO meta and featured image in Shopify Admin**

Shopify Admin → Online Store → Blog posts → open the article → SEO section.

- [ ] **Step 5: Final commit**

```bash
git add .
git commit -m "feat: publish spring cold blog post to viapharma.us"
```
