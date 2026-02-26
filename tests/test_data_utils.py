"""Tests for data_utils.py core functions."""
import pytest
from datetime import datetime, timezone, timedelta
from data_utils import (
    calc_sentiment,
    utc_to_game_date,
    get_week_number,
    get_week_start_date,
    parse_roles,
    build_reaction_matrix,
    SENTIMENT_WEIGHTS,
    POSITIVE,
    MILD_NEGATIVE,
    STRONG_NEGATIVE,
)


class TestCalcSentiment:
    """Test calc_sentiment() function."""

    def test_positive_only(self):
        """Participant with only hearts should have positive sentiment."""
        p = {
            "characteristics": {
                "receivedReactions": [
                    {"label": "Coração", "amount": 3, "participants": []},
                ],
            },
        }
        score = calc_sentiment(p)
        assert score > 0
        assert score == 3.0

    def test_mixed_reactions(self, sample_participant):
        """Mixed reactions: 2 hearts (+2), 1 cobra (-1), 1 planta (-0.5) = 0.5."""
        score = calc_sentiment(sample_participant)
        assert isinstance(score, (int, float))
        assert score == pytest.approx(0.5)

    def test_empty_reactions(self):
        """Participant with no reactions should have 0 sentiment."""
        p = {"characteristics": {"receivedReactions": []}}
        score = calc_sentiment(p)
        assert score == 0.0

    def test_no_characteristics(self):
        """Participant without characteristics key should have 0 sentiment."""
        p = {}
        score = calc_sentiment(p)
        assert score == 0.0

    def test_all_negative(self):
        """All strong negative should give very negative score."""
        p = {
            "characteristics": {
                "receivedReactions": [
                    {"label": "Cobra", "amount": 3, "participants": []},
                    {"label": "Alvo", "amount": 1, "participants": []},
                ],
            },
        }
        score = calc_sentiment(p)
        assert score < 0
        assert score == -4.0

    def test_weight_correctness(self):
        """Verify weights match documented values."""
        assert SENTIMENT_WEIGHTS.get("Coração") == 1.0
        assert SENTIMENT_WEIGHTS.get("Cobra") == -1.0
        assert SENTIMENT_WEIGHTS.get("Planta") == -0.5
        assert SENTIMENT_WEIGHTS.get("Coração partido") == -0.5
        for label in POSITIVE:
            assert SENTIMENT_WEIGHTS.get(label, 0) > 0
        for label in STRONG_NEGATIVE:
            assert SENTIMENT_WEIGHTS.get(label, 0) < 0
        for label in MILD_NEGATIVE:
            assert SENTIMENT_WEIGHTS.get(label, 0) < 0

    def test_category_membership(self):
        """Verify all weighted reactions belong to a category."""
        all_categories = POSITIVE | MILD_NEGATIVE | STRONG_NEGATIVE
        for label in SENTIMENT_WEIGHTS:
            assert label in all_categories, f"{label} not in any category"


class TestUtcToGameDate:
    """Test utc_to_game_date() function."""

    def test_afternoon_brt(self):
        """15:00 UTC (12:00 BRT) should be same day."""
        dt = datetime(2026, 1, 20, 15, 0, 0, tzinfo=timezone.utc)
        result = utc_to_game_date(dt)
        assert result == "2026-01-20"

    def test_early_morning_prev_day(self):
        """05:00 UTC (02:00 BRT) should be PREVIOUS game day."""
        dt = datetime(2026, 1, 20, 5, 0, 0, tzinfo=timezone.utc)
        result = utc_to_game_date(dt)
        assert result == "2026-01-19"

    def test_6am_cutoff(self):
        """09:00 UTC (06:00 BRT) should be current day (cutoff boundary)."""
        dt = datetime(2026, 1, 20, 9, 0, 0, tzinfo=timezone.utc)
        result = utc_to_game_date(dt)
        assert result == "2026-01-20"

    def test_midnight_utc(self):
        """00:00 UTC (21:00 BRT prev day) should be previous day."""
        dt = datetime(2026, 1, 20, 0, 0, 0, tzinfo=timezone.utc)
        result = utc_to_game_date(dt)
        assert result == "2026-01-19"

    def test_just_before_cutoff(self):
        """08:59 UTC (05:59 BRT) should be PREVIOUS game day."""
        dt = datetime(2026, 1, 20, 8, 59, 0, tzinfo=timezone.utc)
        result = utc_to_game_date(dt)
        assert result == "2026-01-19"

    def test_returns_string(self):
        """Result should always be a YYYY-MM-DD string."""
        dt = datetime(2026, 2, 15, 18, 0, 0, tzinfo=timezone.utc)
        result = utc_to_game_date(dt)
        assert isinstance(result, str)
        assert len(result) == 10
        assert result[4] == "-" and result[7] == "-"


