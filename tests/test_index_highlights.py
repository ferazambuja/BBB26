"""Regression tests for index highlight cards and ranking fallback behavior."""

from __future__ import annotations

import re
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from builders.index_data_builder import (
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


def test_latest_sincerao_card_has_valid_radar_structure():
    """Current sincerao card must have well-formed radar with neg_lanes or neg_ranked."""
    payload = build_index_data()
    sinc_card = next(card for card in payload.get("highlights", {}).get("cards", []) if card.get("type") == "sincerao")

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
