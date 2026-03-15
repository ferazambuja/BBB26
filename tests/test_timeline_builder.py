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


# --- Anjo fallback tests ---


def test_anjo_fallback_from_provas_when_auto_events_missing():
    provas_data = {
        "provas": [
            {
                "tipo": "anjo",
                "week": 9,
                "date": "2026-03-14",
                "vencedor": "Breno",
                "nota": "9ª Prova do Anjo.",
            }
        ]
    }

    events = build_game_timeline([], [], {}, None, provas_data)
    anjo_events = [e for e in events if e.get("category") == "anjo"]
    assert any(
        e.get("title") == "Breno → Anjo"
        and e.get("source") == "provas"
        and e.get("emoji") == "😇"
        for e in anjo_events
    )


def test_anjo_fallback_does_not_duplicate_when_auto_event_exists():
    auto_events = [
        {"type": "anjo", "date": "2026-03-14", "target": "Breno", "detail": "API"}
    ]
    provas_data = {
        "provas": [
            {"tipo": "anjo", "week": 9, "date": "2026-03-14", "vencedor": "Breno"}
        ]
    }

    events = build_game_timeline([], auto_events, {}, None, provas_data)
    anjo_events = [
        e for e in events
        if e.get("category") == "anjo" and "Breno" in e.get("participants", [])
    ]
    assert len(anjo_events) == 1
    assert anjo_events[0].get("source") == "auto_events"


# --- Monstro fallback tests ---


def test_monstro_fallback_from_weekly_events():
    manual_events = {
        "weekly_events": [
            {
                "week": 9,
                "anjo": {
                    "vencedor": "Breno",
                    "prova_date": "2026-03-14",
                    "monstro": "Jonas Sulzbach",
                    "monstro_tipo": "Tocando os Sinos",
                },
            }
        ]
    }

    events = build_game_timeline([], [], manual_events, None)
    monstro_events = [e for e in events if e.get("category") == "monstro"]
    assert any(
        e.get("title") == "Jonas Sulzbach → Monstro"
        and e.get("source") == "weekly_events"
        for e in monstro_events
    )


def test_monstro_fallback_does_not_duplicate_when_auto_event_exists():
    auto_events = [
        {"type": "monstro", "date": "2026-03-14", "target": "Jonas Sulzbach", "detail": "API"}
    ]
    manual_events = {
        "weekly_events": [
            {
                "week": 9,
                "anjo": {
                    "vencedor": "Breno",
                    "prova_date": "2026-03-14",
                    "monstro": "Jonas Sulzbach",
                    "monstro_tipo": "Tocando os Sinos",
                },
            }
        ]
    }

    events = build_game_timeline([], auto_events, manual_events, None)
    monstro_events = [
        e for e in events
        if e.get("category") == "monstro" and "Jonas Sulzbach" in e.get("participants", [])
    ]
    assert len(monstro_events) == 1
    assert monstro_events[0].get("source") == "auto_events"


def test_monstro_fallback_handles_monstro_escolha_list():
    """Multi-target monstro via monstro_escolha (e.g., W4 Ligados)."""
    manual_events = {
        "weekly_events": [
            {
                "week": 4,
                "anjo": {
                    "vencedor": "Alberto Cowboy",
                    "prova_date": "2026-02-07",
                    "monstro_escolha": ["Milena", "Juliano Floss"],
                    "monstro_tipo": "Monstro Ligados",
                },
            }
        ]
    }

    events = build_game_timeline([], [], manual_events, None)
    monstro_events = [e for e in events if e.get("category") == "monstro"]
    names = {e.get("title") for e in monstro_events}
    assert "Milena → Monstro" in names
    assert "Juliano Floss → Monstro" in names
    assert len(monstro_events) == 2


def test_monstro_fallback_skips_list_valued_monstro_field():
    """If monstro field is accidentally a list, handle gracefully."""
    manual_events = {
        "weekly_events": [
            {
                "week": 4,
                "anjo": {
                    "vencedor": "Alberto Cowboy",
                    "prova_date": "2026-02-07",
                    "monstro": ["Milena", "Juliano Floss"],
                    "monstro_tipo": "Ligados",
                },
            }
        ]
    }

    events = build_game_timeline([], [], manual_events, None)
    monstro_events = [e for e in events if e.get("category") == "monstro"]
    names = {e.get("title") for e in monstro_events}
    assert "Milena → Monstro" in names
    assert "Juliano Floss → Monstro" in names
