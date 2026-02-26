"""Extended tests for data_utils.py — covers ~32 previously untested functions.

Covers: data loaders, helper functions, poll/prediction functions, viz helpers,
snapshot utilities, and timeline rendering.
"""
import json
import math
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

from data_utils import (
    # Data loaders
    load_paredoes_raw,
    load_paredoes_transformed,
    load_participants_index,
    load_relations_scores,
    load_daily_metrics,
    load_roles_daily,
    load_reaction_matrices,
    deserialize_matrix,
    load_votalhada_polls,
    load_sincerao_edges,
    get_all_snapshots,
    get_daily_snapshots,
    get_all_snapshots_with_data,
    # Helpers
    genero,
    artigo,
    avatar_html,
    avatar_img,
    get_nominee_badge,
    render_cronologia_html,
    normalize_actors,
    patch_missing_raio_x,
    # Poll/prediction
    get_poll_for_paredao,
    calculate_poll_accuracy,
    calculate_precision_weights,
    predict_precision_weighted,
    backtest_precision_model,
    parse_votalhada_hora,
    # Snapshot helpers
    load_snapshots_full,
    # Other
    require_clean_manual_events,
    setup_bbb_dark_theme,
    MONTH_MAP_PT,
)


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def paredoes_json_file(tmp_path):
    """Create a temporary paredoes.json with realistic data."""
    data = {
        "paredoes": [
            {
                "numero": 1,
                "status": "finalizado",
                "data": "2026-01-21",
                "data_formacao": "2026-01-19",
                "titulo": "1º Paredão — 21 de Janeiro de 2026",
                "formacao": {
                    "lider": "Jonas Sulzbach",
                    "indicado_lider": "Aline Campos",
                    "motivo_lider": "Estratégia",
                    "resumo": "Líder indicou Aline. Casa votou Brigido.",
                },
                "indicados_finais": [
                    {"nome": "Aline Campos", "grupo": "Veterano", "como": "Líder"},
                    {"nome": "Brigido", "grupo": "Pipoca", "como": "Casa"},
                    {"nome": "Breno", "grupo": "Pipoca", "como": "Contragolpe"},
                ],
                "votos_casa": {"Marciele": "Brigido", "Milena": "Brigido"},
                "resultado": {
                    "eliminado": "Aline Campos",
                    "votos": {
                        "Aline Campos": {"voto_unico": 45.0, "voto_torcida": 50.0, "voto_total": 47.5},
                        "Brigido": {"voto_unico": 30.0, "voto_torcida": 25.0, "voto_total": 27.5},
                        "Breno": {"voto_unico": 25.0, "voto_torcida": 25.0, "voto_total": 25.0},
                    },
                },
                "fontes": ["https://example.com"],
            },
            {
                "numero": 2,
                "status": "em_andamento",
                "data": "2026-01-28",
                "data_formacao": "2026-01-26",
                "titulo": "2º Paredão — 28 de Janeiro de 2026",
                "formacao": {
                    "lider": "Marciele",
                    "indicado_lider": "Matheus",
                    "resumo": "Líder indicou Matheus.",
                },
                "indicados_finais": [
                    {"nome": "Matheus", "grupo": "Pipoca", "como": "Líder"},
                ],
                "votos_casa": {},
            },
        ]
    }
    filepath = tmp_path / "paredoes.json"
    filepath.write_text(json.dumps(data), encoding="utf-8")
    return filepath


@pytest.fixture
def polls_json_data():
    """Realistic Votalhada polls data for testing."""
    return {
        "paredoes": [
            {
                "numero": 1,
                "data_paredao": "2026-01-21",
                "data_coleta": "2026-01-20T21:00:00-03:00",
                "participantes": ["Aline Campos", "Brigido", "Breno"],
                "consolidado": {
                    "Aline Campos": 48.0,
                    "Brigido": 30.0,
                    "Breno": 22.0,
                    "total_votos": 50000,
                    "predicao_eliminado": "Aline Campos",
                },
                "plataformas": {
                    "sites": {"Aline Campos": 55.0, "Brigido": 25.0, "Breno": 20.0},
                    "youtube": {"Aline Campos": 40.0, "Brigido": 35.0, "Breno": 25.0},
                    "twitter": {"Aline Campos": 46.0, "Brigido": 32.0, "Breno": 22.0},
                    "instagram": {"Aline Campos": 44.0, "Brigido": 31.0, "Breno": 25.0},
                },
                "serie_temporal": [
                    {"hora": "20/jan 15:00", "Aline Campos": 50.0, "Brigido": 28.0, "Breno": 22.0},
                    {"hora": "20/jan 21:00", "Aline Campos": 48.0, "Brigido": 30.0, "Breno": 22.0},
                ],
                "resultado_real": {
                    "Aline Campos": 47.5,
                    "Brigido": 27.5,
                    "Breno": 25.0,
                    "eliminado": "Aline Campos",
                    "predicao_correta": True,
                },
            },
            {
                "numero": 2,
                "data_paredao": "2026-01-28",
                "data_coleta": "2026-01-27T21:00:00-03:00",
                "participantes": ["Matheus", "Samira", "Jordana"],
                "consolidado": {
                    "Matheus": 60.0,
                    "Samira": 25.0,
                    "Jordana": 15.0,
                    "predicao_eliminado": "Matheus",
                },
                "plataformas": {
                    "sites": {"Matheus": 65.0, "Samira": 20.0, "Jordana": 15.0},
                    "youtube": {"Matheus": 55.0, "Samira": 28.0, "Jordana": 17.0},
                    "twitter": {"Matheus": 58.0, "Samira": 26.0, "Jordana": 16.0},
                    "instagram": {"Matheus": 56.0, "Samira": 27.0, "Jordana": 17.0},
                },
                "serie_temporal": [
                    {"hora": "27/jan 15:00", "Matheus": 62.0, "Samira": 23.0, "Jordana": 15.0},
                ],
                "resultado_real": {
                    "Matheus": 58.0,
                    "Samira": 26.0,
                    "Jordana": 16.0,
                    "eliminado": "Matheus",
                },
            },
            {
                "numero": 3,
                "data_paredao": "2026-02-03",
                "data_coleta": "2026-02-02T21:00:00-03:00",
                "participantes": ["Brigido", "Chaiany", "Leandro"],
                "consolidado": {
                    "Brigido": 55.0,
                    "Chaiany": 30.0,
                    "Leandro": 15.0,
                    "predicao_eliminado": "Brigido",
                },
                "plataformas": {
                    "sites": {"Brigido": 60.0, "Chaiany": 25.0, "Leandro": 15.0},
                    "youtube": {"Brigido": 50.0, "Chaiany": 33.0, "Leandro": 17.0},
                    "twitter": {"Brigido": 54.0, "Chaiany": 30.0, "Leandro": 16.0},
                    "instagram": {"Brigido": 52.0, "Chaiany": 32.0, "Leandro": 16.0},
                },
                "serie_temporal": [],
                "resultado_real": {
                    "Brigido": 52.0,
                    "Chaiany": 31.0,
                    "Leandro": 17.0,
                    "eliminado": "Brigido",
                },
            },
        ]
    }


