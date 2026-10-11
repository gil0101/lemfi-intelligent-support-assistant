"""
Scrape all LemFi Support Center articles via the Zendesk Help Center API.

This script fetches categories, sections, and articles from
https://support.lemfi.com/hc/en-us and saves them as structured
Markdown files organized by category → section → article.

Output structure:
    data/documents/raw/
    ├── index.json                          # Full metadata index
    ├── Account_and_Profile/
    │   ├── Get_Started/
    │   │   ├── article-title-1.md
    │   │   └── article-title-2.md
    │   └── Manage_Your_Account/
    │       └── ...
    ├── Login_and_Security/
    │   └── ...
    └── ...

Each .md file contains YAML-style front matter + clean text content.

Usage:
    python scripts/scrape_lemfi_support.py
    python scripts/scrape_lemfi_support.py --output-dir data/documents/raw
    python scripts/scrape_lemfi_support.py --format json   # JSON instead of markdown
"""

import argparse
import json
import os
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE_URL = "https://support.lemfi.com/api/v2/help_center/en-us"
DEFAULT_OUTPUT_DIR = "data/documents/raw"
REQUEST_DELAY = 0.3
PER_PAGE = 100
USER_AGENT = "LemFi-RAG-Scraper/1.0 (Educational Project)"


class HTMLToTextParser(HTMLParser):
    """Convert HTML to clean plain text, preserving structure."""

    def __init__(self):
        super().__init__()
        self._text_parts = []
        self._current_tag = None
        self._list_item_count = 0
        self._in_list = False
        self._skip_tags = {"script", "style", "head"}
        self._skip = False

    def handle_starttag(self, tag, attrs):
        self._current_tag = tag
        if tag in self._skip_tags:
            self._skip = True
        elif tag == "br":
            self._text_parts.append("\n")
        elif tag in ("p", "div", "h1", "h2", "h3", "h4", "h5", "h6"):
            self._text_parts.append("\n\n")
        elif tag == "ul" or tag == "ol":
            self._in_list = True
            self._list_item_count = 0
            self._text_parts.append("\n")
        elif tag == "li":
            self._list_item_count += 1
            self._text_parts.append(f"\n  • ")
        elif tag == "strong" or tag == "b":
            self._text_parts.append("**")
        elif tag == "em" or tag == "i":
            self._text_parts.append("*")
        elif tag == "a":
            href = dict(attrs).get("href", "")
            if href:
                self._text_parts.append("[")

    def handle_endtag(self, tag):
        if tag in self._skip_tags:
            self._skip = False
        elif tag in ("ul", "ol"):
            self._in_list = False
            self._text_parts.append("\n")
        elif tag == "strong" or tag == "b":
            self._text_parts.append("**")
        elif tag == "em" or tag == "i":
            self._text_parts.append("*")
        elif tag in ("p", "div"):
            self._text_parts.append("\n")
        self._current_tag = None

    def handle_data(self, data):
        if not self._skip:
            self._text_parts.append(data)

    def get_text(self):
        text = "".join(self._text_parts)
        # Normalize whitespace: collapse multiple blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Remove leading/trailing whitespace per line
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)
        return text.strip()


def html_to_text(html_content: str) -> str:
    """Convert HTML string to clean plain text."""
    if not html_content:
        return ""
    parser = HTMLToTextParser()
    parser.feed(html_content)
    return parser.get_text()


def fetch_json(url: str, max_retries: int = 3) -> dict:
    """Fetch JSON from a URL with retries and rate limiting."""
    for attempt in range(max_retries):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
            time.sleep(REQUEST_DELAY)
            return data
        except HTTPError as e:
            if e.code == 429:  # Rate limited
                retry_after = int(e.headers.get("Retry-After", 10))
                print(f"  ⏳ Rate limited. Waiting {retry_after}s...")
                time.sleep(retry_after)
            elif attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"  ⚠️  HTTP {e.code} - Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
        except URLError as e:
            if attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"  ⚠️  Connection error: {e.reason} - Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
    return {}


def fetch_all_paginated(endpoint: str) -> list:
    """Fetch all pages from a paginated Zendesk API endpoint."""
    url = f"{BASE_URL}/{endpoint}?per_page={PER_PAGE}"
    all_items = []
    page = 1

    # Determine the key name from the endpoint (e.g., "categories.json" → "categories")
    key = endpoint.replace(".json", "")

    while url:
        print(f"  📄 Fetching {key} page {page}...")
        data = fetch_json(url)

        items = data.get(key, [])
        all_items.extend(items)

        url = data.get("next_page")
        page += 1

    return all_items


def fetch_categories() -> list[dict]:
    """Fetch all help center categories."""
    categories = fetch_all_paginated("categories.json")
    return categories


def fetch_sections() -> list[dict]:
    """Fetch all help center sections."""
    sections = fetch_all_paginated("sections.json")
    return sections


def fetch_articles() -> list[dict]:
    """Fetch all help center articles."""
    articles = fetch_all_paginated("articles.json")
    return articles


