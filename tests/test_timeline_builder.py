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


# --- Scheduled event lifecycle and dedup tests ---


def test_past_scheduled_event_kept_when_no_real_replacement():
    """A past scheduled event with no matching real event stays in timeline as a real event."""
    manual_events = {
        "scheduled_events": [
            {
                "date": "2026-02-01",
                "category": "dinamica",
                "emoji": "🔮",
                "title": "Cinema do Líder",
                "detail": "Exibição especial",
            }
        ]
    }

    events = build_game_timeline([], [], manual_events, None, reference_date="2026-03-15")
    dinamica_events = [e for e in events if e.get("category") == "dinamica"]
    assert any(
        e.get("title") == "Cinema do Líder"
        and e.get("source") == "scheduled"
        for e in dinamica_events
    ), "Past scheduled event with no real replacement must be kept"


def test_past_scheduled_event_displays_as_real():
    """A past scheduled event (date < reference_date) should display as real, not scheduled."""
    manual_events = {
        "scheduled_events": [
            {
                "date": "2026-03-14",
                "category": "dinamica",
                "emoji": "⚡",
                "title": "Pedra, Papel e Tesoura — resultado",
                "detail": "Grupos formados e emparedados definidos.",
                "time": "Ao Vivo",
            }
        ]
    }

    events = build_game_timeline([], [], manual_events, None, reference_date="2026-03-15")
    dinamica_events = [e for e in events if e.get("category") == "dinamica"]
    assert len(dinamica_events) == 1
    ev = dinamica_events[0]
    assert ev["status"] == "", "Past event must not have status='scheduled' even if time is set"
    assert ev["source"] == "scheduled"


def test_future_scheduled_event_stays_scheduled():
    """A future scheduled event should keep status='scheduled'."""
    manual_events = {
        "scheduled_events": [
            {
                "date": "2026-03-16",
                "category": "dinamica",
                "emoji": "⚡",
                "title": "Máquina do Poder",
                "detail": "Caixa premiada salva um emparedado.",
                "time": "Ao Vivo",
            }
        ]
    }

    events = build_game_timeline([], [], manual_events, None, reference_date="2026-03-15")
    dinamica_events = [e for e in events if e.get("category") == "dinamica"]
    assert len(dinamica_events) == 1
    assert dinamica_events[0]["status"] == "scheduled"
    assert dinamica_events[0]["time"] == "Ao Vivo"


def test_same_day_with_time_stays_scheduled():
    """An event on reference_date with time field is still pending (tonight)."""
    manual_events = {
        "scheduled_events": [
            {
                "date": "2026-03-15",
                "category": "paredao_formacao",
                "emoji": "🗳️",
                "title": "Formação do Paredão",
                "detail": "Domingo ao vivo",
                "time": "Ao Vivo",
            }
        ]
    }

    events = build_game_timeline([], [], manual_events, None, reference_date="2026-03-15")
    # On 2026-03-15: manual scheduled wins over scaffold (same date+category)
    pf_on_date = [e for e in events if e.get("category") == "paredao_formacao" and e.get("date") == "2026-03-15"]
    assert len(pf_on_date) == 1
    assert pf_on_date[0]["status"] == "scheduled"


def test_same_day_without_time_is_resolved():
    """An event on reference_date with no time field is resolved."""
    manual_events = {
        "scheduled_events": [
            {
                "date": "2026-03-15",
                "category": "dinamica",
                "emoji": "⚡",
                "title": "Evento já aconteceu",
                "detail": "Resultado final.",
            }
        ]
    }

    events = build_game_timeline([], [], manual_events, None, reference_date="2026-03-15")
    dinamica_events = [e for e in events if e.get("category") == "dinamica"]
    assert len(dinamica_events) == 1
    assert dinamica_events[0]["status"] == ""


def test_past_monstro_suppressed_by_real_monstro():
    """A past monstro is suppressed when a real monstro exists on the same date."""
    auto_events = [
        {"type": "monstro", "date": "2026-03-14", "target": "Jonas Sulzbach", "detail": "API"}
    ]
    manual_events = {
        "scheduled_events": [
            {
                "date": "2026-03-14",
                "category": "monstro",
                "emoji": "👹",
                "title": "Castigo do Monstro — Jonas Sulzbach",
                "detail": "Tocando os Sinos",
                "time": "Ao Vivo",
            }
        ]
    }

    events = build_game_timeline([], auto_events, manual_events, None, reference_date="2026-03-15")
    monstro_events = [e for e in events if e.get("category") == "monstro"]
    assert len(monstro_events) == 1, (
        f"Past monstro should be suppressed by real monstro; got {len(monstro_events)}"
    )
    assert monstro_events[0]["source"] == "auto_events"