@pytest.fixture
def snapshot_dir(tmp_path):
    """Create a temporary snapshots directory with realistic files."""
    snapshots = tmp_path / "snapshots"
    snapshots.mkdir()

    # 15:00 UTC = 12:00 BRT -> game date 2026-01-20
    snap1 = {
        "_metadata": {"captured_at": "2026-01-20T15:00:00+00:00"},
        "participants": [
            {"name": "Alice", "avatar": "https://img/alice.jpg",
             "characteristics": {"group": "Vip", "memberOf": "Pipoca", "roles": [],
                                  "eliminated": False, "balance": 500,
                                  "receivedReactions": [
                                      {"label": "Coração", "amount": 1,
                                       "participants": [{"id": "2", "name": "Bob"}]}
                                  ]}},
            {"name": "Bob", "avatar": "https://img/bob.jpg",
             "characteristics": {"group": "Xepa", "memberOf": "Veterano", "roles": [],
                                  "eliminated": False, "balance": 300,
                                  "receivedReactions": [
                                      {"label": "Cobra", "amount": 1,
                                       "participants": [{"id": "1", "name": "Alice"}]}
                                  ]}},
        ],
    }

    # 18:00 UTC = 15:00 BRT -> game date 2026-01-20 (same day, later capture)
    snap2 = {
        "_metadata": {"captured_at": "2026-01-20T18:00:00+00:00"},
        "participants": [
            {"name": "Alice", "avatar": "https://img/alice.jpg",
             "characteristics": {"group": "Vip", "memberOf": "Pipoca", "roles": [],
                                  "eliminated": False, "balance": 550,
                                  "receivedReactions": [
                                      {"label": "Coração", "amount": 1,
                                       "participants": [{"id": "2", "name": "Bob"}]}
                                  ]}},
            {"name": "Bob", "avatar": "https://img/bob.jpg",
             "characteristics": {"group": "Xepa", "memberOf": "Veterano", "roles": [],
                                  "eliminated": False, "balance": 350,
                                  "receivedReactions": [
                                      {"label": "Planta", "amount": 1,
                                       "participants": [{"id": "1", "name": "Alice"}]}
                                  ]}},
        ],
    }

    # 15:00 UTC next day = 12:00 BRT -> game date 2026-01-21
    snap3 = {
        "_metadata": {"captured_at": "2026-01-21T15:00:00+00:00"},
        "participants": [
            {"name": "Alice", "avatar": "https://img/alice.jpg",
             "characteristics": {"group": "Vip", "memberOf": "Pipoca", "roles": [],
                                  "eliminated": False, "balance": 600,
                                  "receivedReactions": [
                                      {"label": "Coração", "amount": 2,
                                       "participants": [{"id": "2", "name": "Bob"}, {"id": "3", "name": "Carol"}]}
                                  ]}},
            {"name": "Bob", "avatar": "https://img/bob.jpg",
             "characteristics": {"group": "Xepa", "memberOf": "Veterano", "roles": [],
                                  "eliminated": False, "balance": 400,
                                  "receivedReactions": []}},
            {"name": "Carol", "avatar": "https://img/carol.jpg",
             "characteristics": {"group": "Vip", "memberOf": "Pipoca", "roles": [],
                                  "eliminated": False, "balance": 500,
                                  "receivedReactions": [
                                      {"label": "Coração", "amount": 1,
                                       "participants": [{"id": "1", "name": "Alice"}]}
                                  ]}},
        ],
    }

    (snapshots / "2026-01-20_15-00-00.json").write_text(json.dumps(snap1), encoding="utf-8")
    (snapshots / "2026-01-20_18-00-00.json").write_text(json.dumps(snap2), encoding="utf-8")
    (snapshots / "2026-01-21_15-00-00.json").write_text(json.dumps(snap3), encoding="utf-8")

    return snapshots


# ══════════════════════════════════════════════════════════════
# Priority 1: Data Loaders
# ══════════════════════════════════════════════════════════════

