"""Tests for build_derived_data.py core functions.

Covers scoring helpers, edge builders, and data builders with minimal
mock data — no real data files required.
"""
import pytest
import sys
from pathlib import Path
from collections import defaultdict

# Ensure scripts/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_derived_data import (
    _blend_streak,
    _compute_base_weights,
    _compute_base_weights_all,
    compute_streak_data,
    _build_power_event_edges,
    _build_sincerao_edges_section,
    _build_vote_edges,
    build_participants_index,
    build_daily_roles,
    build_auto_events,
    _classify_sentiment,
    _sentiment_value_for_category,
    STREAK_REACTIVE_WEIGHT,
    STREAK_MEMORY_WEIGHT,
    STREAK_BREAK_PENALTY,
    STREAK_BREAK_MAX_LEN,
    STREAK_MEMORY_MAX_LEN,
    RELATION_POWER_WEIGHTS,
    RELATION_SINC_WEIGHTS,
    RELATION_VOTE_WEIGHTS,
    RELATION_POWER_BACKLASH_FACTOR,
    RELATION_SINC_BACKLASH_FACTOR,
    RELATION_VISIBILITY_FACTOR,
)
from data_utils import build_reaction_matrix, SENTIMENT_WEIGHTS


# ─── Fixtures ────────────────────────────────────────────────────────────────


def _make_participant(name, group="Vip", member_of="Pipoca", roles=None,
                      received_reactions=None, balance=500, avatar=""):
    """Helper to build a participant dict matching the API format."""
    return {
        "name": name,
        "avatar": avatar or f"https://example.com/{name.lower()}.jpg",
        "characteristics": {
            "group": group,
            "memberOf": member_of,
            "balance": balance,
            "roles": roles or [],
            "mainRole": None,
            "eliminated": False,
            "receivedReactions": received_reactions or [],
        },
    }


def _make_reaction(label, givers):
    """Helper to build a receivedReaction entry."""
    return {
        "label": label,
        "amount": len(givers),
        "participants": [{"id": str(i), "name": g} for i, g in enumerate(givers, 1)],
    }


def _make_snapshot(date, participants):
    """Helper to build a snapshot dict with date and participants."""
    return {"date": date, "participants": participants}


@pytest.fixture
def three_person_snapshots():
    """5 days of snapshots for Alice, Bob, Carol.

    Day 1-3: Alice ❤️ Bob, Bob ❤️ Alice, Carol ❤️ Alice
    Day 4:   Alice 🐍 Bob (streak break!), Bob ❤️ Alice, Carol ❤️ Alice
    Day 5:   Alice 🐍 Bob, Bob ❤️ Alice, Carol 🌱 Alice
    """
    days = []
    for i, date in enumerate(["2026-01-20", "2026-01-21", "2026-01-22",
                               "2026-01-23", "2026-01-24"]):
        if i < 3:
            # Days 1-3: all hearts
            alice = _make_participant("Alice", received_reactions=[
                _make_reaction("Coração", ["Bob", "Carol"]),
            ])
            bob = _make_participant("Bob", received_reactions=[
                _make_reaction("Coração", ["Alice"]),
            ])
            carol = _make_participant("Carol", received_reactions=[
                _make_reaction("Coração", ["Alice", "Bob"]),
            ])
        elif i == 3:
            # Day 4: Alice switches to Cobra on Bob
            alice = _make_participant("Alice", received_reactions=[
                _make_reaction("Coração", ["Bob", "Carol"]),
            ])
            bob = _make_participant("Bob", received_reactions=[
                _make_reaction("Cobra", ["Alice"]),
            ])
            carol = _make_participant("Carol", received_reactions=[
                _make_reaction("Coração", ["Alice", "Bob"]),
            ])
        else:
            # Day 5: Alice still Cobra on Bob, Carol gives Planta to Alice
            alice = _make_participant("Alice", received_reactions=[
                _make_reaction("Coração", ["Bob"]),
                _make_reaction("Planta", ["Carol"]),
            ])
            bob = _make_participant("Bob", received_reactions=[
                _make_reaction("Cobra", ["Alice"]),
            ])
            carol = _make_participant("Carol", received_reactions=[
                _make_reaction("Coração", ["Alice", "Bob"]),
            ])
        days.append(_make_snapshot(date, [alice, bob, carol]))
    return days


@pytest.fixture
def long_positive_then_break_snapshots():
    """8 days: 6 positive (hearts) then 2 strong negative (cobra).

    This should trigger a streak break (>=5 positive → negative with <=3 recent).
    """
    days = []
    for i in range(8):
        date = f"2026-02-{10 + i:02d}"
        if i < 6:
            # Positive: Alice ❤️ Bob
            bob = _make_participant("Bob", received_reactions=[
                _make_reaction("Coração", ["Alice"]),
            ])
        else:
            # Negative: Alice 🐍 Bob
            bob = _make_participant("Bob", received_reactions=[
                _make_reaction("Cobra", ["Alice"]),
            ])
        alice = _make_participant("Alice", received_reactions=[
            _make_reaction("Coração", ["Bob"]),
        ])
        days.append(_make_snapshot(date, [alice, bob]))
    return days


