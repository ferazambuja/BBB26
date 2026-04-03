from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_QMD = REPO_ROOT / "index.qmd"
COLLAPSE_UI_JS = REPO_ROOT / "assets" / "collapse-ui.js"


def _python_blocks() -> list[list[str]]:
    blocks: list[list[str]] = []
    in_python = False
    current: list[str] = []
    for line in INDEX_QMD.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("```{python"):
            in_python = True
            current = []
            continue
        if stripped == "```" and in_python:
            in_python = False
            blocks.append(current)
            current = []
            continue
        if in_python:
            current.append(line)
    return blocks


def _function_names() -> set[str]:
    names: set[str] = set()
    for block in _python_blocks():
        code = "\n".join(line for line in block if not line.strip().startswith("#|"))
        try:
            tree = ast.parse(code)
        except SyntaxError:
            continue
        names.update(node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
    return names


def test_index_qmd_imports_extracted_index_viz_helpers():
    content = INDEX_QMD.read_text(encoding="utf-8")

    assert "from index_viz import (" in content
    assert "make_cross_table_html" in content
    assert "make_reaction_summary_html" in content
    assert "fmt_date_br" in content
    assert "card_header" in content
    assert "stat_chip" in content
    assert "plant_color" in content
    assert "render_status_chip" in content
    assert "_av" in content
    assert "_av_group_border" in content
    assert "_pair_story_card" in content
    assert "_render_actor_avatars" in content
    assert "_make_event_chips" in content
    assert "_render_avatar_row" in content
    assert "days_ago_str" in content
    assert "render_overflow_toggle as _render_overflow_toggle" in content
    assert "render_dramatic_event_row" in content
    assert "render_viradas_card" in content
    assert "render_ranked_lane as _render_ranked_lane" in content
    assert "render_toggle_pair_lane as _render_toggle_pair_lane" in content
    assert "render_break_row as _render_break_row" in content
    assert "render_blindado_row as _render_blindado_row" in content
    assert "render_na_mira_row as _render_na_mira_row" in content
    assert "render_agressor_row as _render_agressor_row" in content
    assert "render_vx_row as _render_vx_row" in content
    assert "render_profile_sinc_row" in content
    assert "build_rxn_detail_html" in content
    assert "render_pulse_row" in content
    assert "render_pair_chip" in content
    assert "render_pulso_card" in content
    assert "render_saldo_card" in content


def test_index_qmd_uses_cycle_wording_in_context_chip():
    content = INDEX_QMD.read_text(encoding="utf-8")

    assert 'ctx_cycle = ctx.get("cycle", "?")' in content
    assert 'Ciclo do Paredão {ctx_cycle}' in content
    assert 'Semana {ctx_week}' not in content


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
    assert "def _render_profile_sinc_chip(" not in content
    assert "def _render_profile_row(" not in content
    assert "def build_rxn_detail_html(" not in content
    assert "def _pulse_row(" not in content
    assert "def _pair_chip(" not in content
    assert "saldo_profiles = sorted(" not in content
    assert 'max_bal = max(abs(p.get("balance", 0)) for p in saldo_profiles)' not in content


def test_index_qmd_batch_a_helpers_are_no_longer_defined_inline():
    names = _function_names()

    assert "_toggle" not in names
    assert "_event_row" not in names


def test_index_qmd_batch_b_helpers_are_no_longer_defined_inline():
    names = _function_names()

    assert "_rank_chip" not in names
    assert "_render_ranked_lane" not in names
    assert "_render_pair_lane" not in names
    assert "_render_toggle_pair_lane" not in names


def test_index_qmd_batch_c_helpers_are_no_longer_defined_inline():
    names = _function_names()

    assert "_render_alvo_rows" not in names
    assert "_break_row" not in names
    assert "_blindado_row" not in names
    assert "_visado_row" not in names
    assert "_render_vx_row" not in names


def test_index_qmd_no_longer_uses_local_lambda_glue_for_sincerao_lanes():
    content = INDEX_QMD.read_text(encoding="utf-8")

    assert "_rank_avatar_html = lambda" not in content
    assert "_rank_chip = lambda" not in content


def test_index_qmd_uses_grouped_sincerao_negative_lanes_when_available():
    content = INDEX_QMD.read_text(encoding="utf-8")

    assert 'radar.get("neg_lanes", [])' in content


def test_index_qmd_marks_sincerao_card_for_scoped_sync_behavior():
    content = INDEX_QMD.read_text(encoding="utf-8")

    assert 'data-sinc-sync-card' in content


def test_index_qmd_routes_pair_change_surface_through_viradas_card():
    content = INDEX_QMD.read_text(encoding="utf-8")

    assert 'elif ctype == "viradas":' in content
    assert "render_viradas_card" in content
    assert 'elif ctype in ("dramatic", "hostilities"):' not in content
    assert 'elif ctype == "breaks":' not in content


def test_index_qmd_story_order_keeps_arquivo_do_queridometro_before_viradas():
    content = INDEX_QMD.read_text(encoding="utf-8")

    assert '"changes": 20' in content
    assert '"viradas": 30' in content


def test_collapse_ui_supports_scoped_sincerao_toggle_sync():
    content = COLLAPSE_UI_JS.read_text(encoding="utf-8")

    assert 'data-sinc-sync-card' in content
    assert 'data-sinc-sync-toggle="chooser"' in content
    assert '.sinc-more:not([open])' in content


def test_collapse_ui_no_longer_ships_literal_fence_cleanup_workaround():
    content = COLLAPSE_UI_JS.read_text(encoding="utf-8")

    assert 'trim() === ":::"' not in content