class TestLoadParedoesRaw:
    """Test load_paredoes_raw()."""

    def test_returns_dict_with_file(self, tmp_path, monkeypatch):
        """load_paredoes_raw returns dict with 'paredoes' key."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        filepath = data_dir / "paredoes.json"
        data = {"paredoes": [{"numero": 1, "status": "finalizado"}]}
        filepath.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        result = load_paredoes_raw()
        assert isinstance(result, dict)
        assert "paredoes" in result
        assert len(result["paredoes"]) == 1

    def test_missing_file_returns_empty(self, tmp_path, monkeypatch):
        """Missing file returns empty paredoes list."""
        monkeypatch.chdir(tmp_path)
        result = load_paredoes_raw()
        assert result == {"paredoes": []}


class TestLoadParedoesTransformed:
    """Test load_paredoes_transformed()."""

    def test_transforms_finalized_paredao(self, tmp_path, monkeypatch, paredoes_json_file):
        """Finalized paredão should have participantes with vote data."""
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        import shutil
        shutil.copy(paredoes_json_file, data_dir / "paredoes.json")
        monkeypatch.chdir(tmp_path)
        result = load_paredoes_transformed()
        assert isinstance(result, list)
        assert len(result) == 2
        # First paredão is finalized
        p1 = result[0]
        assert p1["numero"] == 1
        assert p1["status"] == "finalizado"
        assert p1["lider"] == "Jonas Sulzbach"
        assert len(p1["participantes"]) == 3
        # Check vote data is present
        aline = next(p for p in p1["participantes"] if p["nome"] == "Aline Campos")
        assert aline["voto_total"] == 47.5
        assert aline["resultado"] == "ELIMINADA"

    def test_transforms_em_andamento(self, tmp_path, monkeypatch, paredoes_json_file):
        """em_andamento paredão should have total_esperado and no vote data."""
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        import shutil
        shutil.copy(paredoes_json_file, data_dir / "paredoes.json")
        monkeypatch.chdir(tmp_path)
        result = load_paredoes_transformed()
        p2 = result[1]
        assert p2["status"] == "em_andamento"
        assert p2["total_esperado"] == 3
        # No vote data in participantes
        assert "voto_total" not in p2["participantes"][0]

    def test_member_of_fallback(self, tmp_path, monkeypatch):
        """member_of dict should fill missing grupo."""
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        data = {
            "paredoes": [{
                "numero": 1, "status": "finalizado", "data": "2026-01-21",
                "titulo": "1º Paredão", "formacao": {"lider": "X"},
                "indicados_finais": [
                    {"nome": "Alice", "como": "Líder"},  # no grupo
                ],
                "resultado": {
                    "eliminado": "Alice",
                    "votos": {"Alice": {"voto_unico": 50, "voto_torcida": 50, "voto_total": 50}},
                },
            }]
        }
        (data_dir / "paredoes.json").write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        result = load_paredoes_transformed(member_of={"Alice": "Pipoca"})
        assert result[0]["participantes"][0]["grupo"] == "Pipoca"

    def test_empty_file_returns_empty_list(self, tmp_path, monkeypatch):
        """Empty paredoes array returns empty list."""
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        (data_dir / "paredoes.json").write_text('{"paredoes": []}', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        result = load_paredoes_transformed()
        assert result == []


class TestLoadParticipantsIndex:
    """Test load_participants_index()."""

    def test_returns_dict(self, tmp_path, monkeypatch):
        derived = tmp_path / "data" / "derived"
        derived.mkdir(parents=True)
        data = {"participants": [{"name": "Alice", "active": True}]}
        (derived / "participants_index.json").write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        result = load_participants_index()
        assert isinstance(result, dict)
        assert "participants" in result
        assert result["participants"][0]["name"] == "Alice"

    def test_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = load_participants_index()
        assert result == {"participants": []}


class TestLoadRelationsScores:
    """Test load_relations_scores()."""

    def test_returns_dict(self, tmp_path, monkeypatch):
        derived = tmp_path / "data" / "derived"
        derived.mkdir(parents=True)
        data = {"pairs_daily": {}, "edges": []}
        (derived / "relations_scores.json").write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        result = load_relations_scores()
        assert isinstance(result, dict)
        assert "pairs_daily" in result

    def test_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = load_relations_scores()
        assert result == {}


class TestLoadDailyMetrics:
    """Test load_daily_metrics()."""

    def test_returns_dict(self, tmp_path, monkeypatch):
        derived = tmp_path / "data" / "derived"
        derived.mkdir(parents=True)
        data = {"2026-01-20": {"total_reactions": 100}}
        (derived / "daily_metrics.json").write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        result = load_daily_metrics()
        assert isinstance(result, dict)
        assert "2026-01-20" in result

    def test_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = load_daily_metrics()
        assert result == {}


class TestLoadRolesDaily:
    """Test load_roles_daily()."""

    def test_returns_dict(self, tmp_path, monkeypatch):
        derived = tmp_path / "data" / "derived"
        derived.mkdir(parents=True)
        data = {"2026-01-20": {"Alice": {"roles": ["Líder"]}}}
        (derived / "roles_daily.json").write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        result = load_roles_daily()
        assert isinstance(result, dict)

    def test_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = load_roles_daily()
        assert result == {}


class TestLoadReactionMatricesAndDeserialize:
    """Test load_reaction_matrices() and deserialize_matrix()."""

    def test_load_reaction_matrices(self, tmp_path, monkeypatch):
        derived = tmp_path / "data" / "derived"
        derived.mkdir(parents=True)
        data = {
            "2026-01-20": {"Alice|Bob": "Coração", "Bob|Alice": "Cobra"},
        }
        (derived / "reaction_matrices.json").write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        result = load_reaction_matrices()
        assert "2026-01-20" in result

    def test_load_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = load_reaction_matrices()
        assert result == {}

    def test_deserialize_basic(self):
        """deserialize_matrix converts 'A|B' keys to (A, B) tuples."""
        serialized = {"Alice|Bob": "Coração", "Bob|Alice": "Cobra"}
        result = deserialize_matrix(serialized)
        assert result[("Alice", "Bob")] == "Coração"
        assert result[("Bob", "Alice")] == "Cobra"
        assert len(result) == 2

    def test_deserialize_empty(self):
        assert deserialize_matrix({}) == {}

    def test_deserialize_malformed_key(self):
        """Keys without pipe separator should be skipped."""
        serialized = {"AliceBob": "Coração", "Bob|Alice": "Cobra"}
        result = deserialize_matrix(serialized)
        assert len(result) == 1
        assert ("Bob", "Alice") in result

    def test_serialization_roundtrip(self):
        """Serialize then deserialize should produce the original matrix."""
        original = {("Alice", "Bob"): "Coração", ("Carol", "Dave"): "Planta"}
        serialized = {f"{k[0]}|{k[1]}": v for k, v in original.items()}
        roundtripped = deserialize_matrix(serialized)
        assert roundtripped == original


class TestLoadVotalhadaPolls:
    """Test load_votalhada_polls()."""

    def test_load_from_file(self, tmp_path):
        data = {"paredoes": [{"numero": 1}]}
        filepath = tmp_path / "polls.json"
        filepath.write_text(json.dumps(data), encoding="utf-8")
        result = load_votalhada_polls(filepath)
        assert isinstance(result, dict)
        assert "paredoes" in result
        assert len(result["paredoes"]) == 1

    def test_missing_file_returns_empty(self, tmp_path):
        result = load_votalhada_polls(tmp_path / "nonexistent.json")
        assert result == {"paredoes": []}


class TestLoadSinceraoEdges:
    """Test load_sincerao_edges()."""

    def test_load_from_file(self, tmp_path):
        data = {"weeks": [1], "edges": [{"from": "A", "to": "B"}], "aggregates": []}
        filepath = tmp_path / "sincerao.json"
        filepath.write_text(json.dumps(data), encoding="utf-8")
        result = load_sincerao_edges(filepath)
        assert "weeks" in result
        assert len(result["edges"]) == 1

    def test_missing_file_returns_default(self, tmp_path):
        result = load_sincerao_edges(tmp_path / "nonexistent.json")
        assert result == {"weeks": [], "edges": [], "aggregates": []}


class TestGetAllSnapshots:
    """Test get_all_snapshots()."""

    def test_returns_sorted_list(self, snapshot_dir):
        result = get_all_snapshots(snapshot_dir)
        assert len(result) == 3
        # Should be sorted by filename
        assert result[0][0].name == "2026-01-20_15-00-00.json"
        assert result[1][0].name == "2026-01-20_18-00-00.json"
        assert result[2][0].name == "2026-01-21_15-00-00.json"

    def test_game_dates_correct(self, snapshot_dir):
        result = get_all_snapshots(snapshot_dir)
        # 15:00 UTC = 12:00 BRT -> same day
        assert result[0][1] == "2026-01-20"
        # 18:00 UTC = 15:00 BRT -> same day
        assert result[1][1] == "2026-01-20"
        # Next day
        assert result[2][1] == "2026-01-21"

    def test_empty_directory(self, tmp_path):
        empty_dir = tmp_path / "empty_snaps"
        empty_dir.mkdir()
        result = get_all_snapshots(empty_dir)
        assert result == []

    def test_nonexistent_directory(self, tmp_path):
        result = get_all_snapshots(tmp_path / "nope")
        assert result == []

    def test_fallback_for_non_timestamp_filename(self, tmp_path):
        """Non-timestamp filenames use stem split fallback."""
        snap_dir = tmp_path / "snaps"
        snap_dir.mkdir()
        (snap_dir / "2026-01-20_manual.json").write_text('[]', encoding="utf-8")
        result = get_all_snapshots(snap_dir)
        assert len(result) == 1
        assert result[0][1] == "2026-01-20"


class TestGetDailySnapshots:
    """Test get_daily_snapshots()."""

    def test_one_per_date(self):
        """Should return only the last capture per date."""
        snaps = [
            {"date": "2026-01-20", "value": "first"},
            {"date": "2026-01-20", "value": "second"},
            {"date": "2026-01-21", "value": "third"},
        ]
        result = get_daily_snapshots(snaps)
        assert len(result) == 2
        # Last capture for Jan 20 should win
        assert result[0]["value"] == "second"
        assert result[1]["value"] == "third"

    def test_empty_list(self):
        assert get_daily_snapshots([]) == []

    def test_sorted_chronologically(self):
        snaps = [
            {"date": "2026-01-22", "id": 3},
            {"date": "2026-01-20", "id": 1},
            {"date": "2026-01-21", "id": 2},
        ]
        result = get_daily_snapshots(snaps)
        assert [s["date"] for s in result] == ["2026-01-20", "2026-01-21", "2026-01-22"]


class TestGetAllSnapshotsWithData:
    """Test get_all_snapshots_with_data()."""

    def test_loads_participant_data(self, snapshot_dir):
        result = get_all_snapshots_with_data(snapshot_dir)
        assert len(result) == 3
        assert "participants" in result[0]
        assert "date" in result[0]
        assert "metadata" in result[0]
        assert "file" in result[0]
        # First snapshot has Alice and Bob
        names = [p["name"] for p in result[0]["participants"]]
        assert "Alice" in names
        assert "Bob" in names


class TestLoadSnapshotsFull:
    """Test load_snapshots_full()."""

    def test_returns_five_tuple(self, snapshot_dir):
        snapshots, member_of, avatars, daily_snaps, late_entrants = load_snapshots_full(snapshot_dir)
        assert isinstance(snapshots, list)
        assert isinstance(member_of, dict)
        assert isinstance(avatars, dict)
        assert isinstance(daily_snaps, list)
        assert isinstance(late_entrants, dict)

    def test_member_of_populated(self, snapshot_dir):
        _, member_of, _, _, _ = load_snapshots_full(snapshot_dir)
        assert member_of["Alice"] == "Pipoca"
        assert member_of["Bob"] == "Veterano"

    def test_avatars_populated(self, snapshot_dir):
        _, _, avatars, _, _ = load_snapshots_full(snapshot_dir)
        assert avatars["Alice"] == "https://img/alice.jpg"

    def test_daily_snapshots_one_per_date(self, snapshot_dir):
        _, _, _, daily_snaps, _ = load_snapshots_full(snapshot_dir)
        dates = [s["date"] for s in daily_snaps]
        assert len(dates) == len(set(dates))  # No duplicates
        assert len(daily_snaps) == 2  # Jan 20 + Jan 21

    def test_late_entrants_detected(self, snapshot_dir):
        _, _, _, _, late_entrants = load_snapshots_full(snapshot_dir)
        # Carol appears only in the third snapshot
        assert "Carol" in late_entrants
        assert late_entrants["Carol"] == "2026-01-21"
        # Alice and Bob are in the first snapshot, not late
        assert "Alice" not in late_entrants

    def test_labels_and_synthetic(self, snapshot_dir):
        snapshots, _, _, _, _ = load_snapshots_full(snapshot_dir)
        for s in snapshots:
            assert "label" in s
            assert "synthetic" in s
            assert s["synthetic"] is False

    def test_empty_directory(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        snapshots, member_of, avatars, daily, late = load_snapshots_full(empty_dir)
        assert snapshots == []
        assert member_of == {}
        assert avatars == {}
        assert daily == []
        assert late == {}


# ══════════════════════════════════════════════════════════════
# Priority 2: Helper Functions
# ══════════════════════════════════════════════════════════════

class TestGenero:
    """Test genero() gender detection."""

    def test_female_names_in_set(self):
        assert genero("Maxiane") == "f"
        assert genero("Marciele") == "f"
        assert genero("Milena") == "f"
        assert genero("Gabriela") == "f"
        assert genero("Jordana") == "f"
        assert genero("Samira") == "f"
        assert genero("Chaiany") == "f"

    def test_male_names(self):
        assert genero("Breno") == "m"
        assert genero("Leandro") == "m"
        assert genero("Jonas Sulzbach") == "m"
        assert genero("Brigido") == "m"

    def test_female_ending_a(self):
        """Names ending in 'a' are female by default."""
        assert genero("Maria") == "f"
        assert genero("Julia") == "f"

    def test_babu_exception(self):
        """Babu ends in 'a'-like but has 'ba' ending exception."""
        assert genero("Babu Santana") == "m"

    def test_full_names_use_first(self):
        """Should use only first name for detection."""
        assert genero("Ana Paula Renault") == "f"  # 'ana' in _FEMALE_NAMES
        assert genero("Solange Couto") == "f"  # 'solange' in _FEMALE_NAMES
        assert genero("Alberto Cowboy") == "m"

    def test_case_insensitive(self):
        """First name is lowercased before matching."""
        assert genero("MAXIANE") == "f"
        assert genero("BRENO") == "m"


class TestArtigo:
    """Test artigo() Portuguese article helper."""

    def test_definido_female(self):
        assert artigo("Marciele") == "a"
        assert artigo("Gabriela") == "a"

    def test_definido_male(self):
        assert artigo("Breno") == "o"
        assert artigo("Leandro") == "o"

    def test_indefinido_female(self):
        assert artigo("Marciele", definido=False) == "uma"

    def test_indefinido_male(self):
        assert artigo("Breno", definido=False) == "um"


class TestAvatarHtml:
    """Test avatar_html() HTML generation."""

    def test_basic_with_name(self):
        avatars = {"Alice": "https://img/alice.jpg"}
        html = avatar_html("Alice", avatars)
        assert "img" in html
        assert 'src="https://img/alice.jpg"' in html
        assert "Alice" in html

    def test_without_name(self):
        avatars = {"Alice": "https://img/alice.jpg"}
        html = avatar_html("Alice", avatars, show_name=False)
        assert "img" in html
        # Name should not appear as text (only in alt/title)
        assert html.count("Alice") <= 2  # alt + title only

    def test_no_avatar_fallback(self):
        """Without avatar URL and no fallback, returns just the name."""
        html = avatar_html("Unknown", {})
        assert html == "Unknown"

    def test_no_avatar_no_name(self):
        """Without avatar URL and show_name=False, returns empty."""
        html = avatar_html("Unknown", {}, show_name=False)
        assert html == ""

    def test_fallback_initials(self):
        """With fallback_initials, shows first 2 chars."""
        html = avatar_html("Unknown Player", {}, fallback_initials=True)
        assert "Un" in html
        assert "span" in html

    def test_border_color(self):
        avatars = {"Alice": "https://img/alice.jpg"}
        html = avatar_html("Alice", avatars, border_color="#ff0000")
        assert "border:2px solid #ff0000" in html

    def test_grayscale(self):
        avatars = {"Alice": "https://img/alice.jpg"}
        html = avatar_html("Alice", avatars, grayscale=True)
        assert "grayscale(100%)" in html
        assert "opacity:0.7" in html

    def test_link(self):
        avatars = {"Alice": "https://img/alice.jpg"}
        html = avatar_html("Alice", avatars, link="#perfil-alice")
        assert 'href="#perfil-alice"' in html
        assert "<a " in html

    def test_custom_size(self):
        avatars = {"Alice": "https://img/alice.jpg"}
        html = avatar_html("Alice", avatars, size=48)
        assert 'width="48"' in html
        assert 'height="48"' in html


class TestAvatarImg:
    """Test avatar_img() convenience wrapper."""

    def test_no_name_shown(self):
        avatars = {"Alice": "https://img/alice.jpg"}
        html = avatar_img("Alice", avatars)
        assert "img" in html
        # Name text should NOT be shown (show_name=False)
        assert not html.endswith(" Alice")

    def test_custom_size(self):
        avatars = {"Alice": "https://img/alice.jpg"}
        html = avatar_img("Alice", avatars, size=32)
        assert 'width="32"' in html


class TestGetNomineeBadge:
    """Test get_nominee_badge()."""

    def test_eliminada_female(self):
        entry = {"resultado": {"eliminado": "Aline Campos"}, "status": "finalizado"}
        text, color, emoji = get_nominee_badge("Aline Campos", entry)
        assert text == "ELIMINADA"
        assert color == "#e74c3c"
        assert emoji == "🔴"

    def test_eliminado_male(self):
        entry = {"resultado": {"eliminado": "Brigido"}, "status": "finalizado"}
        text, color, emoji = get_nominee_badge("Brigido", entry)
        assert text == "ELIMINADO"

    def test_salva_female(self):
        entry = {"resultado": {"eliminado": "Brigido"}, "status": "finalizado"}
        text, color, emoji = get_nominee_badge("Marciele", entry)
        assert text == "SALVA"
        assert color == "#00bc8c"
        assert emoji == "🟢"

    def test_salvo_male(self):
        entry = {"resultado": {"eliminado": "Aline Campos"}, "status": "finalizado"}
        text, color, emoji = get_nominee_badge("Breno", entry)
        assert text == "SALVO"

    def test_em_votacao(self):
        entry = {"status": "em_andamento"}
        text, color, emoji = get_nominee_badge("Alice", entry)
        assert text == "EM VOTAÇÃO"
        assert color == "#f39c12"
        assert emoji == "🟡"

    def test_bate_volta_survivor(self):
        entry = {"resultado": {"eliminado": "X"}, "status": "finalizado"}
        text, color, emoji = get_nominee_badge("Alice", entry, bate_volta_survivors={"Alice"})
        assert text == "ESCAPOU DO BATE-VOLTA"
        assert color == "#3498db"
        assert emoji == "🔵"


class TestRenderCronologiaHtml:
    """Test render_cronologia_html()."""

    def test_empty_events(self):
        html = render_cronologia_html([])
        assert "Nenhum evento" in html

    def test_basic_rendering(self):
        events = [
            {
                "date": "2026-01-13", "week": 1, "category": "entrada",
                "emoji": "🏠", "title": "Entrada dos Participantes",
                "detail": "21 participantes",
            },
        ]
        html = render_cronologia_html(events)
        assert "Semana 1" in html
        assert "Entrada" in html
        assert "2026-01-13" in html
        assert "table" in html

    def test_scheduled_event_rendering(self):
        events = [
            {
                "date": "2026-02-01", "week": 3, "category": "lider",
                "emoji": "👑", "title": "Prova do Líder",
                "detail": "A definir", "status": "scheduled", "time": "Ao Vivo",
            },
        ]
        html = render_cronologia_html(events)
        assert "dashed" in html  # scheduled events use dashed borders
        assert "🔮" in html  # scheduled detail prefix

    def test_multiple_weeks_ordering(self):
        events = [
            {"date": "2026-01-13", "week": 1, "category": "entrada",
             "emoji": "", "title": "Week 1 Event", "detail": ""},
            {"date": "2026-01-20", "week": 2, "category": "lider",
             "emoji": "", "title": "Week 2 Event", "detail": ""},
        ]
        html = render_cronologia_html(events)
        # Latest week should appear first in the HTML
        idx_w2 = html.index("Semana 2")
        idx_w1 = html.index("Semana 1")
        assert idx_w2 < idx_w1  # Week 2 before Week 1


class TestNormalizeActors:
    """Test normalize_actors() with more edge cases."""

    def test_actors_list_preferred(self):
        ev = {"actor": "A + B", "actors": ["X", "Y"]}
        assert normalize_actors(ev) == ["X", "Y"]

    def test_plus_separator(self):
        ev = {"actor": "Alice + Bob + Carol"}
        assert normalize_actors(ev) == ["Alice", "Bob", "Carol"]

    def test_e_separator(self):
        ev = {"actor": "Alice e Bob"}
        assert normalize_actors(ev) == ["Alice", "Bob"]

    def test_single_actor(self):
        ev = {"actor": "Alice"}
        assert normalize_actors(ev) == ["Alice"]

    def test_no_actor(self):
        assert normalize_actors({}) == []

    def test_empty_actors_list_falls_through(self):
        """Empty actors list should fall through to actor string."""
        ev = {"actor": "Alice", "actors": []}
        assert normalize_actors(ev) == ["Alice"]

    def test_filters_empty_strings(self):
        ev = {"actors": ["Alice", "", "Bob"]}
        assert normalize_actors(ev) == ["Alice", "Bob"]


class TestPatchMissingRaioX:
    """Test patch_missing_raio_x()."""

    def test_no_previous_matrix(self):
        matrix = {("Alice", "Bob"): "Coração"}
        participants = [{"name": "Alice"}, {"name": "Bob"}]
        result, carried = patch_missing_raio_x(matrix, participants, {})
        assert carried == []
        assert result == matrix

    def test_carries_forward_missing(self):
        """Participant with 0 outgoing reactions gets previous day's reactions."""
        matrix = {("Alice", "Bob"): "Coração"}  # Bob has no outgoing
        participants = [{"name": "Alice"}, {"name": "Bob"}]
        prev_matrix = {("Bob", "Alice"): "Planta", ("Alice", "Bob"): "Cobra"}
        result, carried = patch_missing_raio_x(matrix, participants, prev_matrix)
        assert "Bob" in carried
        assert result[("Bob", "Alice")] == "Planta"
        # Alice's reaction is not overwritten
        assert result[("Alice", "Bob")] == "Coração"

    def test_no_carry_forward_when_present(self):
        """Participant with outgoing reactions should not be patched."""
        matrix = {("Alice", "Bob"): "Coração", ("Bob", "Alice"): "Planta"}
        participants = [{"name": "Alice"}, {"name": "Bob"}]
        prev_matrix = {("Bob", "Alice"): "Cobra"}
        result, carried = patch_missing_raio_x(matrix, participants, prev_matrix)
        assert carried == []
        assert result[("Bob", "Alice")] == "Planta"  # Not overwritten


