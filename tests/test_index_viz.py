from __future__ import annotations

import sys
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
REPO_ROOT = Path(__file__).resolve().parents[1]

import index_viz
from data_utils import GROUP_COLORS, REACTION_EMOJI, setup_bbb_dark_theme
from index_viz import (
    _short_name,
    av,
    av_group_border,
    card_header,
    days_ago_str,
    fmt_date_br,
    make_cross_table_heatmap,
    make_cross_table_html,
    make_event_chips,
    make_reaction_summary_html,
    pair_story_card,
    plant_color,
    progress_bar,
    render_actor_avatars,
    render_agressor_row,
    render_alvo_rows,
    render_avatar_row,
    render_blindado_row,
    render_break_row,
    render_dramatic_event_row,
    render_na_mira_row,
    render_overflow_toggle,
    render_pair_lane,
    render_pair_chip,
    render_pulso_card,
    render_viradas_card,
    render_profile_sinc_row,
    render_pulse_row,
    render_rank_chip,
    render_ranked_lane,
    render_saldo_card,
    render_status_chip,
    stat_chip,
    render_toggle_pair_lane,
    render_visado_row,
    render_vx_row,
)


@pytest.fixture(autouse=True)
def _setup_theme() -> None:
    setup_bbb_dark_theme()


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


def test_days_ago_str_honors_ref_date_override_when_provided():
    anchor = datetime.strptime("2026-03-20", "%Y-%m-%d").date()

    assert days_ago_str("2026-03-11", "2026-03-12", anchor_brt=anchor) == "há 1 dia"
    assert days_ago_str("2026-03-12", "2026-03-12", anchor_brt=anchor) == "hoje"


def test_short_name_returns_first_token_or_fallback():
    assert _short_name("Ana Paula Renault") == "Ana"
    assert _short_name("") == "?"


def test_card_header_renders_badge_source_link_and_subtitle():
    html = card_header(
        "🗳️",
        "Paredão Ativo",
        "paredao.html",
        badge="Resultado oficial",
        source_tag="📊 Nosso Modelo",
        subtitle="Resumo do paredão encerrado.",
    )

    assert "Paredão Ativo" in html
    assert "Resultado oficial" in html
    assert "📊 Nosso Modelo" in html
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