@pytest.fixture
def sample_streak_info():
    """Pre-built streak info dict for testing _blend_streak."""
    return {
        "Alice": {
            "Bob": {
                "streak_len": 7,
                "streak_category": "positive",
                "streak_sentiment": 1.0,
                "previous_streak_len": 0,
                "previous_category": None,
                "break_from_positive": False,
                "total_days": 7,
            },
        },
        "Carol": {
            "Dave": {
                "streak_len": 2,
                "streak_category": "strong_negative",
                "streak_sentiment": -1.0,
                "previous_streak_len": 8,
                "previous_category": "positive",
                "break_from_positive": True,
                "total_days": 10,
            },
        },
    }


@pytest.fixture
def sample_power_events():
    """Minimal power events for edge building tests."""
    return [
        {
            "type": "indicacao",
            "actor": "Alice",
            "target": "Bob",
            "date": "2026-01-20",
            "week": 1,
            "visibility": "public",
        },
        {
            "type": "contragolpe",
            "actor": "Carol",
            "target": "Dave",
            "date": "2026-01-20",
            "week": 1,
            "visibility": "public",
        },
        {
            "type": "monstro",
            "actor": "Alice",
            "target": "Carol",
            "date": "2026-01-21",
            "week": 1,
            "visibility": "public",
        },
    ]


@pytest.fixture
def sample_sincerao_edges():
    """Minimal Sincerão edges for testing."""
    return {
        "edges": [
            {
                "actor": "Alice",
                "target": "Bob",
                "type": "podio",
                "slot": 1,
                "week": 2,
                "date": "2026-01-25",
                "tema": "Amizade",
            },
            {
                "actor": "Carol",
                "target": "Dave",
                "type": "bomba",
                "week": 2,
                "date": "2026-01-25",
                "tema": "Jogo",
            },
            {
                "actor": "Bob",
                "target": "Alice",
                "type": "regua",
                "slot": 3,
                "week": 2,
                "date": "2026-01-25",
                "tema": "Falsidade",
            },
        ],
    }


# ─── Helper: edge collector ─────────────────────────────────────────────────


class EdgeCollector:
    """Collects edges from add_edge_raw calls for assertion."""

    def __init__(self):
        self.edges = []

    def __call__(self, edge_type, actor, target, weight, week=None, date=None,
                 meta=None, revealed=False):
        self.edges.append({
            "type": edge_type,
            "actor": actor,
            "target": target,
            "weight": weight,
            "week": week,
            "date": date,
            "meta": meta or {},
            "revealed": revealed,
        })


# ═══════════════════════════════════════════════════════════════════════════════
# Priority 1: Scoring Helpers
# ═══════════════════════════════════════════════════════════════════════════════


class TestClassifySentiment:
    """Test _classify_sentiment helper."""

    def test_positive(self):
        assert _classify_sentiment("Coração") == "positive"

    def test_strong_negative(self):
        for label in ["Cobra", "Alvo", "Vômito", "Mentiroso"]:
            assert _classify_sentiment(label) == "strong_negative"

    def test_mild_negative(self):
        for label in ["Planta", "Mala", "Biscoito", "Coração partido"]:
            assert _classify_sentiment(label) == "mild_negative"

    def test_unknown_returns_none(self):
        assert _classify_sentiment("Unknown") is None
        assert _classify_sentiment("") is None


class TestSentimentValueForCategory:
    """Test _sentiment_value_for_category helper."""

    def test_values(self):
        assert _sentiment_value_for_category("positive") == 1.0
        assert _sentiment_value_for_category("mild_negative") == -0.5
        assert _sentiment_value_for_category("strong_negative") == -1.0
        assert _sentiment_value_for_category("unknown") == 0.0


