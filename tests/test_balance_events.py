"""Tests for balance event detection (builders/balance.py)."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from builders.balance import (
    build_balance_events,
    build_compras_fairness,
    _classify_event,
    _classify_punishment_severity,
    _build_punishment_deep_dive,
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


def _make_participant(name, balance=500, group="Vip"):
    return {
        "name": name,
        "characteristics": {
            "group": group,
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
        # Mix of VIP (+1000) and Xepa (+500) participants so mesada reclassifier matches
        vip_names = [f"V{i}" for i in range(5)]
        xepa_names = [f"X{i}" for i in range(5)]
        snap1 = _make_snap("2026-01-20", [
            *[_make_participant(n, 0, group="Vip") for n in vip_names],
            *[_make_participant(n, 0, group="Xepa") for n in xepa_names],
        ], "2026-01-20_06-00-00")
        snap2 = _make_snap("2026-01-20", [
            *[_make_participant(n, 1000, group="Vip") for n in vip_names],
            *[_make_participant(n, 500, group="Xepa") for n in xepa_names],
        ], "2026-01-20_12-00-00")
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
            assert "cycle" in ev
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
                    _make_participant("Alice", 1000, group="Vip"),
                    _make_participant("Bob", 1000, group="Vip"),
                    _make_participant("Carol", 1000, group="Xepa"),
                ],
                "2026-02-01_12-00-00",
            ),
            _make_snap(
                "2026-02-08",
                [
                    _make_participant("Alice", 900, group="Vip"),
                    _make_participant("Bob", 900, group="Vip"),
                    _make_participant("Carol", 750, group="Xepa"),
                ],
                "2026-02-08_12-00-00",
            ),
        ]

        events = [
            {
                "type": "compras",
                "game_date": "2026-02-01",
                "cycle": 3,
                "from_snapshot": "2026-02-01_12-00-00",
                "changes": {"Alice": -200, "Bob": -100, "Carol": -250},
            },
            {
                "type": "compras",
                "game_date": "2026-02-08",
                "cycle": 4,
                "from_snapshot": "2026-02-08_12-00-00",
                "changes": {"Alice": -100, "Bob": -100, "Carol": -400},
            },
        ]

        fairness = build_compras_fairness(events, snapshots, {})
        by_week = {ev["cycle"]: ev for ev in fairness["events"]}

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


# ─── Punishment Deep Dive ────────────────────────────────────────────────


class TestPunishmentSeverity:
    def test_severity_50(self):
        r = _classify_punishment_severity(-50)
        assert r["bucket"] == "leve"
        assert r["label"] == "Leve"
        assert r["units_of_50"] == 1
        assert r["raw_amount"] == -50

    def test_severity_100(self):
        r = _classify_punishment_severity(-100)
        assert r["bucket"] == "multipla"
        assert r["label"] == "2\u00d7 Leve"
        assert r["units_of_50"] == 2

    def test_severity_500(self):
        r = _classify_punishment_severity(-500)
        assert r["bucket"] == "gravissima"
        assert r["label"] == "Gravíssima"
        assert r["units_of_50"] == 10

    def test_severity_550_preserves_raw(self):
        r = _classify_punishment_severity(-550)
        assert r["bucket"] == "gravissima"
        assert r["units_of_50"] == 11
        assert r["raw_amount"] == -550

    def test_severity_700_preserves_raw(self):
        r = _classify_punishment_severity(-700)
        assert r["bucket"] == "gravissima"
        assert r["units_of_50"] == 14
        assert r["raw_amount"] == -700

    def test_severity_below_50(self):
        r = _classify_punishment_severity(-30)
        assert r["bucket"] == "desconhecido"
        assert r["units_of_50"] == 0


class TestPunishmentDeepDive:
    def _make_events(self):
        """Create a mix of punicao, compras, and monstro events."""
        return [
            {
                "type": "punicao", "game_date": "2026-01-14", "cycle": 1,
                "changes": {"Alice": -50, "Bob": -100},
            },
            {
                "type": "punicao", "game_date": "2026-01-20", "cycle": 2,
                "changes": {"Alice": -500},
            },
            {
                "type": "compras", "game_date": "2026-01-21", "cycle": 2,
                "changes": {"Alice": -200, "Bob": -300, "Carol": -250},
            },
            {
                "type": "monstro", "game_date": "2026-01-22", "cycle": 2,
                "changes": {"Bob": -300},
            },
            {
                "type": "punicao", "game_date": "2026-02-01", "cycle": 3,
                "changes": {"Carol": -50},
            },
        ]

    def _make_by_participant(self):
        return {
            "Alice": {
                "total_gained": 2000, "total_lost": -750,
                "n_punicoes": 3, "n_premios": 0,
                "biggest_loss": -500, "biggest_gain": 1000,
                "ta_com_nada_dates": ["2026-01-20", "2026-02-05", "2026-03-10"],
            },
            "Bob": {
                "total_gained": 1500, "total_lost": -700,
                "n_punicoes": 2, "n_premios": 0,
                "biggest_loss": -300, "biggest_gain": 500,
                "ta_com_nada_dates": [],
            },
            "Carol": {
                "total_gained": 1000, "total_lost": -300,
                "n_punicoes": 1, "n_premios": 0,
                "biggest_loss": -250, "biggest_gain": 500,
                "ta_com_nada_dates": ["2026-02-01"],
            },
        }

    def test_who_lost_most_punicao_only(self, monkeypatch):
        """who_lost_most must only count type=punicao, not compras or monstro."""
        monkeypatch.setattr("data_utils.load_roles_daily", lambda: {"daily": []})
        result = _build_punishment_deep_dive(self._make_events(), self._make_by_participant())
        wlm = {r["name"]: r for r in result["who_lost_most"]}
        # Alice: -50 + -500 = -550 (punicao only)
        assert wlm["Alice"]["formal_punishment_total"] == -550
        assert wlm["Alice"]["formal_punishment_count"] == 2
        assert wlm["Alice"]["formal_biggest_loss"] == -500
        # Bob: -100 (punicao only, NOT -300 monstro)
        assert wlm["Bob"]["formal_punishment_total"] == -100
        assert wlm["Bob"]["formal_punishment_count"] == 1
        # Carol: -50 (punicao only, NOT -250 compras)
        assert wlm["Carol"]["formal_punishment_total"] == -50

    def test_recent_max_10(self, monkeypatch):
        """recent_punishments must cap at 10."""
        monkeypatch.setattr("data_utils.load_roles_daily", lambda: {"daily": []})
        events = [
            {"type": "punicao", "game_date": f"2026-01-{d:02d}", "cycle": 1,
             "changes": {"Alice": -50}}
            for d in range(1, 16)  # 15 events
        ]
        result = _build_punishment_deep_dive(events, {})
        assert len(result["recent_punishments"]) == 10

    def test_recent_sorted_desc(self, monkeypatch):
        """recent_punishments must be sorted by date descending."""
        monkeypatch.setattr("data_utils.load_roles_daily", lambda: {"daily": []})
        result = _build_punishment_deep_dive(self._make_events(), self._make_by_participant())
        dates = [r["game_date"] for r in result["recent_punishments"]]
        assert dates == sorted(dates, reverse=True)

    def test_severity_summary(self, monkeypatch):
        """severity_summary must count by bucket across all rows."""
        monkeypatch.setattr("data_utils.load_roles_daily", lambda: {"daily": []})
        result = _build_punishment_deep_dive(self._make_events(), self._make_by_participant())
        ss = result["severity_summary"]
        # Event 1: Alice -50 (leve), Bob -100 (multipla)
        # Event 2: Alice -500 (gravissima)
        # Event 5: Carol -50 (leve)
        # Total: 2 leve, 1 multipla, 1 gravissima
        assert ss["leve"] == 2
        assert ss["multipla"] == 1
        assert ss["gravissima"] == 1

    def test_ta_com_nada_cycles(self, monkeypatch):
        """ta_com_nada_analysis must compute cycle gaps for participants with 2+ zeros."""
        monkeypatch.setattr("data_utils.load_roles_daily", lambda: {"daily": []})
        # Mock get_cycle_number to return simple values
        import builders.balance as bal_mod
        orig_gcn = bal_mod.get_cycle_number
        cycle_map = {"2026-01-20": 2, "2026-02-05": 4, "2026-03-10": 7}
        monkeypatch.setattr(bal_mod, "get_cycle_number", lambda d: cycle_map.get(d, orig_gcn(d)))

        result = _build_punishment_deep_dive(self._make_events(), self._make_by_participant())
        tcn = result["ta_com_nada_analysis"]
        # Alice has 3 dates → 2 gaps
        assert "Alice" in tcn
        assert tcn["Alice"]["cycles"] == [2, 4, 7]
        assert tcn["Alice"]["gaps_in_cycles"] == [2, 3]
        assert tcn["Alice"]["avg_gap"] == 2.5
        # Bob has 0 dates → not in analysis
        assert "Bob" not in tcn
        # Carol has 1 date → not in analysis (needs 2+)
        assert "Carol" not in tcn

    def test_stable_empty_shape(self, monkeypatch):
        """With no punishment events, all keys must be present with empty values."""
        monkeypatch.setattr("data_utils.load_roles_daily", lambda: {"daily": []})
        result = _build_punishment_deep_dive([], {})
        assert result["recent_punishments"] == []
        assert result["who_lost_most"] == []
        assert result["severity_summary"] == {"leve": 0, "multipla": 0, "gravissima": 0}
        assert result["ta_com_nada_analysis"] == {}
        assert result["balance_strip"] == {"top_gainers": [], "top_losers": []}
        assert result["vip_strip"] == {"most_vip": [], "never_vip": []}

    def test_balance_strip_precomputed(self, monkeypatch):
        """balance_strip must have top 3 gainers and bottom 3 losers."""
        monkeypatch.setattr("data_utils.load_roles_daily", lambda: {"daily": []})
        result = _build_punishment_deep_dive([], self._make_by_participant())
        strip = result["balance_strip"]
        # Alice: 2000 + -750 = 1250, Bob: 1500 + -700 = 800, Carol: 1000 + -300 = 700
        assert strip["top_gainers"][0]["name"] == "Alice"
        assert strip["top_gainers"][0]["net"] == 1250
        assert strip["top_losers"][-1]["name"] == "Carol"
        assert strip["top_losers"][-1]["net"] == 700

    def test_vip_strip_precomputed(self, monkeypatch):
        """vip_strip must count VIP appearances and list never-VIP participants."""
        monkeypatch.setattr("data_utils.load_roles_daily", lambda: {
            "daily": [
                {"date": "2026-01-14", "vip": ["Alice", "Bob"], "xepa": ["Carol"]},
                {"date": "2026-01-15", "vip": ["Alice"], "xepa": ["Bob", "Carol"]},
            ]
        })
        result = _build_punishment_deep_dive([], {})
        vs = result["vip_strip"]
        assert vs["most_vip"][0]["name"] == "Alice"
        assert vs["most_vip"][0]["vip_count"] == 2
        assert any(p["name"] == "Carol" for p in vs["never_vip"])

    def test_latest_compras_in_fairness(self, monkeypatch):
        """compras_fairness must include latest_compras pointing to last event."""
        monkeypatch.setattr(
            "data_utils.load_roles_daily",
            lambda: {"daily": [{"date": "2026-02-01", "vip": ["Alice"]}]},
        )
        snapshots = [
            _make_snap("2026-02-01",
                       [_make_participant("Alice", 1000), _make_participant("Bob", 500)],
                       "2026-02-01_12-00-00"),
            _make_snap("2026-02-08",
                       [_make_participant("Alice", 800), _make_participant("Bob", 300)],
                       "2026-02-08_12-00-00"),
        ]
        events = [{
            "type": "compras", "game_date": "2026-02-01", "cycle": 3,
            "from_snapshot": "2026-02-01_12-00-00",
            "changes": {"Alice": -200, "Bob": -200},
        }]
        fairness = build_compras_fairness(events, snapshots, {})
        assert "latest_compras" in fairness
        assert fairness["latest_compras"]["game_date"] == "2026-02-01"
        assert "house_per_capita_spent" in fairness["latest_compras"]
