"""Regression tests for Cartola official-source safeguards and fallbacks."""

from __future__ import annotations

import pytest

from builders.cartola import build_cartola_data


def _participant(name: str, *, roles: list[dict] | None = None, group: str = "Xepa") -> dict:
    return {
        "name": name,
        "avatar": f"https://example.com/{name.lower().replace(' ', '-')}.jpg",
        "characteristics": {
            "group": group,
            "memberOf": "Pipoca",
            "balance": 500,
            "roles": roles or [],
            "mainRole": None,
            "eliminated": False,
            "receivedReactions": [],
        },
    }


def _participants_index(names: list[str]) -> list[dict]:
    return [
        {
            "name": n,
            "grupo": "Pipoca",
            "avatar": f"https://example.com/{n.lower().replace(' ', '-')}.jpg",
            "active": True,
            "first_seen": "2026-01-13",
            "last_seen": "2026-03-06",
        }
        for n in names
    ]


def _events(result: dict, name: str, event_type: str, week: int) -> list[dict]:
    row = next(p for p in result["leaderboard"] if p["name"] == name)
    return [
        evt for evt in row.get("events", [])
        if evt.get("event") == event_type and evt.get("cycle") == week
    ]


def _manual_base() -> dict:
    return {
        "participants": {},
        "cycles": [],
        "special_events": [],
        "power_events": [],
        "cartola_points_log": [],
    }


def test_vip_uses_official_list_plus_troca_vip_and_deduplicates():
    daily_snapshots = [
        {
            "date": "2026-02-13",
            "participants": [
                _participant("Jonas Sulzbach", roles=[{"label": "Líder"}], group="Vip"),
                _participant("Gabriela", group="Vip"),
                _participant("Breno", group="Vip"),
                _participant("Jordana", group="Xepa"),
                _participant("Marciele", group="Xepa"),
                _participant("Ana Paula Renault", group="Xepa"),
            ],
        }
    ]
    manual_events = _manual_base()
    manual_events["power_events"] = [
        {
            "type": "troca_vip",
            "target": "Ana Paula Renault",
            "date": "2026-02-13",
            "cycle": 5,
            "detail": "Troca Xepa->VIP",
        }
    ]
    provas_data = {
        "provas": [
            {
                "numero": 12,
                "tipo": "lider",
                "cycle": 5,
                "date": "2026-02-13",
                "vencedor": "Jonas Sulzbach",
                "vip": ["Gabriela", "Jordana", "Marciele", "Breno"],
                "vip_source": "oficial_gshow",
            }
        ]
    }
    participants_index = _participants_index([
        "Jonas Sulzbach", "Gabriela", "Breno", "Jordana", "Marciele", "Ana Paula Renault",
    ])

    result = build_cartola_data(
        daily_snapshots=daily_snapshots,
        manual_events=manual_events,
        paredoes_data={"paredoes": []},
        participants_index=participants_index,
        provas_data=provas_data,
    )

    for name in ["Gabriela", "Breno", "Jordana", "Marciele", "Ana Paula Renault"]:
        assert len(_events(result, name, "vip", 5)) == 1
    # Líder never accumulates VIP points.
    assert len(_events(result, "Jonas Sulzbach", "vip", 5)) == 0


def test_vip_strict_mode_fails_when_api_has_unexpected_extra_name():
    daily_snapshots = [
        {
            "date": "2026-03-06",
            "participants": [
                _participant("Alberto Cowboy", roles=[{"label": "Líder"}], group="Vip"),
                _participant("Jonas Sulzbach", roles=[{"label": "Líder"}], group="Vip"),
                _participant("Jordana", group="Vip"),
                _participant("Marciele", group="Vip"),
                _participant("Solange Couto", group="Vip"),
                _participant("Breno", group="Vip"),  # unexpected extra in API
            ],
        }
    ]
    provas_data = {
        "provas": [
            {
                "numero": 21,
                "tipo": "lider",
                "cycle": 8,
                "date": "2026-03-06",
                "vencedor": "Alberto Cowboy",
                "vencedores": ["Alberto Cowboy", "Jonas Sulzbach"],
                "vip": ["Jordana", "Marciele", "Solange Couto"],
                "vip_source": "oficial_gshow",
            }
        ]
    }
    participants_index = _participants_index([
        "Alberto Cowboy", "Jonas Sulzbach", "Jordana", "Marciele", "Solange Couto", "Breno",
    ])

    with pytest.raises(RuntimeError, match="vip"):
        build_cartola_data(
            daily_snapshots=daily_snapshots,
            manual_events=_manual_base(),
            paredoes_data={"paredoes": []},
            participants_index=participants_index,
            provas_data=provas_data,
        )


