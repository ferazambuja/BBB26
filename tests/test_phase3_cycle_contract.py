"""Phase 3 cycle migration contract tests.

These tests define the FINAL canonical contract after the week-to-cycle migration.
They are expected to FAIL initially and pass after all migration chunks are complete.

Test categories:
  1. Cycle-only raw fixtures work with builders (data completeness)
  2. Legacy contract fields are GONE from public payloads
  3. Core functions use canonical cycle names (no legacy wrappers)
  4. Tracked gameplay data uses canonical keys
  5. Builder internals have NO legacy fallback code
  6. Migration helper contract
"""
from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


# ---------------------------------------------------------------------------
# Fixtures: cycle-only raw data (no weekly_events, no week, no semana)
# ---------------------------------------------------------------------------

CYCLE_ONLY_MANUAL_EVENTS: dict = {
    "participants": {},
    "cycles": [
        {
            "cycle": 1,
            "start_date": "2026-01-13",
            "end_date": "2026-01-21",
            "lider": "Alberto Cowboy",
            "sincerao": {
                "date": "2026-01-20",
                "format": "Podio e Desce do Podio",
                "scoring_mode": "full",
                "edges": [
                    {"de": "Babu Santana", "para": "Alberto Cowboy", "type": "elogio", "slot": 1},
                    {"de": "Chaiany", "para": "Babu Santana", "type": "ataque", "tema": "maior falso(a)"},
                ],
            },
            "confissao_voto": [
                {"votante": "Chaiany", "alvo": "Babu Santana", "date": "2026-01-19"},
            ],
        },
        {
            "cycle": 2,
            "start_date": "2026-01-22",
            "end_date": "2026-01-28",
            "lider": "Babu Santana",
            "big_fone": [{"date": "2026-01-23", "atendeu": "Chaiany"}],
        },
    ],
    "power_events": [
        {
            "date": "2026-01-15",
            "cycle": 1,
            "type": "contragolpe",
            "actor": "Chaiany",
            "target": "Babu Santana",
            "detail": "Contragolpe test",
            "impacto": "negativo",
        },
    ],
    "special_events": [],
    "scheduled_events": [
        {
            "date": "2026-01-25",
            "cycle": 2,
            "category": "dinamica",
            "title": "Prova Especial",
            "detail": "Test dynamic",
        },
    ],
    "cartola_points_log": [],
}

CYCLE_ONLY_PAREDOES: dict = {
    "paredoes": [
        {
            "numero": 1,
            "cycle": 1,
            "status": "finalizado",
            "data": "2026-01-21",
            "data_formacao": "2026-01-19",
            "titulo": "1 Paredao",
            "total_esperado": 3,
            "formacao": {
                "resumo": "Test formation",
                "lider": "Alberto Cowboy",
                "indicado_lider": "Babu Santana",
            },
            "indicados_finais": [
                {"nome": "Babu Santana", "grupo": "Pipoca", "como": "Lider"},
                {"nome": "Chaiany", "grupo": "Camarote", "como": "Casa"},
            ],
            "votos_casa": {"Gabriela": "Chaiany"},
            "resultado": {
                "eliminado": "Edilson",
                "votos": {
                    "Babu Santana": {"voto_unico": 30.0, "voto_torcida": 25.0, "voto_total": 28.5},
                    "Chaiany": {"voto_unico": 70.0, "voto_torcida": 75.0, "voto_total": 71.5},
                },
            },
            "fontes": [],
        },
    ],
}

CYCLE_ONLY_PROVAS: dict = {
    "provas": [
        {
            "cycle": 1,
            "tipo": "lider",
            "data": "2026-01-13",
            "date": "2026-01-13",
            "titulo": "Prova do Lider 1",
            "vencedor": "Alberto Cowboy",
            "participantes_total": 25,
        },
        {
            "cycle": 2,
            "tipo": "lider",
            "data": "2026-01-22",
            "date": "2026-01-22",
            "titulo": "Prova do Lider 2",
            "vencedor": "Babu Santana",
            "participantes_total": 24,
        },
    ],
}


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
            "last_seen": "2026-01-28",
        }
        for n in names
    ]


