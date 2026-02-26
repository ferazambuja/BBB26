"""Integration tests for build_relations_scores() and build_plant_index().

These are the two most important pipeline functions. Tests use synthetic
fixture data that mimics real API snapshots for 5 participants over 10 days.
"""
from __future__ import annotations

import pytest

from build_derived_data import build_relations_scores, build_plant_index
from data_utils import get_week_number


# ── Helpers ──────────────────────────────────────────────────────────────────

NAMES = ["Alice", "Bob", "Carol", "Dave", "Eve"]
GROUPS = {
    "Alice": "Pipoca",
    "Bob": "Pipoca",
    "Carol": "Veterano",
    "Dave": "Veterano",
    "Eve": "Camarote",
}
AVATARS = {n: f"https://example.com/{n.lower()}.jpg" for n in NAMES}

# Reaction plan per day.  Key = (giver, receiver) → reaction label.
# Week 1 (days 13-17): stable pattern
# Week 2 (days 18-22): some reactions flip to create streak breaks
WEEK1_REACTIONS: dict[tuple[str, str], str] = {
    # Alice gives
    ("Alice", "Bob"): "Coração",
    ("Alice", "Carol"): "Coração",
    ("Alice", "Dave"): "Planta",
    ("Alice", "Eve"): "Cobra",
    # Bob gives
    ("Bob", "Alice"): "Coração",
    ("Bob", "Carol"): "Planta",
    ("Bob", "Dave"): "Alvo",
    ("Bob", "Eve"): "Coração",
    # Carol gives
    ("Carol", "Alice"): "Coração",
    ("Carol", "Bob"): "Coração",
    ("Carol", "Dave"): "Coração",
    ("Carol", "Eve"): "Mala",
    # Dave gives
    ("Dave", "Alice"): "Cobra",
    ("Dave", "Bob"): "Planta",
    ("Dave", "Carol"): "Coração",
    ("Dave", "Eve"): "Coração",
    # Eve gives
    ("Eve", "Alice"): "Cobra",
    ("Eve", "Bob"): "Coração",
    ("Eve", "Carol"): "Planta",
    ("Eve", "Dave"): "Coração",
}

# Week 2 overrides: Alice flips on Bob (streak break), Dave warms to Alice
WEEK2_OVERRIDES: dict[tuple[str, str], str] = {
    ("Alice", "Bob"): "Cobra",       # was Coração → streak break
    ("Alice", "Dave"): "Cobra",      # was Planta → intensifies negative
    ("Dave", "Alice"): "Coração",    # was Cobra → warming
    ("Bob", "Eve"): "Planta",        # was Coração → mild shift
}


def _build_reactions_for_day(day_index: int) -> dict[tuple[str, str], str]:
    """Return reaction map for a given day (0-indexed from 2026-01-13)."""
    base = dict(WEEK1_REACTIONS)
    if day_index >= 5:  # Week 2 starts at day index 5 (Jan 18)
        base.update(WEEK2_OVERRIDES)
    return base


def _make_participant(name: str, reactions_received: dict[str, list[str]]) -> dict:
    """Build a single participant in real API format.

    Args:
        name: participant name
        reactions_received: {reaction_label: [giver_name, ...]}
    """
    received_reactions = []
    for label, givers in reactions_received.items():
        if givers:
            received_reactions.append({
                "label": label,
                "amount": len(givers),
                "participants": [
                    {"id": str(hash(g) % 10000), "name": g} for g in givers
                ],
            })
    return {
        "name": name,
        "avatar": AVATARS[name],
        "characteristics": {
            "group": "Vip",
            "memberOf": GROUPS[name],
            "balance": 500,
            "roles": [],
            "mainRole": None,
            "eliminated": False,
            "receivedReactions": received_reactions,
        },
    }


def _build_snapshot(date: str, reaction_map: dict[tuple[str, str], str]) -> dict:
    """Build one daily snapshot with the given date and reaction map."""
    # Invert: for each receiver, collect {label: [givers]}
    received: dict[str, dict[str, list[str]]] = {n: {} for n in NAMES}
    for (giver, receiver), label in reaction_map.items():
        received[receiver].setdefault(label, []).append(giver)

    participants = [_make_participant(name, received[name]) for name in NAMES]
    return {"date": date, "participants": participants}


def _build_daily_snapshots() -> list[dict]:
    """Build 10 daily snapshots (2026-01-13 to 2026-01-22)."""
    snapshots = []
    for i in range(10):
        day = 13 + i
        date = f"2026-01-{day:02d}"
        reactions = _build_reactions_for_day(i)
        snapshots.append(_build_snapshot(date, reactions))
    return snapshots


