from __future__ import annotations

import sys
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import index_viz
from data_utils import GROUP_COLORS, REACTION_EMOJI, setup_bbb_dark_theme
from index_viz import (
    _fmt_signed,
    _recent_swings,
    _short_name,
    _render_list,
    av,
    av_group_border,
    card_header,
    days_ago_str,
    fmt_date_br,
    make_evolution_chart,
    make_cross_table_heatmap,
    make_cross_table_html,
    make_event_chips,
    make_reaction_summary_html,
    make_sentiment_ranking,
    pair_story_card,
    plant_color,
    progress_bar,
    render_actor_avatars,
    render_avatar_row,
    render_dramatic_event_row,
    render_mobile_evolution_summary,
    render_mobile_queridometro_summary,
    render_overflow_toggle,
    render_pair_lane,
    render_pair_chip,
    render_profile_sinc_row,
    render_pulse_row,
    render_rank_chip,
    render_ranked_lane,
    render_saldo_card,
    render_status_chip,
    stat_chip,
    render_toggle_pair_lane,
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


def test_fmt_date_br_formats_valid_dates_and_preserves_invalid_input():
    assert fmt_date_br("2026-03-12") == "12/03"
    assert fmt_date_br("") == ""
    assert fmt_date_br("not-a-date") == "not-a-date"


def test_days_ago_str_uses_explicit_anchor_date_and_preserves_relative_labels():
    assert days_ago_str("2026-03-08", anchor_brt=datetime.strptime("2026-03-12", "%Y-%m-%d").date()) == "há 4 dias"
    assert days_ago_str("2026-03-12", anchor_brt=datetime.strptime("2026-03-12", "%Y-%m-%d").date()) == "hoje"
    assert days_ago_str("2026-03-11", anchor_brt=datetime.strptime("2026-03-12", "%Y-%m-%d").date()) == "há 1 dia"
    assert days_ago_str("not-a-date", anchor_brt=datetime.strptime("2026-03-12", "%Y-%m-%d").date()) == ""
    assert days_ago_str("2026-03-08T00:00:00", anchor_brt=datetime.strptime("2026-03-12", "%Y-%m-%d").date()) == "há 4 dias"


def test_short_name_fmt_signed_and_render_list_cover_basic_mobile_formatting():
    assert _short_name("Ana Paula Renault") == "Ana"
    assert _short_name("") == "?"
    assert _fmt_signed(1.25, 1) == "+1.2"
    assert _fmt_signed(-0.75, 2) == "-0.75"

    html = _render_list(
        [{"name": "Ana Paula Renault", "delta": 1.5}],
        "Sem linhas.",
        lambda row: f"{_fmt_signed(row['delta'], 1)} pts",
    )

    assert "<strong>Ana</strong>" in html
    assert "+1.5 pts" in html
    assert "Sem linhas." in _render_list([], "Sem linhas.", lambda row: "unused")


def test_card_header_renders_badge_source_link_and_subtitle():
    html = card_header(
        "🗳️",
        "Paredão Ativo",
        "paredao.html",
        badge="Resultado oficial",
        source_tag="🧮 Nosso Modelo",
        subtitle="Resumo do paredão encerrado.",
    )

    assert "Paredão Ativo" in html
    assert "Resultado oficial" in html
    assert "🧮 Nosso Modelo" in html
    assert 'href="paredao.html"' in html
    assert "Resumo do paredão encerrado." in html


def test_avatar_helpers_accept_explicit_page_dependencies():
    calls = []

    def fake_avatar_html(name, avatars, **kwargs):
        calls.append((name, avatars, kwargs))
        return f"<img alt='{name}' data-border='{kwargs['border_color']}'>"

    html = av(
        "Ana Paula Renault",
        avatars={"Ana Paula Renault": "https://example.com/ana.png"},
        avatar_html=fake_avatar_html,
        size=52,
        border_color="#123456",
    )

    assert "Ana Paula Renault" in html
    assert calls[0][1]["Ana Paula Renault"] == "https://example.com/ana.png"
    assert calls[0][2]["size"] == 52
    assert calls[0][2]["border_color"] == "#123456"
    assert calls[0][2]["link"] == "#perfil-ana-paula-renault"

    assert av_group_border("Ana Paula Renault", member_of={"Ana Paula Renault": "Camarote"}) == GROUP_COLORS["Camarote"]
    assert av_group_border("Desconhecido", member_of={}) == "#666"


def test_stat_chip_and_progress_bar_render_expected_markup():
    chip_html = stat_chip("5", "blindados", color="#123456")
    bar_html = progress_bar(4, 8, color="#abcdef", height=10)

    assert "blindados" in chip_html
    assert "#123456" in chip_html
    assert "width:50%" in bar_html
    assert "background:#abcdef" in bar_html
    assert "height:10px" in bar_html


def test_plant_color_thresholds_follow_expected_bands():
    assert plant_color(85) == "#2f7d46"
    assert plant_color(65) == "#6c8a3c"
    assert plant_color(45) == "#b9772a"
    assert plant_color(20) == "#a94442"


def test_render_status_chip_supports_static_and_detail_variants():
    static_html = render_status_chip("🎯", "Vulnerabilidade", "ALTA", "#a94442")
    detail_html = render_status_chip("⚡", "Contradição", "2x", "#6f42c1", "<p>Detalhe</p>")

    assert 'class="status-detail"' not in static_html
    assert "Vulnerabilidade" in static_html
    assert "ALTA" in static_html
    assert 'class="status-detail"' in detail_html
    assert "<summary" in detail_html
    assert "<p>Detalhe</p>" in detail_html


def test_pair_story_card_uses_injected_avatar_and_border_helpers():
    html = pair_story_card(
        "Ana Paula Renault",
        "Babu Santana",
        "🔥",
        "virou rivalidade",
        avatar_fn=lambda name, size=48, border_color="#555": f"<avatar {name} {border_color}>",
        group_border_fn=lambda name: "#111111" if name == "Ana Paula Renault" else "#222222",
        border_color="#abcdef",
    )

    assert "pair-story-card" in html
    assert "<avatar Ana Paula Renault #111111>" in html
    assert "<avatar Babu Santana #222222>" in html
    assert "virou rivalidade" in html
    assert "border-left:3px solid #abcdef" in html


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


def test_make_evolution_chart_builds_rank_annotations_and_paredao_markers():
    rows = [
        {"date": "2026-03-01", "name": "Ana Paula Renault", "sentiment": 1.0, "rank": 2},
        {"date": "2026-03-08", "name": "Ana Paula Renault", "sentiment": 3.0, "rank": 1},
        {"date": "2026-03-01", "name": "Babu Santana", "sentiment": 2.0, "rank": 1},
        {"date": "2026-03-08", "name": "Babu Santana", "sentiment": -1.0, "rank": 2},
    ]

    fig = make_evolution_chart(
        rows,
        "sentiment",
        title="Evolução do Queridômetro",
        y_label="Score",
        part_colors={
            "Ana Paula Renault": "#111111",
            "Babu Santana": "#222222",
        },
        paredoes_markers=[
            {"date": datetime.strptime("2026-03-08", "%Y-%m-%d"), "label": "🗳️ 8º Paredão"},
        ],
        score_fmt="+.1f",
    )

    assert fig is not None
    assert fig.layout.title.text == "Evolução do Queridômetro"
    assert len(fig.data) == 2
    assert fig.data[0].type == "scatter"
    assert any(shape.line.dash == "dash" for shape in fig.layout.shapes)
    assert any(annotation.text == "#1" for annotation in fig.layout.annotations)
    assert any(annotation.text == "🗳️ 8º Paredão" for annotation in fig.layout.annotations)


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


def test_render_saldo_card_renders_expected_markup_and_overflow():
    payload = {
        "icon": "💰",
        "title": "Saldo de Estalecas",
        "link": "evolucao.html#saldo",
        "source_tag": "📸 Dado do dia",
        "subtitle": "Ranking dos participantes com mais estalecas.",
        "display_limit": 2,
        "items_all": [
            {
                "name": "Ana Paula Renault",
                "rank_label": "🥇",
                "border_color": "#123456",
                "balance": 1500,
                "balance_color": "#1a9850",
                "bar_pct": 100,
            },
            {
                "name": "Babu Santana",
                "rank_label": "🥈",
                "border_color": "#654321",
                "balance": 300,
                "balance_color": "#66bd63",
                "bar_pct": 20,
            },
            {
                "name": "Leandro",
                "rank_label": "3º",
                "border_color": "#999999",
                "balance": -50,
                "balance_color": "#e74c3c",
                "bar_pct": 10,
            },
        ],
    }

    html = render_saldo_card(
        payload,
        avatar_fn=lambda name, size=42, border_color="#555": f"<avatar {name} {border_color}>",
    )

    assert "Saldo de Estalecas" in html
    assert 'href="evolucao.html#saldo"' in html
    assert "<avatar Ana Paula Renault #123456>" in html
    assert "<avatar Leandro #999999>" in html
    assert "1,500" in html
    assert "-50" in html
    assert "+1 restantes" in html
    assert "width:100%" in html
    assert "width:10%" in html


def test_render_saldo_card_tolerates_non_numeric_display_limit_and_bar_pct():
    payload = {
        "title": "Saldo de Estalecas",
        "display_limit": "not-a-number",
        "items_all": [
            {
                "name": "Ana Paula Renault",
                "rank_label": "🥇",
                "border_color": "#123456",
                "balance": 1500,
                "balance_color": "#1a9850",
                "bar_pct": "oops",
            },
            {
                "name": "Babu Santana",
                "rank_label": "🥈",
                "border_color": "#654321",
                "balance": 300,
                "balance_color": "#66bd63",
                "bar_pct": "35.7",
            },
        ],
    }

    html = render_saldo_card(
        payload,
        avatar_fn=lambda name, size=42, border_color="#555": f"<avatar {name} {border_color}>",
    )

    assert "Saldo de Estalecas" in html
    assert "<avatar Ana Paula Renault #123456>" in html
    assert "<avatar Babu Santana #654321>" in html
    assert "width:0%" in html
    assert "width:36%" in html
    assert "+1 restantes" not in html


def test_recent_swings_tracks_top_movers_over_recent_window():
    rows = [
        {"date": "2026-03-01", "name": "Ana", "score": 1.0},
        {"date": "2026-03-08", "name": "Ana", "score": 3.5},
        {"date": "2026-03-01", "name": "Babu Santana", "score": 2.0},
        {"date": "2026-03-08", "name": "Babu Santana", "score": -1.0},
        {"date": "2026-03-01", "name": "Milena", "score": 0.0},
        {"date": "2026-03-08", "name": "Milena", "score": 0.5},
    ]

    up_rows, down_rows, start_date, end_date = _recent_swings(rows, "score", lookback_days=7)

    assert start_date.strftime("%Y-%m-%d") == "2026-03-01"
    assert end_date.strftime("%Y-%m-%d") == "2026-03-08"
    assert up_rows[0]["name"] == "Ana"
    assert up_rows[0]["delta"] == pytest.approx(2.5)
    assert down_rows[0]["name"] == "Babu Santana"
    assert down_rows[0]["delta"] == pytest.approx(-3.0)


def test_render_mobile_queridometro_summary_surfaces_kpis_and_pressure_rows():
    today_rows = [
        {"name": "Ana Paula Renault", "score": 4.5, "hearts": 5, "negative": 1},
        {"name": "Babu Santana", "score": 0.5, "hearts": 3, "negative": 3},
        {"name": "Milena", "score": -2.5, "hearts": 0, "negative": 8},
        {"name": "Chaiany", "score": 5.0, "hearts": 8, "negative": 0},
    ]
    change_week = [
        {"name": "Ana Paula Renault", "delta": 2.1},
        {"name": "Milena", "delta": -1.8},
        {"name": "Babu Santana", "delta": -0.5},
    ]

    html = render_mobile_queridometro_summary(today_rows, change_week)

    assert 'class="ranking-mobile-summary"' in html
    assert "blindados (≥4)" in html
    assert "zona cinza" in html
    assert "alerta (≤-2)" in html
    assert "Ana" in html
    assert "Milena" in html
    assert "100% negativas" in html
    assert "ver evolução do queridômetro" in html


def test_render_mobile_queridometro_summary_coerces_invalid_numeric_values_to_zero():
    html = render_mobile_queridometro_summary(
        [{"name": "Ana Paula Renault", "score": "n/a", "hearts": "2", "negative": "x"}],
        [],
    )

    assert 'class="ranking-mobile-summary"' in html
    assert "blindados (≥4)" in html
    assert "alerta (≤-2)" in html


def test_render_mobile_evolution_summary_formats_window_and_changes():
    rows = [
        {"date": "2026-03-01", "name": "Ana Paula Renault", "score": 1.0},
        {"date": "2026-03-08", "name": "Ana Paula Renault", "score": 2.5},
        {"date": "2026-03-01", "name": "Babu Santana", "score": 1.5},
        {"date": "2026-03-08", "name": "Babu Santana", "score": -0.5},
    ]

    html = render_mobile_evolution_summary(
        rows,
        "score",
        "Queridômetro",
        "evolucao.html#sentimento",
        score_decimals=1,
    )

    assert "Queridômetro — últimos 7 dias" in html
    assert "Janela: 01/03 → 08/03" in html
    assert "Ana" in html
    assert "Babu" in html
    assert "abrir gráficos detalhados" in html


def test_actor_event_and_avatar_row_helpers_use_explicit_dependencies():
    actor_html = render_actor_avatars(
        ["Ana Paula Renault", "gshow", "dinâmica da casa"],
        avatars={"Ana Paula Renault": "https://example.com/ana.png"},
        source_icons={"gshow": "📰"},
        border_color="#123456",
        size=20,
    )
    assert "https://example.com/ana.png" in actor_html
    assert "📰" in actor_html
    assert "dinâmica da casa" not in actor_html

    chips_html = make_event_chips(
        [{"emoji": "📞", "label": "Big Fone", "actors": ["Ana Paula Renault"], "count": 2}],
        "#654321",
        render_actor_avatars_fn=lambda actors, border_color, color_lookup=None, size=24, skip_icons=None: "<actors>",
    )
    assert "2x 📞 Big Fone" in chips_html
    assert "<actors>" in chips_html
    assert "border:1px solid #654321" in chips_html

    row_html = render_avatar_row(
        [{"name": "Ana Paula Renault", "their_score": 1.5}, "Babu Santana"],
        "#abcdef",
        avatar_fn=lambda name, size=48, border_color="#555": f"<avatar {name} {border_color}>",
    )
    assert "<avatar Ana Paula Renault #abcdef>" in row_html
    assert "<avatar Babu Santana #abcdef>" in row_html
    assert "+1.5" in row_html


def test_render_avatar_row_respects_max_show_limit():
    row_html = render_avatar_row(
        [
            "Ana Paula Renault",
            "Babu Santana",
            "Milena",
        ],
        "#abcdef",
        max_show=2,
        avatar_fn=lambda name, size=48, border_color="#555": f"<avatar {name} {border_color}>",
    )

    assert "<avatar Ana Paula Renault #abcdef>" in row_html
    assert "<avatar Babu Santana #abcdef>" in row_html
    assert "<avatar Milena #abcdef>" not in row_html


def test_make_evolution_chart_accepts_iso_datetime_strings():
    rows = [
        {"date": "2026-03-01T00:00:00", "name": "Ana Paula Renault", "sentiment": 1.0, "rank": 1},
        {"date": "2026-03-08T00:00:00", "name": "Ana Paula Renault", "sentiment": 2.0, "rank": 1},
    ]

    fig = make_evolution_chart(
        rows,
        "sentiment",
        title="t",
        y_label="y",
        part_colors={"Ana Paula Renault": "#111111"},
        paredoes_markers=[],
    )

    assert fig is not None


def test_render_profile_sinc_row_keeps_week_prefix_and_overflow_details():
    interactions = [
        {"emoji": "🔥", "actor": "Ana Paula Renault", "label": "puxou"},
        {"emoji": "🎯", "actor": "Babu Santana", "label": "mirou"},
        {"emoji": "⚡", "actor": "Chaiany", "label": "contradisse"},
    ]

    html = render_profile_sinc_row(
        "Recebeu",
        interactions,
        "actor",
        2,
        week_prefix="<span class='profile-sinc-week'>S8</span>",
    )

    assert "profile-sinc-row" in html
    assert "profile-sinc-week" in html
    assert "Recebeu" in html
    assert "🔥 Ana <span class='profile-sinc-chip-text'>puxou</span>" in html
    assert "<summary>+1 desta semana</summary>" in html
    assert "⚡ Chaiany <span class='profile-sinc-chip-text'>contradisse</span>" in html


def test_build_rxn_detail_html_groups_names_by_emoji_and_renders_avatar_markup():
    detail = [
        {"emoji": "❤️", "name": "Ana Paula Renault"},
        {"emoji": "❤️", "name": "Babu Santana"},
        {"emoji": "😡", "name": "Chaiany"},
    ]

    html = index_viz.build_rxn_detail_html(
        detail,
        avatar_fn=lambda name, size=48, border_color="#555": f"<avatar {name} {size} {border_color}>",
    )

    assert "❤️ (2)" in html
    assert "😡 (1)" in html
    assert "<avatar Ana Paula Renault 36 #555>" in html
    assert "<avatar Babu Santana 36 #555>" in html
    assert "<avatar Chaiany 36 #555>" in html


def test_render_pulse_row_reuses_progress_bar_output():
    html = render_pulse_row("Melhorias", 3, "#27ae60", total_delta=6)

    assert "Melhorias" in html
    assert ">3<" in html
    assert "width:50%" in html
    assert "background:#27ae60" in html


def test_render_pair_chip_formats_mode_specific_detail_text():
    contra_html = render_pair_chip(
        {
            "ator": "Ana Paula Renault",
            "alvo": "Babu Santana",
            "tipo_label": "Protege",
            "emoji": "😡",
        },
        mode="contra",
    )
    aligned_html = render_pair_chip(
        {
            "ator": "Ana Paula Renault",
            "alvo": "Babu Santana",
            "tipo_label": "Ataca",
            "emoji": "😡",
        },
        mode="aligned",
    )

    assert 'href="#perfil-ana-paula-renault"' in contra_html
    assert 'href="#perfil-babu-santana"' in contra_html
    assert "(Protege mas dá 😡)" in contra_html
    assert "(Ataca + 😡)" in aligned_html


def test_render_overflow_toggle_renders_summary_count():
    html = render_overflow_toggle(3)

    assert html.startswith('<details class="sinc-more"')
    assert "⋯ 3" in html
    assert "</summary>" in html


def test_render_dramatic_event_row_formats_hostility_transition():
    html = render_dramatic_event_row(
        {
            "giver": "Ana Paula Renault",
            "receiver": "Babu Santana",
            "old_emoji": "❤️",
            "new_emoji": "😡",
            "date": "2026-03-08",
        },
        ref_date="2026-03-12",
        is_hostile=True,
        fmt_date_fn=fmt_date_br,
        days_ago_fn=lambda date_str, ref_date: days_ago_str(
            date_str,
            ref_date,
            anchor_brt=datetime.strptime("2026-03-12", "%Y-%m-%d").date(),
        ),
        pair_story_card_fn=lambda giver, receiver, transition_html, meta_text, border_color: (
            f"<pair giver='{giver}' receiver='{receiver}' border='{border_color}'>"
            f"{transition_html}|{meta_text}</pair>"
        ),
    )

    assert "giver='Ana Paula Renault'" in html
    assert "receiver='Babu Santana'" in html
    assert "border='#f39c12'" in html
    assert "Hostilidade unilateral" in html
    assert "08/03 (há 4 dias)" in html
    assert "❤️" in html
    assert "😡" in html


def test_render_rank_chip_renders_profile_link_avatar_and_count_badge():
    html = render_rank_chip(
        {"name": "Ana Paula Renault", "count": 3},
        "attack",
        True,
        avatar_html_fn=lambda name, border_color: f"<avatar {name} {border_color}>",
    )

    assert 'href="#perfil-ana-paula-renault"' in html
    assert "<avatar Ana Paula Renault #e67e22>" in html
    assert "Ana" in html
    assert "3x" in html
    assert 'class="sinc-person-chip attack top"' in html


def test_render_ranked_lane_wraps_overflow_rank_chips_in_details():
    ranked = [
        {"name": "Ana Paula Renault", "count": 4},
        {"name": "Babu Santana", "count": 3},
        {"name": "Milena", "count": 2},
    ]

    html = render_ranked_lane(
        "Atacados",
        "💣",
        ranked,
        "Sem ataques na semana.",
        "attack",
        inline_max=2,
        render_rank_chip_fn=lambda entry, lane_type, is_top, force_count=None: (
            f"<chip {entry['name']} {lane_type} {is_top} {force_count}>"
        ),
    )

    assert "💣 Atacados" in html
    assert "<chip Ana Paula Renault attack True None>" in html
    assert "<chip Babu Santana attack False None>" in html
    assert "<summary>+1 restantes</summary>" in html
    assert "<chip Milena attack False None>" in html


def test_render_pair_lane_and_toggle_pair_lane_wrap_pair_chips():
    pairs = [
        {"ator": "Ana Paula Renault", "alvo": "Babu Santana", "tipo_label": "Protege", "emoji": "😡"},
        {"ator": "Milena", "alvo": "Chaiany", "tipo_label": "Ataca", "emoji": "🎯"},
        {"ator": "Leandro", "alvo": "Jonas Sulzbach", "tipo_label": "Debocha", "emoji": "⚡"},
    ]

    lane_html = render_pair_lane(
        "Contradições",
        "⚡",
        pairs,
        "contra",
        inline_max=2,
        render_pair_chip_fn=lambda item, mode: f"<pairchip {item['ator']} {mode}>",
    )
    toggle_html = render_toggle_pair_lane(
        "Conflito Confirmado",
        "🎯",
        pairs,
        "aligned",
        inline_max=2,
        render_pair_chip_fn=lambda item, mode: f"<pairchip {item['ator']} {mode}>",
    )

    assert "⚡ Contradições" in lane_html
    assert "<pairchip Ana Paula Renault contra>" in lane_html
    assert "<summary>+1 restantes</summary>" in lane_html
    assert "<pairchip Leandro contra>" in lane_html
    assert 'class="sinc-toggle"' in toggle_html
    assert "🎯 Conflito Confirmado" in toggle_html
    assert "sinc-toggle-count" in toggle_html
    assert "<pairchip Ana Paula Renault aligned>" in toggle_html


def test_card_header_escapes_data_text_and_link_attributes():
    html = card_header(
        "🗳️",
        '"><script>alert(1)</script>',
        'paredao.html?x="bad"&y=<tag>',
        badge="<b>badge</b>",
        source_tag='src "quoted"',
        subtitle="sub <line>",
    )

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "&lt;b&gt;badge&lt;/b&gt;" in html
    assert "src &quot;quoted&quot;" in html
    assert "sub &lt;line&gt;" in html
    assert 'href="paredao.html?x=&quot;bad&quot;&amp;y=&lt;tag&gt;"' in html


def test_pair_story_card_escapes_names_and_meta_but_keeps_html_slots_raw():
    html = pair_story_card(
        "A<B",
        'B"Q',
        "<strong>vs</strong>",
        "meta <bad>",
        avatar_fn=lambda name, size=48, border_color="#555": f"<avatar {name}>",
        group_border_fn=lambda name: "#111111",
        border_color="#abcdef",
    )

    assert "<strong>vs</strong>" in html
    assert "meta &lt;bad&gt;" in html
    assert "A&lt;B" in html
    assert "B&quot;Q" in html
    assert "<avatar A<B>" in html


def test_event_chip_and_cross_table_escape_titles_names_and_tooltips():
    chips_html = make_event_chips(
        [{"emoji": "📞", "label": "<Big>", "actors": ['Ana "Q"'], "count": 2}],
        "#654321",
        render_actor_avatars_fn=lambda actors, border_color, color_lookup=None, size=24, skip_icons=None: "<actors>",
    )

    class _SpanParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.spans = []

        def handle_starttag(self, tag, attrs):
            if tag == "span":
                self.spans.append(dict(attrs))

    parser = _SpanParser()
    parser.feed(chips_html)
    assert parser.spans, "event chips must produce a valid <span> start tag"
    assert parser.spans[0].get("class") == "fs-md"
    assert "line-height:1.4;" in parser.spans[0].get("style", "")
    assert "Ana" in parser.spans[0].get("title", "")

    assert "<Big>" not in chips_html
    assert "&lt;Big&gt;" in chips_html
    assert "Ana &quot;Q&quot;" in chips_html
    assert "<actors>" in chips_html

    cross_html = make_cross_table_html(
        {
            "names": ['Ana "Q"', "<Babu>"],
            "matrix": [["", "Coração"], ["Cobra", ""]],
        }
    )
    assert "<Babu>" not in cross_html
    assert "&lt;Babu&gt;" in cross_html
    assert "Ana &quot;Q&quot; → &lt;Babu&gt;: Coração" in cross_html


def test_summary_and_profile_helpers_escape_rendered_names_and_labels():
    summary_html = make_reaction_summary_html(
        {
            "rows": [
                {
                    "name": '<img src=x onerror=1>',
                    "hearts": 3,
                    "planta": 0,
                    "mala": 0,
                    "biscoito": 0,
                    "coracao_partido": 0,
                    "mentiroso": 0,
                    "alvo": 0,
                    "cobra": 0,
                    "vomito": 0,
                    "negative": 1,
                    "score": 2.0,
                }
            ],
            "max_hearts": 3,
        }
    )
    assert '<img src=x onerror=1>' not in summary_html
    assert '&lt;img src=x onerror=1&gt;' in summary_html

    row_html = render_profile_sinc_row(
        "Recebeu",
        [{"emoji": "🔥", "actor": "<Ana>", "label": '"boom"'}],
        "actor",
        2,
    )
    assert "<Ana>" not in row_html
    assert "&lt;Ana&gt;" in row_html
    assert "&quot;boom&quot;" in row_html

    detail_html = index_viz.build_rxn_detail_html(
        [{"emoji": "❤️", "name": "<Ana>"}],
        avatar_fn=lambda name, size=48, border_color="#555": "<avatar>",
    )
    assert "<Ana>" not in detail_html
    assert "&lt;Ana&gt;" in detail_html