# ---------------------------------------------------------------------------
# Test group 1: Cycle-only fixtures work with builders (data completeness)
# ---------------------------------------------------------------------------

class TestCycleOnlyBuildersWork:
    """Builders must produce non-empty, correct results from cycle-only fixtures."""

    def test_sincerao_produces_edges_with_cycle_only_fixtures(self):
        """Sincerao builder must produce non-empty edges from cycle-only fixtures."""
        from builders.sincerao import build_sincerao_edges

        result = build_sincerao_edges(CYCLE_ONLY_MANUAL_EVENTS)
        assert len(result["edges"]) > 0, (
            "Sincerao builder returned empty edges from cycle-only fixtures"
        )

    def test_sincerao_edges_have_cycle_field(self):
        """Every sincerao edge must have 'cycle' key, not 'week'."""
        from builders.sincerao import build_sincerao_edges

        result = build_sincerao_edges(CYCLE_ONLY_MANUAL_EVENTS)
        for edge in result["edges"]:
            assert "cycle" in edge, f"Sincerao edge missing 'cycle': {edge}"
            assert "week" not in edge, f"Sincerao edge has legacy 'week': {edge}"

    def test_cartola_awards_big_fone_with_cycle_only_fixtures(self, monkeypatch):
        """Cartola builder must award Big Fone points from cycle-only fixtures."""
        from builders.cartola import build_cartola_data

        monkeypatch.setattr(
            "builders.cartola.get_cycle_number",
            lambda d, *a, **kw: 1,
        )

        result = build_cartola_data(
            daily_snapshots=[{
                "date": "2026-01-23",
                "participants": [
                    _participant("Chaiany"),
                    _participant("Babu Santana"),
                ],
            }],
            paredoes_data=CYCLE_ONLY_PAREDOES,
            manual_events=CYCLE_ONLY_MANUAL_EVENTS,
            participants_index=_participants_index(["Chaiany", "Babu Santana"]),
            provas_data=CYCLE_ONLY_PROVAS,
        )

        chaiany = next((p for p in result["leaderboard"] if p["name"] == "Chaiany"), None)
        assert chaiany is not None
        big_fone_events = [e for e in chaiany.get("events", []) if e["event"] == "atendeu_big_fone"]
        assert len(big_fone_events) > 0, (
            "Cartola builder did not award Big Fone points from cycle-only fixtures"
        )

    def test_cartola_events_use_cycle_field_only(self, monkeypatch):
        """Every event in cartola leaderboard must have 'cycle', not 'week'."""
        from builders.cartola import build_cartola_data

        monkeypatch.setattr(
            "builders.cartola.get_cycle_number",
            lambda d, *a, **kw: 1,
        )

        result = build_cartola_data(
            daily_snapshots=[{
                "date": "2026-01-23",
                "participants": [
                    _participant("Chaiany"),
                    _participant("Babu Santana"),
                ],
            }],
            paredoes_data=CYCLE_ONLY_PAREDOES,
            manual_events=CYCLE_ONLY_MANUAL_EVENTS,
            participants_index=_participants_index(["Chaiany", "Babu Santana"]),
            provas_data=CYCLE_ONLY_PROVAS,
        )

        for entry in result.get("leaderboard", []):
            for evt in entry.get("events", []):
                assert "week" not in evt, (
                    f"Cartola event for {entry['name']} still has 'week': {evt}"
                )
                assert "cycle" in evt, (
                    f"Cartola event for {entry['name']} missing 'cycle': {evt}"
                )

    def test_timeline_builds_from_cycle_only_fixtures(self):
        """Timeline builder must work without 'weekly_events' key."""
        from builders.timeline import build_game_timeline

        result = build_game_timeline(
            eliminations_detected=[],
            auto_events=[],
            manual_events=CYCLE_ONLY_MANUAL_EVENTS,
            paredoes_data=CYCLE_ONLY_PAREDOES,
            provas_data=CYCLE_ONLY_PROVAS,
            reference_date="2026-01-28",
        )
        assert len(result) > 0, "Timeline builder returned empty from cycle-only fixtures"

    def test_timeline_events_all_have_cycle_field(self):
        """Every timeline event must have 'cycle', not 'week'."""
        from builders.timeline import build_game_timeline

        result = build_game_timeline(
            eliminations_detected=[],
            auto_events=[],
            manual_events=CYCLE_ONLY_MANUAL_EVENTS,
            paredoes_data=CYCLE_ONLY_PAREDOES,
            provas_data=CYCLE_ONLY_PROVAS,
            reference_date="2026-01-28",
        )
        for ev in result:
            assert "cycle" in ev, f"Timeline event missing 'cycle': {ev}"
            assert "week" not in ev, f"Timeline event has legacy 'week': {ev}"

    def test_relations_reads_confissao_from_cycles_key(self):
        """Relations builder must read confissao_voto from 'cycles', not 'weekly_events'."""
        from builders.relations import _build_vote_data

        vote_data = _build_vote_data(CYCLE_ONLY_PAREDOES, CYCLE_ONLY_MANUAL_EVENTS)
        # confissao_voto in cycle 1: Chaiany voted for Babu Santana
        revealed = vote_data["revealed_votes"]
        assert "Babu Santana" in revealed, (
            "Relations builder did not pick up confissao_voto from cycle-only 'cycles' key"
        )
        assert "Chaiany" in revealed["Babu Santana"], (
            "Chaiany not found as revealer for Babu Santana"
        )

    def test_balance_events_publish_cycle_field(self):
        """Balance builder events must publish 'cycle' key, not 'week'."""
        from builders.balance import build_balance_events

        # Two snapshots with a balance change to trigger an event
        p1_snap1 = _participant("Chaiany")
        p1_snap1["characteristics"]["balance"] = 500
        p1_snap2 = _participant("Chaiany")
        p1_snap2["characteristics"]["balance"] = 1000
        p2_snap1 = _participant("Babu Santana")
        p2_snap1["characteristics"]["balance"] = 500
        p2_snap2 = _participant("Babu Santana")
        p2_snap2["characteristics"]["balance"] = 1000

        snapshots = [
            {
                "metadata": {"captured_at": "2026-01-22T10:00:00+00:00"},
                "file": "data/snapshots/2026-01-22_10-00-00.json",
                "date": "2026-01-22",
                "participants": [p1_snap1, p2_snap1],
            },
            {
                "metadata": {"captured_at": "2026-01-22T18:00:00+00:00"},
                "file": "data/snapshots/2026-01-22_18-00-00.json",
                "date": "2026-01-22",
                "participants": [p1_snap2, p2_snap2],
            },
        ]
        result = build_balance_events(snapshots)
        events = result.get("events", [])
        # At minimum, if events are produced, they must have 'cycle' not 'week'
        for ev in events:
            assert "cycle" in ev, f"Balance event missing 'cycle': {ev}"
            assert "week" not in ev, f"Balance event has legacy 'week': {ev}"