# ══════════════════════════════════════════════════════════════
# Priority 3: Poll/Prediction Functions
# ══════════════════════════════════════════════════════════════

class TestGetPollForParedao:
    """Test get_poll_for_paredao()."""

    def test_find_existing(self, polls_json_data):
        result = get_poll_for_paredao(polls_json_data, 1)
        assert result is not None
        assert result["numero"] == 1

    def test_not_found(self, polls_json_data):
        result = get_poll_for_paredao(polls_json_data, 99)
        assert result is None

    def test_empty_data(self):
        result = get_poll_for_paredao({"paredoes": []}, 1)
        assert result is None


class TestCalculatePollAccuracy:
    """Test calculate_poll_accuracy()."""

    def test_correct_prediction(self, polls_json_data):
        poll = polls_json_data["paredoes"][0]
        result = calculate_poll_accuracy(poll)
        assert result is not None
        assert result["predicao_correta"] is True
        assert "erro_medio" in result
        assert isinstance(result["erro_medio"], float)

    def test_per_participant_errors(self, polls_json_data):
        poll = polls_json_data["paredoes"][0]
        result = calculate_poll_accuracy(poll)
        errors = result["erros_por_participante"]
        # Aline: 48.0 - 47.5 = 0.5
        assert errors["Aline Campos"] == pytest.approx(0.5)

    def test_no_resultado_real(self):
        poll = {"consolidado": {"A": 50}, "participantes": ["A"]}
        result = calculate_poll_accuracy(poll)
        assert result is None

    def test_none_poll(self):
        assert calculate_poll_accuracy(None) is None


