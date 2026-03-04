"""Tests for Quarto full-page screenshot capture helpers."""

from pathlib import Path

from capture_quarto_screenshots import (
    REPO_ROOT,
    build_screenshot_command,
    compute_scroll_positions,
    discover_site_pages,
    parse_quarto_render_pages,
    profile_viewport,
    resolve_output_dir,
)


def test_parse_quarto_render_pages_extracts_qmd_entries_in_order():
    content = """
project:
  type: website
  render:
    - index.qmd
    - pages/custom.qmd
    - README.md
website:
  title: Test
""".strip()

    assert parse_quarto_render_pages(content) == ["index.qmd", "pages/custom.qmd"]


def test_discover_site_pages_prefers_quarto_order_and_filters_missing(tmp_path: Path):
    site_dir = tmp_path / "_site"
    site_dir.mkdir()
    (site_dir / "index.html").write_text("<html></html>", encoding="utf-8")
    (site_dir / "datas.html").write_text("<html></html>", encoding="utf-8")

    quarto_config = tmp_path / "_quarto.yml"
    quarto_config.write_text(
        """
project:
  render:
    - index.qmd
    - missing.qmd
    - datas.qmd
""".strip(),
        encoding="utf-8",
    )

    assert discover_site_pages(site_dir, quarto_config) == ["index.html", "datas.html"]


def test_discover_site_pages_falls_back_to_site_html_when_quarto_missing(tmp_path: Path):
    site_dir = tmp_path / "_site"
    site_dir.mkdir()
    (site_dir / "b.html").write_text("<html></html>", encoding="utf-8")
    (site_dir / "a.html").write_text("<html></html>", encoding="utf-8")
    (site_dir / "search.json").write_text("{}", encoding="utf-8")

    assert discover_site_pages(site_dir, tmp_path / "_quarto.yml") == ["a.html", "b.html"]


def test_build_screenshot_command_uses_mobile_viewport_profile(tmp_path: Path):
    out_file = tmp_path / "mobile.png"
    cmd = build_screenshot_command(
        package_ref="playwright@latest",
        page_url="http://127.0.0.1:4444/index.html",
        output_file=out_file,
        profile="mobile",
        wait_ms=3500,
        timeout_ms=120000,
        browser="chromium",
    )

    assert cmd[:5] == ["npx", "-y", "playwright@latest", "screenshot", "--browser"]
    assert "--full-page" in cmd
    assert "--viewport-size" in cmd
    idx = cmd.index("--viewport-size")
    assert cmd[idx + 1] == "390,844"
    assert cmd[-2] == "http://127.0.0.1:4444/index.html"
    assert cmd[-1] == str(out_file)


def test_build_screenshot_command_uses_desktop_viewport_profile(tmp_path: Path):
    out_file = tmp_path / "desktop.png"
    cmd = build_screenshot_command(
        package_ref="playwright@latest",
        page_url="http://127.0.0.1:4444/index.html",
        output_file=out_file,
        profile="desktop",
        wait_ms=3000,
        timeout_ms=90000,
        browser="chromium",
    )

    assert "--viewport-size" in cmd
    idx = cmd.index("--viewport-size")
    assert cmd[idx + 1] == "1600,1200"


def test_resolve_output_dir_maps_relative_paths_under_repo_root():
    output_dir = resolve_output_dir(Path("tmp/page_screenshots/custom"))
    assert output_dir == REPO_ROOT / "tmp/page_screenshots/custom"


def test_profile_viewport_matches_profile_defaults():
    assert profile_viewport("mobile") == (390, 844)
    assert profile_viewport("desktop") == (1600, 1200)


def test_compute_scroll_positions_includes_bottom_position():
    assert compute_scroll_positions(scroll_height=844, viewport_height=844) == [0]
    assert compute_scroll_positions(scroll_height=900, viewport_height=844) == [0, 56]
    assert compute_scroll_positions(scroll_height=2000, viewport_height=844) == [0, 844, 1156]