# ---------------------------------------------------------------------------
# Test group 2: Legacy fields ABSENT from on-disk derived payloads
# ---------------------------------------------------------------------------

class TestLegacyFieldsAbsentFromPayloads:
    """Derived JSON payloads must NOT contain legacy 'week'/'semana'/'weekly_points' keys."""

    def test_index_data_publishes_current_cycle_not_current_cycle_week(self):
        """index_data.json must publish 'current_cycle', not 'current_cycle_week'."""
        path = Path(__file__).resolve().parent.parent / "data" / "derived" / "index_data.json"
        if not path.exists():
            pytest.skip("index_data.json not found")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "current_cycle_week" not in data, "index_data.json still publishes 'current_cycle_week'"
        assert "current_cycle" in data, "index_data.json missing 'current_cycle'"

    def test_game_timeline_events_have_cycle_not_week(self):
        """game_timeline.json events must have 'cycle', not gameplay-facing 'week'."""
        path = Path(__file__).resolve().parent.parent / "data" / "derived" / "game_timeline.json"
        if not path.exists():
            pytest.skip("game_timeline.json not found")
        data = json.loads(path.read_text(encoding="utf-8"))
        for ev in data.get("events", []):
            assert "week" not in ev, f"Timeline event still has 'week': {ev.get('title', ev.get('category', ''))}"
            assert "cycle" in ev, f"Timeline event missing 'cycle': {ev.get('title', ev.get('category', ''))}"

    def test_cartola_publishes_cycle_points_not_weekly_points(self):
        """cartola_data.json must have 'cycle_points', not 'weekly_points'."""
        path = Path(__file__).resolve().parent.parent / "data" / "derived" / "cartola_data.json"
        if not path.exists():
            pytest.skip("cartola_data.json not found")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "weekly_points" not in data, "cartola_data.json still has 'weekly_points'"
        assert "cycle_points" in data, "cartola_data.json missing 'cycle_points'"

    def test_cartola_metadata_has_n_cycles_not_n_weeks(self):
        """cartola _metadata must have 'n_cycles', not 'n_weeks'."""
        path = Path(__file__).resolve().parent.parent / "data" / "derived" / "cartola_data.json"
        if not path.exists():
            pytest.skip("cartola_data.json not found")
        data = json.loads(path.read_text(encoding="utf-8"))
        meta = data.get("_metadata", {})
        assert "n_weeks" not in meta, "cartola_data.json metadata still has 'n_weeks'"
        assert "n_cycles" in meta, "cartola_data.json metadata missing 'n_cycles'"

    def test_cartola_events_have_cycle_not_week(self):
        """cartola_data.json leaderboard events must have 'cycle', not 'week'."""
        path = Path(__file__).resolve().parent.parent / "data" / "derived" / "cartola_data.json"
        if not path.exists():
            pytest.skip("cartola_data.json not found")
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data.get("leaderboard", []):
            for evt in entry.get("events", []):
                assert "week" not in evt, f"Cartola event for {entry['name']} still has 'week'"

    def test_balance_events_no_legacy_week(self):
        """balance_events.json events must use 'cycle', not 'week'."""
        path = Path(__file__).resolve().parent.parent / "data" / "derived" / "balance_events.json"
        if not path.exists():
            pytest.skip("balance_events.json not found")
        data = json.loads(path.read_text(encoding="utf-8"))
        for ev in data.get("events", []):
            assert "week" not in ev, f"Balance event still has 'week': {ev.get('type', '')}"
            assert "cycle" in ev, f"Balance event missing 'cycle': {ev.get('type', '')}"

    def test_prova_rankings_no_legacy_week(self):
        """prova_rankings.json provas_summary must use 'cycle', not 'week'."""
        path = Path(__file__).resolve().parent.parent / "data" / "derived" / "prova_rankings.json"
        if not path.exists():
            pytest.skip("prova_rankings.json not found")
        data = json.loads(path.read_text(encoding="utf-8"))
        for prova in data.get("provas_summary", []):
            assert "week" not in prova, f"Prova still has 'week': {prova.get('titulo', '')}"
            assert "cycle" in prova, f"Prova missing 'cycle': {prova.get('titulo', '')}"

    def test_sincerao_edges_derived_no_legacy_week(self):
        """sincerao_edges.json edges must use 'cycle', not 'week'."""
        path = Path(__file__).resolve().parent.parent / "data" / "derived" / "sincerao_edges.json"
        if not path.exists():
            pytest.skip("sincerao_edges.json not found")
        data = json.loads(path.read_text(encoding="utf-8"))
        for edge in data.get("edges", []):
            assert "week" not in edge, f"Sincerao edge still has 'week': {edge}"
        for week_meta in data.get("weeks", []):
            assert "week" not in week_meta, f"Sincerao week metadata still has 'week': {week_meta}"
        for agg in data.get("aggregates", []):
            assert "week" not in agg, f"Sincerao aggregate still has 'week': {agg}"


