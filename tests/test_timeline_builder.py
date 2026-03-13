"""Unit tests for timeline builder fallback behavior."""
import sys
from pathlib import Path

# Ensure scripts/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from builders.timeline import build_game_timeline


def test_lider_fallback_from_provas_when_auto_events_missing():
    provas_data = {
        "provas": [
            {
                "tipo": "lider",
                "week": 9,
                "date": "2026-03-12",
                "vencedor": "Alberto Cowboy",
                "nota": "Alberto venceu a 9a Prova do Lider.",
            }
        ]
    }

    events = build_game_timeline([], [], {}, None, provas_data)

    lider_events = [e for e in events if e.get("category") == "lider"]
    assert any(
        e.get("title") == "Alberto Cowboy → Lider"
        and e.get("source") == "provas"
        for e in lider_events
    )


def test_lider_fallback_does_not_duplicate_when_auto_event_exists_same_week():
    auto_events = [
        {
            "type": "lider",
            "date": "2026-03-13",
            "target": "Alberto Cowboy",
            "detail": "API role update",
        }
    ]
    provas_data = {
        "provas": [
            {
                "tipo": "lider",
                "week": 9,
                "date": "2026-03-12",
                "vencedor": "Alberto Cowboy",
            }
        ]
    }

    events = build_game_timeline([], auto_events, {}, None, provas_data)
    lider_events = [
        e for e in events
        if e.get("category") == "lider"
        and "Alberto Cowboy" in e.get("participants", [])
    ]
    assert len(lider_events) == 1
    assert lider_events[0].get("source") == "auto_events"


def test_lider_fallback_supports_multiple_winners():
    provas_data = {
        "provas": [
            {
                "tipo": "lider",
                "date": "2026-02-20",
                "vencedores": ["Ana Paula Renault", "Jonas Sulzbach"],
            }
        ]
    }

    events = build_game_timeline([], [], {}, None, provas_data)
    lider_titles = {e.get("title") for e in events if e.get("category") == "lider"}
    assert "Ana Paula Renault → Lider" in lider_titles
    assert "Jonas Sulzbach → Lider" in lider_titles
