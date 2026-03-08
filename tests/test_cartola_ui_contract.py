"""Regression checks for Cartola UI/UX structure and asset wiring."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
QUARTO_CONFIG = REPO_ROOT / "_quarto.yml"
CARTOLA_QMD = REPO_ROOT / "cartola.qmd"
CARTOLA_CSS = REPO_ROOT / "assets" / "cartola.css"
CARTOLA_JS = REPO_ROOT / "assets" / "cartola-ui.js"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_quarto_loads_cartola_assets():
    config = _read(QUARTO_CONFIG)
    assert "assets/cartola.css" in config
    assert "assets/cartola-ui.js" in config


def test_cartola_has_scannable_section_shell_and_quick_jump():
    content = _read(CARTOLA_QMD)
    assert 'class="cartola-page"' in content
    assert 'id="cartola-quick-jump"' in content
    assert 'href="#ranking"' not in content
    assert 'href="#participantes"' in content
    assert 'href="#semanas"' in content
    assert 'href="#pontos"' in content


def test_cartola_has_mobile_progressive_disclosure_hooks():
    content = _read(CARTOLA_QMD)
    assert "cartola-ranking-more" not in content
    assert "cartola-week-more" in content
    assert 'class="collapse-toggle"' in content


def test_cartola_has_evolution_chart_modes():
    content = _read(CARTOLA_QMD)
    assert "Top 8" in content
    assert "Apenas Ativos" in content
    assert "Todos" in content


def test_cartola_hides_internal_data_source_copy():
    content = _read(CARTOLA_QMD)
    assert "baseada em eventos da API" not in content
    assert "registros manuais auditáveis" not in content
    assert "<code>data/manual_events.json</code>" not in content
    assert "`data/manual_events.json`" not in content
    assert "(API)" not in content


def test_cartola_hero_highlights_section_removed():
    content = _read(CARTOLA_QMD)
    assert "Destaques Cartola" not in content
    assert "Resumo dos últimos eventos" not in content
    assert "week_event_feed = []" not in content
    assert "Últimos lançamentos da semana" not in content


def test_cartola_copy_has_no_daily_or_events_summary_wording():
    content = _read(CARTOLA_QMD)
    assert "Panorama diário da disputa" not in content
    assert "últimos eventos" not in content.lower()


def test_cartola_eliminated_avatar_is_grayscale():
    content = _read(CARTOLA_QMD)
    css = _read(CARTOLA_CSS)
    assert 'data-player-state="inactive"' in content
    assert ".cartola-player-card[data-player-state=\"inactive\"] .cartola-player-main-avatar" in css
    assert "grayscale(1)" in css


def test_cartola_week_kpi_has_no_sem_prefix_literal():
    content = _read(CARTOLA_QMD)
    assert "Sem {n_weeks}" not in content
    assert ">{current_cycle_week}<" in content


def test_cartola_role_kpis_count_events_dynamically():
    content = _read(CARTOLA_QMD)
    assert "leader_events_count = sum(1 for p in leaderboard for evt in p.get('events', []) if evt.get('event') == 'lider')" in content
    assert "anjo_events_count = sum(1 for p in leaderboard for evt in p.get('events', []) if evt.get('event') == 'anjo')" in content
    assert "monstro_events_count = sum(1 for p in leaderboard for evt in p.get('events', []) if evt.get('event') == 'monstro')" in content
    assert "seen_roles.get('Líder'" not in content


def test_cartola_role_points_use_constants_not_literals():
    content = _read(CARTOLA_QMD)
    assert "CARTOLA_POINTS.get('lider', 80)" not in content
    assert "CARTOLA_POINTS.get('anjo', 45)" not in content
    assert "CARTOLA_POINTS.get('monstro', -10)" not in content
    assert "CARTOLA_POINTS.get('emparedado', -15)" not in content
    assert 'imune_points = CARTOLA_POINTS[\'imunizado\']' in content
    assert 'points-pos">+80' not in content
    assert 'points-pos">+45' not in content
    assert 'points-pos">+30' not in content
    assert 'points-neg">-10' not in content


def test_cartola_has_top5_extremes_cards_with_ranked_rows():
    content = _read(CARTOLA_QMD)
    css = _read(CARTOLA_CSS)
    assert 'class="cartola-extremes-grid"' in content
    assert "cartola-extreme-positive" in content
    assert "cartola-extreme-negative" in content
    assert "cartola-extreme-list" in content
    assert "cartola-extreme-row" in content
    assert "TOP 5" in content
    assert ".cartola-extremes-grid" in css
    assert ".cartola-extreme-list" in css
    assert ".cartola-extreme-row" in css


def test_cartola_top5_extremes_are_computed_from_events_dynamically():
    content = _read(CARTOLA_QMD)
    assert "week_positive_points_by_participant" in content
    assert "week_negative_points_by_participant" in content
    assert "all_time_positive_points_by_participant" in content
    assert "all_time_negative_points_by_participant" in content
    assert "include_inactive=False" in content
    assert "include_inactive=True" in content
    assert "week_positive_top5 = sorted(" in content
    assert "week_negative_top5 = sorted(" in content
    assert "all_time_positive_top5 = sorted(" in content
    assert "all_time_negative_top5 = sorted(" in content
    assert "[:5]" in content
    assert "positive_breakdown = defaultdict(lambda: {'points': 0, 'count': 0})" in content
    assert "negative_breakdown = defaultdict(lambda: {'points': 0, 'count': 0})" in content
    assert "positive_breakdown[evt_type]['points'] += points" in content
    assert "negative_breakdown[evt_type]['points'] += points" in content
    assert "events = [evt for evt in events if evt.get('week') == week_filter]" in content
    assert "build_extreme_candidates(current_cycle_week, include_inactive=False)" in content
    assert "build_extreme_candidates(include_inactive=True)" in content
    assert "Semana {current_cycle_week}" in content
    assert "temporada" in content.lower()


def test_cartola_extremes_no_longer_use_single_winner_logic():
    content = _read(CARTOLA_QMD)
    assert "top_week_positive = max(" not in content
    assert "top_week_negative = min(" not in content
    assert "top_all_time_positive = max(" not in content
    assert "top_all_time_negative = min(" not in content


def test_cartola_top5_extremes_handle_inactive_and_weekly_gaps():
    content = _read(CARTOLA_QMD)
    css = _read(CARTOLA_CSS)
    assert "status_by_participant" in content
    assert "is-inactive" in content
    assert "Nenhum participante com saldo positivo na semana" in content
    assert "Ainda não houve lançamentos negativos nesta semana" in content
    assert "inclui participantes ativos e eliminados" in content
    assert ".cartola-extreme-row.is-inactive .cartola-extreme-row-avatar" in css


def test_cartola_top5_rows_show_reason_on_hover_and_tap():
    content = _read(CARTOLA_QMD)
    css = _read(CARTOLA_CSS)
    assert "title=\"{reason_summary}\"" in content
    assert 'details class="card-reason"' in content
    assert "card-reason-toggle" in content
    assert "POINTS_LABELS.get(reason['event'], reason['event'])" in content
    assert ".card-reason" in css or ".cartola-extreme-row-reason" in css
    assert ".card-reason-toggle" in css or ".cartola-extreme-row-reason-toggle" in css


def test_cartola_uses_manual_open_week_as_cycle_reference():
    content = _read(CARTOLA_QMD)
    assert "manual_open_weeks = sorted(" in content
    assert "current_cycle_week = manual_open_weeks[-1] if manual_open_weeks else n_weeks" in content
    assert "is_transition_cycle = current_cycle_week != n_weeks" in content
    assert "max_week_for_display = current_cycle_week if is_transition_cycle else n_weeks" in content


def test_cartola_ranking_section_removed_in_favor_of_participant_cards():
    content = _read(CARTOLA_QMD)
    js = _read(CARTOLA_JS)
    assert "# Ranking Cartola {#ranking}" not in content
    assert "leaderboard-cards" not in content
    assert "data-player-jump" not in content
    assert "bindPlayerJumpHandlers" not in js


def test_cartola_quick_navigator_panel_removed():
    content = _read(CARTOLA_QMD)
    assert "## Participantes {#participantes}" in content
    assert 'class="cartola-player-impact-panel"' not in content
    assert "cartola-player-impact-row" not in content
    assert "ranked_all_players_for_jump" in content
    assert "max_abs_score_for_jump" not in content


def test_cartola_participant_cards_expose_full_breakdown_and_mobile_friendly_layout():
    content = _read(CARTOLA_QMD)
    css = _read(CARTOLA_CSS)
    assert 'class="cartola-player-card"' in content
    assert "cartola-player-week-grid" in content
    assert "cartola-player-event-stack" in content
    assert ".cartola-player-impact-panel" not in css
    assert ".cartola-player-impact-row" not in css
    assert ".cartola-player-card" in css
    assert ".cartola-player-card-focus" not in css
    assert ".cartola-player-week-grid" in css
