#!/usr/bin/env python3
"""
Capture full-page screenshots for Quarto pages in desktop and mobile layouts.

Usage:
  python scripts/capture_quarto_screenshots.py
  python scripts/capture_quarto_screenshots.py --render
  python scripts/capture_quarto_screenshots.py --profiles mobile --page paredao.html
"""

from __future__ import annotations

import argparse
import json
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SITE_DIR = REPO_ROOT / "_site"
DEFAULT_QUARTO_CONFIG = REPO_ROOT / "_quarto.yml"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "tmp" / "page_screenshots"

PROFILE_OPTIONS: dict[str, list[str]] = {
    "desktop": ["--viewport-size", "1600,1200"],
    # Viewport-only mobile profile keeps the run chromium-only.
    "mobile": ["--viewport-size", "390,844"],
}


def profile_viewport(profile: str) -> tuple[int, int]:
    if profile not in PROFILE_OPTIONS:
        raise ValueError(f"Unknown profile: {profile}")
    opts = PROFILE_OPTIONS[profile]
    if "--viewport-size" not in opts:
        raise ValueError(f"Profile missing viewport-size option: {profile}")
    idx = opts.index("--viewport-size")
    width_str, height_str = opts[idx + 1].split(",", 1)
    return int(width_str), int(height_str)


def parse_quarto_render_pages(content: str) -> list[str]:
    """Extract project.render QMD entries from a Quarto config string."""
    lines = content.splitlines()
    in_project = False
    in_render = False
    project_indent = 0
    render_indent = 0
    qmd_pages: list[str] = []

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))

        if not in_project and stripped == "project:":
            in_project = True
            project_indent = indent
            continue

        if in_project and indent <= project_indent and stripped.endswith(":") and stripped != "project:":
            in_project = False
            in_render = False

        if not in_project:
            continue

        if not in_render:
            if stripped == "render:":
                in_render = True
                render_indent = indent
            continue

        if indent <= render_indent:
            in_render = False
            continue

        if not stripped.startswith("- "):
            continue

        item = stripped[2:].split("#", 1)[0].strip().strip('"').strip("'")
        if item.endswith(".qmd"):
            qmd_pages.append(item)

    return qmd_pages


def qmd_to_html(qmd_path: str) -> str:
    """Map a QMD source path to the expected HTML output path."""
    return str(Path(qmd_path).with_suffix(".html").as_posix())


def discover_site_pages(site_dir: Path, quarto_config: Path) -> list[str]:
    """Find rendered HTML pages, preferring the _quarto.yml project.render order."""
    if not site_dir.exists():
        raise FileNotFoundError(f"Site directory not found: {site_dir}")

    ordered_pages: list[str] = []
    if quarto_config.exists():
        content = quarto_config.read_text(encoding="utf-8")
        for qmd in parse_quarto_render_pages(content):
            html_rel = qmd_to_html(qmd)
            if (site_dir / html_rel).exists():
                ordered_pages.append(html_rel)
        if ordered_pages:
            return ordered_pages

    return sorted(path.name for path in site_dir.glob("*.html"))


def parse_profiles(value: str) -> list[str]:
    """Parse and validate a comma-separated profile list."""
    profiles = [item.strip() for item in value.split(",") if item.strip()]
    if not profiles:
        raise ValueError("At least one profile is required.")
    unknown = [profile for profile in profiles if profile not in PROFILE_OPTIONS]
    if unknown:
        raise ValueError(
            f"Unknown profile(s): {', '.join(unknown)}. "
            f"Valid options: {', '.join(sorted(PROFILE_OPTIONS))}"
        )
    return profiles


def normalize_page_name(value: str) -> str:
    """Allow users to pass either page.qmd or page.html."""
    value = value.strip()
    if value.endswith(".qmd"):
        return qmd_to_html(value)
    if value.endswith(".html"):
        return value
    return f"{value}.html"


def build_screenshot_command(
    package_ref: str,
    page_url: str,
    output_file: Path,
    profile: str,
    wait_ms: int,
    timeout_ms: int,
    browser: str,
) -> list[str]:
    """Build an npx playwright screenshot command for a page/profile."""
    if profile not in PROFILE_OPTIONS:
        raise ValueError(f"Unknown profile: {profile}")

    command = [
        "npx",
        "-y",
        package_ref,
        "screenshot",
        "--browser",
        browser,
        "--full-page",
        "--block-service-workers",
        "--wait-for-timeout",
        str(wait_ms),
        "--timeout",
        str(timeout_ms),
    ]
    command.extend(PROFILE_OPTIONS[profile])
    command.extend([page_url, str(output_file)])
    return command