# ---------------------------------------------------------------------------
# Test group 3: Core function names are canonical (no legacy)
# ---------------------------------------------------------------------------

class TestCanonicalCycleFunctionNames:
    """After migration, canonical names must exist and legacy wrappers must be gone."""

    def test_cycle_end_dates_constant_exists(self):
        """CYCLE_END_DATES must exist as the canonical constant name."""
        import data_utils
        assert hasattr(data_utils, "CYCLE_END_DATES"), "data_utils missing CYCLE_END_DATES constant"

    def test_week_end_dates_constant_removed(self):
        """WEEK_END_DATES must not exist as a public constant (bridge removed)."""
        import data_utils
        assert not hasattr(data_utils, "WEEK_END_DATES"), "data_utils still has legacy WEEK_END_DATES"

    def test_get_cycle_number_is_standalone(self):
        """get_cycle_number() must be the real implementation, not a wrapper."""
        import data_utils
        source = inspect.getsource(data_utils.get_cycle_number)
        assert "get_week_number" not in source, (
            "get_cycle_number() is still a wrapper around get_week_number()"
        )

    def test_get_cycle_start_date_is_standalone(self):
        """get_cycle_start_date() must be the real implementation, not a wrapper."""
        import data_utils
        source = inspect.getsource(data_utils.get_cycle_start_date)
        assert "get_week_start_date" not in source, (
            "get_cycle_start_date() is still a wrapper around get_week_start_date()"
        )

    def test_get_effective_cycle_end_dates_is_standalone(self):
        """get_effective_cycle_end_dates() must be the real implementation, not a wrapper."""
        import data_utils
        source = inspect.getsource(data_utils.get_effective_cycle_end_dates)
        assert "get_effective_week_end_dates" not in source, (
            "get_effective_cycle_end_dates() is still a wrapper"
        )

    def test_legacy_week_functions_removed(self):
        """Legacy get_week_number/get_week_start_date must not exist."""
        import data_utils
        assert not hasattr(data_utils, "get_week_number"), "data_utils still has legacy get_week_number()"
        assert not hasattr(data_utils, "get_week_start_date"), "data_utils still has legacy get_week_start_date()"
        assert not hasattr(data_utils, "get_effective_week_end_dates"), (
            "data_utils still has legacy get_effective_week_end_dates()"
        )