def test_render_pulso_card_renders_history_drill_and_today_strip():
    payload = {
        "icon": "📊",
        "title": "Arquivo do Queridômetro",
        "link": "evolucao.html#pulso",
        "color": "#3498db",
        "mode": "history",
        "hero": {
            "kind": "chaos_day",
            "scope": "history",
            "date": "2026-01-20",
            "title": "Maior caos da temporada",
            "value": "121",
            "value_label": "reações mudaram",
            "support": "17 💔, 15 🧳, 14 🌱, 12 🍪, 9 🐍, 7 🤥, 1 🎯",
            "summary": "Ressaca do 1º Sincerão: 75 ❤️ mudaram de lugar, e o maior baque foi de Leandro (-16.5).",
            "context": {
                "moment": "Ressaca do 1º Sincerão",
                "chips": ["Líder: Alberto Cowboy", "Pós-Sincerão"],
                "timeline": [
                    {
                        "date": "2026-01-18",
                        "summary": "Entrou com 22 ❤️ e 1 🧳.",
                    },
                    {
                        "date": "2026-01-19",
                        "summary": "No 1º Sincerão, cravou Alberto Cowboy como quem não ganha; depois levou 2x não ganha, de Gabriela (planta) e Jordana (disse que ele mentiu sobre o Quarto Branco), e ficou sem pódio.",
                    },
                    {
                        "date": "2026-01-20",
                        "summary": "10 ❤️ viraram outra coisa ao redor de Leandro: Juliano ❤️→🌱, Solange ❤️→🧳, Sarah ❤️→🍪, Chaiany ❤️→🌱, Aline ❤️→🧳, Breno ❤️→🐍, Marciele ❤️→🌱, Samira ❤️→🌱, Jordana ❤️→🤥, Gabriela ❤️→🌱.",
                    },
                ],
            },
            "participants": [
                {"name": "Leandro", "status": "active"},
            ],
        },
        "facts": [
            {
                "kind": "chaos_day",
                "scope": "history",
                "date": "2026-01-20",
                "title": "Maior caos da temporada",
                "value": "121",
                "value_label": "reações mudaram",
                "support": "17 💔, 15 🧳, 14 🌱, 12 🍪, 9 🐍, 7 🤥, 1 🎯",
                "summary": "Ressaca do 1º Sincerão: 75 ❤️ mudaram de lugar, e o maior baque foi de Leandro (-16.5).",
                "context": {
                    "moment": "Ressaca do 1º Sincerão",
                    "chips": ["Líder: Alberto Cowboy", "Pós-Sincerão"],
                    "timeline": [
                        {
                            "date": "2026-01-18",
                            "summary": "Entrou com 22 ❤️ e 1 🧳.",
                        },
                        {
                            "date": "2026-01-19",
                            "summary": "No 1º Sincerão, cravou Alberto Cowboy como quem não ganha; depois levou 2x não ganha, de Gabriela (planta) e Jordana (disse que ele mentiu sobre o Quarto Branco), e ficou sem pódio.",
                        },
                        {
                            "date": "2026-01-20",
                            "summary": "10 ❤️ viraram outra coisa ao redor de Leandro: Juliano ❤️→🌱, Solange ❤️→🧳, Sarah ❤️→🍪, Chaiany ❤️→🌱, Aline ❤️→🧳, Breno ❤️→🐍, Marciele ❤️→🌱, Samira ❤️→🌱, Jordana ❤️→🤥, Gabriela ❤️→🌱.",
                        },
                    ],
                },
                "participants": [
                    {"name": "Leandro", "status": "active"},
                ],
            },
            {
                "kind": "volatile_giver",
                "scope": "history",
                "date": "2026-02-02",
                "title": "Maior redesenho do queridômetro",
                "value": "19",
                "value_label": "casas preenchidas",
                "support": "8 ❤️, 4 🌱, 3 🤮, 2 🤥, 1 🐍, 1 💔",
                "summary": "No auge do 3º Paredão, Juliano saiu de 19 espaços vazios para um tabuleiro completo: abriu ❤️ para aliados, mas pesou a mão em Brigido 🤮, Jonas 🤮, Alberto 🤥, Sarah 🤥 e Jordana 🐍.",
                "context": {
                    "moment": "Big Fone, 3º Paredão e Sincerão",
                    "chips": ["Líder: Maxiane", "Big Fone na véspera", "Dia de Sincerão", "Tá Com Nada"],
                    "timeline": [
                        {
                            "date": "2026-01-31",
                            "summary": "Atendeu o Big Fone azul e, com Babu e Marcelo, ajudou a colocar Jonas no 3º Paredão.",
                        },
                        {
                            "date": "2026-02-01",
                            "summary": "Na formação, votou em Brigido; a berlinda fechou com Ana Paula, Leandro e o próprio Brigido.",
                        },
                        {
                            "date": "2026-02-02",
                            "summary": "Dia de Tá Com Nada e Sincerão de futebol. Juliano virou alvo de 2x Bola Murcha e 1x Goleiro Frangueiro; na comparação diária, preencheu os 19 espaços com 8 ❤️ e 11 negativas.",
                        },
                    ],
                },
                "participants": [
                    {"name": "Juliano Floss", "status": "active"},
                ],
            },
            {
                "kind": "streak_break",
                "scope": "history",
                "date": "2026-04-02",
                "title": "Maior sequência de ❤️ quebrada",
                "value": "13",
                "value_label": "dias seguidos de ❤️",
                "support": "Marciele → Chaiany",
                "summary": "Marciele passou 13 dias seguidos dando ❤️ para Chaiany e, nessa virada, trocou para 🌱.",
                "context": {
                    "moment": "Ciclo do 13º Paredão",
                    "chips": ["Líder: Samira"],
                },
                "participants": [
                    {"name": "Marciele", "status": "active"},
                    {"name": "Chaiany", "status": "active"},
                ],
            },
            {
                "kind": "receiver_gain",
                "scope": "history",
                "date": "2026-01-19",
                "title": "Maior alta de um dia para o outro",
                "value": "+9.5",
                "value_label": "saldo recebido",
                "support": "Paulo Augusto",
                "summary": "Paulo teve o melhor salto entre esse dia e o anterior.",
                "context": {
                    "moment": "Ciclo do 1º Paredão",
                    "chips": ["Líder: Alberto Cowboy"],
                },
                "participants": [
                    {"name": "Paulo Augusto", "status": "eliminated"},
                ],
            },
        ],
        "today": {
            "date": "2026-04-01",
            "total": 14,
            "pct": 19,
            "improve": 4,
            "worsen": 6,
            "lateral": 4,
            "hearts_gained": 4,
            "hearts_lost": 6,
            "chips": ["3 quebras longas", "3 hostilidades novas"],
        },
    }

    html = render_pulso_card(
        payload,
        avatar_fn=lambda name, size=48, border_color="#555": f"<avatar {name} {size} {border_color}>",
    )

    assert "Arquivo do Queridômetro" in html
    assert "pulso-card" in html
    assert "Maior caos da temporada" in html
    assert "121" in html
    assert "14" in html
    assert "Última comparação" in html
    assert "14 mudanças de um dia para o outro (19%)" in html
    assert 'pulso-fact-breakdown--tokens' in html
    assert "17 💔" in html
    assert "15 🧳" in html
    assert "14 🌱" in html
    assert "12 🍪" in html
    assert "9 🐍" in html
    assert "7 🤥" in html
    assert "1 🎯" in html
    assert "Linha do tempo" in html
    assert "18/01" in html
    assert "22 ❤️" in html
    assert "19/01" in html
    assert "2x não ganha" in html
    assert "sem pódio" in html
    assert "Gabriela" in html
    assert "Jordana" in html
    assert "20/01" in html
    assert "10 ❤️ viraram outra coisa" in html
    assert "Juliano ❤️→🌱" in html
    assert "Maior redesenho do queridômetro" in html
    assert "casas preenchidas" in html
    assert "8 ❤️" in html
    assert "4 🌱" in html
    assert "3 🤮" in html
    assert "2 🤥" in html
    assert "1 🐍" in html
    assert "1 💔" in html
    assert "19 espaços vazios" in html
    assert "Brigido 🤮" in html
    assert "Jonas 🤮" in html
    assert "Alberto 🤥" in html
    assert "31/01" in html
    assert "Big Fone azul" in html
    assert "01/02" in html
    assert "votou em Brigido" in html
    assert "02/02" in html
    assert "2x Bola Murcha" in html
    assert "1x Goleiro Frangueiro" in html
    assert "Quem aparece nessa história" in html
    assert "Contexto do momento" in html
    assert "mais 2 fatos do arquivo" in html
    assert 'class="pulso-rail-toggle"' in html
    assert "3 quebras longas" in html
    assert "Ressaca do 1º Sincerão" in html
    assert "Líder: Alberto Cowboy" in html
    assert "Pós-Sincerão" in html
    assert "Ganha-Ganha" not in html
    assert "<details" in html
    assert "fora" not in html
    assert "<avatar Leandro 34 #4f7cff>" in html