def test_monstro_retirado_vip_fallback_uses_official_vip_even_if_api_misses_transition():
    daily_snapshots = [
        {
            "date": "2026-03-01",
            "participants": [
                _participant("Ana Paula Renault", roles=[{"label": "Monstro"}], group="Xepa"),
                _participant("Samira", roles=[{"label": "Líder"}], group="Vip"),
            ],
        }
    ]
    manual_events = _manual_base()
    manual_events["cycles"] = [
        {
            "cycle": 7,
            "anjo": {
                "vencedor": "Alberto Cowboy",
                "prova_date": "2026-02-28",
                "monstro": "Ana Paula Renault",
            },
        }
    ]
    provas_data = {
        "provas": [
            {
                "numero": 18,
                "tipo": "lider",
                "cycle": 7,
                "date": "2026-02-26",
                "vencedor": "Samira",
                "vip": ["Ana Paula Renault", "Breno", "Juliano Floss", "Milena"],
                "vip_source": "oficial_gshow",
            }
        ]
    }
    participants_index = _participants_index(["Ana Paula Renault", "Samira"])

    result = build_cartola_data(
        daily_snapshots=daily_snapshots,
        manual_events=manual_events,
        paredoes_data={"paredoes": []},
        participants_index=participants_index,
        provas_data=provas_data,
    )

    assert len(_events(result, "Ana Paula Renault", "monstro", 7)) == 1
    assert len(_events(result, "Ana Paula Renault", "monstro_retirado_vip", 7)) == 1


def test_anjo_imunizado_and_emparedado_use_official_fallbacks_when_api_roles_missing():
    daily_snapshots = [
        {
            "date": "2026-01-31",
            "participants": [
                _participant("Sarah Andrade"),
                _participant("Sol Vega"),
                _participant("Brigido"),
            ],
        }
    ]
    manual_events = _manual_base()
    manual_events["power_events"] = [
        {
            "type": "imunidade",
            "actor": "Sarah Andrade",
            "target": "Sol Vega",
            "date": "2026-02-01",
            "cycle": 3,
            "detail": "Anjo imuniza",
        }
    ]
    provas_data = {
        "provas": [
            {
                "numero": 7,
                "tipo": "anjo",
                "cycle": 3,
                "date": "2026-01-31",
                "vencedor": "Sarah Andrade",
            }
        ]
    }
    paredoes_data = {
        "paredoes": [
            {
                "numero": 3,
                "semana": 3,
                "data": "2026-02-03",
                "indicados_finais": [{"nome": "Brigido"}],
            }
        ]
    }
    participants_index = _participants_index(["Sarah Andrade", "Sol Vega", "Brigido"])

    result = build_cartola_data(
        daily_snapshots=daily_snapshots,
        manual_events=manual_events,
        paredoes_data=paredoes_data,
        participants_index=participants_index,
        provas_data=provas_data,
    )

    assert len(_events(result, "Sarah Andrade", "anjo", 3)) == 1
    assert len(_events(result, "Sol Vega", "imunizado", 3)) == 1
    assert len(_events(result, "Brigido", "emparedado", 3)) == 1


def test_bate_volta_winner_gets_emparedado_and_salvo_points():
    daily_snapshots = [
        {
            "date": "2026-02-10",
            "participants": [
                _participant("Ana Paula Renault"),
                _participant("Breno"),
                _participant("Marciele"),
            ],
        }
    ]
    participants_index = _participants_index(["Ana Paula Renault", "Breno", "Marciele"])
    paredoes_data = {
        "paredoes": [
            {
                "numero": 4,
                "semana": 4,
                "data": "2026-02-10",
                "status": "em_andamento",
                "indicados_finais": [{"nome": "Breno"}, {"nome": "Marciele"}],
                "formacao": {
                    "bate_volta": {
                        "participantes": ["Ana Paula Renault", "Breno", "Marciele"],
                        "vencedor": "Ana Paula Renault",
                    }
                },
            }
        ]
    }

    result = build_cartola_data(
        daily_snapshots=daily_snapshots,
        manual_events=_manual_base(),
        paredoes_data=paredoes_data,
        participants_index=participants_index,
        provas_data={"provas": []},
    )

    assert len(_events(result, "Ana Paula Renault", "emparedado", 4)) == 1
    assert len(_events(result, "Ana Paula Renault", "salvo_paredao", 4)) == 1


def test_bate_volta_winner_does_not_get_salvo_when_salvacao_happens_with_open_window():
    daily_snapshots = [
        {
            "date": "2026-02-10",
            "participants": [
                _participant("Ana Paula Renault"),
                _participant("Breno"),
                _participant("Marciele"),
            ],
        }
    ]
    participants_index = _participants_index(["Ana Paula Renault", "Breno", "Marciele"])
    paredoes_data = {
        "paredoes": [
            {
                "numero": 4,
                "semana": 4,
                "data": "2026-02-10",
                "status": "em_andamento",
                "indicados_finais": [{"nome": "Breno"}, {"nome": "Marciele"}],
                "formacao": {
                    "bate_volta": {
                        "participantes": ["Ana Paula Renault", "Breno", "Marciele"],
                        "vencedor": "Ana Paula Renault",
                        "salvacao_com_janela_aberta": True,
                    }
                },
            }
        ]
    }

    result = build_cartola_data(
        daily_snapshots=daily_snapshots,
        manual_events=_manual_base(),
        paredoes_data=paredoes_data,
        participants_index=participants_index,
        provas_data={"provas": []},
    )

    assert len(_events(result, "Ana Paula Renault", "emparedado", 4)) == 1
    assert len(_events(result, "Ana Paula Renault", "salvo_paredao", 4)) == 0
