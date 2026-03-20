"""Regression tests for cycle-aware bridge logic in the index builder."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from builders.index_data_builder import (
    _aggregate_latest_state,
    _compute_breaks_and_context_cards,
)


def test_current_cycle_prefers_manual_open_cycle_when_snapshots_lag(monkeypatch):
    monkeypatch.setattr("builders.index_data_builder.get_effective_week_end_dates", lambda: ["2026-01-21"])

    latest = {
        "date": "2026-01-21",
        "participants": [
            {
                "name": "Babu Santana",
                "characteristics": {"roles": [], "group": "vip"},
            }
        ],
    }
    parsed = {
        "latest": latest,
        "latest_date": "2026-01-21",
        "current_week": 1,
        "plant_index": {"weeks": []},
        "roles_daily": {"daily": []},
        "participants_index": {"participants": [{"name": "Babu Santana", "first_seen": "2026-01-13"}]},
        "paredoes": {"paredoes": []},
        "manual_events": {
            "weekly_events": [
                {"week": 2, "start_date": "2026-01-22"},
            ]
        },
    }

    aggregated = _aggregate_latest_state(parsed, [latest])

    assert aggregated["current_cycle_week"] == 2


def test_context_card_uses_current_cycle_bridge_label():
    latest = {
        "participants": [
            {"name": "Babu Santana", "characteristics": {}},
            {"name": "Chaiany", "characteristics": {"eliminated": True}},
        ]
    }

    highlights, cards = _compute_breaks_and_context_cards(
        {},
        {"Babu Santana"},
        latest,
        1,
        [{"date": "2026-01-21", "participants": []}],
        "2026-01-21",
        current_cycle_week=2,
    )

    context = next(card for card in cards if card.get("type") == "context")
    assert context["week"] == 2
    assert context["cycle"] == 2
    assert highlights[-1].startswith("📅 **Ciclo do Paredão 2**")
