from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_QMD = REPO_ROOT / "index.qmd"


def test_index_qmd_imports_extracted_index_viz_helpers():
    content = INDEX_QMD.read_text(encoding="utf-8")

    assert "from index_viz import (" in content
    assert "make_sentiment_ranking" in content
    assert "make_cross_table_heatmap" in content
    assert "make_cross_table_html" in content
    assert "make_reaction_summary_html" in content
    assert "fmt_date_br" in content
    assert "card_header" in content
    assert "stat_chip" in content
    assert "progress_bar" in content
    assert "plant_color" in content
    assert "render_status_chip" in content
    assert "render_mobile_queridometro_summary" in content
    assert "render_mobile_evolution_summary" in content
    assert "_av" in content
    assert "_av_group_border" in content
    assert "_pair_story_card" in content
    assert "_render_actor_avatars" in content
    assert "_make_event_chips" in content
    assert "_render_avatar_row" in content
    assert "days_ago_str" in content
    assert "make_evolution_chart" in content


def test_index_qmd_no_longer_defines_first_extracted_helpers_inline():
    content = INDEX_QMD.read_text(encoding="utf-8")

    assert "def make_sentiment_ranking(" not in content
    assert "def make_cross_table_heatmap(" not in content
    assert "def make_cross_table_html(" not in content
    assert "def make_reaction_summary_html(" not in content
    assert "def get_cell_style(" not in content
    assert "def fmt_date_br(" not in content
    assert "def card_header(" not in content
    assert "def stat_chip(" not in content
    assert "def progress_bar(" not in content
    assert "def plant_color(" not in content
    assert "def render_status_chip(" not in content
    assert "def _short_name(" not in content
    assert "def _fmt_signed(" not in content
    assert "def _render_list(" not in content
    assert "def render_mobile_queridometro_summary(" not in content
    assert "def _recent_swings(" not in content
    assert "def render_mobile_evolution_summary(" not in content
    assert "def av(" not in content
    assert "def av_group_border(" not in content
    assert "def pair_story_card(" not in content
    assert "def render_actor_avatars(" not in content
    assert "def make_event_chips(" not in content
    assert "def render_avatar_row(" not in content
    assert "def days_ago_str(" not in content
    assert "def make_evolution_chart(" not in content
