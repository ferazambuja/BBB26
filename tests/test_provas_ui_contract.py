"""Regression checks for Provas UI/UX structure after Cartola-aligned overhaul."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
QUARTO_CONFIG = REPO_ROOT / "_quarto.yml"
PROVAS_QMD = REPO_ROOT / "provas.qmd"
PROVAS_CSS = REPO_ROOT / "assets" / "provas.css"
PROVAS_JS = REPO_ROOT / "assets" / "provas-ui.js"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_quarto_loads_provas_assets():
    config = _read(QUARTO_CONFIG)
    assert "assets/provas.css" in config
    assert "assets/provas-ui.js" in config


def test_provas_has_scannable_shell_and_quick_nav():
    content = _read(PROVAS_QMD)
    assert 'class="provas-page"' in content
    assert 'id="provas-page"' in content
    assert 'id="provas-quick-jump"' in content
    assert 'href="#participantes"' in content
    assert 'href="#provas"' in content
    assert 'href="#pontuacao"' in content


def test_provas_removes_legacy_destaques_and_tabset():
    content = _read(PROVAS_QMD)
    assert "Destaques — Provas" not in content
    assert "::: {.panel-tabset}" not in content
    assert "mobile-pruned-table" not in content
    assert "Mobile compacto: mostrando" not in content


def test_provas_has_top5_trajectory_and_quality_cards():
    content = _read(PROVAS_QMD)
    css = _read(PROVAS_CSS)
    assert 'class="provas-top5-grid"' in content
    assert "TOP 5 PONTUAÇÃO ACUMULADA" in content
    assert "TOP 5 MENOR PONTUAÇÃO ACUMULADA" in content
    assert "TOP 5 MELHOR MÉDIA" in content
    assert "TOP 5 MELHOR TAXA DE PÓDIO" in content
    assert ".provas-top5-grid" in css
    assert ".provas-top5-card" in css
    assert ".provas-top5-row" in css


def test_provas_quality_top5_use_minimum_participation_threshold():
    content = _read(PROVAS_QMD)
    assert "provas_participated >= 6" in content
    assert "top3_rate" in content


def test_provas_lowest_accumulated_card_filters_to_active():
    content = _read(PROVAS_QMD)
    assert "lowest_total_active" in content
    assert "if is_active(p['name'])" in content


def test_provas_has_objective_curiosities_block():
    content = _read(PROVAS_QMD)
    css = _read(PROVAS_CSS)
    assert 'class="provas-curiosities-grid"' in content
    assert "Especialista em Prova do Líder" in content
    assert "Especialista em Prova do Anjo" in content
    assert "Destaque em Bate e Volta" in content
    assert "Maior consistência" in content
    assert ".provas-curiosities-grid" in css


def test_provas_participant_cards_are_primary_surface():
    content = _read(PROVAS_QMD)
    css = _read(PROVAS_CSS)
    assert "## Participantes {#participantes}" in content
    assert 'class="provas-player-cards-grid"' in content
    assert 'class="provas-player-card"' in content
    assert "# Classificação Geral {#ranking}" not in content
    assert ".provas-player-cards-grid" in css
    assert ".provas-player-card" in css


def test_provas_accordion_history_replaces_tabset():
    content = _read(PROVAS_QMD)
    css = _read(PROVAS_CSS)
    assert "## Provas {#provas}" in content
    assert 'class="provas-history-accordion"' in content
    assert 'class="provas-prova-details"' in content
    assert ".provas-history-accordion" in css
    assert ".provas-prova-details" in css


def test_provas_hides_internal_data_source_copy():
    content = _read(PROVAS_QMD)
    assert "`data/provas.json`" not in content
    assert "`data/derived/prova_rankings.json`" not in content
    assert "build_derived_data.py" not in content


def test_provas_ui_js_has_mobile_collapse_and_page_guard():
    js = _read(PROVAS_JS)
    assert "#provas-page" in js
    assert "provas-collapse-toggle" in js
    assert "provas-mobile-collapsed" in js