# ---------------------------------------------------------------------------
# Test group 4: Tracked gameplay data uses canonical keys
# ---------------------------------------------------------------------------

class TestTrackedDataCanonical:
    """On-disk tracked gameplay files must use only canonical cycle keys."""

    def _load(self, filename: str) -> dict:
        path = Path(__file__).resolve().parent.parent / "data" / filename
        if not path.exists():
            pytest.skip(f"{filename} not found")
        return json.loads(path.read_text(encoding="utf-8"))

    def test_manual_events_uses_cycles_key(self):
        data = self._load("manual_events.json")
        assert "cycles" in data, "manual_events.json missing 'cycles' key"
        assert "weekly_events" not in data, "manual_events.json still has 'weekly_events'"

    def test_manual_events_cycle_entries_use_cycle_field(self):
        data = self._load("manual_events.json")
        for entry in data.get("cycles", []):
            assert "cycle" in entry, f"Cycle entry missing 'cycle' field: {entry}"
            assert "week" not in entry, f"Cycle entry still has 'week' field: {entry}"

    def test_manual_events_power_events_use_cycle(self):
        data = self._load("manual_events.json")
        for ev in data.get("power_events", []):
            if "cycle" in ev or "week" in ev:
                assert "week" not in ev, f"Power event still has 'week': {ev}"

    def test_manual_events_scheduled_events_use_cycle(self):
        data = self._load("manual_events.json")
        for ev in data.get("scheduled_events", []):
            if "cycle" in ev or "week" in ev:
                assert "week" not in ev, f"Scheduled event still has 'week': {ev}"

    def test_paredoes_use_cycle(self):
        data = self._load("paredoes.json")
        for par in data.get("paredoes", []):
            assert "cycle" in par, f"Paredao #{par.get('numero')} missing 'cycle'"
            assert "semana" not in par, f"Paredao #{par.get('numero')} still has 'semana'"

    def test_provas_use_cycle(self):
        data = self._load("provas.json")
        for prova in data.get("provas", []):
            assert "cycle" in prova, f"Prova missing 'cycle': {prova.get('titulo', '')}"
            assert "week" not in prova, f"Prova still has 'week': {prova.get('titulo', '')}"