class TestBlendStreak:
    """Test _blend_streak() scoring function."""

    def test_no_streak_info_returns_reactive(self):
        """When no streak info exists, return q_reactive unchanged."""
        result = _blend_streak(0.5, "Unknown", "Other", {})
        assert result == 0.5

    def test_no_entry_for_pair_returns_reactive(self):
        """When actor/target not in streak_info, return q_reactive."""
        info = {"Alice": {"Bob": {"streak_len": 3, "streak_sentiment": 1.0}}}
        result = _blend_streak(0.8, "Alice", "Dave", info)
        assert result == 0.8

    def test_positive_streak_blending(self, sample_streak_info):
        """Long positive streak should boost the score via memory component."""
        q_reactive = 0.5
        result = _blend_streak(q_reactive, "Alice", "Bob", sample_streak_info)

        # Q_memory = min(7, 10)/10 * 1.0 = 0.7
        # Q_final = 0.7 * 0.5 + 0.3 * 0.7 + 0 = 0.35 + 0.21 = 0.56
        expected = STREAK_REACTIVE_WEIGHT * q_reactive + STREAK_MEMORY_WEIGHT * (7 / STREAK_MEMORY_MAX_LEN * 1.0)
        assert result == pytest.approx(expected)

    def test_break_penalty_applied(self, sample_streak_info):
        """When break_from_positive is True, penalty should be applied."""
        q_reactive = -0.5
        result = _blend_streak(q_reactive, "Carol", "Dave", sample_streak_info)

        streak = sample_streak_info["Carol"]["Dave"]
        consistency = min(streak["streak_len"], STREAK_MEMORY_MAX_LEN) / STREAK_MEMORY_MAX_LEN
        q_memory = consistency * streak["streak_sentiment"]
        break_pen = STREAK_BREAK_PENALTY * min(streak["previous_streak_len"], STREAK_BREAK_MAX_LEN) / STREAK_BREAK_MAX_LEN

        expected = STREAK_REACTIVE_WEIGHT * q_reactive + STREAK_MEMORY_WEIGHT * q_memory + break_pen
        assert result == pytest.approx(expected)
        # Break penalty is negative, so result should be more negative
        no_break = STREAK_REACTIVE_WEIGHT * q_reactive + STREAK_MEMORY_WEIGHT * q_memory
        assert result < no_break

    def test_result_range_is_reasonable(self, sample_streak_info):
        """Score should be bounded by reasonable sentiment range."""
        # With extreme inputs
        result = _blend_streak(1.0, "Alice", "Bob", sample_streak_info)
        assert -3.0 <= result <= 3.0

        result = _blend_streak(-1.0, "Carol", "Dave", sample_streak_info)
        assert -3.0 <= result <= 3.0

    def test_memory_capped_at_max_len(self):
        """Streak longer than max should be capped at 1.0 consistency."""
        info = {
            "A": {
                "B": {
                    "streak_len": 100,  # Way beyond max
                    "streak_category": "positive",
                    "streak_sentiment": 1.0,
                    "break_from_positive": False,
                },
            },
        }
        result = _blend_streak(0.0, "A", "B", info)
        # consistency = min(100, 10)/10 = 1.0; Q_memory = 1.0
        expected = STREAK_REACTIVE_WEIGHT * 0.0 + STREAK_MEMORY_WEIGHT * 1.0
        assert result == pytest.approx(expected)


class TestComputeStreakData:
    """Test compute_streak_data() streak detection."""

    def test_empty_snapshots(self):
        streak_info, streak_breaks, missing_log = compute_streak_data([])
        assert streak_info == {}
        assert streak_breaks == []
        assert missing_log == []

    def test_single_day_no_break(self):
        """A single day cannot have a streak break."""
        alice = _make_participant("Alice", received_reactions=[
            _make_reaction("Coração", ["Bob"]),
        ])
        bob = _make_participant("Bob", received_reactions=[
            _make_reaction("Coração", ["Alice"]),
        ])
        snaps = [_make_snapshot("2026-01-20", [alice, bob])]
        streak_info, streak_breaks, _ = compute_streak_data(snaps)

        # Should have streak data for both pairs
        assert "Bob" in streak_info  # Bob gave ❤️ to Alice
        assert "Alice" in streak_info.get("Bob", {})
        assert streak_info["Bob"]["Alice"]["streak_len"] == 1
        assert streak_info["Bob"]["Alice"]["streak_category"] == "positive"
        assert streak_breaks == []

    def test_consistent_hearts_build_streak(self, three_person_snapshots):
        """Bob ❤️ Alice for all 5 days should give streak_len=5."""
        streak_info, _, _ = compute_streak_data(three_person_snapshots)
        assert "Bob" in streak_info
        assert "Alice" in streak_info["Bob"]
        bob_to_alice = streak_info["Bob"]["Alice"]
        assert bob_to_alice["streak_len"] == 5
        assert bob_to_alice["streak_category"] == "positive"
        assert bob_to_alice["streak_sentiment"] == 1.0

    def test_streak_break_detected(self, long_positive_then_break_snapshots):
        """6 positive → 2 negative should detect a break."""
        streak_info, streak_breaks, _ = compute_streak_data(
            long_positive_then_break_snapshots
        )
        # Alice→Bob: 6 days positive then 2 days strong_negative
        alice_to_bob = streak_info.get("Alice", {}).get("Bob")
        assert alice_to_bob is not None
        assert alice_to_bob["streak_len"] == 2
        assert alice_to_bob["streak_category"] == "strong_negative"
        assert alice_to_bob["previous_streak_len"] == 6
        assert alice_to_bob["previous_category"] == "positive"
        assert alice_to_bob["break_from_positive"] is True

        # Should appear in streak_breaks list
        assert len(streak_breaks) >= 1
        break_entry = next(
            (b for b in streak_breaks if b["giver"] == "Alice" and b["receiver"] == "Bob"),
            None,
        )
        assert break_entry is not None
        assert break_entry["severity"] == "strong"
        assert break_entry["previous_streak"] == 6

    def test_no_break_if_previous_too_short(self):
        """If previous positive streak < 5, no break detected."""
        days = []
        # 3 positive + 2 negative (previous streak too short for break)
        for i in range(5):
            date = f"2026-02-{10 + i:02d}"
            if i < 3:
                bob = _make_participant("Bob", received_reactions=[
                    _make_reaction("Coração", ["Alice"]),
                ])
            else:
                bob = _make_participant("Bob", received_reactions=[
                    _make_reaction("Cobra", ["Alice"]),
                ])
            alice = _make_participant("Alice", received_reactions=[
                _make_reaction("Coração", ["Bob"]),
            ])
            days.append(_make_snapshot(date, [alice, bob]))

        streak_info, streak_breaks, _ = compute_streak_data(days)
        alice_bob = streak_info.get("Alice", {}).get("Bob", {})
        # Previous streak is 3 (< 5), so no break
        assert alice_bob.get("break_from_positive") is False
        breaks_for_pair = [b for b in streak_breaks if b["giver"] == "Alice" and b["receiver"] == "Bob"]
        assert len(breaks_for_pair) == 0

    def test_eliminated_last_seen_limits_history(self):
        """When a participant is eliminated, streak uses their last_seen date."""
        days = []
        for i in range(5):
            date = f"2026-02-{10 + i:02d}"
            bob = _make_participant("Bob", received_reactions=[
                _make_reaction("Coração", ["Alice"]),
            ])
            alice = _make_participant("Alice", received_reactions=[
                _make_reaction("Coração", ["Bob"]),
            ])
            days.append(_make_snapshot(date, [alice, bob]))

        # Bob was eliminated on day 3
        eliminated_last_seen = {"Bob": "2026-02-12"}
        streak_info, _, _ = compute_streak_data(days, eliminated_last_seen)

        # Bob's outgoing reactions (Bob→Alice) should be limited to 3 days
        bob_to_alice = streak_info.get("Bob", {}).get("Alice", {})
        assert bob_to_alice.get("total_days", 0) == 3


