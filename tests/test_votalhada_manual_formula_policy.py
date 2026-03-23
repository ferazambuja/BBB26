"""Regression checks for the temporary manual Votalhada formula policy."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
POLLS_PATH = REPO_ROOT / "data" / "votalhada" / "polls.json"


def _poll(numero: int) -> dict:
    data = json.loads(POLLS_PATH.read_text(encoding="utf-8"))
    return next(p for p in data["paredoes"] if p["numero"] == numero)


def test_p8_uses_manual_legacy_weighted_snapshot_after_formula_change():
    poll = _poll(8)

    assert poll["data_coleta"] == "2026-03-10T21:00:00-03:00"
    assert poll["consolidado"]["Babu Santana"] == 54.22
    assert poll["consolidado"]["Chaiany"] == 2.63
    assert poll["consolidado"]["Milena"] == 43.23
    assert poll["consolidado"]["total_votos"] == 9032157
    assert poll["consolidado"]["predicao_eliminado"] == "Babu Santana"

    last_row = poll["serie_temporal"][-1]
    assert last_row["hora"] == "10/mar 21:00"
    assert last_row["Babu Santana"] == 54.22
    assert last_row["Chaiany"] == 2.63
    assert last_row["Milena"] == 43.23
    assert last_row["votos"] == 9032157

    metodologia = poll["metodologia"]
    assert metodologia["modo"] == "manual_vision_legacy_weighted"
    assert "0,3 x 0,7" in metodologia["formula_votalhada_exibida"]
    assert "ponderada pelo número de votos" in metodologia["formula_nossa"]


def test_p10_latest_manual_snapshot_matches_23_mar_15h_capture():
    poll = _poll(10)

    assert poll["data_coleta"] == "2026-03-23T15:00:00-03:00"
    assert poll["consolidado"]["Gabriela"] == 10.54
    assert poll["consolidado"]["Jonas Sulzbach"] == 44.51
    assert poll["consolidado"]["Juliano Floss"] == 45.08
    assert poll["consolidado"]["total_votos"] == 7353043
    assert poll["consolidado"]["predicao_eliminado"] == "Juliano Floss"

    assert poll["plataformas"]["sites"] == {
        "Gabriela": 8.21,
        "Jonas Sulzbach": 37.51,
        "Juliano Floss": 54.28,
        "votos": 2097805,
        "label": "Voto da Torcida",
    }
    assert poll["plataformas"]["youtube"] == {
        "Gabriela": 13.00,
        "Jonas Sulzbach": 36.92,
        "Juliano Floss": 50.64,
        "votos": 1210600,
    }
    assert poll["plataformas"]["twitter"] == {
        "Gabriela": 5.85,
        "Jonas Sulzbach": 55.61,
        "Juliano Floss": 38.53,
        "votos": 704888,
    }
    assert poll["plataformas"]["instagram"] == {
        "Gabriela": 15.76,
        "Jonas Sulzbach": 50.00,
        "Juliano Floss": 34.24,
        "votos": 3339750,
    }

    last_row = poll["serie_temporal"][-1]
    assert last_row["hora"] == "23/mar 15:00"
    assert last_row["Gabriela"] == 10.54
    assert last_row["Jonas Sulzbach"] == 44.51
    assert last_row["Juliano Floss"] == 45.08
    assert last_row["votos"] == 7353043