class TestCalculatePrecisionWeights:
    """Test calculate_precision_weights()."""

    def test_sufficient_data(self, polls_json_data):
        result = calculate_precision_weights(polls_json_data)
        assert result["sufficient"] is True
        assert result["n_paredoes"] == 3
        assert "weights" in result
        assert "rmse" in result
        # Weights should sum to ~1
        total = sum(result["weights"].values())
        assert total == pytest.approx(1.0, abs=0.01)

    def test_insufficient_data(self):
        data = {"paredoes": [{"resultado_real": {"A": 50}}]}
        result = calculate_precision_weights(data)
        assert result["sufficient"] is False
        assert all(v == 0.25 for v in result["weights"].values())

    def test_empty_data(self):
        result = calculate_precision_weights({"paredoes": []})
        assert result["sufficient"] is False
        assert result["n_paredoes"] == 0

    def test_all_platforms_have_weights(self, polls_json_data):
        result = calculate_precision_weights(polls_json_data)
        for plat in ["sites", "youtube", "twitter", "instagram"]:
            assert plat in result["weights"]
            assert result["weights"][plat] > 0


class TestPredictPrecisionWeighted:
    """Test predict_precision_weighted()."""

    def test_basic_prediction(self, polls_json_data):
        precision = calculate_precision_weights(polls_json_data)
        poll = polls_json_data["paredoes"][0]
        result = predict_precision_weighted(poll, precision)
        assert result is not None
        assert "prediction" in result
        assert "predicao_eliminado" in result
        assert "weights_used" in result
        # Predictions should sum to ~100
        total = sum(result["prediction"].values())
        assert total == pytest.approx(100.0, abs=0.5)

    def test_insufficient_precision(self, polls_json_data):
        poll = polls_json_data["paredoes"][0]
        precision = {"sufficient": False, "weights": {}}
        result = predict_precision_weighted(poll, precision)
        assert result is None

    def test_no_plataformas(self):
        poll = {"participantes": ["A"], "plataformas": {}}
        precision = {"sufficient": True, "weights": {"sites": 0.5, "twitter": 0.5}}
        result = predict_precision_weighted(poll, precision)
        assert result is None