class TestComputeBaseWeights:
    """Test _compute_base_weights() rolling window calculation."""

    def test_single_day_snapshot(self):
        """With one snapshot, weight should reflect that day's reaction."""
        alice = _make_participant("Alice", received_reactions=[
            _make_reaction("Coração", ["Bob"]),
        ])
        bob = _make_participant("Bob", received_reactions=[
            _make_reaction("Cobra", ["Alice"]),
        ])
        snaps = [_make_snapshot("2026-01-20", [alice, bob])]
        matrix = build_reaction_matrix([alice, bob])

        base = _compute_base_weights("2026-01-20", ["Alice", "Bob"], snaps, matrix, {})
        assert "Alice" in base
        assert "Bob" in base["Alice"]
        # build_reaction_matrix: (giver, receiver) → label
        # Alice has receivedReactions with Coração from Bob → matrix[(Bob, Alice)] = Coração
        # Bob has receivedReactions with Cobra from Alice → matrix[(Alice, Bob)] = Cobra
        # So base["Alice"]["Bob"] = sentiment of Alice→Bob = Cobra = -1.0
        # And base["Bob"]["Alice"] = sentiment of Bob→Alice = Coração = 1.0
        assert base["Alice"]["Bob"] == pytest.approx(SENTIMENT_WEIGHTS["Cobra"])
        assert base["Bob"]["Alice"] == pytest.approx(SENTIMENT_WEIGHTS["Coração"])

    def test_three_day_window_weights(self, three_person_snapshots):
        """With 5 days, window should use last 3 days with weighted average."""
        snaps = three_person_snapshots
        matrix = build_reaction_matrix(snaps[-1]["participants"])

        base = _compute_base_weights(
            "2026-01-24",
            ["Alice", "Bob", "Carol"],
            snaps,
            matrix,
            {},
        )
        # Alice→Bob: In the fixture, Bob receives reactions from Alice:
        # Days 1-3: Bob receives ❤️ from Alice → Alice→Bob = ❤️
        # Day 4-5: Bob receives 🐍 from Alice → Alice→Bob = 🐍
        # Window = last 3 days (day3, day4, day5). REACTIVE_WINDOW_WEIGHTS = [0.6, 0.3, 0.1]
        # Weights assigned in order: oldest(day3)=0.6, middle(day4)=0.3, newest(day5)=0.1
        # = 0.6*(+1) + 0.3*(-1) + 0.1*(-1) = 0.6 - 0.3 - 0.1 = 0.2
        alice_to_bob = base["Alice"]["Bob"]
        assert alice_to_bob == pytest.approx(0.2)

        # Bob→Alice: Bob gives ❤️ to Alice all 5 days (Alice receives ❤️ from Bob)
        bob_to_alice = base["Bob"]["Alice"]
        assert bob_to_alice > 0  # All positive

    def test_empty_snapshots(self):
        base = _compute_base_weights("2026-01-20", ["Alice", "Bob"], [], {}, {})
        assert base == {}

    def test_ref_date_filters_snapshots(self, three_person_snapshots):
        """Only snapshots up to ref_date should be used."""
        snaps = three_person_snapshots
        matrix = build_reaction_matrix(snaps[0]["participants"])

        # Only use first 2 days (before the cobra switch)
        base = _compute_base_weights(
            "2026-01-21",
            ["Alice", "Bob", "Carol"],
            snaps,
            matrix,
            {},
        )
        # Alice→Bob should be positive (only hearts in day 1-2)
        assert base["Alice"]["Bob"] > 0


class TestComputeBaseWeightsAll:
    """Test _compute_base_weights_all() with eliminated participants."""

    def test_includes_eliminated(self):
        """Eliminated participants should get base weights from their last_seen."""
        # 3 days of data
        days = []
        for i in range(3):
            date = f"2026-01-{20 + i:02d}"
            alice = _make_participant("Alice", received_reactions=[
                _make_reaction("Coração", ["Bob"]),
            ])
            bob = _make_participant("Bob", received_reactions=[
                _make_reaction("Cobra", ["Alice"]),
            ])
            days.append(_make_snapshot(date, [alice, bob]))

        matrix = build_reaction_matrix(days[-1]["participants"])
        eliminated_last_seen = {"Bob": "2026-01-22"}

        base = _compute_base_weights_all(
            "2026-01-22",
            ["Alice"],  # active
            ["Alice", "Bob"],  # all
            days,
            matrix,
            {},
            eliminated_last_seen,
        )
        assert "Bob" in base
        assert "Alice" in base["Bob"]
        assert "Bob" in base.get("Alice", {})