def test_future_multi_monstro_not_suppressed_by_different_real_monstro():
    """Future scheduled monstro for participant A is not suppressed by real monstro for participant B."""
    auto_events = [
        {"type": "monstro", "date": "2026-03-20", "target": "Jonas Sulzbach", "detail": "API"}
    ]
    manual_events = {
        "scheduled_events": [
            {
                "date": "2026-03-20",
                "category": "monstro",
                "emoji": "👹",
                "title": "Milena → Monstro",
                "detail": "Monstro Ligados",
                "time": "Ao Vivo",
            }
        ]
    }

    events = build_game_timeline([], auto_events, manual_events, None, reference_date="2026-03-15")
    monstro_events = [e for e in events if e.get("category") == "monstro"]
    titles = {e.get("title") for e in monstro_events}
    assert "Jonas Sulzbach → Monstro" in titles, "Real monstro event must be present"
    assert "Milena → Monstro" in titles, (
        "Future scheduled monstro for a different participant must NOT be suppressed"
    )


def test_future_multi_dinamica_not_suppressed_by_different_real_dinamica():
    """Future scheduled dinamica is not suppressed by a different real dinamica on same date."""
    manual_events = {
        "special_events": [
            {
                "date": "2026-03-20",
                "name": "Festa Surpresa",
                "description": "Festa inesperada",
                "participants": [],
            }
        ],
        "scheduled_events": [
            {
                "date": "2026-03-20",
                "category": "dinamica",
                "emoji": "⚡",
                "title": "Cinema do Líder",
                "detail": "Exibição especial",
                "time": "Ao Vivo",
            }
        ],
    }

    events = build_game_timeline([], [], manual_events, None, reference_date="2026-03-15")
    dinamica_events = [e for e in events if e.get("category") == "dinamica"]
    titles = {e.get("title") for e in dinamica_events}
    assert "Festa Surpresa" in titles, "Real dinamica must be present"
    assert "Cinema do Líder" in titles, (
        "Future scheduled dinamica with different title must NOT be suppressed"
    )


def test_scheduled_big_fone_suppressed_when_real_big_fone_exists_same_date():
    """big_fone is singleton: scheduled placeholder must be dropped when real event exists."""
    manual_events = {
        "weekly_events": [
            {
                "week": 9,
                "big_fone": [
                    {
                        "date": "2026-03-10",
                        "atendeu": "Jonas Sulzbach",
                        "consequencia": "Empareda alguém",
                    }
                ],
            }
        ],
        "scheduled_events": [
            {
                "date": "2026-03-10",
                "category": "big_fone",
                "emoji": "🔮",
                "title": "Big Fone",
                "detail": "Ao vivo",
                "time": "14h",
            }
        ],
    }

    events = build_game_timeline([], [], manual_events, None)
    big_fone_events = [e for e in events if e.get("category") == "big_fone"]
    assert len(big_fone_events) == 1
    assert big_fone_events[0].get("source") == "weekly_events"


def test_scheduled_without_category_defaults_to_dinamica_consistently():
    """Missing category should be normalized to dinamica for both dedup key and event payload."""
    manual_events = {
        "scheduled_events": [
            {
                "date": "2026-03-20",
                "title": "Evento sem categoria",
                "detail": "Teste de default",
                "time": "A definir",
            }
        ]
    }

    events = build_game_timeline([], [], manual_events, None, reference_date="2026-03-15")
    dinamica_events = [
        e for e in events
        if e.get("source") == "scheduled" and e.get("title") == "Evento sem categoria"
    ]
    assert len(dinamica_events) == 1
    assert dinamica_events[0].get("category") == "dinamica"


def test_scheduled_event_with_time_null_treated_as_resolved():
    """JSON `"time": null` should behave like missing time (resolved, time="")."""
    manual_events = {
        "scheduled_events": [
            {
                "date": "2026-03-10",
                "category": "dinamica",
                "title": "Evento com time null",
                "detail": "Teste de null",
                "time": None,
            }
        ]
    }

    events = build_game_timeline([], [], manual_events, None, reference_date="2026-03-15")
    sched = [e for e in events if e.get("title") == "Evento com time null"]
    assert len(sched) == 1
    assert sched[0]["status"] == ""  # resolved (not "scheduled")
    assert sched[0]["time"] == ""    # normalized to empty string, not None


# --- Paredão formation gate tests ---


def test_paredao_formado_not_emitted_when_votos_casa_empty():
    paredoes_data = {
        "paredoes": [
            {
                "numero": 9,
                "data_formacao": "2026-03-15",
                "formacao": {},
                "indicados_finais": [{"nome": "A"}, {"nome": "B"}, {"nome": "C"}],
                "votos_casa": {},
            }
        ]
    }

    events = build_game_timeline([], [], {}, paredoes_data, reference_date="2026-03-15")
    assert not any(
        e.get("source") == "paredoes" and e.get("category") == "paredao_formacao"
        for e in events
    )


def test_paredao_partial_formation_emits_dinamica():
    paredoes_data = {
        "paredoes": [
            {
                "numero": 9,
                "data_formacao": "2026-03-15",
                "formacao": {},
                "indicados_finais": [{"nome": "A"}, {"nome": "B"}, {"nome": "C"}],
                "votos_casa": {},
            }
        ]
    }

    events = build_game_timeline([], [], {}, paredoes_data, reference_date="2026-03-15")
    partial = [
        e for e in events
        if e.get("source") == "paredoes"
        and e.get("category") == "dinamica"
        and e.get("title") == "9º Paredão — Em formação"
    ]
    assert len(partial) == 1
    assert "Emparedados parciais" in partial[0].get("detail", "")


