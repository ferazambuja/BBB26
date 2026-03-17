"""Tests for balance event detection (builders/balance.py)."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from builders.balance import (
    build_balance_events,
    build_compras_fairness,
    _classify_event,
    _get_balances,
    _events_should_merge,
    _merge_events,
    _reclassify_dinamica_events,
    BALANCE_EVENT_TYPES,
    BALANCE_COLLECTIVE_THRESHOLD,
    BALANCE_SIGNIFICANT_LOSS,
    BALANCE_SIGNIFICANT_GAIN,
)


# ─── Helpers ────────────────────────────────────────────────────────────────


def _make_participant(name, balance=500):
    return {
        "name": name,
        "characteristics": {
            "group": "Vip",
            "memberOf": "Pipoca",
            "balance": balance,
            "roles": [],
            "eliminated": False,
            "receivedReactions": [],
        },
    }


def _make_snap(date, participants, stem=None):
    """Build a snapshot dict matching get_all_snapshots_with_data format."""
    stem = stem or f"{date}_12-00-00"
    return {
        "file": f"data/snapshots/{stem}.json",
        "date": date,
        "participants": participants,
        "metadata": {"captured_at": f"{date}T12:00:00+00:00"},
    }


# ─── _get_balances ──────────────────────────────────────────────────────────


def test_get_balances_basic():
    participants = [_make_participant("Alice", 1000), _make_participant("Bob", 500)]
    result = _get_balances(participants)
    assert result == {"Alice": 1000, "Bob": 500}


def test_get_balances_empty_name_skipped():
    participants = [_make_participant("", 100), _make_participant("Alice", 500)]
    result = _get_balances(participants)
    assert "" not in result
    assert result == {"Alice": 500}


# ─── _classify_event ────────────────────────────────────────────────────────


class TestClassifyEvent:
    def test_mesada_all_gain(self):
        gains = {"A": 1000, "B": 1000, "C": 500, "D": 500, "E": 500}
        events = _classify_event(gains, {}, 5, [])
        types = [e["type"] for e in events]
        assert "mesada" in types

    def test_compras_all_lose(self):
        losses = {"A": -600, "B": -400, "C": -350, "D": -200, "E": -150}
        events = _classify_event({}, losses, 5, [])
        types = [e["type"] for e in events]
        assert "compras" in types

    def test_punicao_few_lose(self):
        losses = {"A": -500, "B": -500}
        events = _classify_event({}, losses, 20, [])
        types = [e["type"] for e in events]
        assert "punicao" in types

    def test_punicao_collective(self):
        """8 out of 20 losing is still classified as punição (not compras)."""
        losses = {f"P{i}": -50 for i in range(8)}
        events = _classify_event({}, losses, 20, [])
        types = [e["type"] for e in events]
        assert "punicao" in types
        assert "compras" not in types

    def test_premio_individual_gain(self):
        gains = {"Jonas": 500}
        events = _classify_event(gains, {}, 20, [])
        types = [e["type"] for e in events]
        assert "premio" in types

    def test_premio_requires_significant_gain(self):
        """Gains below BALANCE_SIGNIFICANT_GAIN become 'outro'."""
        gains = {"Alice": 10}
        events = _classify_event(gains, {}, 20, [])
        types = [e["type"] for e in events]
        assert "outro" in types
        assert "premio" not in types

    def test_dinamica_mixed(self):
        gains = {"Alice": 500}
        losses = {"Bob": -300}
        events = _classify_event(gains, losses, 20, [])
        types = [e["type"] for e in events]
        assert "dinamica" in types

    def test_ta_com_nada_emitted(self):
        losses = {"Alice": -100}
        events = _classify_event({}, losses, 20, ["Alice"])
        types = [e["type"] for e in events]
        assert "ta_com_nada" in types
        assert "punicao" in types  # Also classified as punição

    def test_ta_com_nada_standalone(self):
        """tá com nada event contains the participant who hit zero."""
        events = _classify_event({}, {"Alice": -100}, 20, ["Alice"])
        tcn = [e for e in events if e["type"] == "ta_com_nada"]
        assert len(tcn) == 1
        assert "Alice" in tcn[0]["changes"]

    def test_no_events_when_no_changes(self):
        events = _classify_event({}, {}, 20, [])
        assert events == []

    def test_collective_threshold_boundary(self):
        """Exactly 80% gaining → mesada."""
        # 4 out of 5 = 80%
        gains = {f"P{i}": 500 for i in range(4)}
        events = _classify_event(gains, {}, 5, [])
        types = [e["type"] for e in events]
        assert "mesada" in types

    def test_below_collective_threshold(self):
        """3 out of 5 = 60% → prêmio, not mesada."""
        gains = {f"P{i}": 500 for i in range(3)}
        events = _classify_event(gains, {}, 5, [])
        types = [e["type"] for e in events]
        assert "premio" in types
        assert "mesada" not in types

    def test_compras_with_tiny_gain(self):
        """Collective losses + tiny gain (< 100) → compras, not dinamica.

        Real case: W4 Feb 6 — Ana Paula gained +60 during compras day
        (estalecas debt recovery) while 18 others lost.
        """
        losses = {f"P{i}": -400 for i in range(18)}
        gains = {"AnaP": 60}  # Below BALANCE_SIGNIFICANT_GAIN (100)
        events = _classify_event(gains, losses, 20, [])
        types = [e["type"] for e in events]
        assert "compras" in types
        assert "dinamica" not in types
        # Tiny gain should NOT be in the compras changes
        compras = [e for e in events if e["type"] == "compras"][0]
        assert "AnaP" not in compras["changes"]

    def test_compras_with_significant_gain_is_dinamica(self):
        """Collective losses + significant gain (≥ 100) → dinamica."""
        losses = {f"P{i}": -400 for i in range(18)}
        gains = {"Winner": 500}  # Above BALANCE_SIGNIFICANT_GAIN
        events = _classify_event(gains, losses, 20, [])
        types = [e["type"] for e in events]
        assert "dinamica" in types
        assert "compras" not in types


# ─── Merge logic ────────────────────────────────────────────────────────────


class TestMergeEvents:
    def test_merge_same_type_overlapping(self):
        from datetime import datetime, timezone
        t1 = datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 2, 1, 13, 0, tzinfo=timezone.utc)  # 1h apart
        events = [
            {"type": "punicao", "changes": {"Alice": -50}, "from_snapshot": "s1", "to_snapshot": "s2", "_timestamp": t1},
            {"type": "punicao", "changes": {"Alice": -50}, "from_snapshot": "s2", "to_snapshot": "s3", "_timestamp": t2},
        ]
        merged = _merge_events(events)
        assert len(merged) == 1
        assert merged[0]["changes"]["Alice"] == -100

    def test_no_merge_different_types(self):
        from datetime import datetime, timezone
        t1 = datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc)
        events = [
            {"type": "punicao", "changes": {"Alice": -50}, "_timestamp": t1, "from_snapshot": "s1", "to_snapshot": "s2"},
            {"type": "premio", "changes": {"Alice": 100}, "_timestamp": t1, "from_snapshot": "s1", "to_snapshot": "s2"},
        ]
        merged = _merge_events(events)
        assert len(merged) == 2

    def test_no_merge_beyond_window(self):
        from datetime import datetime, timezone
        t1 = datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 2, 1, 15, 0, tzinfo=timezone.utc)  # 3h apart > 2h window
        events = [
            {"type": "punicao", "changes": {"Alice": -50}, "_timestamp": t1, "from_snapshot": "s1", "to_snapshot": "s2"},
            {"type": "punicao", "changes": {"Alice": -50}, "_timestamp": t2, "from_snapshot": "s3", "to_snapshot": "s4"},
        ]
        merged = _merge_events(events)
        assert len(merged) == 2

    def test_no_merge_no_overlap(self):
        from datetime import datetime, timezone
        t1 = datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 2, 1, 13, 0, tzinfo=timezone.utc)
        events = [
            {"type": "punicao", "changes": {"Alice": -50}, "_timestamp": t1, "from_snapshot": "s1", "to_snapshot": "s2"},
            {"type": "punicao", "changes": {"Bob": -50}, "_timestamp": t2, "from_snapshot": "s2", "to_snapshot": "s3"},
        ]
        merged = _merge_events(events)
        assert len(merged) == 2  # Different people, no overlap


# ─── build_balance_events (integration) ─────────────────────────────────────


class TestBuildBalanceEvents:
    def test_no_events_single_snapshot(self):
        snap = _make_snap("2026-01-20", [_make_participant("Alice", 500)])
        result = build_balance_events([snap])
        assert result["events"] == []
        assert result["_metadata"]["n_events"] == 0

    def test_no_events_when_unchanged(self):
        snap1 = _make_snap("2026-01-20", [_make_participant("Alice", 500)], "2026-01-20_12-00-00")
        snap2 = _make_snap("2026-01-21", [_make_participant("Alice", 500)], "2026-01-21_12-00-00")
        result = build_balance_events([snap1, snap2])
        assert result["events"] == []

    def test_detects_mesada(self):
        names = [f"P{i}" for i in range(10)]
        snap1 = _make_snap("2026-01-20", [_make_participant(n, 0) for n in names], "2026-01-20_06-00-00")
        snap2 = _make_snap("2026-01-20", [_make_participant(n, 500) for n in names], "2026-01-20_12-00-00")
        result = build_balance_events([snap1, snap2])
        types = [e["type"] for e in result["events"]]
        assert "mesada" in types

    def test_detects_punicao(self):
        snap1 = _make_snap("2026-02-01", [
            _make_participant("Alice", 1000),
            _make_participant("Bob", 1000),
            *[_make_participant(f"P{i}", 500) for i in range(10)],
        ], "2026-02-01_12-00-00")
        snap2 = _make_snap("2026-02-01", [
            _make_participant("Alice", 500),  # -500
            _make_participant("Bob", 500),    # -500
            *[_make_participant(f"P{i}", 500) for i in range(10)],  # unchanged
        ], "2026-02-01_18-00-00")
        result = build_balance_events([snap1, snap2])
        types = [e["type"] for e in result["events"]]
        assert "punicao" in types
        punicao = [e for e in result["events"] if e["type"] == "punicao"][0]
        assert punicao["changes"]["Alice"] == -500
        assert punicao["changes"]["Bob"] == -500

    def test_detects_ta_com_nada_on_transition_to_zero(self):
        snap1 = _make_snap("2026-02-01", [
            _make_participant("Alice", 50),
            *[_make_participant(f"P{i}", 500) for i in range(10)],
        ], "2026-02-01_12-00-00")
        snap2 = _make_snap("2026-02-01", [
            _make_participant("Alice", 0),  # Transition to 0
            *[_make_participant(f"P{i}", 500) for i in range(10)],
        ], "2026-02-01_18-00-00")
        result = build_balance_events([snap1, snap2])
        types = [e["type"] for e in result["events"]]
        assert "ta_com_nada" in types

    def test_no_ta_com_nada_when_already_zero(self):
        """If balance was already 0 and stays 0, no tá com nada."""
        snap1 = _make_snap("2026-02-01", [
            _make_participant("Alice", 0),
            *[_make_participant(f"P{i}", 500) for i in range(10)],
        ], "2026-02-01_12-00-00")
        snap2 = _make_snap("2026-02-02", [
            _make_participant("Alice", 0),  # Still 0, no transition
            *[_make_participant(f"P{i}", 500) for i in range(10)],
        ], "2026-02-02_12-00-00")
        result = build_balance_events([snap1, snap2])
        types = [e["type"] for e in result["events"]]
        assert "ta_com_nada" not in types

    def test_skips_exited_participants(self):
        """Participants who disappear between snapshots should not produce events."""
        snap1 = _make_snap("2026-02-01", [
            _make_participant("Alice", 1000),
            _make_participant("Eliminated", 500),
        ], "2026-02-01_12-00-00")
        snap2 = _make_snap("2026-02-02", [
            _make_participant("Alice", 1000),
            # "Eliminated" is gone
        ], "2026-02-02_12-00-00")
        result = build_balance_events([snap1, snap2])
        assert result["events"] == []

    def test_event_ids_sequential(self):
        snap1 = _make_snap("2026-02-01", [
            _make_participant("Alice", 1000),
            _make_participant("Bob", 500),
            *[_make_participant(f"P{i}", 500) for i in range(10)],
        ], "2026-02-01_12-00-00")
        snap2 = _make_snap("2026-02-01", [
            _make_participant("Alice", 500),  # punição
            _make_participant("Bob", 0),      # punição + ta com nada
            *[_make_participant(f"P{i}", 500) for i in range(10)],
        ], "2026-02-01_18-00-00")
        result = build_balance_events([snap1, snap2])
        ids = [e["id"] for e in result["events"]]
        assert all(id.startswith("bal_2026-02-01_") for id in ids)

    def test_by_participant_summary(self):
        snap1 = _make_snap("2026-02-01", [
            _make_participant("Alice", 1000),
            *[_make_participant(f"P{i}", 500) for i in range(10)],
        ], "2026-02-01_12-00-00")
        snap2 = _make_snap("2026-02-01", [
            _make_participant("Alice", 500),
            *[_make_participant(f"P{i}", 500) for i in range(10)],
        ], "2026-02-01_18-00-00")
        result = build_balance_events([snap1, snap2])
        assert "Alice" in result["by_participant"]
        alice = result["by_participant"]["Alice"]
        assert alice["total_lost"] == -500
        assert alice["n_punicoes"] == 1
        assert alice["biggest_loss"] == -500

    def test_weekly_summary(self):
        snap1 = _make_snap("2026-02-01", [
            _make_participant("Alice", 1000),
            *[_make_participant(f"P{i}", 500) for i in range(10)],
        ], "2026-02-01_12-00-00")
        snap2 = _make_snap("2026-02-01", [
            _make_participant("Alice", 500),
            *[_make_participant(f"P{i}", 500) for i in range(10)],
        ], "2026-02-01_18-00-00")
        result = build_balance_events([snap1, snap2])
        assert len(result["weekly_summary"]) >= 1

    def test_constants_defined(self):
        assert len(BALANCE_EVENT_TYPES) >= 7  # grows as new event types are added
        assert BALANCE_COLLECTIVE_THRESHOLD == 0.80
        assert BALANCE_SIGNIFICANT_LOSS == 50
        assert BALANCE_SIGNIFICANT_GAIN == 100

    def test_event_has_required_fields(self):
        snap1 = _make_snap("2026-02-01", [
            _make_participant("Alice", 1000),
            *[_make_participant(f"P{i}", 500) for i in range(10)],
        ], "2026-02-01_12-00-00")
        snap2 = _make_snap("2026-02-01", [
            _make_participant("Alice", 500),
            *[_make_participant(f"P{i}", 500) for i in range(10)],
        ], "2026-02-01_18-00-00")
        result = build_balance_events([snap1, snap2])
        for ev in result["events"]:
            assert "id" in ev
            assert "type" in ev
            assert "game_date" in ev
            assert "week" in ev
            assert "from_snapshot" in ev
            assert "to_snapshot" in ev
            assert "changes" in ev
            assert "emoji" in ev
            assert "label" in ev
            assert "_timestamp" not in ev  # Internal field stripped

    def test_premiere_all_zeros_no_events(self):
        """First snapshot with all zeros should not produce any events when
        followed by another all-zeros snapshot."""
        names = [f"P{i}" for i in range(20)]
        snap1 = _make_snap("2026-01-13", [_make_participant(n, 0) for n in names], "2026-01-13_22-00-00")
        snap2 = _make_snap("2026-01-14", [_make_participant(n, 0) for n in names], "2026-01-14_20-00-00")
        result = build_balance_events([snap1, snap2])
        assert result["events"] == []

    def test_dinamica_mixed_changes(self):
        snap1 = _make_snap("2026-02-01", [
            _make_participant("Winner", 500),
            _make_participant("Loser", 500),
            *[_make_participant(f"P{i}", 500) for i in range(10)],
        ], "2026-02-01_12-00-00")
        snap2 = _make_snap("2026-02-01", [
            _make_participant("Winner", 1000),  # +500
            _make_participant("Loser", 200),    # -300
            *[_make_participant(f"P{i}", 500) for i in range(10)],
        ], "2026-02-01_18-00-00")
        result = build_balance_events([snap1, snap2])
        types = [e["type"] for e in result["events"]]
        assert "dinamica" in types


class TestComprasFairnessPerCapita:
    def test_weekly_per_capita_and_average_distance_fields(self, monkeypatch):
        """Compras fairness exposes weekly per-capita and distance-to-average fields."""
        monkeypatch.setattr(
            "data_utils.load_roles_daily",
            lambda: {
                "daily": [
                    {"date": "2026-02-01", "vip": ["Alice", "Bob"]},
                    {"date": "2026-02-08", "vip": ["Alice", "Bob"]},
                ]
            },
        )

        snapshots = [
            _make_snap(
                "2026-02-01",
                [
                    _make_participant("Alice", 1000),
                    _make_participant("Bob", 1000),
                    _make_participant("Carol", 1000),
                ],
                "2026-02-01_12-00-00",
            ),
            _make_snap(
                "2026-02-08",
                [
                    _make_participant("Alice", 900),
                    _make_participant("Bob", 900),
                    _make_participant("Carol", 750),
                ],
                "2026-02-08_12-00-00",
            ),
        ]

        events = [
            {
                "type": "compras",
                "game_date": "2026-02-01",
                "week": 3,
                "from_snapshot": "2026-02-01_12-00-00",
                "changes": {"Alice": -200, "Bob": -100, "Carol": -250},
            },
            {
                "type": "compras",
                "game_date": "2026-02-08",
                "week": 4,
                "from_snapshot": "2026-02-08_12-00-00",
                "changes": {"Alice": -100, "Bob": -100, "Carol": -400},
            },
        ]

        fairness = build_compras_fairness(events, snapshots, {})
        by_week = {ev["week"]: ev for ev in fairness["events"]}

        w3 = by_week[3]
        assert w3["vip_n"] == 2
        assert w3["xepa_n"] == 1
        assert w3["vip_total_spent"] == 300
        assert w3["xepa_total_spent"] == 250
        assert w3["vip_per_capita_spent"] == 150.0
        assert w3["xepa_per_capita_spent"] == 250.0
        assert w3["house_per_capita_spent"] == pytest.approx(183.3, abs=0.1)
        assert w3["vip_vs_house_delta"] == pytest.approx(-33.3, abs=0.1)
        assert w3["xepa_vs_house_delta"] == pytest.approx(66.7, abs=0.1)

        # VIP historical per-capita avg = (150 + 100) / 2 = 125
        # Xepa historical per-capita avg = (250 + 400) / 2 = 325
        assert w3["vip_vs_own_avg_delta"] == pytest.approx(25.0, abs=0.1)
        assert w3["xepa_vs_own_avg_delta"] == pytest.approx(-75.0, abs=0.1)

        w4 = by_week[4]
        assert w4["vip_per_capita_spent"] == 100.0
        assert w4["xepa_per_capita_spent"] == 400.0
        assert w4["vip_vs_own_avg_delta"] == pytest.approx(-25.0, abs=0.1)
        assert w4["xepa_vs_own_avg_delta"] == pytest.approx(75.0, abs=0.1)


# ─── Reclassification ─────────────────────────────────────────────────────


class TestReclassifyDinamicaEvents:
    def test_reclassifies_punicao_matching_special_event(self, monkeypatch):
        """Punição on a date with a matching special_event dinamica should be reclassified."""
        fake_manual = {
            "special_events": [
                {
                    "date": "2026-02-18",
                    "type": "dinamica",
                    "name": "Máquina do Poder",
                    "participants_affected": ["Jonas", "Marciele", "Leandro", "Alberto", "Maxiane"],
                },
            ],
        }
        monkeypatch.setattr("data_utils.load_manual_events", lambda: fake_manual)

        events = [
            {
                "type": "punicao",
                "game_date": "2026-02-18",
                "changes": {"Jonas": -600, "Marciele": -300, "Leandro": -300, "Alberto": -150, "Maxiane": -150},
                "emoji": "🚨",
                "label": "Punição",
            },
        ]
        result = _reclassify_dinamica_events(events)
        assert result[0]["type"] == "dinamica"
        assert result[0]["subtype"] == "Máquina do Poder"
        assert result[0]["emoji"] == "⚡"

    def test_no_reclassify_without_overlap(self, monkeypatch):
        """Punição with different participants should NOT be reclassified."""
        fake_manual = {
            "special_events": [
                {
                    "date": "2026-02-18",
                    "type": "dinamica",
                    "name": "Máquina do Poder",
                    "participants_affected": ["Jonas", "Marciele", "Leandro"],
                },
            ],
        }
        monkeypatch.setattr("data_utils.load_manual_events", lambda: fake_manual)

        events = [
            {
                "type": "punicao",
                "game_date": "2026-02-18",
                "changes": {"Alice": -100, "Bob": -200},
                "emoji": "🚨",
                "label": "Punição",
            },
        ]
        result = _reclassify_dinamica_events(events)
        assert result[0]["type"] == "punicao"

    def test_no_reclassify_wrong_date(self, monkeypatch):
        """Punição on a different date should NOT be reclassified."""
        fake_manual = {
            "special_events": [
                {
                    "date": "2026-02-18",
                    "type": "dinamica",
                    "name": "Máquina do Poder",
                    "participants_affected": ["Jonas", "Marciele"],
                },
            ],
        }
        monkeypatch.setattr("data_utils.load_manual_events", lambda: fake_manual)

        events = [
            {
                "type": "punicao",
                "game_date": "2026-02-19",
                "changes": {"Jonas": -100, "Marciele": -200},
                "emoji": "🚨",
                "label": "Punição",
            },
        ]
        result = _reclassify_dinamica_events(events)
        assert result[0]["type"] == "punicao"

    def test_no_reclassify_non_punicao(self, monkeypatch):
        """Non-punicao events should never be reclassified."""
        fake_manual = {
            "special_events": [
                {
                    "date": "2026-02-18",
                    "type": "dinamica",
                    "name": "Máquina do Poder",
                    "participants_affected": ["Jonas"],
                },
            ],
        }
        monkeypatch.setattr("data_utils.load_manual_events", lambda: fake_manual)

        events = [
            {
                "type": "mesada",
                "game_date": "2026-02-18",
                "changes": {"Jonas": 500},
                "emoji": "💰",
                "label": "Mesada",
            },
        ]
        result = _reclassify_dinamica_events(events)
        assert result[0]["type"] == "mesada"
