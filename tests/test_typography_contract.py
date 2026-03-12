"""Contracts for the global typography rebalance."""

from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
TYPOGRAPHY_CSS = REPO_ROOT / "assets" / "typography.css"
CARDS_CSS = REPO_ROOT / "assets" / "cards.css"
INDEX_QMD = REPO_ROOT / "index.qmd"
QUARTO_CONFIG = REPO_ROOT / "_quarto.yml"
TITLE_BLOCK_HELPER = REPO_ROOT / "assets" / "title-block-dedupe.js"

TARGET_FILES = [
    REPO_ROOT / "assets" / "typography.css",
    REPO_ROOT / "assets" / "cards.css",
    REPO_ROOT / "assets" / "navbar.css",
    REPO_ROOT / "assets" / "page-nav.css",
    REPO_ROOT / "assets" / "cartola.css",
    REPO_ROOT / "assets" / "provas.css",
    REPO_ROOT / "assets" / "economia.css",
    REPO_ROOT / "assets" / "economia-v2.css",
    REPO_ROOT / "economia.qmd",
    REPO_ROOT / "economia_v2.qmd",
    REPO_ROOT / "evolucao.qmd",
    REPO_ROOT / "votacao.qmd",
    REPO_ROOT / "paredao.qmd",
]

FONT_SIZE_DECL = re.compile(r"font-size\s*:\s*([^;\n}]*)")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _raw_font_size_literals(text: str) -> list[str]:
    offenders = []
    for match in FONT_SIZE_DECL.finditer(text):
        value = match.group(1).strip()
        if value.startswith("var(") or value.startswith("clamp("):
            continue
        if any(unit in value for unit in ("rem", "em", "px")):
            offenders.append(match.group(0))
    return offenders


def test_global_typography_uses_token_roles_for_core_elements():
    css = _read(TYPOGRAPHY_CSS)
    expected_snippets = [
        "h1, .h1 {\n  font-size: var(--fs-4xl);",
        "h2, .h2 {\n  font-size: var(--fs-3xl);",
        "h3, .h3 {\n  font-size: var(--fs-2xl);",
        "h4, .h4 {\n  font-size: var(--fs-xl);",
        "h5, .h5 {\n  font-size: var(--fs-lg);",
        "h6, .h6 {\n  font-size: var(--fs-base);",
        "body {\n  font-size: var(--fs-md);",
        "table {\n  font-size: var(--fs-md);",
        ".callout {\n  font-size: var(--fs-base);",
        ".callout-title {\n  font-size: var(--fs-lg);",
        "pre, code {\n  font-size: var(--fs-md);",
        ".navbar-brand {\n  font-size: var(--fs-xl);",
        ".nav-link {\n  font-size: var(--fs-base);",
        ".page-footer {\n  font-size: var(--fs-sm);",
    ]
    for snippet in expected_snippets:
        assert snippet in css, f"missing core token role: {snippet}"


def test_targeted_surfaces_do_not_track_removed_toc_offcanvas_assets():
    target_names = {path.name for path in TARGET_FILES}
    assert "toc-offcanvas.css" not in target_names
    assert "toc-offcanvas.js" not in target_names


def test_targeted_public_surfaces_avoid_raw_font_size_literals():
    offenders = []
    for path in TARGET_FILES:
        matches = _raw_font_size_literals(_read(path))
        if matches:
            offenders.append((path.relative_to(REPO_ROOT).as_posix(), matches[:5]))

    assert not offenders, f"raw font-size literals still present: {offenders}"


def test_quarto_loads_shared_title_block_dedupe_helper():
    config = _read(QUARTO_CONFIG)
    assert "assets/title-block-dedupe.js" in config


def test_title_block_dedupe_helper_targets_matching_subtitle_and_description():
    helper = _read(TITLE_BLOCK_HELPER)
    assert "#title-block-header" in helper
    assert ".subtitle.lead" in helper
    assert ".description" in helper
    assert "normalizeWhitespace" in helper
    assert "dataset.dedupedDescription" in helper


def test_index_card_header_uses_structured_title_and_meta_rows():
    index_qmd = _read(INDEX_QMD)
    assert "dashboard-card-header" in index_qmd
    assert "dashboard-card-header-main" in index_qmd
    assert "dashboard-card-header-meta" in index_qmd
    assert "dashboard-card-title" in index_qmd
    assert '.u-s333' not in index_qmd


def test_index_drops_parenthetical_recency_from_dramatic_title():
    index_qmd = _read(INDEX_QMD)
    assert "Mudanças Dramáticas (Recente)" not in index_qmd
    assert "Mudanças Dramáticas" in index_qmd


def test_index_mobile_highlights_have_explicit_single_column_hardening():
    cards_css = _read(CARDS_CSS)
    assert "@media (max-width: 575.98px)" in cards_css
    assert ".u-s371" in cards_css
    assert "grid-template-columns: 1fr;" in cards_css


def test_index_pair_story_cards_use_shared_layout_instead_of_strip_rows():
    index_qmd = _read(INDEX_QMD)
    cards_css = _read(CARDS_CSS)
    assert "pair-story-card" in index_qmd
    assert "pair-story-grid" in index_qmd
    assert ".pair-story-card" in cards_css
    assert ".pair-story-grid" in cards_css
    assert 'class="u-s342"' not in index_qmd
