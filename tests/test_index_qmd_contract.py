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


def test_index_qmd_no_longer_defines_first_extracted_helpers_inline():
    content = INDEX_QMD.read_text(encoding="utf-8")

    assert "def make_sentiment_ranking(" not in content
    assert "def make_cross_table_heatmap(" not in content
    assert "def make_cross_table_html(" not in content
    assert "def make_reaction_summary_html(" not in content
    assert "def get_cell_style(" not in content
