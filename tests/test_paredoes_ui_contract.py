"""Regression checks for the week-8 spotlight on paredoes.qmd."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PAREDOES_QMD = REPO_ROOT / "paredoes.qmd"
PAREDAO_QMD = REPO_ROOT / "paredao.qmd"
INDEX_QMD = REPO_ROOT / "index.qmd"
INDEX_VIZ = REPO_ROOT / "scripts" / "index_viz.py"
PAREDAO_VIZ = REPO_ROOT / "scripts" / "paredao_viz.py"
CARDS_CSS = REPO_ROOT / "assets" / "cards.css"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_paredoes_has_milena_spotlight_render_hook():
    content = _read(PAREDOES_QMD)
    helper = _read(PAREDAO_VIZ)
    assert 'featured_story = _pa_entry.get("featured_story")' in content
    assert "render_featured_story" in content
    assert 'class="paredao-spotlight"' in helper
    assert "Voto Único" in helper
    assert "Motivo salvo" not in helper
    assert "Queridômetro no domingo da formação" in helper
    assert "🔒 Queridômetro secreto" in helper
    assert "Quando o poder caiu na mão deles" in helper
    assert "🎯 No Sincerão e nos ataques diretos" in helper
    assert "↩️ Quando Milena devolveu" in helper
    assert "paredao-spotlight-summary-list" in helper
    assert "private_signal_note" in helper
    assert 'story.get("caveat"' in helper
    assert "Agora:" not in helper
    assert "Emoji mais constante" not in helper
    assert "No fechamento desse recorte" not in helper


def test_paredao_live_page_has_milena_spotlight_render_hook():
    content = _read(PAREDAO_QMD)
    assert 'featured_story = pa_entry.get("featured_story")' in content
    assert "render_featured_story" in content


def test_live_and_index_pages_use_shared_paredao_card_renderers():
    live = _read(PAREDAO_QMD)
    index = _read(INDEX_QMD)
    helper = _read(PAREDAO_VIZ)

    assert "build_paredao_card_payload" in helper
    assert "build_poll_comparison_payload" in helper
    assert "render_paredao_live_card" in helper
    assert "render_paredao_index_card" in helper
    assert "render_poll_comparison_card" in helper
    assert "render_paredao_live_card" in live
    assert "render_poll_comparison_card" in live
    assert "render_paredao_index_card" in index
    assert "build_paredao_card_payload" in index
    assert "build_paredao_history" in index
    assert "load_votalhada_polls" in index
    assert "get_poll_for_paredao" in index
    assert "nosso-modelo-back-test" in helper
    assert "teste retrospectivo" in helper


def test_live_page_shows_history_after_prediction_without_details_collapse():
    live = _read(PAREDAO_QMD)
    assert "<details class=\"paredao-history-box\"" not in live
    assert "📋 Histórico em paredões anteriores" in live


def test_index_keeps_restored_highlight_layout_hooks():
    index = _read(INDEX_QMD)
    helper = _read(INDEX_VIZ)
    css = _read(CARDS_CSS)

    assert 'movers_label = card.get("movers_label", "📅 Variação vs ontem")' in index
    assert "Mudanças Dramáticas (Recente)" not in index
    assert "dashboard-card-header" in helper
    assert "dashboard-card-header" in css
    assert "pair-story-card" in helper
    assert "pair-story-card" in css
    assert "ranking-column" not in index
    assert ".ranking-column" not in css
    assert 'av(name, 42, "#27ae60")' in index
    assert 'av(name, 42, "#e74c3c")' in index
    assert "blindado-tag-list" not in index
    assert "render_blindado_tag" not in index
    assert "background:#1b3f5c;color:#9dd3ff;" in helper
    assert "background:#123b2a;color:#8fe3b8;" in helper
    assert "background:#2d1b3f;color:#d9b3ff;" in helper
    assert "blindado-tag" not in css
    assert 'protection_tags = item.get("protection_tags") or []' in helper
    assert "tag.get('text', '')" in helper
    assert 'podium_positive = [p for p in podium_all if p["score"] > 0]' in index
    assert "highlight-card-span-3" in index
    assert ".highlight-card-span-3" in css
    assert "width: 100%" in css
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in css
    assert "@media (max-width: 1100px)" in css
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in css


def test_index_places_paredao_before_ranking_in_highlight_order():
    index = _read(INDEX_QMD)

    assert '"paredao": 5' in index
    assert '"ranking": 10' in index


def test_backtest_explanation_uses_portuguese_label_with_stable_anchor():
    archive = _read(PAREDOES_QMD)
    helper = _read(PAREDAO_VIZ)

    assert "## 🧮 Nosso Modelo — Teste retrospectivo {#nosso-modelo-back-test}" in archive
    assert "Ver teste retrospectivo" in helper


def test_paredoes_spotlight_has_mobile_first_styles():
    css = _read(CARDS_CSS)
    assert ".paredao-spotlight" in css
    assert ".paredao-spotlight-grid" in css
    assert "@media (max-width: 768px)" in css
    assert ".paredao-live-card" in css
    assert ".paredao-index-card" in css


def test_paredao_pages_define_scoped_typography_layer():
    live = _read(PAREDAO_QMD)
    archive = _read(PAREDOES_QMD)
    css = _read(CARDS_CSS)

    assert "body-classes: paredao-page" in live
    assert "body-classes: paredao-page" in archive
    assert "body.paredao-page #title-block-header .title" in css
    assert "body.paredao-page #title-block-header .subtitle" in css
    assert "body.paredao-page main.content h2" in css
    assert "body.paredao-page .paredao-spotlight-section-title" in css
    assert "body.paredao-page .paredao-spotlight-note" in css
    assert "body.paredao-page .nav-tabs .nav-link" in css
    assert "body.paredao-page .paredao-history-summary" in css


def test_paredoes_has_nunca_paredao_anchor():
    content = _read(PAREDOES_QMD)
    assert "### Nunca foi ao Paredão {#nunca-paredao}" in content


def test_paredoes_has_figurinha_repetida_anchor():
    content = _read(PAREDOES_QMD)
    assert "### Figurinha Repetida {#figurinha-repetida}" in content


def test_paredoes_imports_load_index_data():
    content = _read(PAREDOES_QMD)
    assert "load_index_data" in content


def test_index_has_nunca_paredao_card_branch():
    content = _read(INDEX_QMD)
    assert '"nunca_paredao"' in content
    assert "nunca_paredao" in content


def test_index_has_figurinha_repetida_card_branch():
    content = _read(INDEX_QMD)
    assert '"figurinha_repetida"' in content
    assert "figurinha_repetida" in content


def test_index_card_story_order_includes_new_cards():
    content = _read(INDEX_QMD)
    assert '"nunca_paredao": 87' in content
    assert '"figurinha_repetida": 88' in content


def test_paredoes_tabs_include_current_open_week():
    content = _read(PAREDOES_QMD)
    assert "paredoes_visiveis = [p for p in paredoes if p.get('status') in ('finalizado', 'em_andamento')]" in content
    assert "for i, paredao in enumerate(reversed(paredoes_visiveis))" in content


def test_paredao_and_archive_pages_have_votalhada_formula_change_disclaimer_hooks():
    live = _read(PAREDAO_QMD)
    archive = _read(PAREDOES_QMD)

    assert 'poll.get("metodologia", {}).get("disclaimer_publico")' in live
    assert "0,3 x 0,7" in live
    assert "fórmula anterior" in live
    assert "10 de março de 2026" in archive
    assert "0,3 x 0,7" in archive
    assert "fórmula anterior" in archive


def test_platform_tables_avoid_flex_utility_row_classes():
    live = _read(PAREDAO_QMD)
    archive = _read(PAREDOES_QMD)

    assert '<tr class="u-s049"' not in live
    assert '<tr class="u-s048"' not in live
    assert '<tr class="u-s049"' not in archive
    assert '<tr class="u-s048"' not in archive


def test_platform_precision_table_has_mobile_scroll_wrapper():
    archive = _read(PAREDOES_QMD)
    css = _read(CARDS_CSS)

    assert "poll-precision-table" in archive
    assert "poll-precision-table-wrap" in archive
    assert ".poll-precision-table-wrap" in css
    assert ".poll-precision-table" in css


def test_elimination_summary_uses_fixed_columns_without_dynamic_nan_paths():
    archive = _read(PAREDOES_QMD)
    css = _read(CARDS_CSS)

    assert "'Eliminado(a)'" in archive
    assert "'→ Q. Secreto'" not in archive
    assert "'Grupo':" not in archive
    assert "_col_label" not in archive
    assert "poll-elim-summary-wrap" in archive
    assert "poll-elim-summary" in archive
    assert ".poll-elim-summary-wrap" in css
    assert ".poll-elim-summary" in css