def test_pulso_archive_toggle_is_not_hidden_on_desktop():
    css = (REPO_ROOT / "assets" / "cards.css").read_text(encoding="utf-8")

    assert css.count(".pulso-rail-toggle:not([open]) > .pulso-rail") == 1
    assert "@media (max-width: 819px)" in css
    assert ".pulso-rail-toggle:not([open]) > .pulso-rail {\n    display: none;" in css


def test_render_viradas_card_renders_hero_summary_and_grouped_drill():
    payload = {
        "icon": "🔄",
        "title": "Viradas",
        "link": "evolucao.html#pulso",
        "source_tag": "📅 Ontem → Hoje",
        "subtitle": "As principais viradas de um dia para o outro no queridômetro.",
        "state": "partial",
        "total": 4,
        "counts": {"dramatic": 2, "hostilities": 1, "breaks": 1},
        "hero": {
            "kind": "breaks",
            "kicker": "Aliança rompida",
            "title": "Ruptura com ❤️ ainda do outro lado",
            "body": "Entre as viradas do dia, esta pesa mais porque quebra uma sequência longa de ❤️ e vira só de um lado.",
            "date": "2026-04-02",
            "giver": "Gabriela",
            "receiver": "Leandro",
            "old_emoji": "❤️",
            "new_emoji": "💔",
            "prior_same_emoji_days": 9,
            "prior_heart_days": 9,
            "other_side_current_emoji": "❤️",
            "other_side_kept_heart": True,
            "meta_line": "Depois de 9 dias de ❤️ · Leandro manteve ❤️ · 02/04",
            "severity_score": 2.0,
            "severity_label": "grave",
            "stat_value": "9",
            "stat_label": "dias de ❤️",
            "chips": [{"text": "Leandro manteve ❤️", "tone": "accent"}],
        },
        "summary": [
            {"kind": "dramatic", "title": "Mudanças Dramáticas", "count": 2, "note": "máx 9 dias antes da troca"},
            {"kind": "hostilities", "title": "Novas Hostilidades", "count": 1, "note": "1 com ❤️ do outro lado"},
            {"kind": "breaks", "title": "Alianças Rompidas", "count": 1, "note": "1 sequência longa quebrada"},
        ],
        "groups": [
            {
                "kind": "dramatic",
                "title": "Mudanças Dramáticas",
                "count": 2,
                "items": [
                    {
                        "kind": "dramatic",
                        "date": "2026-04-02",
                        "giver": "Jordana",
                        "receiver": "Chaiany",
                        "old_emoji": "❤️",
                        "new_emoji": "🌱",
                        "prior_same_emoji_days": 4,
                        "prior_heart_days": 4,
                        "other_side_current_emoji": "🌱",
                        "other_side_kept_heart": False,
                        "meta_line": "Depois de 4 dias de ❤️ · 02/04",
                        "severity_score": 1.5,
                        "severity_label": "alta",
                    },
                    {
                        "kind": "dramatic",
                        "date": "2026-04-02",
                        "giver": "Leandro",
                        "receiver": "Marciele",
                        "old_emoji": "❤️",
                        "new_emoji": "💔",
                        "prior_same_emoji_days": 2,
                        "prior_heart_days": 2,
                        "other_side_current_emoji": "🌱",
                        "other_side_kept_heart": False,
                        "meta_line": "Depois de 2 dias de ❤️ · 02/04",
                        "severity_score": 1.5,
                        "severity_label": "alta",
                    },
                ],
            },
            {
                "kind": "hostilities",
                "title": "Novas Hostilidades",
                "count": 1,
                "items": [
                    {
                        "kind": "hostilities",
                        "date": "2026-04-02",
                        "giver": "Marciele",
                        "receiver": "Chaiany",
                        "old_emoji": "❤️",
                        "new_emoji": "🌱",
                        "prior_same_emoji_days": 3,
                        "prior_heart_days": 3,
                        "other_side_current_emoji": "❤️",
                        "other_side_kept_heart": True,
                        "meta_line": "Depois de 3 dias de ❤️ · Chaiany manteve ❤️ · 02/04",
                        "severity_score": 2.0,
                        "severity_label": "hostilidade",
                    }
                ],
            },
            {
                "kind": "breaks",
                "title": "Alianças Rompidas",
                "count": 1,
                "items": [
                    {
                        "kind": "breaks",
                        "date": "2026-04-02",
                        "giver": "Gabriela",
                        "receiver": "Leandro",
                        "old_emoji": "❤️",
                        "new_emoji": "💔",
                        "prior_same_emoji_days": 9,
                        "prior_heart_days": 9,
                        "other_side_current_emoji": "❤️",
                        "other_side_kept_heart": True,
                        "meta_line": "Depois de 9 dias de ❤️ · Leandro manteve ❤️ · 02/04",
                        "severity_score": 2.0,
                        "severity_label": "grave",
                    }
                ],
            },
        ],
    }

    html = render_viradas_card(
        payload,
        avatar_fn=lambda name, size=48, border_color="#555": f"<avatar {name} {size} {border_color}>",
    )

    assert "Viradas" in html
    assert "Ruptura com ❤️ ainda do outro lado" in html
    assert "Gabriela" in html
    assert "Leandro" in html
    assert "Depois de 9 dias de ❤️ · Leandro manteve ❤️ · 02/04" in html
    assert "9" in html
    assert "dias de ❤️" in html
    assert "Mudanças Dramáticas" in html
    assert "Novas Hostilidades" in html
    assert "Alianças Rompidas" in html
    assert "mais 4 viradas do dia" in html
    assert "Jordana" in html
    assert "Marciele" in html
    assert "Chaiany manteve ❤️" in html
    assert "<avatar Gabriela 46 #4f7cff>" in html
    assert html.count("<div") == html.count("</div>")