def _build_daily_roles() -> list[dict]:
    """Build daily_roles entries matching the 10-day window."""
    roles = []
    for i in range(10):
        day = 13 + i
        date = f"2026-01-{day:02d}"
        roles.append({
            "date": date,
            "lider": "Alice",
            "anjo": None,
            "monstro": [],
            "imune": [],
            "paredao": [],
            "vip": ["Bob"],
        })
    return roles


def _build_participants_index() -> list[dict]:
    """Build participants_index for all 5 participants."""
    return [
        {
            "name": name,
            "grupo": GROUPS[name],
            "avatar": AVATARS[name],
            "active": True,
            "first_seen": "2026-01-13",
            "last_seen": "2026-01-22",
        }
        for name in NAMES
    ]


def _build_manual_events() -> dict:
    """Build manual_events with one power event (Alice nominates Dave)."""
    return {
        "participants": {},
        "power_events": [
            {
                "type": "indicacao",
                "actor": "Alice",
                "target": "Dave",
                "week": 1,
                "date": "2026-01-15",
                "detail": "test nomination",
            },
        ],
        "weekly_events": [],
        "special_events": [],
        "scheduled_events": [],
        "cartola_points_log": [],
    }


def _build_auto_events() -> list[dict]:
    """Build auto_events with one leader event."""
    return [
        {
            "type": "lider",
            "actor": "Alice",
            "date": "2026-01-13",
            "week": 1,
            "source": "auto",
        },
    ]


def _build_sincerao_edges() -> dict:
    return {"edges": [], "weeks": []}


def _build_paredoes() -> dict:
    return {"paredoes": []}


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def daily_snapshots():
    return _build_daily_snapshots()


@pytest.fixture
def latest_snapshot(daily_snapshots):
    return daily_snapshots[-1]


@pytest.fixture
def manual_events():
    return _build_manual_events()


@pytest.fixture
def auto_events():
    return _build_auto_events()


@pytest.fixture
def sincerao_edges():
    return _build_sincerao_edges()


@pytest.fixture
def paredoes():
    return _build_paredoes()


@pytest.fixture
def daily_roles():
    return _build_daily_roles()


@pytest.fixture
def participants_index():
    return _build_participants_index()


@pytest.fixture
def relations_result(
    latest_snapshot, daily_snapshots, manual_events, auto_events,
    sincerao_edges, paredoes, daily_roles, participants_index,
):
    """Run build_relations_scores once and cache the result."""
    return build_relations_scores(
        latest_snapshot=latest_snapshot,
        daily_snapshots=daily_snapshots,
        manual_events=manual_events,
        auto_events=auto_events,
        sincerao_edges=sincerao_edges,
        paredoes=paredoes,
        daily_roles=daily_roles,
        participants_index=participants_index,
    )


@pytest.fixture
def plant_result(daily_snapshots, manual_events, auto_events, sincerao_edges, paredoes):
    """Run build_plant_index once and cache the result."""
    return build_plant_index(
        daily_snapshots=daily_snapshots,
        manual_events=manual_events,
        auto_events=auto_events,
        sincerao_edges=sincerao_edges,
        paredoes=paredoes,
    )


# ── TestBuildRelationsScores ─────────────────────────────────────────────────

