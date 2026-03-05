"""Tests for homepage frontpage insights in index_data_builder."""

import sys
from pathlib import Path
from collections import Counter, defaultdict


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from builders.index_data_builder import (
    _compute_blindados_leaders,
    _compute_vip_xepa_extremes,
    _build_frontpage_insights,
)


def test_compute_blindados_leaders_tie_returns_all_min_ratio():
    active_names = ["Ana", "Breno", "Caio"]
    house_vote_ineligible = defaultdict(list, {
        "Ana": [(1, "Líder"), (2, "imune")],      # eligible 2/4
        "Breno": [(1, "no Paredão"), (2, "imune")],  # eligible 2/4 (tie)
        "Caio": [(1, "imune")],                   # eligible 3/4
    })
    total_house_votes = Counter({"Ana": 1, "Breno": 2, "Caio": 0})

    leaders = _compute_blindados_leaders(
        active_names=active_names,
        house_vote_ineligible=house_vote_ineligible,
        n_paredoes_with_votes=4,
        total_house_votes=total_house_votes,
    )

    assert [row["name"] for row in leaders] == ["Ana", "Breno"]
    assert all(row["eligible"] == 2 for row in leaders)
    assert all(row["total"] == 4 for row in leaders)


def test_compute_vip_xepa_extremes_ties_on_both_axes():
    active_names = ["Ana", "Breno", "Caio", "Dora"]
    vip_days = {"Ana": 9, "Breno": 9, "Caio": 5, "Dora": 3}
    xepa_days = {"Ana": 2, "Breno": 3, "Caio": 2, "Dora": 8}
    total_days = {"Ana": 11, "Breno": 12, "Caio": 7, "Dora": 11}

    most_vip, least_xepa = _compute_vip_xepa_extremes(
        active_names=active_names,
        vip_days=vip_days,
        xepa_days=xepa_days,
        total_days=total_days,
    )

    assert {row["name"] for row in most_vip} == {"Ana", "Breno"}
    assert {row["name"] for row in least_xepa} == {"Ana", "Caio"}


def test_compute_extremes_respects_active_scope_only():
    active_names = ["Ana", "Breno"]
    vip_days = {"Ana": 4, "Breno": 3, "Eliminado": 50}
    xepa_days = {"Ana": 2, "Breno": 1, "Eliminado": 0}
    total_days = {"Ana": 6, "Breno": 6, "Eliminado": 50}

    most_vip, least_xepa = _compute_vip_xepa_extremes(
        active_names=active_names,
        vip_days=vip_days,
        xepa_days=xepa_days,
        total_days=total_days,
    )

    assert all(row["name"] in set(active_names) for row in most_vip)
    assert all(row["name"] in set(active_names) for row in least_xepa)


def test_build_frontpage_insights_has_fixed_card_order():
    ctx = {
        "active_names": ["Ana", "Breno"],
        "active_set": {"Ana", "Breno"},
        "avatars": {"Ana": "a.jpg", "Breno": "b.jpg"},
        "relations_pairs": {
            "Ana": {"Breno": {"score": 1.0}},
            "Breno": {"Ana": {"score": -1.0}},
        },
        "received_impact": {
            "Ana": {"negative": -2.0, "positive": 0.5},
            "Breno": {"negative": -1.0, "positive": 0.2},
        },
        "vip_days": {"Ana": 3, "Breno": 2},
        "xepa_days": {"Ana": 1, "Breno": 2},
        "total_days": {"Ana": 4, "Breno": 4},
    }
    lookups = {
        "house_vote_ineligible": defaultdict(list, {
            "Ana": [(1, "Líder")],
            "Breno": [],
        }),
        "n_paredoes_with_votes": 3,
        "total_house_votes": Counter({"Ana": 1, "Breno": 2}),
    }
    hl_data = {
        "pair_contradictions": [{
            "ator": "Ana",
            "alvo": "Breno",
            "tipo": "bomba",
            "tipo_label": "bomba",
            "emoji": "❤️",
        }],
    }

    payload = _build_frontpage_insights(ctx, lookups, hl_data)
    card_types = [card["type"] for card in payload["cards"]]
    assert card_types == [
        "sincerao_contradictions",
        "blindados",
        "vip_xepa_extremos",
        "hidden_risk",
        "impacto_negativo",
    ]
