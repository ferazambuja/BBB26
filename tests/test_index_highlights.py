"""Regression tests for index highlight cards and ranking fallback behavior."""

from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from builders.index_data_builder import _compute_daily_movers_cards


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
