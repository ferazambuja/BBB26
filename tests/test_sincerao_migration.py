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
            "podio", "regua", "bomba", "nao_ganha",
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
            "podio": "pos", "regua": "pos",
            "bomba": "neg", "nao_ganha": "neg", "paredao_perfeito": "neg",
            "regua_fora": "neg", "quem_sai": "neg", "prova_eliminou": "neg",
        }
        for t, val in expected.items():
            assert SINC_TYPE_META[t]["valence"] == val


class TestResolveSincLabel:
    """resolve_sinc_label() produces human-readable text for any edge."""

    def test_bomba_with_tema_uses_tema(self):
        from builders.index_data_builder import resolve_sinc_label

        result = resolve_sinc_label("bomba", "maior traidor(a)", "Gabriela")
        assert result == "maior traidora"  # feminine resolved

    def test_bomba_with_tema_masculine(self):
        from builders.index_data_builder import resolve_sinc_label

        result = resolve_sinc_label("bomba", "maior traidor(a)", "Breno")
        assert result == "maior traidor"  # masculine resolved

    def test_regua_fora_without_tema_uses_label(self):
        from builders.index_data_builder import resolve_sinc_label

        result = resolve_sinc_label("regua_fora", None, "Breno")
        assert result == "fora da regua"  # human label, not "regua_fora"

    def test_nao_ganha_without_tema(self):
        from builders.index_data_builder import resolve_sinc_label

        result = resolve_sinc_label("nao_ganha", None, "Milena")
        assert "ganha" in result.lower()  # human label
        assert "_" not in result

    def test_podio_without_tema(self):
        from builders.index_data_builder import resolve_sinc_label

        result = resolve_sinc_label("podio", None, "Breno")
        assert "podio" in result.lower() or "pódio" in result.lower()

    def test_unknown_type_humanized_with_underscore_removal(self):
        from builders.index_data_builder import resolve_sinc_label

        result = resolve_sinc_label("new_future_type", None, "Breno")
        assert result == "new future type"  # underscores replaced with spaces
        assert "_" not in result


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
        """Sincerao data with edges for Breno: receives bomba, gives podio."""
        return _make_sinc_data(
            edges=[
                _make_edge("Alberto Cowboy", "Breno", "bomba", 7, tema="maior traidor(a)"),
                _make_edge("Milena", "Breno", "regua_fora", 7),
                _make_edge("Breno", "Gabriela", "podio", 7, slot=1),
                _make_edge("Breno", "Alberto Cowboy", "bomba", 7, tema="mais falso(a)"),
                # Older week
                _make_edge("Jonas Sulzbach", "Breno", "podio", 6, slot=2),
                _make_edge("Breno", "Milena", "nao_ganha", 6),
            ],
            weeks=[
                {"week": 7, "format": "Bombas + Podio"},
                {"week": 6, "format": "Regua"},
            ],
            aggregates=[
                {"week": 7, "scores": {"Breno": -0.5}, "reasons": {"Breno": ["💣 bomba"]}},
                {"week": 6, "scores": {"Breno": 0.2}, "reasons": {"Breno": ["🏆 podio"]}},
            ],
        )

    def test_received_current_week(self, sinc_data_basic):
        from builders.index_data_builder import _build_profile_sincerao

        result = _build_profile_sincerao("Breno", sinc_data_basic, current_week=7,
                                          latest_matrix={}, sinc_weeks_meta={7: "Bombas + Podio", 6: "Regua"})
        current_received = result["current"]["received"]
        # Breno receives: bomba from Alberto, regua_fora from Milena in week 7
        assert len(current_received) == 2
        types = {i["type"] for i in current_received}
        assert "bomba" in types
        assert "regua_fora" in types
        # Labels must be human-readable
        for i in current_received:
            assert "_" not in i["label"] or i["type"] == "new_future_type"

    def test_given_current_week(self, sinc_data_basic):
        from builders.index_data_builder import _build_profile_sincerao

        result = _build_profile_sincerao("Breno", sinc_data_basic, current_week=7,
                                          latest_matrix={}, sinc_weeks_meta={7: "Bombas + Podio", 6: "Regua"})
        current_given = result["current"]["given"]
        # Breno gives: podio to Gabriela, bomba to Alberto in week 7
        assert len(current_given) == 2
        actors = {i["target"] for i in current_given}
        assert "Gabriela" in actors
        assert "Alberto Cowboy" in actors

    def test_summary_totals(self, sinc_data_basic):
        from builders.index_data_builder import _build_profile_sincerao

        result = _build_profile_sincerao("Breno", sinc_data_basic, current_week=7,
                                          latest_matrix={}, sinc_weeks_meta={})
        s = result["summary"]
        # Received: bomba(neg) + regua_fora(neg) in W7, podio(pos) in W6 = 2 neg, 1 pos
        assert s["received_pos"] == 1
        assert s["received_neg"] == 2
        assert s["received_total"] == 3
        # Given: podio(pos) + bomba(neg) in W7, nao_ganha(neg) in W6 = 1 pos, 2 neg
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
        # Week 6: 1 interaction received (podio from Jonas)
        assert len(season_received[1]["interactions"]) == 1

    def test_season_given_by_week(self, sinc_data_basic):
        from builders.index_data_builder import _build_profile_sincerao

        result = _build_profile_sincerao("Breno", sinc_data_basic, current_week=7,
                                          latest_matrix={}, sinc_weeks_meta={7: "Bombas + Podio", 6: "Regua"})
        season_given = result["season"]["given_by_week"]
        weeks = [w["week"] for w in season_given]
        assert weeks == [7, 6]
        # Week 7: 2 given (podio + bomba)
        assert len(season_given[0]["interactions"]) == 2
        # Week 6: 1 given (nao_ganha)
        assert len(season_given[1]["interactions"]) == 1

    def test_contradiction_detection(self, sinc_data_basic):
        from builders.index_data_builder import _build_profile_sincerao

        # Breno gives bomba to Alberto but also gives Coracao in queridometro
        matrix = {("Breno", "Alberto Cowboy"): "Coracao"}
        result = _build_profile_sincerao("Breno", sinc_data_basic, current_week=7,
                                          latest_matrix=matrix, sinc_weeks_meta={})
        assert result["summary"]["contradiction_count"] == 1
        assert "Alberto Cowboy" in result["summary"]["contradiction_targets"]

    def test_no_contradiction_without_heart(self, sinc_data_basic):
        from builders.index_data_builder import _build_profile_sincerao

        # Breno gives bomba to Alberto but gives Cobra (no contradiction)
        matrix = {("Breno", "Alberto Cowboy"): "Cobra"}
        result = _build_profile_sincerao("Breno", sinc_data_basic, current_week=7,
                                          latest_matrix=matrix, sinc_weeks_meta={})
        assert result["summary"]["contradiction_count"] == 0

    def test_gender_resolution_in_received(self, sinc_data_basic):
        from builders.index_data_builder import _build_profile_sincerao

        result = _build_profile_sincerao("Breno", sinc_data_basic, current_week=7,
                                          latest_matrix={}, sinc_weeks_meta={})
        bomba_items = [i for i in result["current"]["received"] if i["type"] == "bomba"]
        # "maior traidor(a)" -> "maior traidor" for Breno (masculine)
        assert bomba_items[0]["label"] == "maior traidor"

    def test_regua_fora_gets_human_label(self, sinc_data_basic):
        from builders.index_data_builder import _build_profile_sincerao

        result = _build_profile_sincerao("Breno", sinc_data_basic, current_week=7,
                                          latest_matrix={}, sinc_weeks_meta={})
        fora_items = [i for i in result["current"]["received"] if i["type"] == "regua_fora"]
        assert len(fora_items) == 1
        assert fora_items[0]["label"] == "fora da regua"  # NOT "regua_fora"

    def test_current_week_field(self, sinc_data_basic):
        from builders.index_data_builder import _build_profile_sincerao

        result = _build_profile_sincerao("Breno", sinc_data_basic, current_week=7,
                                          latest_matrix={}, sinc_weeks_meta={})
        assert result["current_week"] == 7

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
            _make_edge("Alberto Cowboy", "Breno", "bomba", 7, tema="maior traidor(a)"),
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
            _make_edge("Breno", "Gabriela", "podio", 7, slot=1),
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
            _make_edge("A", "Breno", "bomba", 7),
            _make_edge("B", "Breno", "bomba", 7),
            _make_edge("C", "Breno", "nao_ganha", 7),
            _make_edge("A", "Milena", "bomba", 7),
        ]
        radar = _compute_sincerao_radar(edges, week=7, latest_matrix={})
        assert radar["most_targeted_neg"]["names"] == ["Breno"]
        assert radar["most_targeted_neg"]["count"] == 3

    def test_most_praised(self):
        from builders.index_data_builder import _compute_sincerao_radar

        edges = [
            _make_edge("A", "Gabriela", "podio", 7, slot=1),
            _make_edge("B", "Gabriela", "podio", 7, slot=2),
            _make_edge("A", "Breno", "podio", 7, slot=1),
        ]
        radar = _compute_sincerao_radar(edges, week=7, latest_matrix={})
        assert radar["most_praised"]["names"] == ["Gabriela"]
        assert radar["most_praised"]["count"] == 2

    def test_ties_shown_explicitly(self):
        from builders.index_data_builder import _compute_sincerao_radar

        edges = [
            _make_edge("A", "Breno", "bomba", 7),
            _make_edge("A", "Milena", "bomba", 7),
        ]
        radar = _compute_sincerao_radar(edges, week=7, latest_matrix={})
        assert sorted(radar["most_targeted_neg"]["names"]) == ["Breno", "Milena"]
        assert radar["most_targeted_neg"]["count"] == 1

    def test_highest_contradiction_count(self):
        from builders.index_data_builder import _compute_sincerao_radar

        edges = [
            _make_edge("Breno", "Alberto Cowboy", "bomba", 7),
            _make_edge("Breno", "Milena", "nao_ganha", 7),
            _make_edge("Jonas Sulzbach", "Gabriela", "bomba", 7),
        ]
        matrix = {
            ("Breno", "Alberto Cowboy"): "Coracao",
            ("Breno", "Milena"): "Coracao",
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
        assert "radar" in sinc
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
