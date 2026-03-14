"""Live-data contracts, builder integration, and pipeline emission tests."""
from __future__ import annotations

import json
import pytest
from collections import Counter
from pathlib import Path

from builders.paredao_exposure import (
    compute_paredao_exposure_stats,
    build_nunca_paredao_items,
    build_figurinha_repetida_items,
)


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def live_paredoes():
    path = Path("data/paredoes.json")
    if not path.exists():
        pytest.skip("data/paredoes.json not found")
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def live_active_set():
    path = Path("data/latest.json")
    if not path.exists():
        pytest.skip("data/latest.json not found")
    data = json.loads(path.read_text())
    participants = data.get("participants", data) if isinstance(data, dict) else data
    return {p["name"] for p in participants}


@pytest.fixture(scope="module")
def live_manual_events():
    path = Path("data/manual_events.json")
    if not path.exists():
        return {}
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def live_participants_index():
    path = Path("data/derived/participants_index.json")
    if not path.exists():
        return {}
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def live_ctx(live_paredoes, live_active_set, live_manual_events, live_participants_index):
    return {
        "paredoes": live_paredoes,
        "active_set": live_active_set,
        "manual_events": live_manual_events,
        "participants_index": live_participants_index,
    }


# ── Live-data contracts ─────────────────────────────────────────────────

class TestLiveDataContracts:
    """Shape and invariant checks against real repo data.

    Contract guarantees:
    - Every stats.metrics entry has exactly {rate, n, total, scope}
    - rate in [0,1] when total>0, None when total==0
    - Scope sizes ordered: real_only <= all_finalized <= with_indicados
    - first_timer.total == count of real-only eliminations
    - nunca items genuinely absent from all indicados_finais
    - figurinha history length == appearance_count, route sums match
    - BV losers survived + eliminated == total losers
    """

    def test_metric_schema(self, live_ctx):
        stats = compute_paredao_exposure_stats(live_ctx)
        required = {"rate", "n", "total", "scope"}
        valid_scopes = {"real_only", "all_finalized", "with_indicados"}
        for key, metric in stats["metrics"].items():
            assert set(metric.keys()) == required, f"{key}: {set(metric.keys())}"
            assert isinstance(metric["n"], int)
            assert isinstance(metric["total"], int)
            assert metric["scope"] in valid_scopes
            if metric["total"] > 0:
                assert 0 <= metric["rate"] <= 1
            else:
                assert metric["rate"] is None

    def test_scope_sizes_ordered(self, live_ctx):
        sizes = compute_paredao_exposure_stats(live_ctx)["facts"]["scope_sizes"]
        assert sizes["real_only"] <= sizes["all_finalized"] <= sizes["with_indicados"]

    def test_first_timer_denominator(self, live_ctx):
        stats = compute_paredao_exposure_stats(live_ctx)
        paredoes_list = live_ctx["paredoes"].get("paredoes", [])
        real_elims = sum(
            1 for p in paredoes_list
            if p.get("status") == "finalizado"
            and not p.get("paredao_falso")
            and (p.get("resultado") or {}).get("eliminado")
        )
        assert stats["metrics"]["first_timer"]["total"] == real_elims

    def test_nunca_items_genuinely_absent(self, live_ctx):
        paredoes_list = live_ctx["paredoes"].get("paredoes", [])
        all_nominees: set[str] = set()
        for p in paredoes_list:
            for ind in p.get("indicados_finais", []):
                all_nominees.add(ind["nome"] if isinstance(ind, dict) else ind)
        items, exited = build_nunca_paredao_items(live_ctx, paredoes_list, Counter(), Counter())
        for item in items + exited:
            assert item["name"] not in all_nominees

    def test_figurinha_history_matches_count(self, live_ctx):
        paredoes_list = live_ctx["paredoes"].get("paredoes", [])
        for item in build_figurinha_repetida_items(live_ctx, paredoes_list):
            assert len(item["history"]) == item["appearance_count"]

    def test_figurinha_route_sums_match(self, live_ctx):
        paredoes_list = live_ctx["paredoes"].get("paredoes", [])
        for item in build_figurinha_repetida_items(live_ctx, paredoes_list):
            assert sum(item["route_summary"].values()) == item["appearance_count"]

    def test_bv_losers_consistency(self, live_ctx):
        m = compute_paredao_exposure_stats(live_ctx)["metrics"]
        assert (m["bv_losers_survived"]["n"] + m["bv_losers_eliminated"]["n"]
                == m["bv_losers_survived"]["total"])