class TestBuildRelationsScores:
    """Integration tests for build_relations_scores()."""

    def test_smoke_returns_expected_keys(self, relations_result):
        """Output must contain all required top-level keys."""
        expected_keys = {
            "_metadata",
            "edges",
            "pairs_daily",
            "pairs_paredao",
            "pairs_all",
            "contradictions",
            "received_impact",
            "voting_blocs",
            "streak_breaks",
            "missing_raio_x",
        }
        assert expected_keys == set(relations_result.keys())

    def test_pairs_daily_structure(self, relations_result):
        """pairs_daily must be dict-of-dicts with score (float) and components (dict).

        Alice gave Planta/Cobra to Dave AND has an indicacao power event
        targeting Dave, so Alice->Dave score should be negative.
        """
        pairs_daily = relations_result["pairs_daily"]
        assert isinstance(pairs_daily, dict)

        # Check structure: at least one pair present
        assert len(pairs_daily) > 0

        # Verify the nested structure of an arbitrary pair
        for actor, targets in pairs_daily.items():
            assert isinstance(targets, dict)
            for target, data in targets.items():
                assert "score" in data
                assert isinstance(data["score"], (int, float))
                assert "components" in data
                assert isinstance(data["components"], dict)
            break  # one pair is enough for structural check

        # Alice -> Dave should be negative (planta/cobra reactions + indicacao)
        alice_dave = pairs_daily.get("Alice", {}).get("Dave", {})
        assert alice_dave, "Alice->Dave pair must exist in pairs_daily"
        assert alice_dave["score"] < 0, (
            f"Alice->Dave score should be negative (got {alice_dave['score']})"
        )

    def test_edges_contain_power_event(self, relations_result):
        """At least one edge must be a power_event involving Alice->Dave."""
        edges = relations_result["edges"]
        assert isinstance(edges, list)

        power_edges = [
            e for e in edges
            if e.get("type") == "power_event"
            and e.get("actor") == "Alice"
            and e.get("target") == "Dave"
        ]
        assert len(power_edges) >= 1, (
            "Expected at least one power_event edge from Alice to Dave"
        )

    def test_received_impact_all_participants(self, relations_result):
        """received_impact must have dict entries with numeric totals for all 5 participants."""
        received_impact = relations_result["received_impact"]
        assert isinstance(received_impact, dict)

        for name in NAMES:
            assert name in received_impact, f"{name} missing from received_impact"
            value = received_impact[name]
            assert isinstance(value, dict), (
                f"received_impact[{name}] should be a dict, got {type(value)}"
            )
            # Must have a 'total' key with a numeric value
            assert "total" in value, (
                f"received_impact[{name}] missing 'total' key"
            )
            assert isinstance(value["total"], (int, float)), (
                f"received_impact[{name}]['total'] should be numeric, "
                f"got {type(value['total'])}"
            )

    def test_metadata_weights(self, relations_result):
        """_metadata.weights must contain all expected weight categories."""
        metadata = relations_result["_metadata"]
        assert "weights" in metadata

        expected_weight_keys = {
            "queridometro",
            "power_events",
            "sincerao",
            "votes",
            "vip",
            "anjo",
        }
        actual_keys = set(metadata["weights"].keys())
        # Check that all expected keys are present (there may be extras)
        assert expected_weight_keys.issubset(actual_keys), (
            f"Missing weight keys: {expected_weight_keys - actual_keys}"
        )


# ── TestBuildPlantIndex ──────────────────────────────────────────────────────

class TestBuildPlantIndex:
    """Integration tests for build_plant_index()."""

    def test_smoke_returns_expected_keys(self, plant_result):
        """Output must have _metadata, weeks (non-empty list), and latest."""
        assert "_metadata" in plant_result
        assert "weeks" in plant_result
        assert "latest" in plant_result

        weeks = plant_result["weeks"]
        assert isinstance(weeks, list)
        assert len(weeks) > 0, "weeks should be non-empty for 10 days of data"

    def test_week_scores_bounded(self, plant_result):
        """Every participant's final_score must be in [0, 100]."""
        for week_entry in plant_result["weeks"]:
            scores = week_entry["scores"]
            for name, rec in scores.items():
                score = rec["score"]
                assert 0 <= score <= 100, (
                    f"Week {week_entry['week']}, {name}: "
                    f"score {score} out of [0, 100] range"
                )

    def test_components_present(self, plant_result):
        """Each participant in latest week must have a breakdown list with 5 entries."""
        latest_scores = plant_result["latest"]["scores"]
        assert len(latest_scores) > 0, "latest scores should not be empty"

        for name, rec in latest_scores.items():
            assert "breakdown" in rec, f"{name} missing breakdown"
            # 5 base components (invisibility, low_power, low_sincerao, plant_emoji, heart_uniformity)
            assert len(rec["breakdown"]) >= 5, (
                f"{name} breakdown has {len(rec['breakdown'])} items, expected >= 5"
            )

            assert "components" in rec, f"{name} missing components dict"
            expected_components = {
                "invisibility",
                "low_power_events",
                "low_sincerao",
                "plant_emoji",
                "heart_uniformity",
            }
            actual_components = set(rec["components"].keys())
            assert expected_components.issubset(actual_components), (
                f"{name}: missing component keys: "
                f"{expected_components - actual_components}"
            )

    def test_metadata_weights_sum_to_one(self, plant_result):
        """Sum of _metadata.weights values must equal 1.0."""
        weights = plant_result["_metadata"]["weights"]
        total = sum(weights.values())
        assert total == pytest.approx(1.0), (
            f"Weights sum to {total}, expected 1.0"
        )

    def test_active_participants_scored(self, plant_result):
        """All 5 participants must have scores in the latest week."""
        latest_scores = plant_result["latest"]["scores"]
        for name in NAMES:
            assert name in latest_scores, (
                f"{name} missing from latest week scores"
            )
            assert "score" in latest_scores[name], (
                f"{name} has no 'score' key"
            )
