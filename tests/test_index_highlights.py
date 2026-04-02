"""Regression tests for index highlight cards and ranking fallback behavior."""

from __future__ import annotations

import re
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from builders.index_data_builder import (
    _build_pulso_changes_card,
    build_index_data,
    _compute_daily_movers_cards,
    _compute_sincerao_highlight,
    _compute_static_cards,
    _compute_vulnerability_cards,
    DELIBERATE_POWER_TYPES,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _participant(name: str, hearts: int, vomit: int = 0) -> dict:
    return {
        "name": name,
        "characteristics": {
            "eliminated": False,
            "receivedReactions": [
                {"label": "Coração", "amount": hearts},
                {"label": "Vômito", "amount": vomit},
            ],
        },
    }


def _daily_change(
    date: str,
    *,
    total_changes: int,
    pct_changed: float,
    dramatic_count: int,
    top_receiver: tuple[str, float] = ("", 0.0),
    top_loser: tuple[str, float] = ("", 0.0),
    top_volatile_giver: tuple[str, int] = ("", 0),
    new_mutual_hostilities: list[dict] | None = None,
    new_streak_breaks: list[dict] | None = None,
    transition_counts: dict[str, int] | None = None,
) -> dict:
    return {
        "date": date,
        "total_changes": total_changes,
        "pct_changed": pct_changed,
        "dramatic_count": dramatic_count,
        "n_melhora": max(0, total_changes // 3),
        "n_piora": max(0, total_changes // 3),
        "n_lateral": max(0, total_changes - 2 * (total_changes // 3)),
        "hearts_gained": max(0, total_changes // 4),
        "hearts_lost": max(0, total_changes // 5),
        "top_receiver": {"name": top_receiver[0], "delta": top_receiver[1]},
        "top_loser": {"name": top_loser[0], "delta": top_loser[1]},
        "top_volatile_giver": {"name": top_volatile_giver[0], "changes": top_volatile_giver[1]},
        "transition_counts": transition_counts or {},
        "new_mutual_hostilities": new_mutual_hostilities or [],
        "new_streak_breaks": new_streak_breaks or [],
        "new_blind_spots": [],
        "receiver_deltas": {},
        "pair_changes": [],
        "giver_volatility": {},
    }


def test_ranking_highlight_falls_back_to_week_when_day_is_flat():
    daily_snapshots = [
        {"date": "2026-03-01", "participants": [_participant("Ana", 3), _participant("Beto", 1, 1)]},
        {"date": "2026-03-02", "participants": [_participant("Ana", 3), _participant("Beto", 1, 1)]},
        {"date": "2026-03-03", "participants": [_participant("Ana", 3), _participant("Beto", 1, 1)]},
        {"date": "2026-03-04", "participants": [_participant("Ana", 3), _participant("Beto", 1, 1)]},
        {"date": "2026-03-05", "participants": [_participant("Ana", 5), _participant("Beto", 0, 2)]},
        {"date": "2026-03-06", "participants": [_participant("Ana", 5), _participant("Beto", 0, 2)]},
        {"date": "2026-03-07", "participants": [_participant("Ana", 5), _participant("Beto", 0, 2)]},
    ]
    daily_matrices = [{} for _ in daily_snapshots]

    _highlights, cards = _compute_daily_movers_cards(daily_snapshots, daily_matrices, ["Ana", "Beto"])
    ranking = next(card for card in cards if card["type"] == "ranking")

    assert ranking["movers_scope"] == "week"
    assert ranking["movers_label"] == "📅 Variação na semana"
    assert ranking["delta_all"], "Expected weekly fallback rows when yesterday deltas are flat"
    assert ranking["delta_all"][0]["name"] == "Ana"
    assert ranking["delta_all"][0]["delta"] > 0


def test_pulso_changes_card_prefers_history_when_latest_day_is_not_extreme():
    history = [
        _daily_change(
            "2026-01-19",
            total_changes=82,
            pct_changed=28.0,
            dramatic_count=36,
            top_receiver=("Paulo Augusto", 9.5),
            top_loser=("Marciele", -6.0),
            top_volatile_giver=("Juliano Floss", 12),
            transition_counts={"Planta→Coração": 14},
        ),
        _daily_change(
            "2026-01-20",
            total_changes=121,
            pct_changed=36.8,
            dramatic_count=96,
            top_receiver=("Paulo Augusto", 7.0),
            top_loser=("Leandro", -16.5),
            top_volatile_giver=("Solange Couto", 17),
            transition_counts={"Coração→Planta": 22},
        ),
        _daily_change(
            "2026-02-02",
            total_changes=95,
            pct_changed=27.6,
            dramatic_count=52,
            top_receiver=("Jordana", 6.0),
            top_loser=("Gabriela", -8.5),
            top_volatile_giver=("Solange Couto", 19),
            transition_counts={"Coração→Coração partido": 20},
        ),
        _daily_change(
            "2026-04-01",
            total_changes=14,
            pct_changed=19.4,
            dramatic_count=10,
            top_receiver=("Milena", 3.0),
            top_loser=("Marciele", -3.0),
            top_volatile_giver=("Marciele", 4),
            new_mutual_hostilities=[
                {"pair": ["Gabriela", "Marciele"]},
                {"pair": ["Leandro", "Marciele"]},
                {"pair": ["Leandro", "Samira"]},
            ],
            new_streak_breaks=[
                {"giver": "Gabriela", "receiver": "Marciele", "previous_streak": 49, "new_emoji": "Mala"},
                {"giver": "Marciele", "receiver": "Gabriela", "previous_streak": 48, "new_emoji": "Coração partido"},
                {"giver": "Chaiany", "receiver": "Marciele", "previous_streak": 16, "new_emoji": "Coração partido"},
            ],
            transition_counts={"Coração→Coração partido": 2, "Mala→Coração": 2},
        ),
    ]
    current = {
        **history[-1],
        "reference_date": "2026-04-01",
        "from_date": "2026-03-31",
        "to_date": "2026-04-01",
        "total_possible": 72,
        "improve": 4,
        "worsen": 6,
        "lateral": 4,
        "net": -2,
        "hearts_gained": 4,
        "hearts_lost": 6,
    }

    card = _build_pulso_changes_card(
        current,
        history,
        active_set={"Gabriela", "Marciele", "Milena", "Leandro", "Samira", "Chaiany"},
        current_cycle=13,
        latest_date="2026-04-01",
        manual_events={},
        auto_events={"events": []},
        paredoes={
            "paredoes": [
                {
                    "numero": 2,
                    "cycle": 2,
                    "data_formacao": "2026-01-25",
                    "data": "2026-01-27",
                    "formacao": {"lider": "Babu Santana"},
                },
                {
                    "numero": 13,
                    "cycle": 13,
                    "data_formacao": "2026-04-03",
                    "data": "2026-04-05",
                    "formacao": {"lider": "Samira"},
                },
            ]
        },
    )

    assert card["mode"] == "history"
    assert card["hero"]["scope"] == "history"
    assert card["today"]["total"] == 14
    assert any("49 dias" in chip for chip in card["today"]["chips"])
    assert any("3 hostilidades" in chip for chip in card["today"]["chips"])

    chaos_fact = next(fact for fact in card["facts"] if fact["kind"] == "chaos_day")
    assert chaos_fact["date"] == "2026-01-20"
    assert "2º Paredão" in chaos_fact["context"]["moment"]
    assert any("Babu Santana" in chip for chip in chaos_fact["context"]["chips"])
    assert any(
        participant["name"] == "Solange Couto" and participant["status"] == "eliminated"
        for fact in card["facts"]
        for participant in fact.get("participants", [])
    )


def test_pulso_changes_card_uses_today_mode_when_latest_day_is_extreme():
    history = [
        _daily_change(
            "2026-01-10",
            total_changes=18,
            pct_changed=9.0,
            dramatic_count=5,
            top_receiver=("Ana", 2.0),
            top_loser=("Beto", -1.5),
            top_volatile_giver=("Ana", 4),
        ),
        _daily_change(
            "2026-01-11",
            total_changes=26,
            pct_changed=13.0,
            dramatic_count=8,
            top_receiver=("Ana", 2.5),
            top_loser=("Beto", -2.0),
            top_volatile_giver=("Beto", 5),
        ),
        _daily_change(
            "2026-01-12",
            total_changes=110,
            pct_changed=34.0,
            dramatic_count=70,
            top_receiver=("Ana", 8.0),
            top_loser=("Beto", -10.0),
            top_volatile_giver=("Ana", 21),
            transition_counts={"Coração→Planta": 18},
        ),
    ]
    current = {
        **history[-1],
        "reference_date": "2026-01-12",
        "from_date": "2026-01-11",
        "to_date": "2026-01-12",
        "total_possible": 72,
        "improve": 40,
        "worsen": 50,
        "lateral": 20,
        "net": -10,
        "hearts_gained": 18,
        "hearts_lost": 27,
    }

    card = _build_pulso_changes_card(
        current,
        history,
        active_set={"Ana", "Beto"},
        current_cycle=1,
        latest_date="2026-01-12",
        manual_events={},
        auto_events={"events": []},
        paredoes={
            "paredoes": [
                {
                    "numero": 1,
                    "cycle": 1,
                    "data_formacao": "2026-01-12",
                    "data": "2026-01-14",
                    "formacao": {"lider": "Ana"},
                }
            ]
        },
    )

    assert card["mode"] == "today"
    assert card["hero"]["scope"] == "today"
    assert card["hero"]["kind"] == "today_snapshot"
    assert card["hero"]["date"] == "2026-01-12"
    assert "1º Paredão" in card["hero"]["context"]["moment"]
    assert card["facts"], "Historical facts should still be available for rotation even on hot days"


def test_index_template_uses_dynamic_paredao_subtitle():
    content = (REPO_ROOT / "index.qmd").read_text(encoding="utf-8")

    assert 'subtitle=card.get("subtitle"' in content


def test_daily_highlight_cards_use_valid_cross_page_links():
    daily_snapshots = [
        {"date": "2026-03-11", "participants": [_participant("Ana", 3), _participant("Beto", 1)]},
        {"date": "2026-03-12", "participants": [_participant("Ana", 4), _participant("Beto", 1, 1)]},
    ]
    daily_matrices = [
        {
            ("Ana", "Beto"): "Coração",
            ("Beto", "Ana"): "Coração",
        },
        {
            ("Ana", "Beto"): "Cobra",
            ("Beto", "Ana"): "Coração",
        },
    ]

    highlights, cards = _compute_daily_movers_cards(daily_snapshots, daily_matrices, ["Ana", "Beto"])
    cards_by_type = {card["type"]: card for card in cards}

    assert cards_by_type["ranking"]["link"] == "evolucao.html#sentimento"
    assert cards_by_type["hostilities"]["link"] == "relacoes.html#hostilidades"
    assert any("[ranking](evolucao.html#sentimento)" in item for item in highlights)
    assert any("relacoes.html#hostilidades" in item for item in highlights)


def test_static_vip_xepa_cards_link_to_relacoes_anchor():
    _highlights, cards, _stats = _compute_static_cards(
        {
            "active_set": {"Ana", "Beto"},
            "paredoes": {"paredoes": []},
            "vip_days": {"Ana": 7, "Beto": 2},
            "xepa_days": {"Ana": 3, "Beto": 8},
            "total_days": {"Ana": 10, "Beto": 10},
        }
    )
    cards_by_type = {card["type"]: card for card in cards}

    assert cards_by_type["vip"]["link"] == "relacoes.html#vip-xepa"
    assert cards_by_type["xepa"]["link"] == "relacoes.html#vip-xepa"


def test_sincerao_card_link_points_to_existing_relacoes_anchor():
    sinc_data = {
        "weeks": [{"cycle": 1, "format": "Sincerão #1"}],
        "edges": [
            {"cycle": 1, "type": "ataque", "actor": "Ana", "target": "Beto"},
        ],
    }
    latest_matrix = {("Ana", "Beto"): "Coração"}

    _highlights, cards, *_rest = _compute_sincerao_highlight(
        sinc_data=sinc_data,
        current_cycle=1,
        latest_matrix=latest_matrix,
        active_set={"Ana", "Beto"},
    )
    sinc_card = next(card for card in cards if card["type"] == "sincerao")

    assert sinc_card["link"] == "relacoes.html#sincerao-contradictions"


def test_sincerao_card_splits_negative_lanes_by_tema_when_needed():
    sinc_data = {
        "weeks": [{"cycle": 9, "date": "2026-03-16", "format": "quem faz alguem de bobo + quem esta sendo feito de bobo"}],
        "edges": [
            {"cycle": 9, "type": "ataque", "actor": "Ana", "target": "Beto", "tema": "faz alguem de bobo"},
            {"cycle": 9, "type": "ataque", "actor": "Cora", "target": "Beto", "tema": "faz alguem de bobo"},
            {"cycle": 9, "type": "ataque", "actor": "Duda", "target": "Eva", "tema": "esta sendo feito de bobo"},
            {"cycle": 9, "type": "ataque", "actor": "Fabi", "target": "Eva", "tema": "esta sendo feito de bobo"},
            {"cycle": 9, "type": "ataque", "actor": "Gabi", "target": "Eva", "tema": "esta sendo feito de bobo"},
        ],
    }

    _highlights, cards, *_rest = _compute_sincerao_highlight(
        sinc_data=sinc_data,
        current_cycle=9,
        latest_matrix={},
        active_set={"Ana", "Beto", "Cora", "Duda", "Eva", "Fabi", "Gabi"},
    )
    sinc_card = next(card for card in cards if card["type"] == "sincerao")

    neg_lanes = sinc_card["radar"]["neg_lanes"]
    assert [lane["label"] for lane in neg_lanes] == [
        "Quem faz alguém de bobo",
        "Quem está sendo feito de bobo",
    ]
    assert neg_lanes[0]["ranked"] == [{"name": "Beto", "count": 2, "actors": ["Ana", "Cora"]}]
    assert neg_lanes[1]["ranked"] == [{"name": "Eva", "count": 3, "actors": ["Duda", "Fabi", "Gabi"]}]
    assert sinc_card["radar"]["neg_ranked"] == [
        {"name": "Eva", "count": 3, "actors": ["Duda", "Fabi", "Gabi"]},
        {"name": "Beto", "count": 2, "actors": ["Ana", "Cora"]},
    ]


def test_sincerao_card_keeps_unlabeled_negative_targets_visible_when_split_lanes_exist():
    sinc_data = {
        "weeks": [{"cycle": 9, "date": "2026-03-16", "format": "placa dupla com sobra sem tema"}],
        "edges": [
            {"cycle": 9, "type": "ataque", "actor": "Ana", "target": "Beto", "tema": "faz alguem de bobo"},
            {"cycle": 9, "type": "ataque", "actor": "Cora", "target": "Eva", "tema": "esta sendo feito de bobo"},
            {"cycle": 9, "type": "ataque", "actor": "Duda", "target": "Lia"},
        ],
    }

    _highlights, cards, *_rest = _compute_sincerao_highlight(
        sinc_data=sinc_data,
        current_cycle=9,
        latest_matrix={},
        active_set={"Ana", "Beto", "Cora", "Duda", "Eva", "Lia"},
    )
    sinc_card = next(card for card in cards if card["type"] == "sincerao")

    neg_lanes = sinc_card["radar"]["neg_lanes"]
    assert [lane["label"] for lane in neg_lanes] == [
        "Quem faz alguém de bobo",
        "Quem está sendo feito de bobo",
        "Atacados",
    ]
    assert neg_lanes[2]["ranked"] == [{"name": "Lia", "count": 1, "actors": ["Duda"]}]
    assert sinc_card["radar"]["neg_ranked"] == [
        {"name": "Beto", "count": 1, "actors": ["Ana"]},
        {"name": "Eva", "count": 1, "actors": ["Cora"]},
        {"name": "Lia", "count": 1, "actors": ["Duda"]},
    ]


def test_sincerao_card_is_hidden_when_current_cycle_has_no_sincerao_yet():
    sinc_data = {
        "weeks": [{"cycle": 10, "date": "2026-03-23", "format": "Chato de Galocha"}],
        "edges": [
            {"cycle": 10, "type": "ataque", "actor": "Ana", "target": "Beto"},
            {"cycle": 10, "type": "elogio", "actor": "Cora", "target": "Duda"},
        ],
    }

    _highlights, cards, pair_contradictions, pair_aligned_pos, pair_aligned_neg, sinc_week_used, available_weeks, radar = _compute_sincerao_highlight(
        sinc_data=sinc_data,
        current_cycle=13,
        latest_matrix={
            ("Ana", "Beto"): "Coração",
            ("Cora", "Duda"): "Coração",
        },
        active_set={"Ana", "Beto", "Cora", "Duda"},
    )

    assert sinc_week_used == 10
    assert available_weeks == [10]
    assert radar["neg_ranked"] == [{"name": "Beto", "count": 1, "actors": ["Ana"]}]
    assert pair_contradictions == [{
        "ator": "Ana",
        "alvo": "Beto",
        "tipo": "ataque",
        "tipo_label": "ataque",
        "tema": None,
        "reacao": "Coração",
        "emoji": "❤️",
    }]
    assert pair_aligned_pos == [{
        "ator": "Cora",
        "alvo": "Duda",
        "tipo": "elogio",
        "tipo_label": "elogio",
        "tema": None,
        "reacao": "Coração",
        "emoji": "❤️",
    }]
    assert pair_aligned_neg == []
    assert not any(card.get("type") == "sincerao" for card in cards)


def test_latest_sincerao_card_has_valid_radar_structure():
    """Current sincerao card must have well-formed radar with neg_lanes or neg_ranked."""
    payload = build_index_data()
    sinc_card = next((card for card in payload.get("highlights", {}).get("cards", []) if card.get("type") == "sincerao"), None)
    if not sinc_card:
        return

    radar = sinc_card["radar"]
    assert "neg_lanes" in radar or "neg_ranked" in radar
    # neg_lanes (if present) must have label + ranked entries
    for lane in radar.get("neg_lanes", []):
        assert "label" in lane
        assert "ranked" in lane
        for entry in lane["ranked"]:
            assert "name" in entry
            assert "count" in entry
            assert entry["count"] >= 1
    # neg_ranked (if present) must have the same structure
    for entry in radar.get("neg_ranked", []):
        assert "name" in entry
        assert "count" in entry
        assert entry["count"] >= 1


def test_all_highlight_card_links_follow_navigation_contract():
    payload = build_index_data()
    assert payload is not None

    card_links = {
        card.get("link")
        for card in payload.get("highlights", {}).get("cards", [])
        if card.get("link")
    }
    item_links: set[str] = set()
    for item in payload.get("highlights", {}).get("items", []):
        if not isinstance(item, str):
            continue
        item_links.update(re.findall(r"\[[^\]]+\]\(([^)]+)\)", item))

    links = card_links | item_links
    allowed_links = {
        "evolucao.html#impacto",
        "evolucao.html#pulso",
        "evolucao.html#sentimento",
        "paredao.html",
        "paredoes.html",
        "paredoes.html#nunca-paredao",
        "paredoes.html#figurinha-repetida",
        "relacoes.html#aliancas",
        "relacoes.html#hostilidades",
        "relacoes.html#sincerao-contradictions",
        "relacoes.html#vip-xepa",
        "#perfis",
    }

    assert card_links
    assert links.issubset(allowed_links), f"Unexpected card links: {sorted(links - allowed_links)}"
    assert not any("%" in link for link in links), f"Percent-encoded links are forbidden: {sorted(links)}"


def test_vulnerability_cards_no_mais_alvo_card():
    """M-2: mais_alvo card removed (replaced by Na Mira in _compute_static_cards)."""
    latest = {
        "date": "2026-02-20",
        "participants": [
            _participant("Ana", 3),
            _participant("Beto", 1, 1),
        ],
    }
    active_names = ["Ana", "Beto"]
    active_set = {"Ana", "Beto"}

    edges = [
        {"actor": "Beto", "target": "Ana", "type": "vote",
         "weight": -10.0, "week": 3, "backlash": False},
    ]
    relations_data = {"edges": edges}

    _hl, cards, _pn = _compute_vulnerability_cards(
        latest, active_names, active_set,
        received_impact={}, relations_pairs={},
        relations_data=relations_data,
        latest_date="2026-02-20",
    )

    card_types = [c.get("type") for c in cards]
    assert "mais_alvo" not in card_types, "mais_alvo card should no longer be produced"


def test_deliberate_power_types_is_module_level_constant():
    """M-3: DELIBERATE_POWER_TYPES should be a module-level constant with all expected types."""
    expected = {
        "indicacao", "contragolpe", "monstro", "veto_prova",
        "mira_do_lider", "barrado_baile", "veto_ganha_ganha",
        "duelo_de_risco", "imunidade", "troca_xepa", "troca_vip",
    }
    assert set(DELIBERATE_POWER_TYPES) == expected
    # Should be a frozenset (immutable module-level constant)
    assert isinstance(DELIBERATE_POWER_TYPES, frozenset)
