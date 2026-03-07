"""Regression checks for global Quarto UI config."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
QUARTO_CONFIG = REPO_ROOT / "_quarto.yml"


def _read_quarto_config() -> str:
    return QUARTO_CONFIG.read_text(encoding="utf-8")


def test_quarto_disables_global_search_in_navbar():
    config = _read_quarto_config()
    assert "\n  search: false\n" in config


def test_quarto_does_not_load_nesta_pagina_assets():
    config = _read_quarto_config()
    assert "assets/toc-offcanvas.css" not in config
    assert "assets/toc-offcanvas.js" not in config


def test_quarto_does_not_show_topbar_create_issue_action():
    config = _read_quarto_config()
    assert "repo-actions:" not in config


def test_index_list_cards_do_not_use_external_plus_n_more_links():
    index_qmd = (REPO_ROOT / "index.qmd").read_text(encoding="utf-8")
    assert '+{extra} mais ↗' not in index_qmd


def test_index_relative_dates_are_anchored_to_generated_date_not_latest_snapshot():
    index_qmd = (REPO_ROOT / "index.qmd").read_text(encoding="utf-8")
    assert "DATA_GENERATED_DATE_BRT" in index_qmd
    assert "delta = (_anchor_brt - d0).days" in index_qmd
