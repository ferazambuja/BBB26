#!/usr/bin/env python3
"""
Capture mobile viewport slices (top/mid/bottom) for Quarto pages.

This is an alternative capture mode for very long pages where full-page
screenshots can be unreliable.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from capture_quarto_screenshots import (
    DEFAULT_QUARTO_CONFIG,
    DEFAULT_SITE_DIR,
    REPO_ROOT,
    discover_site_pages,
    ensure_binary,
    find_available_port,
    run_quarto_render,
    start_http_server,
    wait_for_server,
)

DEFAULT_OUTPUT_ROOT = REPO_ROOT / "tmp" / "page_screenshots" / "mobile_slices"


def extract_result_block(output: str) -> str:
    """Extract the text under `### Result` from playwright-cli output."""
    marker = "### Result"
    start = output.find(marker)
    if start == -1:
        raise ValueError("Could not find `### Result` marker in playwright-cli output.")
    start += len(marker)
    rest = output[start:].lstrip()
    end_marker = "\n### "
    end = rest.find(end_marker)
    if end == -1:
        return rest.strip()
    return rest[:end].strip()


def compute_slice_positions(scroll_height: int, viewport_height: int) -> list[tuple[str, int]]:
    """Return unique top/mid/bottom viewport origins."""
    max_y = max(0, scroll_height - viewport_height)
    candidates = [
        ("top", 0),
        ("mid", max(0, (scroll_height - viewport_height) // 2)),
        ("bottom", max_y),
    ]
    seen: set[int] = set()
    results: list[tuple[str, int]] = []
    for label, y in candidates:
        if y in seen:
            continue
        seen.add(y)
        results.append((label, y))
    return results


def build_default_output_dir() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    return DEFAULT_OUTPUT_ROOT / stamp


def resolve_output_dir(output_dir: Path) -> Path:
    if output_dir.is_absolute():
        return output_dir
    return REPO_ROOT / output_dir


def page_slug(page_name: str) -> str:
    return page_name.replace("/", "__").removesuffix(".html")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture top/mid/bottom mobile viewport slices.")
    parser.add_argument("--site-dir", type=Path, default=DEFAULT_SITE_DIR)
    parser.add_argument("--quarto-config", type=Path, default=DEFAULT_QUARTO_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4444)
    parser.add_argument("--viewport-width", type=int, default=390)
    parser.add_argument("--viewport-height", type=int, default=844)
    parser.add_argument("--wait-ms", type=int, default=500)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--quarto-bin", type=str, default="quarto")
    parser.add_argument("--pwcli-path", type=Path, default=None)
    return parser.parse_args()


def run_pwcli(pwcli: Path, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    cmd = [str(pwcli), *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"playwright-cli command failed: {' '.join(args)}\n"
            f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
        )
    return result


def get_default_pwcli_path() -> Path:
    codex_home = Path.home() / ".codex"
    return codex_home / "skills" / "playwright" / "scripts" / "playwright_cli.sh"


def main() -> int:
    args = parse_args()
    ensure_binary("npx")
    if args.render:
        ensure_binary(args.quarto_bin)
        run_quarto_render(args.quarto_bin)

    pwcli = args.pwcli_path or get_default_pwcli_path()
    if not pwcli.exists():
        raise FileNotFoundError(f"playwright-cli wrapper not found: {pwcli}")

    pages = discover_site_pages(args.site_dir, args.quarto_config)
    if not pages:
        raise RuntimeError("No rendered HTML pages found.")

    output_dir = resolve_output_dir(args.output_dir or build_default_output_dir())
    output_dir.mkdir(parents=True, exist_ok=True)

    port = find_available_port(args.host, args.port)
    server = start_http_server(args.site_dir, args.host, port)
    base_url = f"http://{args.host}:{port}"

    try:
        wait_for_server(args.host, port)
        run_pwcli(pwcli, ["close-all"], check=False)

        captures: list[dict[str, str | int]] = []
        for idx, page in enumerate(pages):
            page_url = f"{base_url}/{page}"
            if idx == 0:
                run_pwcli(pwcli, ["open", page_url])
                run_pwcli(pwcli, ["resize", str(args.viewport_width), str(args.viewport_height)])
            else:
                run_pwcli(pwcli, ["goto", page_url])

            run_pwcli(
                pwcli,
                [
                    "eval",
                    f"async () => {{ await new Promise(r => setTimeout(r, {args.wait_ms})); return true; }}",
                ],
            )

            result = run_pwcli(pwcli, ["eval", "() => document.documentElement.scrollHeight"])
            scroll_height = int(float(extract_result_block(result.stdout)))
            for label, y in compute_slice_positions(scroll_height, args.viewport_height):
                run_pwcli(
                    pwcli,
                    [
                        "eval",
                        f"async () => {{ window.scrollTo(0, {y}); await new Promise(r => setTimeout(r, 200)); return window.scrollY; }}",
                    ],
                )
                file_path = output_dir / f"{page_slug(page)}_{label}.png"
                try:
                    run_pwcli(pwcli, ["screenshot", "--filename", str(file_path)])
                except RuntimeError as exc:
                    if "not open" in str(exc).lower():
                        # Recover when playwright-cli loses the persisted session.
                        run_pwcli(pwcli, ["close-all"], check=False)
                        run_pwcli(pwcli, ["open", page_url])
                        run_pwcli(pwcli, ["resize", str(args.viewport_width), str(args.viewport_height)])
                        run_pwcli(
                            pwcli,
                            [
                                "eval",
                                f"async () => {{ await new Promise(r => setTimeout(r, {args.wait_ms})); return true; }}",
                            ],
                        )
                        run_pwcli(
                            pwcli,
                            [
                                "eval",
                                f"async () => {{ window.scrollTo(0, {y}); await new Promise(r => setTimeout(r, 200)); return window.scrollY; }}",
                            ],
                        )
                        run_pwcli(pwcli, ["screenshot", "--filename", str(file_path)])
                    else:
                        raise
                captures.append(
                    {
                        "page": page,
                        "slice": label,
                        "scroll_y": y,
                        "file": str(file_path.relative_to(REPO_ROOT)),
                        "scroll_height": scroll_height,
                    }
                )

            print(f"[OK] {page} -> {len(compute_slice_positions(scroll_height, args.viewport_height))} slices")

        manifest = {
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "base_url": base_url,
            "viewport": {"width": args.viewport_width, "height": args.viewport_height},
            "pages": pages,
            "captures": captures,
        }
        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"Done: {len(captures)} slices saved to {output_dir.relative_to(REPO_ROOT)}")
        print(f"Manifest: {manifest_path.relative_to(REPO_ROOT)}")
        return 0
    finally:
        run_pwcli(pwcli, ["close-all"], check=False)
        server.terminate()
        try:
            server.wait(timeout=2)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