def sanitize_filename(name: str, max_length: int = 80) -> str:
    """Convert a string into a safe filename."""
    # Remove/replace problematic characters
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = re.sub(r"['\u2019\u2018]", "", name)
    # Replace spaces and special chars with underscores
    name = re.sub(r"[\s\-–—]+", "_", name)
    # Remove consecutive underscores
    name = re.sub(r"_+", "_", name)
    # Strip leading/trailing underscores and dots
    name = name.strip("_.")
    # Truncate
    if len(name) > max_length:
        name = name[:max_length].rstrip("_")
    return name or "untitled"


def build_article_markdown(article: dict, category_name: str, section_name: str) -> str:
    """Build a markdown document from an article with front matter metadata."""
    title = article.get("title", "Untitled")
    body_html = article.get("body", "")
    body_text = html_to_text(body_html)
    url = article.get("html_url", "")
    created = article.get("created_at", "")
    updated = article.get("updated_at", "")
    article_id = article.get("id", "")
    labels = ", ".join(article.get("label_names", []))

    md = f"""---
title: "{title}"
article_id: {article_id}
url: "{url}"
category: "{category_name}"
section: "{section_name}"
created_at: "{created}"
updated_at: "{updated}"
labels: "{labels}"
source: "LemFi Support Center"
---

# {title}

{body_text}
"""
    return md


def build_article_json(article: dict, category_name: str, section_name: str) -> dict:
    """Build a structured JSON object from an article."""
    return {
        "id": article.get("id"),
        "title": article.get("title", "Untitled"),
        "url": article.get("html_url", ""),
        "category": category_name,
        "section": section_name,
        "content_text": html_to_text(article.get("body", "")),
        "content_html": article.get("body", ""),
        "labels": article.get("label_names", []),
        "created_at": article.get("created_at", ""),
        "updated_at": article.get("updated_at", ""),
        "source": "LemFi Support Center",
    }



def run_scraper(output_dir: str, output_format: str = "markdown"):
    """Run the full scraping pipeline."""
    print("=" * 60)
    print("🚀 LemFi Support Center Scraper")
    print("=" * 60)

    # Fetch all data from Zendesk API
    categories = fetch_categories()
    sections = fetch_sections()
    articles = fetch_articles()

    # Build lookup maps
    category_map = {c["id"]: c for c in categories}
    section_map = {s["id"]: s for s in sections}

    # Map section_id → category_id
    section_to_category = {s["id"]: s.get("category_id") for s in sections}

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    saved_count = 0
    skipped_count = 0
    index_data = []

    for article in articles:
        # Skip drafts
        if article.get("draft", False):
            skipped_count += 1
            continue

        # Skip articles with no content
        if not article.get("body"):
            skipped_count += 1
            continue

        # Resolve category and section names
        section_id = article.get("section_id")
        section = section_map.get(section_id, {})
        section_name = section.get("name", "General").strip()

        category_id = section_to_category.get(section_id)
        category = category_map.get(category_id, {})
        category_name = category.get("name", "Other").strip()

        # Build file path
        cat_dir = sanitize_filename(category_name)
        sec_dir = sanitize_filename(section_name)
        article_filename = sanitize_filename(article.get("title", "untitled"))

        if output_format == "json":
            # Save all as a single JSON file
            article_data = build_article_json(article, category_name, section_name)
            index_data.append(article_data)
        else:
            # Save individual markdown files
            file_dir = output_path / cat_dir / sec_dir
            file_dir.mkdir(parents=True, exist_ok=True)

            file_path = file_dir / f"{article_filename}.md"

            # Handle duplicate filenames
            counter = 1
            while file_path.exists():
                file_path = file_dir / f"{article_filename}_{counter}.md"
                counter += 1

            md_content = build_article_markdown(article, category_name, section_name)
            file_path.write_text(md_content, encoding="utf-8")

            index_data.append({
                "id": article.get("id"),
                "title": article.get("title"),
                "url": article.get("html_url"),
                "category": category_name,
                "section": section_name,
                "file_path": str(file_path.relative_to(output_path)),
                "updated_at": article.get("updated_at"),
            })

        saved_count += 1
        sys.stdout.write(f"\r   Saved: {saved_count} articles...")
        sys.stdout.flush()

    print()

    # 5. Save index / JSON output
    if output_format == "json":
        json_path = output_path / "articles.json"
        json_path.write_text(
            json.dumps(index_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"\n📦 JSON saved to: {json_path}")
    else:
        index_path = output_path / "index.json"
        index_path.write_text(
            json.dumps({
                "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "source": "https://support.lemfi.com/hc/en-us",
                "total_categories": len(categories),
                "total_sections": len(sections),
                "total_articles": saved_count,
                "articles": index_data,
            }, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    return saved_count


def main():
    parser = argparse.ArgumentParser(
        description="Scrape LemFi Support Center articles for RAG.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/scrape_lemfi_support.py
  python scripts/scrape_lemfi_support.py --output-dir data/documents/raw
  python scripts/scrape_lemfi_support.py --format json
        """
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for scraped documents (default: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format: 'markdown' (individual .md files) or 'json' (single file)"
    )

    args = parser.parse_args()

    try:
        count = run_scraper(args.output_dir, args.format)
        if count == 0:
            sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        sys.exit(1)


if __name__ == "__main__":
    main()
