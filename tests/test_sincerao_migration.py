"""Tests for Sincerao migration: type dictionary, label resolution, model building."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


# ── Task 1: Type dict + label resolution ──

class TestSincTypeMeta:
    """Central type dictionary covers all edge types."""

    def test_all_known_types_have_metadata(self):
        from builders.index_data_builder import SINC_TYPE_META

        required_types = [
            "elogio", "regua", "ataque", "nao_ganha",
            "paredao_perfeito", "regua_fora", "quem_sai", "prova_eliminou",
        ]
        for t in required_types:
            assert t in SINC_TYPE_META, f"Missing type: {t}"
            meta = SINC_TYPE_META[t]
            assert "label" in meta
            assert "emoji" in meta
            assert "valence" in meta
            assert meta["valence"] in ("pos", "neg")

    def test_no_raw_tokens_in_labels(self):
        """Labels must be human-readable, not raw type tokens."""
        from builders.index_data_builder import SINC_TYPE_META

        raw_tokens = {"regua_fora", "nao_ganha", "paredao_perfeito", "prova_eliminou", "quem_sai"}
        for t, meta in SINC_TYPE_META.items():
            assert meta["label"] not in raw_tokens, f"Raw token leaked as label for {t}: {meta['label']}"
            assert "_" not in meta["label"], f"Underscore in label for {t}: {meta['label']}"

    def test_valence_matches_legacy(self):
        """Valence classification must match the old SINC_VALENCE dict."""
        from builders.index_data_builder import SINC_TYPE_META

        expected = {
            "elogio": "pos", "regua": "pos",
            "ataque": "neg", "nao_ganha": "neg", "paredao_perfeito": "neg",
            "regua_fora": "neg", "quem_sai": "neg", "prova_eliminou": "neg",
        }
        for t, val in expected.items():
            assert SINC_TYPE_META[t]["valence"] == val

    def test_type_meta_covers_all_types_seen_in_data(self):
        """Every Sincerao type present in manual/derived data must be mapped."""
        import json
        from builders.index_data_builder import SINC_TYPE_META

        root = Path(__file__).resolve().parents[1]
        manual = json.loads((root / "data" / "manual_events.json").read_text(encoding="utf-8"))
        derived = json.loads((root / "data" / "derived" / "sincerao_edges.json").read_text(encoding="utf-8"))

        seen_types: set[str] = set()

        for weekly in manual.get("weekly_events", []):
            sinc = weekly.get("sincerao")
            if not sinc:
                continue
            blocks = sinc if isinstance(sinc, list) else [sinc]
            for block in blocks:
                for edge in block.get("edges", []) or []:
                    etype = edge.get("type")
                    if etype:
                        seen_types.add(etype)

        for edge in derived.get("edges", []) or []:
            etype = edge.get("type")
            if etype:
                seen_types.add(etype)

        missing = sorted(t for t in seen_types if t not in SINC_TYPE_META)
        assert missing == [], f"Unmapped Sincerao types in data: {missing}"


class TestResolveSincLabel:
    """resolve_sinc_label() produces human-readable text for any edge."""

    def test_ataque_with_tema_uses_tema(self):
        from builders.index_data_builder import resolve_sinc_label

        result = resolve_sinc_label("ataque", "maior traidor(a)", "Gabriela")
        assert result == "maior traidora"  # feminine resolved

    def test_ataque_with_tema_masculine(self):
        from builders.index_data_builder import resolve_sinc_label

        result = resolve_sinc_label("ataque", "maior traidor(a)", "Breno")
        assert result == "maior traidor"  # masculine resolved

    def test_regua_fora_without_tema_uses_label(self):
        from builders.index_data_builder import resolve_sinc_label

        result = resolve_sinc_label("regua_fora", None, "Breno")
        assert result == "fora da régua"  # human label, not "regua_fora"

    def test_nao_ganha_without_tema(self):
        from builders.index_data_builder import resolve_sinc_label

        result = resolve_sinc_label("nao_ganha", None, "Milena")
        assert "ganha" in result.lower()  # human label
        assert "_" not in result

    def test_elogio_without_tema(self):
        from builders.index_data_builder import resolve_sinc_label

        result = resolve_sinc_label("elogio", None, "Breno")
        assert "elogio" in result.lower()

    def test_unknown_type_humanized_with_underscore_removal(self):
        from builders.index_data_builder import resolve_sinc_label

        result = resolve_sinc_label("new_future_type", None, "Breno")
        assert result == "new future type"  # underscores replaced with spaces
        assert "_" not in result


class TestReactionCanonicalization:
    """Positive heart reaction detection should be accent-tolerant."""

    def test_positive_reaction_accepts_canonical_heart(self):
        from builders.index_data_builder import _is_positive_heart_reaction
        assert _is_positive_heart_reaction("Coração") is True

    def test_positive_reaction_accepts_unaccented_heart(self):
        from builders.index_data_builder import _is_positive_heart_reaction
        assert _is_positive_heart_reaction("Coracao") is True

    def test_positive_reaction_rejects_non_heart(self):
        from builders.index_data_builder import _is_positive_heart_reaction
        assert _is_positive_heart_reaction("Cobra") is False

    def test_canonical_reaction_label_unaccented_heart(self):
        from builders.index_data_builder import _canonical_reaction_label
        assert _canonical_reaction_label("Coracao") == "Coração"


# ── Task 2: Profile sincerao model ──

def _make_sinc_data(edges: list[dict], weeks: list[dict] | None = None,
                    aggregates: list[dict] | None = None) -> dict:
    """Helper to build minimal sinc_data for testing."""
    return {
        "edges": edges,
        "weeks": weeks or [],
        "aggregates": aggregates or [],
    }


def _make_edge(actor: str, target: str, etype: str, week: int,
               tema: str | None = None, slot: int | None = None) -> dict:
    edge = {"actor": actor, "target": target, "type": etype, "week": week, "date": "2026-01-20"}
    if tema:
        edge["tema"] = tema
    if slot is not None:
        edge["slot"] = slot
    return edge


class TestProfileSincerao:
    """New profile sincerao model: received/given split."""

    @pytest.fixture
    def sinc_data_basic(self):
        """Sincerao data with edges for Breno: receives ataque, gives elogio."""
        return _make_sinc_data(
            edges=[
                _make_edge("Alberto Cowboy", "Breno", "ataque", 7, tema="maior traidor(a)"),
                _make_edge("Milena", "Breno", "regua_fora", 7),
                _make_edge("Breno", "Gabriela", "elogio", 7, slot=1),
                _make_edge("Breno", "Alberto Cowboy", "ataque", 7, tema="mais falso(a)"),
                # Older week
                _make_edge("Jonas Sulzbach", "Breno", "elogio", 6, slot=2),
                _make_edge("Breno", "Milena", "nao_ganha", 6),
            ],
            weeks=[
                {"week": 7, "format": "Ataques + Elogios"},
                {"week": 6, "format": "Regua"},
            ],
            aggregates=[
                {"week": 7, "scores": {"Breno": -0.5}, "reasons": {"Breno": ["💣 ataque"]}},
                {"week": 6, "scores": {"Breno": 0.2}, "reasons": {"Breno": ["🏆 elogio"]}},
            ],
        )

    def test_received_current_week(self, sinc_data_basic):
        from builders.index_data_builder import _build_profile_sincerao

        result = _build_profile_sincerao("Breno", sinc_data_basic, current_week=7,
                                          latest_matrix={}, sinc_weeks_meta={7: "Bombas + Podio", 6: "Regua"})
        current_received = result["current"]["received"]
        # Breno receives: ataque from Alberto, regua_fora from Milena in week 7
        assert len(current_received) == 2
        types = {i["type"] for i in current_received}
        assert "ataque" in types
        assert "regua_fora" in types
        # Labels must be human-readable
        for i in current_received:
            assert "_" not in i["label"] or i["type"] == "new_future_type"

    def test_given_current_week(self, sinc_data_basic):
        from builders.index_data_builder import _build_profile_sincerao

        result = _build_profile_sincerao("Breno", sinc_data_basic, current_week=7,
                                          latest_matrix={}, sinc_weeks_meta={7: "Bombas + Podio", 6: "Regua"})
        current_given = result["current"]["given"]
        # Breno gives: elogio to Gabriela, ataque to Alberto in week 7
        assert len(current_given) == 2
        actors = {i["target"] for i in current_given}
        assert "Gabriela" in actors
        assert "Alberto Cowboy" in actors

    def test_summary_totals(self, sinc_data_basic):
        from builders.index_data_builder import _build_profile_sincerao

        result = _build_profile_sincerao("Breno", sinc_data_basic, current_week=7,
                                          latest_matrix={}, sinc_weeks_meta={})
        s = result["summary"]
        # Received: ataque(neg) + regua_fora(neg) in W7, elogio(pos) in W6 = 2 neg, 1 pos
        assert s["received_pos"] == 1
        assert s["received_neg"] == 2
        assert s["received_total"] == 3
        # Given: elogio(pos) + ataque(neg) in W7, nao_ganha(neg) in W6 = 1 pos, 2 neg
        assert s["given_pos"] == 1
        assert s["given_neg"] == 2
        assert s["given_total"] == 3

    def test_season_received_by_week(self, sinc_data_basic):
        from builders.index_data_builder import _build_profile_sincerao

        result = _build_profile_sincerao("Breno", sinc_data_basic, current_week=7,
                                          latest_matrix={}, sinc_weeks_meta={7: "Bombas + Podio", 6: "Regua"})
        season_received = result["season"]["received_by_week"]
        # Should be sorted descending (newest first)
        weeks = [w["week"] for w in season_received]
        assert weeks == [7, 6]
        # Week 7: 2 interactions received
        assert len(season_received[0]["interactions"]) == 2
        # Week 6: 1 interaction received (elogio from Jonas)
        assert len(season_received[1]["interactions"]) == 1

    def test_season_given_by_week(self, sinc_data_basic):
        from builders.index_data_builder import _build_profile_sincerao

        result = _build_profile_sincerao("Breno", sinc_data_basic, current_week=7,
                                          latest_matrix={}, sinc_weeks_meta={7: "Bombas + Podio", 6: "Regua"})
        season_given = result["season"]["given_by_week"]
        weeks = [w["week"] for w in season_given]
        assert weeks == [7, 6]
        # Week 7: 2 given (elogio + ataque)
        assert len(season_given[0]["interactions"]) == 2
        # Week 6: 1 given (nao_ganha)
        assert len(season_given[1]["interactions"]) == 1

    def test_contradiction_detection(self, sinc_data_basic):
        from builders.index_data_builder import _build_profile_sincerao

        # Breno gives ataque to Alberto but also gives Coração in queridometro
        matrix = {("Breno", "Alberto Cowboy"): "Coração"}
        result = _build_profile_sincerao("Breno", sinc_data_basic, current_week=7,
                                          latest_matrix=matrix, sinc_weeks_meta={})
        assert result["summary"]["contradiction_count"] == 1
        assert "Alberto Cowboy" in result["summary"]["contradiction_targets"]

    def test_contradiction_detection_with_unaccented_legacy_label(self, sinc_data_basic):
        from builders.index_data_builder import _build_profile_sincerao

        # Legacy/unaccented label should still count as contradiction
        matrix = {("Breno", "Alberto Cowboy"): "Coracao"}
        result = _build_profile_sincerao("Breno", sinc_data_basic, current_week=7,
                                          latest_matrix=matrix, sinc_weeks_meta={})
        assert result["summary"]["contradiction_count"] == 1

    def test_no_contradiction_without_heart(self, sinc_data_basic):
        from builders.index_data_builder import _build_profile_sincerao

        # Breno gives ataque to Alberto but gives Cobra (no contradiction)
        matrix = {("Breno", "Alberto Cowboy"): "Cobra"}
        result = _build_profile_sincerao("Breno", sinc_data_basic, current_week=7,
                                          latest_matrix=matrix, sinc_weeks_meta={})
        assert result["summary"]["contradiction_count"] == 0

    def test_gender_resolution_in_received(self, sinc_data_basic):
        from builders.index_data_builder import _build_profile_sincerao

        result = _build_profile_sincerao("Breno", sinc_data_basic, current_week=7,
                                          latest_matrix={}, sinc_weeks_meta={})
        ataque_items = [i for i in result["current"]["received"] if i["type"] == "ataque"]
        # "maior traidor(a)" -> "maior traidor" for Breno (masculine)
        assert ataque_items[0]["label"] == "maior traidor"

    def test_regua_fora_gets_human_label(self, sinc_data_basic):
        from builders.index_data_builder import _build_profile_sincerao

        result = _build_profile_sincerao("Breno", sinc_data_basic, current_week=7,
                                          latest_matrix={}, sinc_weeks_meta={})
        fora_items = [i for i in result["current"]["received"] if i["type"] == "regua_fora"]
        assert len(fora_items) == 1
        assert fora_items[0]["label"] == "fora da régua"  # NOT "regua_fora"

    def test_current_week_field(self, sinc_data_basic):
        from builders.index_data_builder import _build_profile_sincerao

        result = _build_profile_sincerao("Breno", sinc_data_basic, current_week=7,
                                          latest_matrix={}, sinc_weeks_meta={})
        assert result["current_week"] == 7

    def test_attack_only_week_has_no_positive_and_still_renders_sections(self):
        """Weeks with only attack options (all negative) should be represented cleanly."""
        from builders.index_data_builder import _build_profile_sincerao

        sinc_data = _make_sinc_data([
            _make_edge("Breno", "Gabriela", "ataque", 8, tema="maior traidor(a)"),
            _make_edge("Breno", "Milena", "ataque", 8, tema="maior traidor(a)"),
            _make_edge("Jonas Sulzbach", "Breno", "ataque", 8, tema="maior traidor(a)"),
        ])
        result = _build_profile_sincerao(
            "Breno",
            sinc_data,
            current_week=8,
            latest_matrix={},
            sinc_weeks_meta={8: "Só ataques"},
        )
        summary = result["summary"]
        assert summary["given_total"] == 2
        assert summary["given_pos"] == 0
        assert summary["given_neg"] == 2
        assert summary["received_total"] == 1
        assert summary["received_pos"] == 0
        assert summary["received_neg"] == 1
        assert result["current"]["given"] != []
        assert result["current"]["received"] != []

    def test_empty_sinc_data(self):
        from builders.index_data_builder import _build_profile_sincerao

        result = _build_profile_sincerao("Breno", _make_sinc_data([]), current_week=7,
                                          latest_matrix={}, sinc_weeks_meta={})
        assert result["summary"]["received_total"] == 0
        assert result["summary"]["given_total"] == 0
        assert result["current"]["received"] == []
        assert result["current"]["given"] == []
        assert result["season"]["received_by_week"] == []
        assert result["season"]["given_by_week"] == []


class TestProfileSincerao_InteractionShape:
    """Each interaction item has the required fields."""

    def test_interaction_has_all_fields(self):
        from builders.index_data_builder import _build_profile_sincerao

        sinc_data = _make_sinc_data([
            _make_edge("Alberto Cowboy", "Breno", "ataque", 7, tema="maior traidor(a)"),
        ])
        result = _build_profile_sincerao("Breno", sinc_data, current_week=7,
                                          latest_matrix={}, sinc_weeks_meta={})
        item = result["current"]["received"][0]
        assert "type" in item
        assert "label" in item
        assert "emoji" in item
        assert "actor" in item
        assert "valence" in item

    def test_given_interaction_has_target(self):
        from builders.index_data_builder import _build_profile_sincerao

        sinc_data = _make_sinc_data([
            _make_edge("Breno", "Gabriela", "elogio", 7, slot=1),
        ])
        result = _build_profile_sincerao("Breno", sinc_data, current_week=7,
                                          latest_matrix={}, sinc_weeks_meta={})
        item = result["current"]["given"][0]
        assert "target" in item
        assert item["target"] == "Gabriela"


# ── Task 3: Radar ──

class TestRadar:
    """Weekly Sincerao radar summary."""

    def test_most_targeted_negative(self):
        from builders.index_data_builder import _compute_sincerao_radar

        edges = [
            _make_edge("A", "Breno", "ataque", 7),
            _make_edge("B", "Breno", "ataque", 7),
            _make_edge("C", "Breno", "nao_ganha", 7),
            _make_edge("A", "Milena", "ataque", 7),
        ]
        radar = _compute_sincerao_radar(edges, week=7, latest_matrix={})
        assert radar["most_targeted_neg"]["names"] == ["Breno"]
        assert radar["most_targeted_neg"]["count"] == 3

    def test_most_praised(self):
        from builders.index_data_builder import _compute_sincerao_radar

        edges = [
            _make_edge("A", "Gabriela", "elogio", 7, slot=1),
            _make_edge("B", "Gabriela", "elogio", 7, slot=2),
            _make_edge("A", "Breno", "elogio", 7, slot=1),
        ]
        radar = _compute_sincerao_radar(edges, week=7, latest_matrix={})
        assert radar["most_praised"]["names"] == ["Gabriela"]
        assert radar["most_praised"]["count"] == 2

    def test_ties_shown_explicitly(self):
        from builders.index_data_builder import _compute_sincerao_radar

        edges = [
            _make_edge("A", "Breno", "ataque", 7),
            _make_edge("A", "Milena", "ataque", 7),
        ]
        radar = _compute_sincerao_radar(edges, week=7, latest_matrix={})
        assert sorted(radar["most_targeted_neg"]["names"]) == ["Breno", "Milena"]
        assert radar["most_targeted_neg"]["count"] == 1

    def test_highest_contradiction_count(self):
        from builders.index_data_builder import _compute_sincerao_radar

        edges = [
            _make_edge("Breno", "Alberto Cowboy", "ataque", 7),
            _make_edge("Breno", "Milena", "nao_ganha", 7),
            _make_edge("Jonas Sulzbach", "Gabriela", "ataque", 7),
        ]
        matrix = {
            ("Breno", "Alberto Cowboy"): "Coração",
            ("Breno", "Milena"): "Coração",
            ("Jonas Sulzbach", "Gabriela"): "Cobra",  # not a contradiction
        }
        radar = _compute_sincerao_radar(edges, week=7, latest_matrix=matrix)
        assert radar["most_contradictions"]["names"] == ["Breno"]
        assert radar["most_contradictions"]["count"] == 2

    def test_empty_week_returns_empty_radar(self):
        from builders.index_data_builder import _compute_sincerao_radar

        radar = _compute_sincerao_radar([], week=7, latest_matrix={})
        assert radar["most_targeted_neg"]["names"] == []
        assert radar["most_praised"]["names"] == []
        assert radar["most_contradictions"]["names"] == []

    def test_radar_contradictions_accept_unaccented_matrix_label(self):
        from builders.index_data_builder import _compute_sincerao_radar

        edges = [_make_edge("Breno", "Alberto Cowboy", "ataque", 7)]
        matrix = {("Breno", "Alberto Cowboy"): "Coracao"}  # legacy/unaccented
        radar = _compute_sincerao_radar(edges, week=7, latest_matrix=matrix)
        assert radar["most_contradictions"]["names"] == ["Breno"]
        assert radar["most_contradictions"]["count"] == 1

    def test_radar_active_only_scope_filters_inactive_names(self):
        from builders.index_data_builder import _compute_sincerao_radar

        edges = [
            _make_edge("Breno", "Milena", "ataque", 7),        # active pair
            _make_edge("Eliminado", "Milena", "ataque", 7),    # inactive actor
            _make_edge("Breno", "Eliminado", "elogio", 7),     # inactive target
        ]
        radar = _compute_sincerao_radar(
            edges,
            week=7,
            latest_matrix={("Breno", "Milena"): "Coração"},
            active_set={"Breno", "Milena"},
        )
        assert radar["most_targeted_neg"]["names"] == ["Milena"]
        assert radar["most_targeted_neg"]["count"] == 1
        assert radar["most_praised"]["names"] == []


# ── Week resolution / reaction-date anchoring ──

class TestSincWeekResolution:
    """When a new week starts without Sincerao, keep the last Sincerao week."""

    def test_falls_back_to_latest_available_week(self):
        from builders.index_data_builder import _resolve_sinc_week

        sinc_data = _make_sinc_data(
            edges=[_make_edge("A", "B", "ataque", 7)],
            aggregates=[{"week": 7, "scores": {"B": -1}}],
        )
        week_used, available = _resolve_sinc_week(sinc_data, current_week=8)
        assert available == [7]
        assert week_used == 7

    def test_matrix_resolution_prefers_exact_then_previous_date(self):
        from builders.index_data_builder import _resolve_matrix_for_date

        daily_snapshots = [
            {"date": "2026-03-01"},
            {"date": "2026-03-02"},
            {"date": "2026-03-04"},
        ]
        daily_matrices = [
            {("A", "B"): "Coração"},
            {("A", "B"): "Cobra"},
            {("A", "B"): "Planta"},
        ]

        matrix, matrix_date = _resolve_matrix_for_date(
            "2026-03-03",
            daily_snapshots,
            daily_matrices,
            fallback_matrix={("A", "B"): "Mala"},
            fallback_date="2026-02-28",
        )
        assert matrix_date == "2026-03-02"
        assert matrix[("A", "B")] == "Cobra"


class TestDailyCardsReferenceDate:
    """Daily cards should anchor to the latest complete matrix day."""

    @staticmethod
    def _participant(name: str) -> dict:
        return {"name": name, "characteristics": {"receivedReactions": []}}

    def test_daily_cards_use_last_complete_day(self):
        from builders.index_data_builder import _compute_daily_movers_cards

        daily_snapshots = [
            {"date": "2026-03-01", "participants": [self._participant("A"), self._participant("B")]},
            {"date": "2026-03-02", "participants": [self._participant("A"), self._participant("B")]},
            {"date": "2026-03-03", "participants": [self._participant("A"), self._participant("B")]},
        ]
        # Day 3 is intentionally incomplete (only 1/2 directed pairs).
        daily_matrices = [
            {("A", "B"): "Coração", ("B", "A"): "Coração"},
            {("A", "B"): "Cobra", ("B", "A"): "Coração"},
            {("A", "B"): "Cobra"},
        ]

        _highlights, cards = _compute_daily_movers_cards(daily_snapshots, daily_matrices, ["A", "B"])
        by_type = {c.get("type"): c for c in cards}

        assert by_type["changes"]["reference_date"] == "2026-03-02"
        assert by_type["changes"]["from_date"] == "2026-03-01"
        assert by_type["changes"]["to_date"] == "2026-03-02"
        assert "net" in by_type["changes"]
        assert by_type["dramatic"]["reference_date"] == "2026-03-02"
        assert by_type["hostilities"]["reference_date"] == "2026-03-02"
        assert by_type["dramatic"]["scope"] == "today"
        assert by_type["hostilities"]["scope"] == "today"
        assert by_type["dramatic"]["state"] == "today"
        assert by_type["hostilities"]["state"] == "today"
        assert by_type["dramatic"]["display_limit"] == 4
        assert by_type["hostilities"]["display_limit"] == 4
        assert by_type["dramatic"]["event_latest_date"] == "2026-03-02"
        assert by_type["hostilities"]["event_latest_date"] == "2026-03-02"
        assert by_type["dramatic"]["items"][0]["date"] == "2026-03-02"
        assert by_type["hostilities"]["items"][0]["date"] == "2026-03-02"

    def test_daily_cards_emit_empty_state_cards_when_no_events(self):
        from builders.index_data_builder import _compute_daily_movers_cards

        daily_snapshots = [
            {"date": "2026-03-01", "participants": [self._participant("A"), self._participant("B")]},
            {"date": "2026-03-02", "participants": [self._participant("A"), self._participant("B")]},
        ]
        daily_matrices = [
            {("A", "B"): "Coração", ("B", "A"): "Coração"},
            {("A", "B"): "Coração", ("B", "A"): "Coração"},
        ]

        _highlights, cards = _compute_daily_movers_cards(daily_snapshots, daily_matrices, ["A", "B"])
        by_type = {c.get("type"): c for c in cards}

        assert by_type["dramatic"]["state"] == "empty"
        assert by_type["hostilities"]["state"] == "empty"
        assert by_type["dramatic"]["scope"] == "empty"
        assert by_type["hostilities"]["scope"] == "empty"
        assert by_type["dramatic"]["items"] == []
        assert by_type["hostilities"]["items"] == []
        assert by_type["dramatic"]["total"] == 0
        assert by_type["hostilities"]["total"] == 0


class TestBreaksCardReferenceDate:
    """Break card should expose the date anchor used for relative age labels."""

    def test_breaks_card_carries_reference_date(self):
        from builders.index_data_builder import _compute_breaks_and_context_cards

        relations_data = {
            "streak_breaks": [
                {
                    "giver": "A",
                    "receiver": "B",
                    "previous_streak": 6,
                    "new_emoji": "Cobra",
                    "severity": "strong",
                    "date": "2026-03-01",
                }
            ]
        }
        latest = {"participants": [{"name": "A", "characteristics": {}}, {"name": "B", "characteristics": {}}]}

        _highlights, cards = _compute_breaks_and_context_cards(
            relations_data=relations_data,
            active_set={"A", "B"},
            latest=latest,
            current_week=8,
            daily_snapshots=[{"date": "2026-03-01", "participants": latest["participants"]}],
            reference_date="2026-03-05",
        )

        breaks_card = next(c for c in cards if c.get("type") == "breaks")
        assert breaks_card["reference_date"] == "2026-03-05"
        assert breaks_card["display_limit"] == 4
        assert breaks_card["event_latest_date"] == "2026-03-01"


# ── Task 4: Contract tests (run after builder wiring) ──

class TestTopLevelSincerao:
    """Contract test for the top-level sincerao shape in index_data.json."""

    def test_new_keys_present(self):
        import json
        path = Path(__file__).resolve().parents[1] / "data" / "derived" / "index_data.json"
        if not path.exists():
            pytest.skip("index_data.json not built yet")
        with open(path) as f:
            data = json.load(f)
        sinc = data.get("sincerao", {})
        assert "current_week" in sinc
        assert "available_weeks" in sinc
        assert "reaction_reference_date" in sinc
        assert "radar" in sinc
        assert sinc.get("radar", {}).get("scope") == "active_only"
        assert "type_coverage" in sinc
        assert "seen" in sinc["type_coverage"]
        assert "unknown" in sinc["type_coverage"]
        if sinc.get("current_week") is not None:
            assert sinc.get("reaction_reference_date")
        pairs = sinc.get("pairs", {})
        assert "contradictions" in pairs
        assert "aligned_positive" in pairs
        assert "aligned_negative" in pairs

    def test_removed_keys_absent(self):
        import json
        path = Path(__file__).resolve().parents[1] / "data" / "derived" / "index_data.json"
        if not path.exists():
            pytest.skip("index_data.json not built yet")
        with open(path) as f:
            data = json.load(f)
        sinc = data.get("sincerao", {})
        assert "week" not in sinc  # renamed to current_week
        pairs = sinc.get("pairs", {})
        assert "aligned_pos" not in pairs
        assert "aligned_neg" not in pairs

    def test_highlight_card_carries_reaction_reference_date(self):
        import json
        path = Path(__file__).resolve().parents[1] / "data" / "derived" / "index_data.json"
        if not path.exists():
            pytest.skip("index_data.json not built yet")
        with open(path) as f:
            data = json.load(f)
        sinc = data.get("sincerao", {})
        cards = data.get("highlights", {}).get("cards", [])
        sinc_card = next((c for c in cards if c.get("type") == "sincerao"), None)
        if not sinc_card:
            pytest.skip("No sincerao highlight card for current dataset")
        assert sinc_card.get("week") == sinc.get("current_week")
        if sinc.get("current_week") is not None:
            assert sinc_card.get("reaction_reference_date") == sinc.get("reaction_reference_date")

    def test_list_cards_expose_full_payload_for_in_card_toggles(self):
        """List cards must carry full payloads so index can expand all rows in-card."""
        from builders.index_data_builder import build_index_data

        data = build_index_data()
        if not data:
            pytest.skip("index data unavailable for this environment")

        cards = {c.get("type"): c for c in data.get("highlights", {}).get("cards", [])}

        ranking = cards.get("ranking")
        if ranking:
            assert "podium_all" in ranking
            assert "bottom_all" in ranking
            assert "delta_all" in ranking
            assert len(ranking.get("podium_all", [])) >= len(ranking.get("podium", []))
            assert len(ranking.get("bottom_all", [])) >= len(ranking.get("bottom3", []))

        alvo = cards.get("mais_alvo")
        if alvo:
            assert "items_all" in alvo
            assert "items_recent_all" in alvo
            assert len(alvo.get("items_all", [])) >= len(alvo.get("items", []))
            assert len(alvo.get("items_recent_all", [])) >= len(alvo.get("items_recent", []))

        agressor = cards.get("mais_agressor")
        if agressor:
            assert "items_all" in agressor
            assert len(agressor.get("items_all", [])) >= len(agressor.get("items", []))

        vuln = cards.get("vulnerability")
        if vuln:
            assert "items_all" in vuln
            assert len(vuln.get("items_all", [])) >= len(vuln.get("items", []))

        blindados = cards.get("blindados")
        if blindados:
            assert "items_all" in blindados
            assert len(blindados.get("items_all", [])) >= len(blindados.get("items", []))
            assert blindados.get("display_limit") == 4
            # Verify new fields from Phase 1 bug fixes
            if blindados["items_all"]:
                item = blindados["items_all"][0]
                for field in ("exposure", "bv_escapes", "votes_total", "votes_available",
                              "by_lider", "by_casa", "by_dynamic", "nom_text", "bv_text",
                              "last_voted_paredao"):
                    assert field in item, f"Missing field '{field}' in blindados item"


class TestProfileSincerao_Contract:
    """Contract test for profiles[*].sincerao shape."""

    def test_new_profile_sincerao_shape(self):
        import json
        path = Path(__file__).resolve().parents[1] / "data" / "derived" / "index_data.json"
        if not path.exists():
            pytest.skip("index_data.json not built yet")
        with open(path) as f:
            data = json.load(f)
        for prof in data.get("profiles", [])[:3]:
            sinc = prof.get("sincerao", {})
            assert "current_week" in sinc
            assert "summary" in sinc
            s = sinc["summary"]
            assert "received_total" in s
            assert "received_pos" in s
            assert "received_neg" in s
            assert "given_total" in s
            assert "given_pos" in s
            assert "given_neg" in s
            assert "contradiction_count" in s
            assert "contradiction_targets" in s
            assert "current" in sinc
            assert "received" in sinc["current"]
            assert "given" in sinc["current"]
            assert "season" in sinc
            assert "received_by_week" in sinc["season"]
            assert "given_by_week" in sinc["season"]
            for wk in sinc["season"].get("received_by_week", []):
                assert "meta" in wk
                assert "count_total" in wk["meta"]
                assert "count_pos" in wk["meta"]
                assert "count_neg" in wk["meta"]
            for wk in sinc["season"].get("given_by_week", []):
                assert "meta" in wk
                assert "count_total" in wk["meta"]
                assert "count_pos" in wk["meta"]
                assert "count_neg" in wk["meta"]

    def test_removed_profile_keys_absent(self):
        import json
        path = Path(__file__).resolve().parents[1] / "data" / "derived" / "index_data.json"
        if not path.exists():
            pytest.skip("index_data.json not built yet")
        with open(path) as f:
            data = json.load(f)
        for prof in data.get("profiles", [])[:3]:
            sinc = prof.get("sincerao", {})
            assert "reasons" not in sinc
            assert "bombas" not in sinc
            assert "all_interactions" not in sinc
            assert "sinc_contra" not in prof  # moved into sincerao.summary


class TestStaticCardOrderingContract:
    def test_visados_renders_after_blindados(self):
        from builders.index_data_builder import build_index_data

        data = build_index_data()
        cards = data.get("highlights", {}).get("cards", [])
        types = [c.get("type") for c in cards]
        if "blindados" not in types or "visados" not in types:
            pytest.skip("blindados/visados cards not present")

        blindados_idx = types.index("blindados")
        visados_idx = types.index("visados")
        assert visados_idx == blindados_idx + 1, (
            f"visados must come immediately after blindados, got indexes "
            f"{blindados_idx} and {visados_idx}"
        )

    def test_qmd_story_order_places_visados_after_blindados(self):
        import re

        qmd_path = Path(__file__).resolve().parents[1] / "index.qmd"
        if not qmd_path.exists():
            pytest.skip("index.qmd not available")
        text = qmd_path.read_text(encoding="utf-8")
        m = re.search(r"CARD_STORY_ORDER\s*=\s*\{(?P<body>.*?)\n\}", text, re.S)
        assert m, "CARD_STORY_ORDER map not found in index.qmd"
        body = m.group("body")
        keys = re.findall(r'"([^"]+)"\s*:', body)
        assert "blindados" in keys
        assert "visados" in keys
        blindados_idx = keys.index("blindados")
        visados_idx = keys.index("visados")
        assert visados_idx == blindados_idx + 1, (
            f"index.qmd CARD_STORY_ORDER must place visados immediately after blindados; "
            f"got {blindados_idx} and {visados_idx}"
        )
