"""Regression tests for Cartola leader fallback from provas.json."""

from __future__ import annotations

from builders.cartola import build_cartola_data


def _participant(name: str, roles: list[dict] | None = None) -> dict:
    return {
        "name": name,
        "avatar": f"https://example.com/{name.lower().replace(' ', '-')}.jpg",
        "characteristics": {
            "group": "Xepa",
            "memberOf": "Pipoca",
            "balance": 500,
            "roles": roles or [],
            "mainRole": None,
            "eliminated": False,
            "receivedReactions": [],
        },
    }


def _leader_events(result: dict, name: str) -> list[dict]:
    row = next(p for p in result["leaderboard"] if p["name"] == name)
    return [evt for evt in row.get("events", []) if evt.get("event") == "lider"]


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


def test_cartola_adds_leader_points_from_provas_when_snapshot_role_is_missing():
    daily_snapshots = [
        {
            "date": "2026-03-06",
            "participants": [
                _participant("Alberto Cowboy"),
                _participant("Jonas Sulzbach"),
            ],
        }
    ]
    manual_events = {
        "participants": {},
        "weekly_events": [],
        "special_events": [],
        "power_events": [],
        "cartola_points_log": [],
    }
    paredoes_data = {"paredoes": []}
    provas_data = {
        "provas": [
            {
                "numero": 21,
                "tipo": "lider",
                "week": 8,
                "date": "2026-03-06",
                "vencedor": "Alberto Cowboy",
                "vencedores": ["Alberto Cowboy", "Jonas Sulzbach"],
            }
        ]
    }
    participants_index = _participants_index(["Alberto Cowboy", "Jonas Sulzbach"])

    result = build_cartola_data(
        daily_snapshots=daily_snapshots,
        manual_events=manual_events,
        paredoes_data=paredoes_data,
        participants_index=participants_index,
        provas_data=provas_data,
    )

    for winner in ["Alberto Cowboy", "Jonas Sulzbach"]:
        leader_events = _leader_events(result, winner)
        assert any(
            evt["week"] == 8 and evt["points"] == 80 and evt["date"] == "2026-03-06"
            for evt in leader_events
        ), f"{winner} should receive +80 leader points in week 8 from provas fallback"


def test_cartola_does_not_duplicate_leader_points_when_role_and_provas_both_exist():
    daily_snapshots = [
        {
            "date": "2026-03-06",
            "participants": [
                _participant("Alberto Cowboy", roles=[{"label": "Líder"}]),
                _participant("Jonas Sulzbach"),
            ],
        }
    ]
    manual_events = {
        "participants": {},
        "weekly_events": [],
        "special_events": [],
        "power_events": [],
        "cartola_points_log": [],
    }
    paredoes_data = {"paredoes": []}
    provas_data = {
        "provas": [
            {
                "numero": 21,
                "tipo": "lider",
                "week": 8,
                "date": "2026-03-06",
                "vencedor": "Alberto Cowboy",
                "vencedores": ["Alberto Cowboy", "Jonas Sulzbach"],
            }
        ]
    }
    participants_index = _participants_index(["Alberto Cowboy", "Jonas Sulzbach"])

    result = build_cartola_data(
        daily_snapshots=daily_snapshots,
        manual_events=manual_events,
        paredoes_data=paredoes_data,
        participants_index=participants_index,
        provas_data=provas_data,
    )

    # Alberto has leader role in snapshot and also appears in provas.
    # Must have exactly one +80 leader event in week 8.
    alberto_leader_events = [
        evt
        for evt in _leader_events(result, "Alberto Cowboy")
        if evt["week"] == 8 and evt["points"] == 80
    ]
    assert len(alberto_leader_events) == 1

    # Jonas has no role in snapshot but appears in provas, so fallback should add one.
    jonas_leader_events = [
        evt
        for evt in _leader_events(result, "Jonas Sulzbach")
        if evt["week"] == 8 and evt["points"] == 80
    ]
    assert len(jonas_leader_events) == 1