# ---------------------------------------------------------------------------
# Test group 5: Builder internals have NO legacy fallback code
#
# These tests inspect source code to verify that bridge/fallback patterns
# (reading "weekly_events", "week", "semana" as fallbacks) are GONE.
# This is the key category of tests expected to FAIL before full migration.
# ---------------------------------------------------------------------------

class TestBuilderInternalsNoLegacyFallback:
    """Builder source code must not contain legacy fallback patterns."""

    def test_timeline_iter_cycle_entries_no_weekly_events_fallback(self):
        """timeline._iter_cycle_entries() must not fall back to 'weekly_events'."""
        from builders.timeline import _iter_cycle_entries
        source = inspect.getsource(_iter_cycle_entries)
        assert "weekly_events" not in source, (
            "_iter_cycle_entries() still falls back to 'weekly_events'"
        )

    def test_timeline_get_event_cycle_no_week_fallback(self):
        """timeline._get_event_cycle() must not fall back to 'week' or 'semana'."""
        from builders.timeline import _get_event_cycle
        source = inspect.getsource(_get_event_cycle)
        assert '"week"' not in source, (
            "_get_event_cycle() still falls back to legacy 'week' key"
        )
        assert '"semana"' not in source, (
            "_get_event_cycle() still falls back to legacy 'semana' key"
        )

    def test_sincerao_builder_no_weekly_events_fallback(self):
        """sincerao.build_sincerao_edges() must not fall back to 'weekly_events'."""
        from builders.sincerao import build_sincerao_edges
        source = inspect.getsource(build_sincerao_edges)
        assert "weekly_events" not in source, (
            "build_sincerao_edges() still falls back to 'weekly_events'"
        )

    def test_sincerao_builder_no_week_fallback(self):
        """sincerao.build_sincerao_edges() must not fall back to 'week' key."""
        from builders.sincerao import build_sincerao_edges
        source = inspect.getsource(build_sincerao_edges)
        assert '.get("week")' not in source, (
            "build_sincerao_edges() still falls back to legacy 'week' key"
        )

    def test_cartola_no_weekly_events_fallback(self):
        """cartola builder must not fall back to 'weekly_events'."""
        import builders.cartola as cartola_mod
        source = inspect.getsource(cartola_mod)
        assert "weekly_events" not in source, (
            "builders/cartola.py still references 'weekly_events'"
        )

    def test_cartola_no_week_key_fallback(self):
        """cartola builder must not use '.get(\"week\")' fallback."""
        import builders.cartola as cartola_mod
        source = inspect.getsource(cartola_mod)
        assert '.get("week")' not in source and ".get('week')" not in source, (
            "builders/cartola.py still uses .get('week') fallback"
        )

    def test_relations_no_weekly_events_fallback(self):
        """relations builder must not fall back to 'weekly_events'."""
        import builders.relations as relations_mod
        source = inspect.getsource(relations_mod)
        assert "weekly_events" not in source, (
            "builders/relations.py still references 'weekly_events'"
        )

    def test_relations_no_semana_fallback(self):
        """relations builder must not use '.get(\"semana\")' fallback."""
        import builders.relations as relations_mod
        source = inspect.getsource(relations_mod)
        assert '.get("semana")' not in source, (
            "builders/relations.py still uses .get('semana') fallback"
        )

    def test_relations_no_week_fallback(self):
        """relations builder must not use '.get(\"week\")' fallback."""
        import builders.relations as relations_mod
        source = inspect.getsource(relations_mod)
        assert '.get("week")' not in source and ".get('week')" not in source, (
            "builders/relations.py still uses .get('week') fallback"
        )

    def test_participants_no_weekly_events_fallback(self):
        """participants builder must not fall back to 'weekly_events'."""
        import builders.participants as participants_mod
        source = inspect.getsource(participants_mod)
        assert "weekly_events" not in source, (
            "builders/participants.py still references 'weekly_events'"
        )

    def test_plant_index_no_weekly_events_fallback(self):
        """plant_index builder must not fall back to 'weekly_events'."""
        import builders.plant_index as plant_mod
        source = inspect.getsource(plant_mod)
        assert "weekly_events" not in source, (
            "builders/plant_index.py still references 'weekly_events'"
        )

    def test_plant_index_no_week_fallback(self):
        """plant_index builder must not use '.get(\"week\")' or '.get(\"semana\")' fallback."""
        import builders.plant_index as plant_mod
        source = inspect.getsource(plant_mod)
        assert '.get("week")' not in source and ".get('week')" not in source, (
            "builders/plant_index.py still uses .get('week') fallback"
        )
        assert '.get("semana")' not in source, (
            "builders/plant_index.py still uses .get('semana') fallback"
        )

    def test_paredao_analysis_no_semana_fallback(self):
        """paredao_analysis builder must not use '.get(\"semana\")' fallback."""
        import builders.paredao_analysis as pa_mod
        source = inspect.getsource(pa_mod)
        assert '.get("semana")' not in source, (
            "builders/paredao_analysis.py still uses .get('semana') fallback"
        )

    def test_paredao_analysis_no_week_fallback(self):
        """paredao_analysis builder must not use '.get(\"week\")' or 'week=' named arg."""
        import builders.paredao_analysis as pa_mod
        source = inspect.getsource(pa_mod)
        assert '.get("week")' not in source and ".get('week')" not in source, (
            "builders/paredao_analysis.py still uses .get('week') fallback"
        )
        # Check for `week=event.get("week")` patterns (named argument passing legacy key)
        assert 'week=event.get("week")' not in source and "week=event.get('week')" not in source, (
            "builders/paredao_analysis.py still passes legacy 'week' via named argument"
        )

    def test_index_data_builder_no_weekly_events_fallback(self):
        """index_data_builder must not fall back to 'weekly_events'."""
        import builders.index_data_builder as idx_mod
        source = inspect.getsource(idx_mod)
        assert "weekly_events" not in source, (
            "builders/index_data_builder.py still references 'weekly_events'"
        )

    def test_index_data_builder_no_week_fallback_in_edge_reading(self):
        """index_data_builder must not use '.get(\"week\")' fallback when reading edges."""
        import builders.index_data_builder as idx_mod
        source = inspect.getsource(idx_mod)
        assert '.get("week")' not in source and ".get('week')" not in source, (
            "builders/index_data_builder.py still uses .get('week') fallback"
        )

    def test_index_data_builder_no_semana_fallback(self):
        """index_data_builder must not use '.get(\"semana\")' fallback."""
        import builders.index_data_builder as idx_mod
        source = inspect.getsource(idx_mod)
        assert '.get("semana")' not in source, (
            "builders/index_data_builder.py still uses .get('semana') fallback"
        )

    def test_index_data_builder_internal_key_is_current_cycle(self):
        """index_data_builder aggregate must use 'current_cycle' internally, not 'current_cycle_week'."""
        from builders.index_data_builder import _aggregate_latest_state
        source = inspect.getsource(_aggregate_latest_state)
        assert "current_cycle_week" not in source, (
            "_aggregate_latest_state still uses 'current_cycle_week' internal key"
        )

    def test_data_utils_no_weekly_events_fallback(self):
        """data_utils.py must not fall back to 'weekly_events'."""
        import data_utils
        source = inspect.getsource(data_utils)
        assert "weekly_events" not in source, (
            "data_utils.py still references 'weekly_events'"
        )

    def test_balance_builder_no_week_fallback(self):
        """balance builder must not use 'get(\"week\"' fallback."""
        import builders.balance as balance_mod
        source = inspect.getsource(balance_mod)
        assert 'get("week"' not in source and "get('week'" not in source, (
            "builders/balance.py still uses get('week') fallback"
        )