def test_render_pulso_participants_keeps_semantic_eliminated_label():
    html = index_viz._render_pulso_participants(
        [{"name": "Paulo Augusto", "status": "eliminated"}],
        avatar_fn=lambda name, size=48, border_color="#555": f"<avatar {name} {size} {border_color}>",
    )

    assert 'aria-label="Paulo Augusto (eliminado)"' in html
    assert "<avatar Paulo Augusto 34 #7a7f87>" in html


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


def test_render_rank_chip_uses_avatar_link_and_body_toggle_when_actor_list_exists():
    html = render_rank_chip(
        {"name": "Gabriela", "count": 5, "actors": ["Breno", "Juliano Floss", "Leandro"]},
        "attack",
        True,
        avatar_html_fn=lambda name, border_color: f"<avatar {name} {border_color}>",
    )

    assert 'href="#perfil-gabriela"' in html
    assert 'class="sinc-person-card sinc-person-chip attack top"' in html
    assert 'class="sinc-person-avatar-link"' in html
    assert 'class="sinc-person-chip-toggle"' in html
    assert 'class="sinc-person-chip-summary"' in html
    assert 'data-sinc-sync-toggle="chooser"' in html
    assert "ver quem escolheu" not in html
    assert "Breno" in html
    assert "Juliano" in html
    assert "Leandro" in html


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


