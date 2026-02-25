#!/usr/bin/env python3
"""
Scrape article text from GShow (gshow.globo.com) BBB pages into Markdown.

Usage:
  python scripts/scrape_gshow.py <url> [--output FILE]
  python scripts/scrape_gshow.py "https://gshow.globo.com/realities/bbb/bbb-26/dentro-da-casa/noticia/..."

If --output is omitted, prints to stdout. Output path can be a directory
(e.g. docs/scraped/); then the filename is derived from the article URL slug.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, NavigableString

# GShow often checks User-Agent; use a polite identifier
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BBB26-scraper/1.0; +https://github.com/BBB26)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

# Stop capturing body when we hit these (sidebar / related)
BODY_STOP_MARKERS = (
    "Quem você quer eliminar",
    "Mais do BBB",
    "Veja mais",
)


def _text_with_links(el) -> str:
    """Recursively get text, turning <a> into [text](href) Markdown."""
    parts = []
    for child in el.children:
        if isinstance(child, NavigableString):
            parts.append(child.strip())
            continue
        if child.name == "a" and child.get("href"):
            href = child.get("href", "").strip()
            text = child.get_text(separator=" ", strip=True)
            if text and href:
                parts.append(f"[{text}]({href})")
            elif href:
                parts.append(href)
        else:
            parts.append(_text_with_links(child))
    return " ".join(p for p in parts if p).strip()


def _normalize_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n", "\n\n", text)).strip()
    # Normalize em dash spacing: "foo—bar" -> "foo — bar"
    text = re.sub(r"([^\s])—([^\s])", r"\1 — \2", text)
    return text


def scrape_gshow_article(url: str, session: requests.Session | None = None) -> dict:
    """
    Fetch a GShow article URL and return structured content.

    Returns:
        dict with keys: url, title, subtitle, byline, date_updated, body_md, body_raw
    """
    session = session or requests.Session()
    resp = session.get(url, headers=DEFAULT_HEADERS, timeout=20)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    out = {
        "url": url,
        "title": "",
        "subtitle": "",
        "byline": "",
        "date_updated": "",
        "body_md": "",
        "body_raw": "",
    }

    # Title (h1)
    h1 = soup.find("h1", class_=re.compile(r"content-head__title"))
    if h1:
        out["title"] = h1.get_text(strip=True)

    # Subtitle (h2)
    h2 = soup.find("h2", class_=re.compile(r"content-head__subtitle"))
    if h2:
        out["subtitle"] = h2.get_text(strip=True)

    # Byline and date
    byline_el = soup.find("p", class_=re.compile(r"content-publication-data__from"))
    if byline_el:
        out["byline"] = _normalize_whitespace(byline_el.get_text(strip=True))

    date_el = soup.find("time", itemprop="datePublished")
    if date_el:
        out["date_updated"] = date_el.get_text(strip=True)
    if not out["date_updated"]:
        updated_el = soup.find("p", class_=re.compile(r"content-publication-data__updated"))
        if updated_el:
            out["date_updated"] = _normalize_whitespace(updated_el.get_text(strip=True))

    # Article body: div.mc-column.content-text with p.content-text__container
    body_parts = []
    for div in soup.find_all("div", class_=re.compile(r"content-text")):
        # Only take divs that look like article body (have content-text__container or paragraph)
        container = div.find("p", class_=re.compile(r"content-text__container"))
        if not container:
            # Some blocks use content-intertitle (subheadings)
            inter = div.find(class_=re.compile(r"content-intertitle"))
            if inter:
                line = _normalize_whitespace(inter.get_text(strip=True))
                if line and not any(m in line for m in BODY_STOP_MARKERS):
                    body_parts.append(f"\n## {line}\n")
            continue
        raw = container.get_text(separator=" ", strip=True)
        if any(m in raw for m in BODY_STOP_MARKERS):
            break
        md = _text_with_links(container)
        if not md:
            continue
        # List items: parent might be content-unordered-list
        ul = container.find_parent("ul", class_=re.compile(r"content-unordered-list"))
        if ul and container.name == "li":
            body_parts.append("- " + md + "\n")
        else:
            body_parts.append(md + "\n\n")
        out["body_raw"] += raw + "\n"

    out["body_md"] = _normalize_whitespace("".join(body_parts))
    return out


def article_to_markdown(data: dict, include_url: bool = True) -> str:
    """Turn scraped article dict into a single Markdown string. Date at top."""
    lines = []
    if data["date_updated"]:
        lines.append(f"**Data:** {data['date_updated']}\n")
    if data["title"]:
        lines.append(f"# {data['title']}\n")
    if data["subtitle"]:
        lines.append(f"## {data['subtitle']}\n")
    if data["byline"]:
        lines.append(f"**{data['byline']}**\n")
    if include_url and data["url"]:
        lines.append(f"**Fonte:** [{data['url']}]({data['url']})\n")
    lines.append("---\n")
    if data["body_md"]:
        lines.append(data["body_md"])
    return _normalize_whitespace("\n".join(lines)) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scrape GShow BBB article to Markdown.",
        epilog="Example: python scripts/scrape_gshow.py 'https://gshow.globo.com/...' -o docs/scraped/",
    )
    parser.add_argument("url", help="Full GShow article URL")
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Output file (or directory; then filename from URL slug). Default: stdout",
    )
    parser.add_argument(
        "--no-url",
        action="store_true",
        help="Do not include source URL in the Markdown body",
    )
    args = parser.parse_args()

    url = args.url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    if "gshow.globo.com" not in url:
        print("Warning: URL is not gshow.globo.com; selectors may not match.", file=sys.stderr)

    try:
        data = scrape_gshow_article(url)
    except requests.RequestException as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return 1

    md = article_to_markdown(data, include_url=not args.no_url)

    out_path = None
    if args.output:
        out_path = Path(args.output)
        if out_path.is_dir():
            # Derive filename from URL path slug (last path segment without .ghtml)
            slug = urlparse(url).path.rstrip("/").split("/")[-1]
            if slug.endswith(".ghtml"):
                slug = slug[:-6]
            out_path = out_path / f"{slug}.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(md, encoding="utf-8")
        print(f"Wrote {out_path}", file=sys.stderr)
    else:
        print(md, end="")

    return 0


if __name__ == "__main__":
    sys.exit(main())