# ---------------------------------------------------------------------------
# Test group 6: Migration helper contract
# ---------------------------------------------------------------------------

class TestMigrationHelper:
    """Tests for the week-to-cycle migration helper script."""

    def test_migration_helper_rewrites_raw_gameplay_keys(self, tmp_path):
        """Migration helper correctly renames weekly_events->cycles, week->cycle, semana->cycle."""
        try:
            from migrate_week_to_cycle import migrate_manual_events, migrate_paredoes, migrate_provas
        except ImportError:
            pytest.skip("Migration helper not yet implemented")

        raw_manual = {
            "participants": {},
            "weekly_events": [
                {"week": 1, "start_date": "2026-01-13", "lider": "Alberto"},
            ],
            "power_events": [
                {"week": 1, "date": "2026-01-15", "type": "contragolpe"},
            ],
            "special_events": [
                {"week": 1, "date": "2026-01-16", "type": "test"},
            ],
            "scheduled_events": [
                {"week": 2, "date": "2026-01-25", "category": "dinamica"},
            ],
            "cartola_points_log": [
                {"week": 1, "participant": "Chaiany", "events": []},
            ],
        }
        migrated = migrate_manual_events(raw_manual)
        assert "cycles" in migrated
        assert "weekly_events" not in migrated
        assert migrated["cycles"][0]["cycle"] == 1
        assert "week" not in migrated["cycles"][0]
        assert migrated["power_events"][0]["cycle"] == 1
        assert "week" not in migrated["power_events"][0]
        assert migrated["special_events"][0]["cycle"] == 1
        assert migrated["scheduled_events"][0]["cycle"] == 2
        assert migrated["cartola_points_log"][0]["cycle"] == 1

        raw_paredoes = {
            "paredoes": [
                {"numero": 1, "semana": 1, "status": "finalizado"},
            ],
        }
        migrated_par = migrate_paredoes(raw_paredoes)
        assert migrated_par["paredoes"][0]["cycle"] == 1
        assert "semana" not in migrated_par["paredoes"][0]

        raw_provas = {
            "provas": [
                {"week": 1, "tipo": "lider", "data": "2026-01-13"},
            ],
        }
        migrated_provas = migrate_provas(raw_provas)
        assert migrated_provas["provas"][0]["cycle"] == 1
        assert "week" not in migrated_provas["provas"][0]

    def test_migration_preserves_string_values(self):
        """Migration must NOT rewrite prose strings containing 'semana'."""
        try:
            from migrate_week_to_cycle import migrate_paredoes
        except ImportError:
            pytest.skip("Migration helper not yet implemented")

        raw = {
            "paredoes": [
                {
                    "numero": 1,
                    "semana": 1,
                    "titulo": "1 Paredao -- Semana 1",
                    "formacao": {"resumo": "Paredao da primeira semana"},
                    "fontes": [{"titulo": "Resultado semana 1"}],
                },
            ],
        }
        migrated = migrate_paredoes(raw)
        par = migrated["paredoes"][0]
        assert par["cycle"] == 1
        assert "semana" not in par
        assert "Semana 1" in par["titulo"]
        assert "semana" in par["formacao"]["resumo"]
        assert "semana" in par["fontes"][0]["titulo"]