def test_render_ranked_lane_can_build_chips_without_qmd_lambda_glue():
    html = render_ranked_lane(
        "Atacados",
        "💣",
        [{"name": "Ana Paula Renault", "count": 2}],
        "Sem ataques na semana.",
        "attack",
        inline_max=2,
        avatar_html_fn=lambda name, avatars, size, show_name, border_color, fallback_initials: (
            f"<avatar {name} border={border_color} size={size} fallback={fallback_initials}>"
        ),
        avatars={"Ana Paula Renault": "x"},
        avatar_size=30,
    )

    assert "💣 Atacados" in html
    assert "<avatar Ana Paula Renault border=#e67e22 size=30 fallback=True>" in html
    assert "Ana" in html
    assert "2x" in html


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


def test_render_pair_chip_prefers_tema_over_generic_tipo_label():
    item = {
        "ator": "Breno",
        "alvo": "Gabriela",
        "tipo_label": "ataque",
        "tema": "esta sendo feito de bobo",
        "emoji": "❤️",
    }

    html = render_pair_chip(item, mode="contra")

    assert "esta sendo feito de bobo" in html
    assert "ataque mas dá" not in html


def test_render_alvo_rows_wraps_rows_and_overflow_details():
    html = render_alvo_rows(
        [
            {"name": "Ana Paula Renault", "score": -4.0},
            {"name": "Babu Santana", "score": -3.0},
            {"name": "Milena", "score": -2.0},
            {"name": "Chaiany", "score": -1.0},
            {"name": "Leandro", "score": -0.5},
            {"name": "Jonas Sulzbach", "score": -0.2},
        ],
        "alvo-recent",
        avatar_fn=lambda name, size=42, border_color="#555": f"<avatar {name} {border_color}>",
    )

    assert 'id="alvo-recent"' in html
    assert "<avatar Ana Paula Renault #c0392b>" in html
    assert 'href="#perfil-ana-paula-renault"' in html
    assert "<summary>+1 restantes</summary>" in html
    assert "width:100%" in html


