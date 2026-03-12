"""Regression checks for UI shell cleanup and navigation standardization."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
QUARTO_CONFIG = REPO_ROOT / "_quarto.yml"
PROJECT_METADATA = REPO_ROOT / "_metadata.yml"
SOCIAL_PREVIEW_SCRIPT = REPO_ROOT / "scripts" / "generate_social_preview.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_quarto_does_not_include_accessibility_assets():
    config = _read(QUARTO_CONFIG)
    assert "assets/accessibility.css" not in config
    assert "assets/accessibility.js" not in config


def test_quarto_does_not_include_disclaimer_injected_block():
    config = _read(QUARTO_CONFIG)
    assert "assets/disclaimer.html" not in config


def test_quarto_includes_social_metadata_defaults():
    config = _read(QUARTO_CONFIG)
    project_metadata = _read(PROJECT_METADATA)
    preview_script = _read(SOCIAL_PREVIEW_SCRIPT)
    assert "site-url:" in config
    assert "open-graph:" in config
    assert "locale: pt_BR" in config
    assert "twitter-card:" in config
    assert "card-style: summary_large_image" in config
    assert "image: assets/social-preview.png" in config
    assert 'image: assets/social-preview.png' in project_metadata
    assert 'output_path: str = "assets/social-preview.png"' in preview_script
    assert '<link rel="icon" href="https://github.githubassets.com/favicons/favicon.svg" type="image/svg+xml">' in config
    assert '<link rel="shortcut icon" href="https://github.githubassets.com/favicons/favicon.png" type="image/png">' in config


def test_quarto_uses_text_first_navbar_labels():
    config = _read(QUARTO_CONFIG)
    assert 'title: "BBB26"' in config
    expected_labels = [
        'text: "Painel"',
        'text: "Evolução"',
        'text: "Relações"',
        'text: "Paredão"',
        'text: "Cartola"',
        'text: "Provas"',
        'text: "Paredões"',
        'text: "Votação"',
    ]
    for label in expected_labels:
        assert label in config


def test_quarto_loads_navbar_and_page_nav_assets():
    config = _read(QUARTO_CONFIG)
    assert "assets/navbar.css" in config
    assert "assets/page-nav.css" in config
    assert "assets/page-nav.js" in config


def test_legacy_navigation_callouts_removed_from_pages():
    pages = [
        REPO_ROOT / "relacoes.qmd",
        REPO_ROOT / "evolucao.qmd",
        REPO_ROOT / "paredao.qmd",
    ]
    markers = [
        "📍 Navegação",
        ":::{.callout-tip title=\"🧭 Navegação\"}",
        '<h5>📍 Navegação</h5>',
    ]
    for page in pages:
        content = _read(page)
        for marker in markers:
            assert marker not in content


def test_shared_social_preview_exists():
    assert (REPO_ROOT / "assets" / "social-preview.png").exists()
    assert not (REPO_ROOT / "assets" / "social-preview.jpg").exists()


def test_accessibility_files_removed():
    assert not (REPO_ROOT / "assets" / "accessibility.css").exists()
    assert not (REPO_ROOT / "assets" / "accessibility.js").exists()


def test_navbar_collapse_rules_are_mobile_only():
    css = _read(REPO_ROOT / "assets" / "navbar.css")
    marker = "@media (max-width: 991.98px)"
    assert marker in css
    before_mobile_block = css.split(marker, 1)[0]
    assert ".navbar.navbar-expand-lg .navbar-collapse {\n  display: none !important;" not in before_mobile_block