def ensure_binary(binary_name: str) -> None:
    if shutil.which(binary_name) is None:
        raise RuntimeError(f"Required binary not found in PATH: {binary_name}")


def find_first_binary(candidates: list[str]) -> str | None:
    for name in candidates:
        if shutil.which(name):
            return name
    return None


def get_image_dimensions(image_path: Path) -> tuple[int, int]:
    result = subprocess.run(
        ["identify", "-format", "%w %h", str(image_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    width_str, height_str = result.stdout.strip().split()
    return int(width_str), int(height_str)


def extract_result_block(output: str) -> str:
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


def run_pwcli(pwcli: Path, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run([str(pwcli), *args], capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"playwright-cli command failed: {' '.join(args)}\n"
            f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
        )
    return result


def get_default_pwcli_path() -> Path:
    return Path.home() / ".codex" / "skills" / "playwright" / "scripts" / "playwright_cli.sh"


def compute_scroll_positions(scroll_height: int, viewport_height: int) -> list[int]:
    max_y = max(0, scroll_height - viewport_height)
    positions = list(range(0, max_y + 1, viewport_height))
    if not positions:
        return [0]
    if positions[-1] != max_y:
        positions.append(max_y)
    return positions


def capture_stitched_fullpage_with_pwcli(
    *,
    pwcli: Path,
    page_url: str,
    output_file: Path,
    viewport_width: int,
    viewport_height: int,
    wait_ms: int,
    convert_binary: str,
    verbose: bool = False,
) -> tuple[int, int]:
    temp_dir = output_file.parent / f".{output_file.stem}_tiles"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        run_pwcli(pwcli, ["close-all"], check=False)
        run_pwcli(pwcli, ["open", page_url])
        run_pwcli(pwcli, ["resize", str(viewport_width), str(viewport_height)])
        run_pwcli(
            pwcli,
            [
                "eval",
                f"async () => {{ await new Promise(r => setTimeout(r, {wait_ms})); return true; }}",
            ],
        )

        height_result = run_pwcli(
            pwcli,
            [
                "eval",
                "() => Math.max(document.documentElement.scrollHeight || 0, document.body.scrollHeight || 0)",
            ],
        )
        scroll_height = int(float(extract_result_block(height_result.stdout)))
        positions = compute_scroll_positions(scroll_height, viewport_height)
        if verbose:
            print(
                f"[VERBOSE] stitch start: {page_url} "
                f"scroll_height={scroll_height} tiles={len(positions)} "
                f"viewport={viewport_width}x{viewport_height}"
            )

        tile_paths: list[str] = []
        def restore_browser_at(y_pos: int) -> None:
            run_pwcli(pwcli, ["close-all"], check=False)
            run_pwcli(pwcli, ["open", page_url])
            run_pwcli(pwcli, ["resize", str(viewport_width), str(viewport_height)])
            run_pwcli(
                pwcli,
                [
                    "eval",
                    f"async () => {{ await new Promise(r => setTimeout(r, {wait_ms})); return true; }}",
                ],
            )
            run_pwcli(
                pwcli,
                [
                    "eval",
                    f"async () => {{ window.scrollTo(0, {y_pos}); await new Promise(r => setTimeout(r, 200)); return window.scrollY; }}",
                ],
            )

        for idx, y in enumerate(positions):
            if verbose and (idx == 0 or idx == len(positions) - 1 or idx % 5 == 0):
                print(f"[VERBOSE] tile {idx + 1}/{len(positions)} y={y}")
            run_pwcli(
                pwcli,
                [
                    "eval",
                    f"async () => {{ window.scrollTo(0, {y}); await new Promise(r => setTimeout(r, 160)); return window.scrollY; }}",
                ],
            )
            tile_file = temp_dir / f"{idx:04d}.png"
            try:
                run_pwcli(pwcli, ["screenshot", "--filename", str(tile_file)])
            except RuntimeError as exc:
                # playwright-cli sessions can sporadically drop on long pages.
                if "not open" in str(exc).lower():
                    if verbose:
                        print(f"[VERBOSE] stitch recover: reopening browser at tile {idx + 1}")
                    restore_browser_at(y)
                    run_pwcli(pwcli, ["screenshot", "--filename", str(tile_file)])
                else:
                    raise
            tile_paths.append(str(tile_file))

        stitch_command = [
            convert_binary,
            *tile_paths,
            "-append",
            "-crop",
            f"{viewport_width}x{scroll_height}+0+0",
            "+repage",
            str(output_file),
        ]
        subprocess.run(stitch_command, check=True, capture_output=True, text=True)
        if verbose:
            print(f"[VERBOSE] stitch done: {output_file}")
        return scroll_height, len(tile_paths)
    finally:
        run_pwcli(pwcli, ["close-all"], check=False)
        shutil.rmtree(temp_dir, ignore_errors=True)


def install_playwright_browser(package_ref: str, browser: str) -> None:
    command = ["npx", "-y", package_ref, "install", browser]
    subprocess.run(command, check=True, cwd=REPO_ROOT)


def run_quarto_render(quarto_bin: str) -> None:
    command = [quarto_bin, "render"]
    subprocess.run(command, check=True, cwd=REPO_ROOT)


def wait_for_server(host: str, port: int, timeout_seconds: float = 5.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex((host, port)) == 0:
                return
        time.sleep(0.05)
    raise RuntimeError(f"Timed out waiting for HTTP server at http://{host}:{port}")


def find_available_port(host: str, preferred_port: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if sock.connect_ex((host, preferred_port)) != 0:
            return preferred_port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def start_http_server(site_dir: Path, host: str, port: int) -> subprocess.Popen:
    command = [sys.executable, "-m", "http.server", str(port), "--bind", host]
    return subprocess.Popen(
        command,
        cwd=site_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )


def build_default_output_dir() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    return DEFAULT_OUTPUT_ROOT / stamp


def resolve_output_dir(output_dir: Path) -> Path:
    """Resolve relative output paths from the repository root."""
    if output_dir.is_absolute():
        return output_dir
    return REPO_ROOT / output_dir


def page_slug(page_name: str) -> str:
    return page_name.replace("/", "__").removesuffix(".html")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture full-page desktop/mobile screenshots for Quarto pages.",
    )
    parser.add_argument("--site-dir", type=Path, default=DEFAULT_SITE_DIR)
    parser.add_argument("--quarto-config", type=Path, default=DEFAULT_QUARTO_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--profiles",
        type=str,
        default="desktop,mobile",
        help="Comma-separated profiles (desktop,mobile).",
    )
    parser.add_argument(
        "--page",
        action="append",
        default=[],
        help="Limit to one or more pages (supports .qmd or .html). Repeat flag.",
    )
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4444)
    parser.add_argument("--wait-ms", type=int, default=3500)
    parser.add_argument("--timeout-ms", type=int, default=120000)
    parser.add_argument("--playwright-package", type=str, default="playwright@latest")
    parser.add_argument("--browser", type=str, default="chromium")
    parser.add_argument(
        "--mobile-stitch-threshold",
        type=int,
        default=35000,
        help=(
            "If a mobile full-page image is taller than this threshold, replace it with "
            "a stitched viewport capture to avoid blank full-page segments. Set 0 to disable."
        ),
    )
    parser.add_argument("--pwcli-path", type=Path, default=None)
    parser.add_argument(
        "--mobile-stitch-viewport-height",
        type=int,
        default=5000,
        help="Viewport height used for stitched mobile fallback captures (reduces tile count).",
    )
    parser.add_argument("--skip-install", action="store_true")
    parser.add_argument("--render", action="store_true", help="Run `quarto render` first.")
    parser.add_argument("--quarto-bin", type=str, default="quarto")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    profiles = parse_profiles(args.profiles)

    ensure_binary("npx")
    if args.render:
        ensure_binary(args.quarto_bin)
        print("Rendering Quarto site...")
        run_quarto_render(args.quarto_bin)

    if not args.skip_install:
        print(f"Ensuring Playwright browser is installed ({args.browser})...")
        install_playwright_browser(args.playwright_package, args.browser)

    pages = discover_site_pages(args.site_dir, args.quarto_config)
    if args.page:
        requested = {normalize_page_name(item) for item in args.page}
        pages = [page for page in pages if page in requested]
        missing = sorted(requested - set(pages))
        if missing:
            raise RuntimeError(f"Requested page(s) not found in site output: {', '.join(missing)}")

    if not pages:
        raise RuntimeError("No HTML pages found to capture.")

    output_dir = resolve_output_dir(args.output_dir or build_default_output_dir())
    output_dir.mkdir(parents=True, exist_ok=True)

    port = find_available_port(args.host, args.port)
    if port != args.port:
        print(f"Port {args.port} busy, using port {port}.")

    server = start_http_server(args.site_dir, args.host, port)
    base_url = f"http://{args.host}:{port}"
    try:
        wait_for_server(args.host, port)
        failures: list[dict[str, str]] = []
        captures: list[dict[str, str | int]] = []

        pwcli_path: Path | None = None
        convert_binary: str | None = None
        identify_binary: str | None = None
        if "mobile" in profiles and args.mobile_stitch_threshold > 0:
            candidate_pwcli = args.pwcli_path or get_default_pwcli_path()
            if not candidate_pwcli.exists():
                print(
                    f"Warning: playwright-cli wrapper not found at {candidate_pwcli}; "
                    "mobile stitched fallback disabled."
                )
            else:
                identify_binary = find_first_binary(["identify"])
                convert_binary = find_first_binary(["convert"])
                if not identify_binary or not convert_binary:
                    print(
                        "Warning: ImageMagick tools (identify/convert) unavailable; "
                        "mobile stitched fallback disabled."
                    )
                    convert_binary = None
                    identify_binary = None
                else:
                    pwcli_path = candidate_pwcli
                    print(
                        f"Mobile stitch fallback enabled for heights >= "
                        f"{args.mobile_stitch_threshold}px."
                    )

        print(f"Capturing {len(pages)} page(s) for profiles: {', '.join(profiles)}")
        for profile in profiles:
            profile_dir = output_dir / profile
            profile_dir.mkdir(parents=True, exist_ok=True)

            for page in pages:
                output_file = profile_dir / f"{page_slug(page)}.png"
                page_url = f"{base_url}/{page}"
                if args.verbose:
                    print(f"[VERBOSE] begin {profile} {page}")
                force_mobile_stitch = (
                    profile == "mobile"
                    and pwcli_path is not None
                    and convert_binary is not None
                    and page.endswith("_debug.html")
                )
                if force_mobile_stitch:
                    vw, vh = profile_viewport(profile)
                    stitch_vh = max(vh, args.mobile_stitch_viewport_height)
                    try:
                        stitched_height, tiles = capture_stitched_fullpage_with_pwcli(
                            pwcli=pwcli_path,
                            page_url=page_url,
                            output_file=output_file,
                            viewport_width=vw,
                            viewport_height=stitch_vh,
                            wait_ms=args.wait_ms,
                            convert_binary=convert_binary,
                            verbose=args.verbose,
                        )
                        captures.append(
                            {
                                "profile": profile,
                                "page": page,
                                "file": str(output_file.relative_to(REPO_ROOT)),
                                "mode": "stitched-scroll-forced",
                                "scroll_height": stitched_height,
                                "tiles": tiles,
                            }
                        )
                        print(f"[OK]   {profile:<8} {page} (forced stitch, {tiles} tiles)")
                        continue
                    except Exception as stitch_exc:  # noqa: BLE001
                        failures.append(
                            {
                                "profile": profile,
                                "page": page,
                                "stderr": f"forced_stitch_error: {stitch_exc}",
                                "stdout": "",
                            }
                        )
                        print(f"[FAIL] {profile:<8} {page}")
                        if args.fail_fast:
                            raise RuntimeError(f"Capture failed for {profile}/{page}")
                        continue

                command = build_screenshot_command(
                    package_ref=args.playwright_package,
                    page_url=page_url,
                    output_file=output_file,
                    profile=profile,
                    wait_ms=args.wait_ms,
                    timeout_ms=args.timeout_ms,
                    browser=args.browser,
                )
                if args.verbose:
                    print(f"[VERBOSE] full-page command: {' '.join(command)}")
                result = subprocess.run(command, capture_output=True, text=True)
                if result.returncode != 0:
                    if args.verbose:
                        err_tail = result.stderr.strip().splitlines()[-5:]
                        if err_tail:
                            print("[VERBOSE] full-page failed tail:")
                            for line in err_tail:
                                print(f"[VERBOSE] {line}")
                    if (
                        profile == "mobile"
                        and pwcli_path is not None
                        and convert_binary is not None
                    ):
                        vw, vh = profile_viewport(profile)
                        stitch_vh = max(vh, args.mobile_stitch_viewport_height)
                        try:
                            stitched_height, tiles = capture_stitched_fullpage_with_pwcli(
                                pwcli=pwcli_path,
                                page_url=page_url,
                                output_file=output_file,
                                viewport_width=vw,
                                viewport_height=stitch_vh,
                                wait_ms=args.wait_ms,
                                convert_binary=convert_binary,
                                verbose=args.verbose,
                            )
                            captures.append(
                                {
                                    "profile": profile,
                                    "page": page,
                                    "file": str(output_file.relative_to(REPO_ROOT)),
                                    "mode": "stitched-scroll-fallback",
                                    "scroll_height": stitched_height,
                                    "tiles": tiles,
                                }
                            )
                            print(
                                f"[OK]   {profile:<8} {page} "
                                f"(stitched fallback after full-page failure)"
                            )
                            continue
                        except Exception as stitch_exc:  # noqa: BLE001
                            failures.append(
                                {
                                    "profile": profile,
                                    "page": page,
                                    "stderr": (
                                        f"{result.stderr.strip()}\n\n"
                                        f"stitch_fallback_error: {stitch_exc}"
                                    ),
                                    "stdout": result.stdout.strip(),
                                }
                            )
                            print(f"[FAIL] {profile:<8} {page}")
                            if args.fail_fast:
                                raise RuntimeError(f"Capture failed for {profile}/{page}")
                            continue

                    failures.append(
                        {
                            "profile": profile,
                            "page": page,
                            "stderr": result.stderr.strip(),
                            "stdout": result.stdout.strip(),
                        }
                    )
                    print(f"[FAIL] {profile:<8} {page}")
                    if args.fail_fast:
                        raise RuntimeError(f"Capture failed for {profile}/{page}")
                    continue

                capture_entry: dict[str, str | int] = {
                    "profile": profile,
                    "page": page,
                    "file": str(output_file.relative_to(REPO_ROOT)),
                    "mode": "full-page",
                }

                if (
                    profile == "mobile"
                    and pwcli_path is not None
                    and convert_binary is not None
                    and identify_binary is not None
                ):
                    width, height = get_image_dimensions(output_file)
                    if height >= args.mobile_stitch_threshold:
                        vw, vh = profile_viewport(profile)
                        stitch_vh = max(vh, args.mobile_stitch_viewport_height)
                        try:
                            stitched_height, tiles = capture_stitched_fullpage_with_pwcli(
                                pwcli=pwcli_path,
                                page_url=page_url,
                                output_file=output_file,
                                viewport_width=vw,
                                viewport_height=stitch_vh,
                                wait_ms=args.wait_ms,
                                convert_binary=convert_binary,
                                verbose=args.verbose,
                            )
                            capture_entry["mode"] = "stitched-scroll"
                            capture_entry["scroll_height"] = stitched_height
                            capture_entry["tiles"] = tiles
                            print(
                                f"[OK]   {profile:<8} {page} "
                                f"(stitched {tiles} tiles; {stitched_height}px)"
                            )
                        except Exception as exc:  # noqa: BLE001
                            capture_entry["stitch_error"] = str(exc)
                            print(
                                f"[OK]   {profile:<8} {page} "
                                f"(full-page kept; stitch fallback failed)"
                            )
                    else:
                        print(f"[OK]   {profile:<8} {page}")
                else:
                    print(f"[OK]   {profile:<8} {page}")

                captures.append(capture_entry)

        manifest = {
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "profiles": profiles,
            "pages": pages,
            "base_url": base_url,
            "captures": captures,
            "failures": failures,
        }
        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        if failures:
            print(f"\nDone with failures: {len(captures)} success, {len(failures)} failed.")
            print(f"Manifest: {manifest_path.relative_to(REPO_ROOT)}")
            return 1

        print(f"\nDone: {len(captures)} screenshots saved to {output_dir.relative_to(REPO_ROOT)}")
        print(f"Manifest: {manifest_path.relative_to(REPO_ROOT)}")
        return 0
    finally:
        server.terminate()
        try:
            server.wait(timeout=2)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
