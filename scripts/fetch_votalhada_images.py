#!/usr/bin/env python3
"""
Download Votalhada poll images from a pesquisa post page.

Votalhada updates consolidados/platform screenshots at roughly:
  Monday: 1:00, 8:00, 12:00, 15:00, 18:00, 21:00 BRT
  Tuesday: 8:00, 12:00, 15:00, 18:00, 21:00 BRT

Usage:
  python scripts/fetch_votalhada_images.py --paredao 6
  python scripts/fetch_votalhada_images.py --url "https://votalhada.blogspot.com/2026/02/pesquisa6.html"
  python scripts/fetch_votalhada_images.py --paredao 6 --no-timestamp   # overwrite previous captures

By default, images are saved with a datetime suffix (e.g. consolidados_2026-03-04_00-25.png)
to keep a history of captures. Use --no-timestamp to overwrite instead.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

# Project root (script lives in scripts/)
REPO_ROOT = Path(__file__).resolve().parent.parent
VOTALHADA_DIR = REPO_ROOT / "data" / "votalhada"
PAREDOES_JSON = REPO_ROOT / "data" / "paredoes.json"
CAPTURE_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}(?:-\d{2})?$")
DEDUPE_MODES = ("off", "size", "sha256", "size+sha256")


def _load_paredoes():
    import json
    with open(PAREDOES_JSON, encoding="utf-8") as f:
        return json.load(f)


def get_post_url_for_paredao(numero: int) -> tuple[str, str]:
    """Return (url, folder_YYYY_MM_DD) for the Votalhada pesquisa post.

    If the paredão exists in paredoes.json, uses data_formacao for the URL
    month/year and folder name. Otherwise falls back to the current month/year
    (the URL pattern is predictable: /YYYY/MM/pesquisaN.html).
    """
    data = _load_paredoes()
    for p in data["paredoes"]:
        if p["numero"] == numero:
            data_formacao = p.get("data_formacao") or p.get("data")
            if not data_formacao:
                break  # fall through to fallback
            year, month, _ = data_formacao.split("-")
            url = f"https://votalhada.blogspot.com/{year}/{month}/pesquisa{numero}.html"
            folder = data_formacao.replace("-", "_")
            return url, folder

    # Fallback: paredão not in paredoes.json yet — derive from current date
    now = datetime.now(timezone.utc)
    # BRT = UTC-3; use BRT date for month derivation
    from datetime import timedelta
    brt_now = now - timedelta(hours=3)
    year = brt_now.strftime("%Y")
    month = brt_now.strftime("%m")
    url = f"https://votalhada.blogspot.com/{year}/{month}/pesquisa{numero}.html"
    folder = brt_now.strftime("%Y_%m_%d")
    print(f"  (P{numero} not in paredoes.json — using current month: {year}/{month})")
    return url, folder


def extract_image_urls(html: str) -> list[str]:
    """Extract img src URLs from the main post body (Blogger post content)."""
    # Restrict to main post: content between id="Blog1" and typical end of post.
    # (The exact DOM can drift; keep this best-effort and fall back to the whole HTML.)
    blog1 = re.search(
        r'<div[^>]*id="Blog1"[^>]*>(.*?)</div>\s*</div>\s*</div>',
        html,
        re.DOTALL | re.IGNORECASE,
    )
    block = blog1.group(1) if blog1 else html

    def _attr_value(tag: str, attr: str) -> str | None:
        m = re.search(rf'\b{re.escape(attr)}\s*=\s*[\'"]([^\'"]+)[\'"]', tag, re.IGNORECASE)
        return m.group(1) if m else None

    def _first_url_from_srcset(srcset: str) -> str | None:
        # srcset example: "url1 1x, url2 2x" -> take the first url1
        parts = [p.strip() for p in srcset.split(",") if p.strip()]
        if not parts:
            return None
        first = parts[0].split()
        return first[0] if first else None

    urls: list[str] = []
    # Iterate img tags to preserve on-page order, and pick the best lazyload candidate.
    for tag in re.findall(r"<img\b[^>]*>", block, re.IGNORECASE):
        # Prefer actual lazyload payloads over the current `src` (which may be a placeholder).
        chosen: str | None = None
        chosen_from: str | None = None
        for attr in ("data-original", "data-src", "src"):
            v = _attr_value(tag, attr)
            if v:
                chosen = v
                chosen_from = attr
                break

        # If we picked `src` but it's not Blogger CDN, the real poll images may be in srcset.
        if chosen is None or (
            chosen_from == "src"
            and not ("blogger.googleusercontent.com" in chosen or "blogspot.com" in chosen)
        ):
            for attr in ("srcset", "data-srcset"):
                v = _attr_value(tag, attr)
                if v:
                    chosen = _first_url_from_srcset(v)
                    if chosen:
                        break

        if chosen and chosen.startswith("http"):
            urls.append(chosen)

    # Keep only the poll-card images (PNGs).
    # Excludes banners like "000.jpg" (Pesquisa de Popularidade) and
    # other Blogger images in the post header/comments.
    # Observed patterns:
    # - .../2026-03-17_194618.png (HHMMSS, old layout)
    # - .../2026-03-17_19-46-18.png (HH-MM-SS, old layout)
    # - .../1.Twitter.png, 5.Consolidados.png (numbered platform names, new layout)
    card_name_re = re.compile(
        r"^(?:\d{4}-\d{2}-\d{2}_(?:\d{6}|\d{2}-\d{2}-\d{2})|"
        r"\d+\.\w+)\.png$",
        re.IGNORECASE,
    )

    def _is_card_url(u: str) -> bool:
        name = u.split("/")[-1].split("?")[0]
        return bool(card_name_re.match(name))

    chosen_urls = [u for u in urls if ("blogger.googleusercontent.com" in u or "blogspot.com" in u) and _is_card_url(u)]

    # De-dupe while preserving order (exact URL duplicates only).
    def _dedupe_preserve(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for x in items:
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out

    return _dedupe_preserve(chosen_urls)


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


def _display_path(path: Path) -> str:
    """Return a stable, human-readable path for logs."""
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_capture_for_base(path: Path, base: str) -> bool:
    stem = path.stem
    if stem == base:
        return True
    prefix = f"{base}_"
    if not stem.startswith(prefix):
        return False
    tail = stem[len(prefix) :]
    return bool(CAPTURE_TS_RE.fullmatch(tail))


def _files_match(existing: Path, incoming: Path, mode: str) -> bool:
    if mode == "off":
        return False

    existing_size = existing.stat().st_size
    incoming_size = incoming.stat().st_size

    if mode == "size":
        return existing_size == incoming_size
    if mode == "sha256":
        return _sha256_file(existing) == _sha256_file(incoming)
    if mode == "size+sha256":
        if existing_size != incoming_size:
            return False
        return _sha256_file(existing) == _sha256_file(incoming)

    raise ValueError(f"Unsupported dedupe mode: {mode}")


def _find_duplicate_capture(out_dir: Path, base: str, incoming: Path, mode: str) -> Path | None:
    if mode == "off":
        return None

    candidates = []
    for candidate in sorted(out_dir.glob("*.png")):
        if candidate.resolve() == incoming.resolve():
            continue
        if not _is_capture_for_base(candidate, base):
            continue
        if _files_match(candidate, incoming, mode):
            candidates.append(candidate)

    if not candidates:
        return None

    return max(candidates, key=lambda p: p.stat().st_mtime)


def _format_platform_audit_lines(report: dict) -> list[str]:
    summary = report.get("summary", {})
    lines = [
        (
            "Platform consistency audit: "
            f"{summary.get('total_platform_cards', 0)} cards | "
            f"ok {summary.get('ok', 0)} | "
            f"anomaly {summary.get('anomaly', 0)} | "
            f"inconclusive {summary.get('inconclusive', 0)}"
        )
    ]
    for card in report.get("cards", []):
        if card.get("status") != "anomaly":
            continue
        image_name = Path(card.get("image", "")).name
        platform = card.get("platform", "unknown")
        declared_sum = card.get("declared_media", {}).get("sum")
        max_delta = card.get("declared_vs_unweighted_delta", {}).get("max")
        rows_count = card.get("rows_count")
        lines.append(
            "  anomaly: "
            f"{image_name} ({platform}) "
            f"sum={declared_sum} max_delta={max_delta} rows={rows_count}"
        )
    return lines


def _run_platform_consistency_audit(
    out_dir: Path,
    *,
    output_path: Path | None = None,
) -> dict | None:
    try:
        from votalhada_platform_consistency_audit import audit_platform_cards_in_dir
    except Exception as e:
        print(f"Platform consistency audit unavailable: {e}", file=sys.stderr)
        return None

    try:
        report = audit_platform_cards_in_dir(out_dir)
    except Exception as e:
        print(f"Platform consistency audit failed: {e}", file=sys.stderr)
        return None

    for line in _format_platform_audit_lines(report):
        print(line)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  Audit report saved to {_display_path(output_path)}")

    return report


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
        "--no-timestamp",
        action="store_true",
        help="Overwrite files without datetime suffix (default: keep timestamped history)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Override output directory (default: data/votalhada/YYYY_MM_DD)",
    )
    parser.add_argument(
        "--dedupe",
        choices=DEDUPE_MODES,
        default="off",
        help="Optional duplicate detection across captures in the same folder.",
    )
    parser.add_argument(
        "--skip-platform-audit",
        action="store_true",
        help="Skip post-fetch platform-card consistency audit.",
    )
    parser.add_argument(
        "--platform-audit-output",
        type=Path,
        default=None,
        help="Optional JSON output path for platform consistency audit.",
    )
    parser.add_argument(
        "--platform-audit-strict",
        action="store_true",
        help="Exit with code 2 if audit finds high-confidence anomalies.",
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
        sys.exit(3)  # exit 3 = "page not available yet" (distinct from real errors)
    print(f"Found {len(urls)} image(s).")

    suffix = ""
    if not args.no_timestamp:
        suffix = "_" + datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")

    saved = 0
    skipped_dupes = 0
    for i, url in enumerate(urls):
        if i == 0:
            base = "consolidados"
        else:
            base = f"consolidados_{i + 1}"
        name = f"{base}{suffix}.png"
        path = out_dir / name
        if download_image(url, path, session):
            duplicate = _find_duplicate_capture(out_dir, base, path, mode=args.dedupe)
            if duplicate is not None:
                path.unlink(missing_ok=True)
                print(
                    "  Skipped duplicate "
                    f"{_display_path(path)} (same as {_display_path(duplicate)} via {args.dedupe})"
                )
                skipped_dupes += 1
                continue
            print(f"  Saved {_display_path(path)}")
            saved += 1

    print(
        f"Done. {saved}/{len(urls)} images saved to {_display_path(out_dir)}"
        f" (duplicates skipped: {skipped_dupes})."
    )

    if args.skip_platform_audit:
        return

    report = _run_platform_consistency_audit(
        out_dir,
        output_path=args.platform_audit_output,
    )
    if report is None:
        return
    if args.platform_audit_strict and report.get("summary", {}).get("anomaly", 0) > 0:
        sys.exit(2)


if __name__ == "__main__":
    main()