# ── Exited vote stats regression ───────────────────────────────────────

class TestExitedVoteStatsRegression:
    """Live regression tests for exited participant vote counts."""

    def test_paulo_augusto_votes(self, live_ctx):
        """Paulo Augusto received 11 house votes in P1."""
        paredoes_list = live_ctx["paredoes"].get("paredoes", [])
        _, exited = build_nunca_paredao_items(live_ctx, paredoes_list, Counter(), Counter())
        pa = next((i for i in exited if i["name"] == "Paulo Augusto"), None)
        assert pa is not None, "Paulo Augusto should be in exited items (desclassificado, never nominated)"
        assert pa["votes_total"] >= 11, f"Paulo Augusto votes_total={pa['votes_total']}, expected >= 11"

    def test_edilson_protected(self, live_ctx):
        """Edilson was protected (Imune) at least once."""
        paredoes_list = live_ctx["paredoes"].get("paredoes", [])
        _, exited = build_nunca_paredao_items(live_ctx, paredoes_list, Counter(), Counter())
        edi = next((i for i in exited if i["name"] == "Edilson"), None)
        assert edi is not None, "Edilson should be in exited items (desclassificado, never nominated)"
        assert edi["protected"] >= 1, f"Edilson protected={edi['protected']}, expected >= 1"


# ── Builder integration ─────────────────────────────────────────────────

class TestBuilderIntegration:

    def test_payload_includes_exposure_stats(self):
        from builders.index_data_builder import build_index_data
        payload = build_index_data()
        assert payload is not None
        stats = payload["paredao_exposure"]["stats"]
        assert "metrics" in stats
        assert len(stats["metrics"]) > 0

    def test_nunca_paredao_counters_match_blindados(self):
        """nunca_paredao available/protected must match blindados counters."""
        from builders.index_data_builder import build_index_data
        payload = build_index_data()
        assert payload is not None
        cards = payload["highlights"]["cards"]
        blindados = next((c for c in cards if c["type"] == "blindados"), None)
        nunca = next((c for c in cards if c["type"] == "nunca_paredao"), None)
        if not blindados or not nunca:
            pytest.skip("blindados or nunca_paredao card not emitted")
        blind_by_name = {i["name"]: i for i in blindados["items_all"]}
        for item in nunca["items_all"]:
            name = item["name"]
            b = blind_by_name.get(name)
            if b is None:
                continue  # exited participant not in blindados
            assert item["available"] == b["available"], \
                f"{name}: nunca available={item['available']} != blindados={b['available']}"
            assert item["protected"] == b["protected"], \
                f"{name}: nunca protected={item['protected']} != blindados={b['protected']}"


# ── Pipeline emission schema (non-skippable, uses builder directly) ─────


class TestPipelineEmissionSchema:
    """Validates stats schema by building from the builder — no file dependency."""

    def test_stats_schema_from_builder(self):
        from builders.index_data_builder import build_index_data
        payload = build_index_data()
        assert payload is not None
        stats = payload["paredao_exposure"]["stats"]
        assert "metrics" in stats and "facts" in stats
        required = {"rate", "n", "total", "scope"}
        for key, metric in stats["metrics"].items():
            assert set(metric.keys()) == required, f"{key}: {set(metric.keys())}"


# ── Pipeline emission file check (complementary, skip on clean env) ─────

_STATS_PATH = Path("data/derived/paredao_exposure_stats.json")


@pytest.mark.skipif(not _STATS_PATH.exists(),
                    reason="derived data not built — run build_derived_data.py first")
class TestPipelineEmissionFile:

    def test_stats_json_has_metadata(self):
        data = json.loads(_STATS_PATH.read_text())
        assert "stats" in data and "_metadata" in data
        assert "content_hash" in data["_metadata"]