def test_paredao_formado_emitted_when_votos_casa_populated():
    paredoes_data = {
        "paredoes": [
            {
                "numero": 9,
                "data_formacao": "2026-03-15",
                "formacao": {},
                "indicados_finais": [{"nome": "A"}, {"nome": "B"}, {"nome": "C"}],
                "votos_casa": {"V1": "A", "V2": "B", "V3": "A"},
            }
        ]
    }

    events = build_game_timeline([], [], {}, paredoes_data, reference_date="2026-03-15")
    formed = [
        e for e in events
        if e.get("source") == "paredoes"
        and e.get("category") == "paredao_formacao"
        and e.get("title") == "9º Paredão — Formado"
    ]
    assert len(formed) == 1


def test_partial_formation_does_not_suppress_scheduled_event():
    paredoes_data = {
        "paredoes": [
            {
                "numero": 9,
                "data_formacao": "2026-03-15",
                "formacao": {},
                "indicados_finais": [{"nome": "A"}, {"nome": "B"}, {"nome": "C"}],
                "votos_casa": {},
            }
        ]
    }
    manual_events = {
        "scheduled_events": [
            {
                "date": "2026-03-15",
                "category": "paredao_formacao",
                "title": "Formação do Paredão",
                "detail": "Domingo ao vivo",
                "time": "Ao Vivo",
            }
        ]
    }

    events = build_game_timeline([], [], manual_events, paredoes_data, reference_date="2026-03-15")
    assert any(
        e.get("source") == "scheduled" and e.get("category") == "paredao_formacao"
        for e in events
    )


# --- Auto-scaffold tests ---


def test_scaffold_generates_sincerao_for_week(monkeypatch):
    monkeypatch.setattr("builders.timeline.get_effective_week_end_dates", lambda *_args, **_kwargs: ["2026-01-19"])
    events = build_game_timeline([], [], {}, None, reference_date="2026-01-18")
    assert any(
        e.get("source") == "scaffold"
        and e.get("category") == "sincerao"
        and e.get("date") == "2026-01-19"
        for e in events
    )


def test_scaffold_suppressed_by_real_event(monkeypatch):
    monkeypatch.setattr("builders.timeline.get_effective_week_end_dates", lambda *_args, **_kwargs: ["2026-01-19"])
    manual_events = {
        "weekly_events": [
            {"week": 1, "sincerao": {"date": "2026-01-19", "format": "ao vivo"}}
        ]
    }
    events = build_game_timeline([], [], manual_events, None, reference_date="2026-01-18")
    sinc = [e for e in events if e.get("category") == "sincerao" and e.get("date") == "2026-01-19"]
    assert len(sinc) == 1
    assert sinc[0].get("source") == "weekly_events"


def test_scaffold_suppressed_by_manual_scheduled(monkeypatch):
    monkeypatch.setattr("builders.timeline.get_effective_week_end_dates", lambda *_args, **_kwargs: ["2026-01-19"])
    manual_events = {
        "scheduled_events": [
            {
                "date": "2026-01-19",
                "category": "sincerao",
                "title": "Sincerão",
                "detail": "Manual placeholder",
                "time": "Ao Vivo",
            }
        ]
    }
    events = build_game_timeline([], [], manual_events, None, reference_date="2026-01-18")
    sinc = [e for e in events if e.get("category") == "sincerao" and e.get("date") == "2026-01-19"]
    assert len(sinc) == 1
    assert sinc[0].get("source") == "scheduled"


def test_scaffold_not_generated_before_first_week(monkeypatch):
    monkeypatch.setattr("builders.timeline.get_effective_week_end_dates", lambda *_args, **_kwargs: ["2026-01-19"])
    events = build_game_timeline([], [], {}, None, reference_date="2026-01-14")
    assert not any(
        e.get("source") == "scaffold"
        and e.get("category") == "ganha_ganha"
        and e.get("date") <= "2026-01-19"
        for e in events
    )


def test_scaffold_future_is_scheduled_past_is_resolved(monkeypatch):
    monkeypatch.setattr("builders.timeline.get_effective_week_end_dates", lambda *_args, **_kwargs: ["2026-01-19"])
    events = build_game_timeline([], [], {}, None, reference_date="2026-01-19")
    by_key = {(e.get("date"), e.get("category")): e for e in events if e.get("source") == "scaffold"}
    assert by_key[("2026-01-18", "presente_anjo")]["status"] == ""
    assert by_key[("2026-01-19", "sincerao")]["status"] == "scheduled"


def test_scaffold_open_week_generates_events(monkeypatch):
    monkeypatch.setattr("builders.timeline.get_effective_week_end_dates", lambda *_args, **_kwargs: [])
    events = build_game_timeline([], [], {}, None, reference_date="2026-01-13")
    assert any(
        e.get("source") == "scaffold"
        and e.get("category") == "sincerao"
        and e.get("date") == "2026-01-19"
        for e in events
    )