class TestGetWeekNumber:
    """Test get_week_number() — Líder-transition-based week boundaries."""

    def test_premiere_day(self):
        """Premiere day (2026-01-13) should be week 1."""
        assert get_week_number("2026-01-13") == 1

    def test_day_before_premiere(self):
        """Day before premiere should be clamped to 1."""
        assert get_week_number("2026-01-12") == 1

    def test_paredao_result_in_same_week(self):
        """Paredão result days belong to the week they close."""
        assert get_week_number("2026-01-21") == 1  # 1st paredão
        assert get_week_number("2026-01-27") == 2  # 2nd paredão
        assert get_week_number("2026-02-03") == 3  # 3rd paredão
        assert get_week_number("2026-02-10") == 4  # 4th paredão
        assert get_week_number("2026-02-17") == 5  # 5th paredão
        assert get_week_number("2026-02-25") == 6  # 6th paredão

    def test_barrado_in_same_week_as_lider(self):
        """Barrado no baile lands in the week of the Líder who decided it."""
        assert get_week_number("2026-01-21") == 1  # Alberto barrado
        assert get_week_number("2026-01-28") == 2  # Babu barrado
        assert get_week_number("2026-02-04") == 3  # Maxiane barrado
        assert get_week_number("2026-02-11") == 4  # Jonas barrado
        assert get_week_number("2026-02-18") == 5  # Jonas barrado

    def test_new_lider_starts_new_week(self):
        """New Líder definition day starts the next week."""
        assert get_week_number("2026-01-22") == 2  # Babu Líder
        assert get_week_number("2026-01-29") == 3  # Maxiane Líder
        assert get_week_number("2026-02-05") == 4  # Jonas Líder
        assert get_week_number("2026-02-13") == 5  # Jonas 2nd Líder

    def test_after_last_week(self):
        """Day after last known week boundary starts the next week."""
        assert get_week_number("2026-02-26") == 7

    def test_monotonic_increase(self):
        """Week numbers should be monotonically non-decreasing."""
        dates = ["2026-01-13", "2026-01-21", "2026-01-22", "2026-01-28",
                 "2026-01-29", "2026-02-04", "2026-02-05", "2026-02-12",
                 "2026-02-13", "2026-02-18", "2026-02-25", "2026-02-26"]
        weeks = [get_week_number(d) for d in dates]
        for i in range(1, len(weeks)):
            assert weeks[i] >= weeks[i - 1]


class TestGetWeekStartDate:
    """Test get_week_start_date() — derives start date for each game week."""

    def test_week_1_starts_at_premiere(self):
        assert get_week_start_date(1) == "2026-01-13"

    def test_week_2_starts_after_week_1_end(self):
        assert get_week_start_date(2) == "2026-01-22"

    def test_week_3_starts_after_week_2_end(self):
        assert get_week_start_date(3) == "2026-01-29"

    def test_week_4_jonas_first_term(self):
        assert get_week_start_date(4) == "2026-02-05"

    def test_week_5_jonas_second_term(self):
        assert get_week_start_date(5) == "2026-02-13"

    def test_week_6_jonas_third_term(self):
        assert get_week_start_date(6) == "2026-02-19"

    def test_open_week_after_last_boundary(self):
        assert get_week_start_date(7) == "2026-02-26"

    def test_week_0_clamps_to_premiere(self):
        assert get_week_start_date(0) == "2026-01-13"


class TestParseRoles:
    """Test parse_roles() function."""

    def test_dict_format(self):
        """Parse roles from dict format: [{'label': 'Líder'}, ...]."""
        roles = parse_roles([{"label": "Líder"}, {"label": "Anjo"}])
        assert "Líder" in roles
        assert "Anjo" in roles

    def test_string_format(self):
        """Parse roles from string list format."""
        roles = parse_roles(["Líder", "Anjo"])
        assert "Líder" in roles
        assert "Anjo" in roles

    def test_mixed_format(self):
        """Parse roles from mixed dict + string list."""
        roles = parse_roles([{"label": "Líder"}, "Monstro"])
        assert "Líder" in roles
        assert "Monstro" in roles

    def test_empty_none(self):
        """None/empty should return empty list."""
        assert parse_roles(None) == []
        assert parse_roles([]) == []

    def test_filters_empty_labels(self):
        """Should filter out empty string labels."""
        roles = parse_roles([{"label": "Líder"}, {"label": ""}, "Anjo", ""])
        assert "" not in roles
        assert len(roles) == 2

    def test_dict_without_label(self):
        """Dict without 'label' key should produce empty string (filtered out)."""
        roles = parse_roles([{"role": "Líder"}])
        assert roles == []


class TestBuildReactionMatrix:
    """Test build_reaction_matrix() function."""

    def test_basic_matrix(self, sample_participants):
        """Build matrix from 4 participants with cross-reactions."""
        matrix = build_reaction_matrix(sample_participants)
        assert isinstance(matrix, dict)
        # Bob gave Alice Coração (Bob is in Alice's heart participants)
        assert matrix.get(("Bob", "Alice")) == "Coração"
        # Dave gave Alice Cobra (Dave is in Alice's cobra participants)
        assert matrix.get(("Dave", "Alice")) == "Cobra"

    def test_all_pairs_present(self, sample_participants):
        """Matrix should have entries for all giver-receiver pairs that exist."""
        matrix = build_reaction_matrix(sample_participants)
        # Carol gave Alice Coração
        assert matrix.get(("Carol", "Alice")) == "Coração"
        # Carol gave Bob Planta
        assert matrix.get(("Carol", "Bob")) == "Planta"
        # Dave gave Bob Alvo
        assert matrix.get(("Dave", "Bob")) == "Alvo"
        # Alice, Bob, Dave all gave Carol Coração
        assert matrix.get(("Alice", "Carol")) == "Coração"
        assert matrix.get(("Bob", "Carol")) == "Coração"
        assert matrix.get(("Dave", "Carol")) == "Coração"

    def test_empty_participants(self):
        """Empty list should return empty matrix."""
        matrix = build_reaction_matrix([])
        assert matrix == {}

    def test_no_self_reactions(self, sample_participants):
        """No participant should have a reaction to themselves."""
        matrix = build_reaction_matrix(sample_participants)
        for giver, receiver in matrix:
            assert giver != receiver

    def test_real_snapshot_integration(self, real_snapshot):
        """Integration test with real snapshot data."""
        matrix = build_reaction_matrix(real_snapshot)
        assert len(matrix) > 0
        # All keys should be (str, str) tuples
        for key in matrix:
            assert isinstance(key, tuple)
            assert len(key) == 2
            assert isinstance(key[0], str)
            assert isinstance(key[1], str)
