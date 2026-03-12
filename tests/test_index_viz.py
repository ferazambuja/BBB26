from __future__ import annotations

import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from data_utils import GROUP_COLORS, REACTION_EMOJI, setup_bbb_dark_theme
from index_viz import (
    make_cross_table_heatmap,
    make_cross_table_html,
    make_reaction_summary_html,
    make_sentiment_ranking,
)


@pytest.fixture(autouse=True)
def _setup_theme() -> None:
    setup_bbb_dark_theme()


def test_make_sentiment_ranking_builds_expected_bar_chart():
    rows = [
        {"name": "Ana", "score": 1.5, "group": "Camarote", "hearts": 5, "negative": 1},
        {"name": "Babu Santana", "score": -0.5, "group": "Pipoca", "hearts": 1, "negative": 3},
    ]

    fig = make_sentiment_ranking(rows, title_suffix="Semana 8", fixed_height=640)

    assert fig.data[0].type == "bar"
    assert fig.layout.title.text == "Ranking de Sentimento — Semana 8"
    assert fig.layout.height == 640
    assert len(fig.data) == 1 + len(GROUP_COLORS)
    assert list(fig.data[0].x) == [-0.5, 1.5]
    assert list(fig.data[0].text) == ["-0.5", "+1.5"]


def test_make_cross_table_heatmap_builds_heatmap_with_short_names():
    participants = [
        {"name": "Ana Paula Renault", "characteristics": {"eliminated": False}},
        {"name": "Babu Santana", "characteristics": {"eliminated": False}},
    ]
    matrix = {
        ("Ana Paula Renault", "Babu Santana"): "Coração",
        ("Babu Santana", "Ana Paula Renault"): "Cobra",
    }

    fig = make_cross_table_heatmap(participants, matrix, title_suffix="Semana 8")

    assert fig.data[0].type == "heatmap"
    assert fig.layout.title.text == "Mapa de Reações — Semana 8"
    assert list(fig.data[0].x) == ["Ana", "Babu Santana"]
    assert list(fig.data[0].y) == ["Ana", "Babu Santana"]
    assert fig.data[0].text[0][1] == REACTION_EMOJI["Coração"]
    assert fig.data[0].text[1][0] == REACTION_EMOJI["Cobra"]


def test_make_cross_table_html_renders_table_markup_and_cell_styles():
    cross_data = {
        "names": ["Ana Paula Renault", "Babu Santana"],
        "matrix": [
            ["", "Coração"],
            ["Cobra", ""],
        ],
    }

    html = make_cross_table_html(cross_data, title_suffix="Semana 8")

    assert 'class="index-cross-table scroll-x"' in html
    assert '<table class="index-cross-table__table">' in html
    assert "<style>" not in html
    assert "Ana Paula Renault → Babu Santana: Coração" in html
    assert "Babu Santana → Ana Paula Renault: Cobra" in html
    assert REACTION_EMOJI["Coração"] in html
    assert REACTION_EMOJI["Cobra"] in html
    assert "background: #1a9850; color: #fff;" in html
    assert "background: #d73027; color: #fff;" in html


def test_make_reaction_summary_html_renders_toggle_and_score_formatting():
    summary_data = {
        "rows": [
            {
                "name": "Ana",
                "hearts": 4,
                "planta": 0,
                "mala": 0,
                "biscoito": 0,
                "cobra": 0,
                "alvo": 1,
                "vomito": 0,
                "mentiroso": 0,
                "coracao_partido": 0,
                "score": 11.0,
            },
            {
                "name": "Babu Santana",
                "hearts": 1,
                "planta": 0,
                "mala": 0,
                "biscoito": 0,
                "cobra": 3,
                "alvo": 0,
                "vomito": 0,
                "mentiroso": 0,
                "coracao_partido": 0,
                "score": -6.0,
            },
        ],
        "max_hearts": 4,
        "max_neg": 3,
    }

    html = make_reaction_summary_html(summary_data, collapsed_rows=1)

    assert 'class="index-reaction-summary"' in html
    assert 'class="index-reaction-summary__table"' in html
    assert 'class="index-reaction-summary__row--collapsed"' in html
    assert 'class="index-reaction-summary__toggle"' in html
    assert "<style>" not in html
    assert 'id="reaction-summary-table"' not in html
    assert "closest('.index-reaction-summary')" in html
    assert "querySelectorAll('.index-reaction-summary__row--collapsed')" in html
    assert "▼ Ver todos os 2 participantes" in html
    assert "background: #1a9850; color: #fff; font-weight: bold;" in html
    assert "background: #d73027; color: #fff; font-weight: bold;" in html
    assert "+11.0" in html
    assert "-6.0" in html