class TestBacktestPrecisionModel:
    """Test backtest_precision_model()."""

    def test_with_sufficient_data(self, polls_json_data):
        result = backtest_precision_model(polls_json_data)
        assert result is not None
        assert "per_paredao" in result
        assert "aggregate" in result
        assert result["aggregate"]["n_paredoes"] > 0
        assert "consolidado_mae" in result["aggregate"]
        assert "model_mae" in result["aggregate"]

    def test_insufficient_data(self):
        data = {"paredoes": [
            {"numero": 1, "resultado_real": {"A": 50}},
            {"numero": 2, "resultado_real": {"A": 50}},
        ]}
        result = backtest_precision_model(data)
        assert result is None  # < 3 finalized

    def test_empty_data(self):
        result = backtest_precision_model({"paredoes": []})
        assert result is None


class TestParseVotalhadaHora:
    """Test parse_votalhada_hora()."""

    def test_basic_parse(self):
        result = parse_votalhada_hora("20/jan 15:00")
        assert result == datetime(2026, 1, 20, 15, 0)

    def test_february(self):
        result = parse_votalhada_hora("03/fev 21:30")
        assert result == datetime(2026, 2, 3, 21, 30)

    def test_custom_year(self):
        result = parse_votalhada_hora("15/mar 10:00", year=2025)
        assert result == datetime(2025, 3, 15, 10, 0)

    def test_all_months_in_map(self):
        """All 12 months should be in MONTH_MAP_PT."""
        assert len(MONTH_MAP_PT) == 12
        for i, month in enumerate(['jan', 'fev', 'mar', 'abr', 'mai', 'jun',
                                     'jul', 'ago', 'set', 'out', 'nov', 'dez'], 1):
            assert MONTH_MAP_PT[month] == i