# ═══════════════════════════════════════════════════════════════════════════════
# Priority 2: Edge Builders
# ═══════════════════════════════════════════════════════════════════════════════


class TestBuildPowerEventEdges:
    """Test _build_power_event_edges() edge generation."""

    def test_basic_edges_created(self, sample_power_events):
        collector = EdgeCollector()
        _build_power_event_edges(sample_power_events, 1, collector)

        # indicacao + contragolpe + monstro → each creates forward + backlash
        assert len(collector.edges) > 0
        types = {e["meta"].get("event_type") for e in collector.edges}
        assert "indicacao" in types
        assert "contragolpe" in types
        assert "monstro" in types

    def test_forward_edge_has_correct_fields(self, sample_power_events):
        collector = EdgeCollector()
        _build_power_event_edges(sample_power_events, 1, collector)

        # Find the indicacao forward edge
        indicacao = next(
            e for e in collector.edges
            if e["meta"].get("event_type") == "indicacao" and not e["meta"].get("backlash")
        )
        assert indicacao["type"] == "power_event"
        assert indicacao["actor"] == "Alice"
        assert indicacao["target"] == "Bob"
        assert indicacao["weight"] < 0  # indicacao is negative
        assert indicacao["week"] == 1
        assert indicacao["date"] == "2026-01-20"

    def test_backlash_created_for_public_events(self, sample_power_events):
        collector = EdgeCollector()
        _build_power_event_edges(sample_power_events, 1, collector)

        backlash_edges = [e for e in collector.edges if e["meta"].get("backlash")]
        assert len(backlash_edges) > 0
        # Backlash goes from target → actor
        ind_backlash = next(
            e for e in backlash_edges
            if e["meta"].get("event_type") == "indicacao"
        )
        assert ind_backlash["actor"] == "Bob"  # target retaliates
        assert ind_backlash["target"] == "Alice"  # against the actor

    def test_no_backlash_for_secret_events(self):
        events = [{
            "type": "indicacao",
            "actor": "Alice",
            "target": "Bob",
            "date": "2026-01-20",
            "week": 1,
            "visibility": "secret",
        }]
        collector = EdgeCollector()
        _build_power_event_edges(events, 1, collector)
        backlash_edges = [e for e in collector.edges if e["meta"].get("backlash")]
        assert len(backlash_edges) == 0

    def test_self_inflicted_skipped(self):
        events = [{
            "type": "indicacao",
            "actor": "Alice",
            "target": "Alice",
            "date": "2026-01-20",
            "week": 1,
            "self": True,
        }]
        collector = EdgeCollector()
        _build_power_event_edges(events, 1, collector)
        assert len(collector.edges) == 0

    def test_system_actor_skipped(self):
        events = [{
            "type": "indicacao",
            "actor": "Prova do Líder",
            "target": "Alice",
            "date": "2026-01-20",
            "week": 1,
        }]
        collector = EdgeCollector()
        _build_power_event_edges(events, 1, collector)
        assert len(collector.edges) == 0

    def test_zero_weight_type_skipped(self):
        events = [{
            "type": "voto_duplo",  # weight = 0.0 in RELATION_POWER_WEIGHTS
            "actor": "Alice",
            "target": "Bob",
            "date": "2026-01-20",
            "week": 1,
        }]
        collector = EdgeCollector()
        _build_power_event_edges(events, 1, collector)
        assert len(collector.edges) == 0

    def test_visibility_factor_applied(self):
        events = [{
            "type": "indicacao",
            "actor": "Alice",
            "target": "Bob",
            "date": "2026-01-20",
            "week": 1,
            "visibility": "secret",
        }]
        collector = EdgeCollector()
        _build_power_event_edges(events, 1, collector)

        edge = collector.edges[0]
        expected_weight = RELATION_POWER_WEIGHTS["indicacao"] * RELATION_VISIBILITY_FACTOR["secret"]
        assert edge["weight"] == pytest.approx(expected_weight)

    def test_consensus_event_multiple_actors(self):
        """Event with actors list should create edges for each actor."""
        events = [{
            "type": "indicacao",
            "actor": "Alice + Bob",
            "actors": ["Alice", "Bob"],
            "target": "Carol",
            "date": "2026-01-20",
            "week": 1,
            "visibility": "public",
        }]
        collector = EdgeCollector()
        _build_power_event_edges(events, 1, collector)

        forward = [e for e in collector.edges if not e["meta"].get("backlash")]
        actors = {e["actor"] for e in forward}
        assert "Alice" in actors
        assert "Bob" in actors


