"""Contract tests for chronology mobile review assets."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_cronologia_mobile_review_page_exists():
    assert (REPO_ROOT / "cronologia_mobile_review.qmd").exists()


def test_cronologia_mobile_review_styles_prefer_single_axis_mobile_layout():
    css = _read(REPO_ROOT / "assets" / "cards.css")
    assert ".cronologia-mobile-table {\n  width: 100%;\n  table-layout: fixed;" in css
    assert "max-height: clamp(320px, 44vh, 460px);" in css
    assert ".cronologia-shell--review .cronologia-table-wrap {\n  overflow-x: visible;\n}" in css
    assert ".cronologia-detail-toggle > summary" in css