# ══════════════════════════════════════════════════════════════
# Priority 4: Viz Helpers (require plotly)
# ══════════════════════════════════════════════════════════════

class TestMakeHorizontalBar:
    """Test make_horizontal_bar()."""

    def test_returns_figure(self):
        from data_utils import make_horizontal_bar
        setup_bbb_dark_theme()
        fig = make_horizontal_bar(
            ["Alice", "Bob", "Carol"],
            [10.0, 5.0, 3.0],
            title="Test Bar",
        )
        import plotly.graph_objects as go
        assert isinstance(fig, go.Figure)

    def test_auto_height(self):
        from data_utils import make_horizontal_bar
        setup_bbb_dark_theme()
        fig = make_horizontal_bar(
            ["A", "B"],
            [1.0, 2.0],
        )
        # Auto height = max(300, 2*32 + 100) = 300
        assert fig.layout.height == 300

    def test_custom_colors(self):
        from data_utils import make_horizontal_bar
        setup_bbb_dark_theme()
        fig = make_horizontal_bar(
            ["A", "B"],
            [1.0, 2.0],
            colors="#ff0000",
        )
        assert fig.data[0].marker.color == "#ff0000"

    def test_custom_height(self):
        from data_utils import make_horizontal_bar
        setup_bbb_dark_theme()
        fig = make_horizontal_bar(
            ["A", "B"],
            [1.0, 2.0],
            height=500,
        )
        assert fig.layout.height == 500


