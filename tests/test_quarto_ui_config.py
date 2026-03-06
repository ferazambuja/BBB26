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