class TestBuildSinceraoEdges:
    """Test _build_sincerao_edges_section() edge generation."""

    def test_podio_creates_positive_edge(self, sample_sincerao_edges):
        collector = EdgeCollector()
        _build_sincerao_edges_section(sample_sincerao_edges, collector)

        podio = next(
            e for e in collector.edges
            if e["meta"].get("sinc_type") == "podio" and not e["meta"].get("backlash")
        )
        assert podio["actor"] == "Alice"
        assert podio["target"] == "Bob"
        assert podio["weight"] > 0  # podio slot 1 = 0.7

    def test_bomba_creates_negative_edge(self, sample_sincerao_edges):
        collector = EdgeCollector()
        _build_sincerao_edges_section(sample_sincerao_edges, collector)

        bomba = next(
            e for e in collector.edges
            if e["meta"].get("sinc_type") == "bomba" and not e["meta"].get("backlash")
        )
        assert bomba["actor"] == "Carol"
        assert bomba["target"] == "Dave"
        assert bomba["weight"] < 0

    def test_bomba_has_backlash(self, sample_sincerao_edges):
        collector = EdgeCollector()
        _build_sincerao_edges_section(sample_sincerao_edges, collector)

        bomba_backlash = [
            e for e in collector.edges
            if e["meta"].get("sinc_type") == "bomba" and e["meta"].get("backlash")
        ]
        assert len(bomba_backlash) == 1
        assert bomba_backlash[0]["actor"] == "Dave"  # target retaliates
        assert bomba_backlash[0]["target"] == "Carol"

    def test_podio_no_backlash(self, sample_sincerao_edges):
        """Podio has no backlash factor defined."""
        collector = EdgeCollector()
        _build_sincerao_edges_section(sample_sincerao_edges, collector)

        podio_backlash = [
            e for e in collector.edges
            if e["meta"].get("sinc_type") == "podio" and e["meta"].get("backlash")
        ]
        assert len(podio_backlash) == 0

    def test_regua_edge(self, sample_sincerao_edges):
        collector = EdgeCollector()
        _build_sincerao_edges_section(sample_sincerao_edges, collector)

        regua = next(
            e for e in collector.edges
            if e["meta"].get("sinc_type") == "regua" and not e["meta"].get("backlash")
        )
        assert regua["actor"] == "Bob"
        assert regua["target"] == "Alice"
        expected_weight = RELATION_SINC_WEIGHTS["regua"][3]  # slot 3
        assert regua["weight"] == pytest.approx(expected_weight)

    def test_empty_edges(self):
        collector = EdgeCollector()
        _build_sincerao_edges_section({"edges": []}, collector)
        assert len(collector.edges) == 0

    def test_none_edges(self):
        collector = EdgeCollector()
        _build_sincerao_edges_section(None, collector)
        assert len(collector.edges) == 0


class TestBuildVoteEdges:
    """Test _build_vote_edges() edge generation."""

    def test_secret_vote_creates_edge(self):
        votes = {1: {"Bob": {"Alice": 1}}}
        collector = EdgeCollector()
        _build_vote_edges(votes, set(), defaultdict(set), {}, {1: "2026-01-20"}, collector)

        assert len(collector.edges) == 1
        edge = collector.edges[0]
        assert edge["actor"] == "Alice"
        assert edge["target"] == "Bob"
        assert edge["weight"] == pytest.approx(RELATION_VOTE_WEIGHTS["secret"])
        assert edge["revealed"] is False

    def test_secret_vote_no_backlash(self):
        votes = {1: {"Bob": {"Alice": 1}}}
        collector = EdgeCollector()
        _build_vote_edges(votes, set(), defaultdict(set), {}, {1: "2026-01-20"}, collector)

        backlash = [e for e in collector.edges if e["actor"] == "Bob"]
        assert len(backlash) == 0

    def test_open_vote_creates_backlash(self):
        votes = {1: {"Bob": {"Alice": 1}}}
        open_weeks = {1}
        collector = EdgeCollector()
        _build_vote_edges(votes, open_weeks, defaultdict(set), {}, {1: "2026-01-20"}, collector)

        # Should have forward + backlash
        assert len(collector.edges) == 2
        forward = next(e for e in collector.edges if e["actor"] == "Alice")
        assert forward["weight"] == pytest.approx(RELATION_VOTE_WEIGHTS["open_vote"])
        assert forward["revealed"] is True

        backlash = next(e for e in collector.edges if e["actor"] == "Bob")
        assert backlash["weight"] == pytest.approx(RELATION_VOTE_WEIGHTS["open_vote_backlash"])

    def test_confissao_vote(self):
        votes = {1: {"Bob": {"Alice": 1}}}
        revealed = defaultdict(set, {"Bob": {"Alice"}})
        revelation_type = {("Alice", "Bob"): "confissao"}
        collector = EdgeCollector()
        _build_vote_edges(votes, set(), revealed, revelation_type, {1: "2026-01-20"}, collector)

        forward = next(e for e in collector.edges if e["actor"] == "Alice")
        assert forward["weight"] == pytest.approx(RELATION_VOTE_WEIGHTS["confissao"])

        backlash = next(e for e in collector.edges if e["actor"] == "Bob")
        assert backlash["weight"] == pytest.approx(RELATION_VOTE_WEIGHTS["confissao_backlash"])

    def test_dedo_duro_vote(self):
        votes = {1: {"Bob": {"Alice": 1}}}
        revealed = defaultdict(set, {"Bob": {"Alice"}})
        revelation_type = {("Alice", "Bob"): "dedo_duro"}
        collector = EdgeCollector()
        _build_vote_edges(votes, set(), revealed, revelation_type, {1: "2026-01-20"}, collector)

        forward = next(e for e in collector.edges if e["actor"] == "Alice")
        assert forward["weight"] == pytest.approx(RELATION_VOTE_WEIGHTS["dedo_duro"])

    def test_double_vote_multiplied(self):
        votes = {1: {"Bob": {"Alice": 2}}}  # voto duplo
        collector = EdgeCollector()
        _build_vote_edges(votes, set(), defaultdict(set), {}, {1: "2026-01-20"}, collector)

        edge = collector.edges[0]
        assert edge["weight"] == pytest.approx(RELATION_VOTE_WEIGHTS["secret"] * 2)

    def test_zero_count_skipped(self):
        votes = {1: {"Bob": {"Alice": 0}}}
        collector = EdgeCollector()
        _build_vote_edges(votes, set(), defaultdict(set), {}, {1: "2026-01-20"}, collector)
        assert len(collector.edges) == 0

    def test_empty_votes(self):
        collector = EdgeCollector()
        _build_vote_edges({}, set(), defaultdict(set), {}, {}, collector)
        assert len(collector.edges) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Priority 3: Data Builders