class TestMakeSentimentHeatmap:
    """Test make_sentiment_heatmap()."""

    def test_returns_figure(self):
        from data_utils import make_sentiment_heatmap
        setup_bbb_dark_theme()
        fig = make_sentiment_heatmap(
            z_data=[[1.0, -0.5], [-1.0, 0.5]],
            x_labels=["Alice", "Bob"],
            y_labels=["Alice", "Bob"],
            title="Test Heatmap",
        )
        import plotly.graph_objects as go
        assert isinstance(fig, go.Figure)

    def test_auto_height(self):
        from data_utils import make_sentiment_heatmap
        setup_bbb_dark_theme()
        fig = make_sentiment_heatmap(
            z_data=[[1.0]],
            x_labels=["A"],
            y_labels=["A"],
        )
        # Auto height = max(400, 1*28 + 150) = 400
        assert fig.layout.height == 400

    def test_custom_zmin_zmax(self):
        from data_utils import make_sentiment_heatmap
        setup_bbb_dark_theme()
        fig = make_sentiment_heatmap(
            z_data=[[1.0, -1.0], [0.5, -0.5]],
            x_labels=["A", "B"],
            y_labels=["A", "B"],
            zmin=-2.0,
            zmax=2.0,
        )
        assert fig.data[0].zmin == -2.0
        assert fig.data[0].zmax == 2.0

    def test_text_matrix(self):
        from data_utils import make_sentiment_heatmap
        setup_bbb_dark_theme()
        fig = make_sentiment_heatmap(
            z_data=[[1.0]],
            x_labels=["A"],
            y_labels=["A"],
            text_matrix=[["hello"]],
        )
        assert list(fig.data[0].text) == [["hello"]]


class TestMakePollTimeseries:
    """Test make_poll_timeseries()."""

    def test_returns_figure(self, polls_json_data):
        from data_utils import make_poll_timeseries
        setup_bbb_dark_theme()
        poll = polls_json_data["paredoes"][0]
        fig = make_poll_timeseries(poll)
        import plotly.graph_objects as go
        assert isinstance(fig, go.Figure)
        # Should have one trace per participant
        assert len(fig.data) == 3

    def test_with_resultado_real(self, polls_json_data):
        from data_utils import make_poll_timeseries
        setup_bbb_dark_theme()
        poll = polls_json_data["paredoes"][0]
        fig = make_poll_timeseries(poll, resultado_real=poll["resultado_real"])
        assert fig is not None

    def test_compact_mode(self, polls_json_data):
        from data_utils import make_poll_timeseries
        setup_bbb_dark_theme()
        poll = polls_json_data["paredoes"][0]
        fig = make_poll_timeseries(poll, compact=True)
        assert fig.layout.height == 350

    def test_empty_serie_temporal(self):
        from data_utils import make_poll_timeseries
        poll = {"serie_temporal": [], "participantes": ["A"]}
        assert make_poll_timeseries(poll) is None

    def test_no_participantes(self):
        from data_utils import make_poll_timeseries
        poll = {"serie_temporal": [{"hora": "20/jan 15:00"}], "participantes": []}
        assert make_poll_timeseries(poll) is None


# ══════════════════════════════════════════════════════════════
# Other Functions
# ══════════════════════════════════════════════════════════════

class TestRequireCleanManualEvents:
    """Test require_clean_manual_events()."""

    def test_clean_audit_passes(self, tmp_path):
        audit_file = tmp_path / "audit.json"
        audit_file.write_text('{"issues_count": 0}', encoding="utf-8")
        # Should not raise
        require_clean_manual_events(audit_file)

    def test_dirty_audit_raises(self, tmp_path):
        audit_file = tmp_path / "audit.json"
        audit_file.write_text('{"issues_count": 3}', encoding="utf-8")
        with pytest.raises(RuntimeError, match="3 problema"):
            require_clean_manual_events(audit_file)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(RuntimeError, match="não encontrado"):
            require_clean_manual_events(tmp_path / "nonexistent.json")


class TestSetupBbbDarkTheme:
    """Test setup_bbb_dark_theme()."""

    def test_registers_template(self):
        import plotly.io as pio
        setup_bbb_dark_theme()
        assert "bbb_dark" in pio.templates
        assert pio.templates.default == "bbb_dark"