def test_render_break_row_formats_break_card_metadata():
    html = render_break_row(
        {
            "giver": "Ana Paula Renault",
            "receiver": "Babu Santana",
            "streak": 7,
            "new_emoji": "😡",
            "severity": "strong",
            "date": "2026-03-08",
        },
        break_ref_date="2026-03-12",
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
    assert "7d ❤️" in html
    assert "😡" in html
    assert "Rompimento grave" in html
    assert "08/03 (há 4 dias)" in html
    assert "border='#e74c3c'" in html


def test_render_blindado_row_renders_badges_and_counts():
    html = render_blindado_row(
        {
            "name": "Ana Paula Renault",
            "paredao": 0,
            "protected": 3,
            "available": 5,
            "votes": 1,
            "voted_paredoes": 1,
            "bv_escape": True,
            "bv_text": 'Escapou "BV"',
            "escape_tags": [
                {"label": "Bate-Volta", "text": 'Escapou "BV"'},
            ],
            "protection_tags": [
                {"label": "Líder", "text": "Líder 2x"},
                {"label": "Casa", "text": "Casa 1x"},
            ],
        },
        n_par=4,
        avatar_fn=lambda name, size=42, border_color="#555": f"<avatar {name} {border_color}>",
    )

    assert "<avatar Ana Paula Renault #3498db>" in html
    assert 'href="#perfil-ana-paula-renault"' in html
    assert "0 paredões" in html
    assert "1 voto em 5 elegíveis" in html
    assert "votado em 1 paredão" in html
    assert "protegido 3x" in html
    assert "Escapou &quot;BV&quot;" in html
    assert "Líder 2x" in html
    assert "Casa 1x" in html


def test_render_blindado_row_tolerates_null_protection_tags():
    html = render_blindado_row(
        {
            "name": "Ana Paula Renault",
            "paredao": 0,
            "protected": 1,
            "available": 3,
            "votes": 2,
            "voted_paredoes": 2,
            "protection_tags": None,
        },
        n_par=4,
        avatar_fn=lambda name, size=42, border_color="#555": f"<avatar {name} {border_color}>",
    )

    assert "<avatar Ana Paula Renault #27ae60>" in html
    assert "protegido 1x" in html
    assert "2 votos em 3 elegíveis" in html
    assert "votado em 2 paredões" in html
    assert "display:flex;flex-direction:column" not in html


def test_render_visado_row_renders_pressure_badges():
    html = render_visado_row(
        {
            "name": "Babu Santana",
            "paredao": 2,
            "votes_total": 6,
            "votes_recent": 3,
            "intensity_prevote": 0.67,
            "bv_escapes": 1,
            "fake_paredao_count": 1,
            "fake_paredao_nums": [5],
            "by_lider": 2,
            "by_casa": 1,
            "by_dynamic": 1,
        },
        max_votes=6,
        recent_window=3,
        avatar_fn=lambda name, size=42, border_color="#555": f"<avatar {name} {border_color}>",
    )

    assert "<avatar Babu Santana #c0392b>" in html
    assert "2 paredões" in html
    assert "6 votos total" in html
    assert "3 recentes (3 ciclos)" in html
    assert "67%" in html  # intensidade % now wrapped in colored span
    assert "Escapou Bate-Volta 1x" in html
    assert "Paredão falso 1x (5º)" in html
    assert "Líder 2x" in html
    assert "Casa 1x" in html
    assert "Dinâmica 1x" in html


def test_render_visado_row_tolerates_null_fake_paredao_nums():
    html = render_visado_row(
        {
            "name": "Babu Santana",
            "paredao": 1,
            "votes_total": 4,
            "votes_recent": 2,
            "intensity_prevote": 0.4,
            "fake_paredao_count": 2,
            "fake_paredao_nums": None,
        },
        max_votes=6,
        recent_window=3,
        avatar_fn=lambda name, size=42, border_color="#555": f"<avatar {name} {border_color}>",
    )

    assert "<avatar Babu Santana #d35400>" in html
    assert "Paredão falso 2x" in html
    assert "Paredão falso 2x ()" not in html


def test_render_vx_row_formats_day_share_and_bar():
    html = render_vx_row(
        {"name": "Milena", "vip": 4, "total": 10},
        day_key="vip",
        accent="#f1c40f",
        max_days=8,
        avatar_fn=lambda name, size=38, border_color="#555": f"<avatar {name} {border_color}>",
    )

    assert "<avatar Milena #f1c40f>" in html
    assert 'href="#perfil-milena"' in html
    assert "4d (40%)" in html
    assert "width:50%" in html


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


def test_render_na_mira_row_renders_power_tags_and_drill_down():
    html = render_na_mira_row(
        {
            "name": "Ana Paula Renault",
            "power_hits": 6,
            "power_hits_recent": 2,
            "paredao": 3,
            "power_tags": [
                {"label": "Indicação", "count": 2, "text": "Indicação 2x"},
                {"label": "Barrado", "count": 2, "text": "Barrado 2x"},
            ],
            "power_detail": [
                {"type": "indicacao", "actor": "Alberto Cowboy", "cycle": 8, "date": "2026-03-01"},
                {"type": "barrado_baile", "actor": "Jonas Sulzbach", "cycle": 6, "date": "2026-02-15"},
            ],
        },
        max_hits=8,
        avatar_fn=lambda name, size=42, border_color="#555": f"<avatar {name} {border_color}>",
        tag_labels={"indicacao": "Indicação", "barrado_baile": "Barrado"},
    )

    assert "<avatar Ana Paula Renault #c0392b>" in html
    assert "6 ações contra" in html
    assert "3 paredões" in html
    assert "2 recentes (3 sem.)" in html
    assert "Indicação 2x" in html
    assert "Barrado 2x" in html
    assert "#3f1b1b" in html  # dark red badge bg
    assert "#ff9d9d" in html  # dark red badge text
    assert "Detalhes (2)" in html
    assert ">▶ Detalhes (2)</summary>" not in html
    assert ">Detalhes (2)</summary>" in html
    assert "Indicação por Alberto Cowboy (8º)" in html
    assert "Barrado por Jonas Sulzbach (6º)" in html


def test_render_na_mira_row_handles_zero_hits():
    html = render_na_mira_row(
        {
            "name": "Breno",
            "power_hits": 0,
            "power_hits_recent": 0,
            "paredao": 0,
            "power_tags": [],
            "power_detail": [],
        },
        max_hits=6,
        avatar_fn=lambda name, size=42, border_color="#555": f"<avatar {name} {border_color}>",
    )

    assert "<avatar Breno #7f8c8d>" in html
    assert "0 paredões" in html
    assert "Detalhes" not in html


def test_render_agressor_row_renders_purple_tags_and_drill_down():
    html = render_agressor_row(
        {
            "name": "Alberto Cowboy",
            "power_hits": 14,
            "power_hits_recent": 3,
            "power_tags": [
                {"label": "Na Mira", "count": 5, "text": "Na Mira 5x"},
                {"label": "Indicação", "count": 3, "text": "Indicação 3x"},
            ],
            "power_detail": [
                {"type": "mira_do_lider", "target": "Milena", "cycle": 8, "date": "2026-03-01"},
            ],
        },
        max_hits=14,
        avatar_fn=lambda name, size=42, border_color="#555": f"<avatar {name} {border_color}>",
        tag_labels={"mira_do_lider": "Na Mira"},
    )

    assert "<avatar Alberto Cowboy #8e44ad>" in html
    assert "14 ações" in html
    assert "Na Mira 5x" in html
    assert "Indicação 3x" in html
    assert "#2d1b3f" in html  # purple badge bg
    assert "#d9b3ff" in html  # purple badge text
    assert "Detalhes (1)" in html
    assert ">▶ Detalhes (1)</summary>" not in html
    assert ">Detalhes (1)</summary>" in html
    assert "Na Mira → Milena (8º)" in html