# ═══════════════════════════════════════════════════════════════════════════════


class TestBuildParticipantsIndex:
    """Test build_participants_index() output structure."""

    def test_basic_output_fields(self):
        alice = _make_participant("Alice", member_of="Pipoca")
        bob = _make_participant("Bob", member_of="Veterano")
        snaps = [_make_snapshot("2026-01-20", [alice, bob])]
        result = build_participants_index(snaps, {})

        assert isinstance(result, list)
        assert len(result) == 2
        names = {r["name"] for r in result}
        assert names == {"Alice", "Bob"}

        for r in result:
            assert "name" in r
            assert "grupo" in r
            assert "avatar" in r
            assert "first_seen" in r
            assert "last_seen" in r
            assert "active" in r

    def test_first_last_seen_tracking(self):
        alice_d1 = _make_participant("Alice")
        bob_d1 = _make_participant("Bob")
        alice_d2 = _make_participant("Alice")
        snaps = [
            _make_snapshot("2026-01-20", [alice_d1, bob_d1]),
            _make_snapshot("2026-01-21", [alice_d2]),  # Bob disappears
        ]
        result = build_participants_index(snaps, {})
        index = {r["name"]: r for r in result}

        assert index["Alice"]["first_seen"] == "2026-01-20"
        assert index["Alice"]["last_seen"] == "2026-01-21"
        assert index["Alice"]["active"] is True

        assert index["Bob"]["first_seen"] == "2026-01-20"
        assert index["Bob"]["last_seen"] == "2026-01-20"
        assert index["Bob"]["active"] is False  # Not in latest snapshot

    def test_manual_status_overrides_active(self):
        alice = _make_participant("Alice")
        snaps = [_make_snapshot("2026-01-20", [alice])]
        manual = {"participants": {"Alice": {"status": "eliminada"}}}
        result = build_participants_index(snaps, manual)
        assert result[0]["active"] is False
        assert result[0]["status"] == "eliminada"

    def test_empty_snapshots(self):
        result = build_participants_index([], {})
        assert result == []

    def test_sorted_by_name(self):
        c = _make_participant("Charlie")
        a = _make_participant("Alice")
        b = _make_participant("Bob")
        snaps = [_make_snapshot("2026-01-20", [c, a, b])]
        result = build_participants_index(snaps, {})
        names = [r["name"] for r in result]
        assert names == ["Alice", "Bob", "Charlie"]


class TestBuildDailyRoles:
    """Test build_daily_roles() roles extraction."""

    def test_basic_role_extraction(self):
        alice = _make_participant("Alice", roles=["Líder"])
        bob = _make_participant("Bob", roles=["Anjo"])
        carol = _make_participant("Carol")
        snaps = [_make_snapshot("2026-01-20", [alice, bob, carol])]
        result = build_daily_roles(snaps)

        assert len(result) == 1
        entry = result[0]
        assert entry["date"] == "2026-01-20"
        assert "Alice" in entry["roles"]["Líder"]
        assert "Bob" in entry["roles"]["Anjo"]
        assert entry["participant_count"] == 3

    def test_vip_tracking(self):
        alice = _make_participant("Alice", group="Vip")
        bob = _make_participant("Bob", group="Xepa")
        snaps = [_make_snapshot("2026-01-20", [alice, bob])]
        result = build_daily_roles(snaps)

        assert "Alice" in result[0]["vip"]
        assert "Bob" not in result[0]["vip"]

    def test_empty_snapshots(self):
        result = build_daily_roles([])
        assert result == []

    def test_all_roles_present_in_output(self):
        p = _make_participant("Alice")
        snaps = [_make_snapshot("2026-01-20", [p])]
        result = build_daily_roles(snaps)

        roles = result[0]["roles"]
        for role in ["Líder", "Anjo", "Monstro", "Imune", "Paredão"]:
            assert role in roles

    def test_multiple_days(self):
        d1 = [_make_participant("Alice", roles=["Líder"]),
              _make_participant("Bob")]
        d2 = [_make_participant("Alice"),
              _make_participant("Bob", roles=["Líder"])]
        snaps = [
            _make_snapshot("2026-01-20", d1),
            _make_snapshot("2026-01-21", d2),
        ]
        result = build_daily_roles(snaps)
        assert len(result) == 2
        assert "Alice" in result[0]["roles"]["Líder"]
        assert "Bob" in result[1]["roles"]["Líder"]


