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

