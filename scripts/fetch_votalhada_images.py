#!/usr/bin/env python3
"""
Download Votalhada poll images from a pesquisa post page.

Votalhada updates consolidados/platform screenshots at roughly:
  Monday: 1:00, 8:00, 12:00, 15:00, 18:00, 21:00 BRT
  Tuesday: 8:00, 12:00, 15:00, 18:00, 21:00 BRT

Usage:
  python scripts/fetch_votalhada_images.py --paredao 6
  python scripts/fetch_votalhada_images.py --url "https://votalhada.blogspot.com/2026/02/pesquisa6.html"
  python scripts/fetch_votalhada_images.py --paredao 6 --timestamp   # keep timestamped copies

By default, images overwrite the last capture (consolidados.png, consolidados_2.png, ...).
Use --timestamp to save with a datetime suffix so you keep a history of captures.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

# Project root (script lives in scripts/)
REPO_ROOT = Path(__file__).resolve().parent.parent
VOTALHADA_DIR = REPO_ROOT / "data" / "votalhada"
PAREDOES_JSON = REPO_ROOT / "data" / "paredoes.json"


def _load_paredoes():
    import json
    with open(PAREDOES_JSON, encoding="utf-8") as f:
        return json.load(f)


def get_post_url_for_paredao(numero: int) -> tuple[str, str]:
    """Return (url, folder_YYYY_MM_DD) for the Votalhada pesquisa post."""
    data = _load_paredoes()
    for p in data["paredoes"]:
        if p["numero"] == numero:
            data_formacao = p.get("data_formacao") or p.get("data")
            if not data_formacao:
                raise ValueError(f"Paredão {numero}: no data_formacao/data in paredoes.json")
            # Votalhada URL pattern: /YYYY/MM/pesquisaN.html
            year, month, _ = data_formacao.split("-")
            url = f"https://votalhada.blogspot.com/{year}/{month}/pesquisa{numero}.html"
            folder = data_formacao.replace("-", "_")
            return url, folder
    raise ValueError(f"Paredão {numero} not found in paredoes.json")


def extract_image_urls(html: str) -> list[str]:
    """Extract img src URLs from the main post body (Blogger post content)."""
    # Restrict to main post: content between id="Blog1" and typical end of post
    blog1 = re.search(r'<div[^>]*id="Blog1"[^>]*>(.*?)</div>\s*</div>\s*</div>', html, re.DOTALL | re.IGNORECASE)
    block = blog1.group(1) if blog1 else html

    # All <img ... src="..."> in this block (Blogger in-post images usually use blogger.googleusercontent.com)
    urls = re.findall(r'<img[^>]+src="(https?://[^"]+)"', block, re.IGNORECASE)
    # Filter to in-post images only (Blogger CDN), keep order
    in_post = [u for u in urls if "blogger.googleusercontent.com" in u or "blogspot.com" in u]
    return in_post if in_post else urls


def download_image(url: str, path: Path, session: requests.Session) -> bool:
    """Download a single image to path. Returns True on success."""
    try:
        r = session.get(url, timeout=30)
        r.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r.content)
        return True
    except Exception as e:
        print(f"  Failed {url[:60]}...: {e}", file=sys.stderr)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download Votalhada poll images from a pesquisa post.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--paredao", type=int, metavar="N", help="Paredão number (e.g. 6)")
    g.add_argument("--url", type=str, metavar="URL", help="Full Votalhada post URL")
    parser.add_argument(
        "--timestamp",
        action="store_true",
        help="Add datetime to filenames (e.g. consolidados_2026-02-24_21-05.png) to keep history",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Override output directory (default: data/votalhada/YYYY_MM_DD)",
    )
    args = parser.parse_args()

    if args.paredao:
        post_url, folder_name = get_post_url_for_paredao(args.paredao)
    else:
        post_url = args.url.rstrip("/")
        # Derive folder: prefer paredão number from URL (pesquisa6.html -> 6) for consistent path
        m = re.search(r"pesquisa(\d+)\.html", post_url, re.IGNORECASE)
        if m:
            try:
                _, folder_name = get_post_url_for_paredao(int(m.group(1)))
            except ValueError:
                folder_name = datetime.now(timezone.utc).strftime("%Y_%m_%d")
        else:
            folder_name = datetime.now(timezone.utc).strftime("%Y_%m_%d")

    if args.out_dir is not None:
        out_dir = Path(args.out_dir)
    else:
        out_dir = VOTALHADA_DIR / folder_name

    print(f"Fetching: {post_url}")
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; BBB26 fetch_votalhada_images)",
    })
    try:
        r = session.get(post_url, timeout=30)
        r.raise_for_status()
        html = r.text
    except Exception as e:
        print(f"Error fetching page: {e}", file=sys.stderr)
        sys.exit(1)

    urls = extract_image_urls(html)
    if not urls:
        print("No images found in post body.", file=sys.stderr)
        sys.exit(1)
    print(f"Found {len(urls)} image(s).")

    suffix = ""
    if args.timestamp:
        suffix = "_" + datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")

    saved = 0
    for i, url in enumerate(urls):
        if i == 0:
            base = "consolidados"
        else:
            base = f"consolidados_{i + 1}"
        name = f"{base}{suffix}.png"
        path = out_dir / name
        if download_image(url, path, session):
            print(f"  Saved {path.relative_to(REPO_ROOT)}")
            saved += 1

    print(f"Done. {saved}/{len(urls)} images saved to {out_dir.relative_to(REPO_ROOT)}.")


if __name__ == "__main__":
    main()