class TestBuildAutoEvents:
    """Test build_auto_events() auto event detection."""

    def test_leader_change_detected(self):
        roles = [
            {"date": "2026-01-20", "roles": {"Líder": ["Alice"], "Anjo": [], "Monstro": [], "Imune": [], "Paredão": []}, "vip": [], "participants": ["Alice", "Bob"], "participant_count": 2},
            {"date": "2026-01-21", "roles": {"Líder": ["Bob"], "Anjo": [], "Monstro": [], "Imune": [], "Paredão": []}, "vip": [], "participants": ["Alice", "Bob"], "participant_count": 2},
        ]
        events = build_auto_events(roles)
        leader_events = [e for e in events if e["type"] == "lider"]
        assert len(leader_events) == 1
        assert leader_events[0]["target"] == "Bob"
        assert leader_events[0]["date"] == "2026-01-21"
        assert leader_events[0]["source"] == "api_roles"

    def test_anjo_change_detected(self):
        roles = [
            {"date": "2026-01-20", "roles": {"Líder": [], "Anjo": ["Alice"], "Monstro": [], "Imune": [], "Paredão": []}, "vip": [], "participants": ["Alice", "Bob"], "participant_count": 2},
            {"date": "2026-01-21", "roles": {"Líder": [], "Anjo": ["Bob"], "Monstro": [], "Imune": [], "Paredão": []}, "vip": [], "participants": ["Alice", "Bob"], "participant_count": 2},
        ]
        events = build_auto_events(roles)
        anjo_events = [e for e in events if e["type"] == "anjo"]
        assert len(anjo_events) == 1
        assert anjo_events[0]["target"] == "Bob"

    def test_monstro_new_added(self):
        roles = [
            {"date": "2026-01-20", "roles": {"Líder": [], "Anjo": ["Alice"], "Monstro": [], "Imune": [], "Paredão": []}, "vip": [], "participants": ["Alice", "Bob", "Carol"], "participant_count": 3},
            {"date": "2026-01-21", "roles": {"Líder": [], "Anjo": ["Alice"], "Monstro": ["Bob"], "Imune": [], "Paredão": []}, "vip": [], "participants": ["Alice", "Bob", "Carol"], "participant_count": 3},
        ]
        events = build_auto_events(roles)
        monstro_events = [e for e in events if e["type"] == "monstro"]
        assert len(monstro_events) == 1
        assert monstro_events[0]["target"] == "Bob"
        assert monstro_events[0]["actor"] == "Alice"  # Anjo gives Monstro

    def test_no_event_when_no_change(self):
        roles = [
            {"date": "2026-01-20", "roles": {"Líder": ["Alice"], "Anjo": [], "Monstro": [], "Imune": [], "Paredão": []}, "vip": [], "participants": ["Alice", "Bob"], "participant_count": 2},
            {"date": "2026-01-21", "roles": {"Líder": ["Alice"], "Anjo": [], "Monstro": [], "Imune": [], "Paredão": []}, "vip": [], "participants": ["Alice", "Bob"], "participant_count": 2},
        ]
        events = build_auto_events(roles)
        assert len(events) == 0

    def test_single_day_no_events(self):
        roles = [
            {"date": "2026-01-20", "roles": {"Líder": ["Alice"], "Anjo": [], "Monstro": [], "Imune": [], "Paredão": []}, "vip": [], "participants": ["Alice"], "participant_count": 1},
        ]
        events = build_auto_events(roles)
        assert events == []

    def test_immunity_detected(self):
        roles = [
            {"date": "2026-01-20", "roles": {"Líder": [], "Anjo": [], "Monstro": [], "Imune": [], "Paredão": []}, "vip": [], "participants": ["Alice", "Bob"], "participant_count": 2},
            {"date": "2026-01-21", "roles": {"Líder": [], "Anjo": [], "Monstro": [], "Imune": ["Alice"], "Paredão": []}, "vip": [], "participants": ["Alice", "Bob"], "participant_count": 2},
        ]
        events = build_auto_events(roles)
        imune_events = [e for e in events if e["type"] == "imunidade"]
        assert len(imune_events) == 1
        assert imune_events[0]["target"] == "Alice"

    def test_event_has_required_fields(self):
        roles = [
            {"date": "2026-01-20", "roles": {"Líder": ["Alice"], "Anjo": [], "Monstro": [], "Imune": [], "Paredão": []}, "vip": [], "participants": ["Alice", "Bob"], "participant_count": 2},
            {"date": "2026-01-21", "roles": {"Líder": ["Bob"], "Anjo": [], "Monstro": [], "Imune": [], "Paredão": []}, "vip": [], "participants": ["Alice", "Bob"], "participant_count": 2},
        ]
        events = build_auto_events(roles)
        assert len(events) == 1
        event = events[0]
        required_fields = {"date", "week", "type", "actor", "target", "detail", "impacto", "origem", "source"}
        assert required_fields.issubset(event.keys())
