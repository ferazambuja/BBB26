"""Regression checks for the temporary manual Votalhada formula policy."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
POLLS_PATH = REPO_ROOT / "data" / "votalhada" / "polls.json"
sys.path.insert(0, str(REPO_ROOT / "scripts"))


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


def test_p9_keeps_legacy_weighted_consolidado_and_3070_series_separate():
    poll = _poll(9)

    assert poll["consolidado"]["Ana Paula Renault"] == 31.54
    assert poll["consolidado"]["Breno"] == 46.68
    assert poll["consolidado"]["Leandro"] == 21.69
    assert poll["consolidado"]["predicao_eliminado"] == "Breno"

    last_row = poll["serie_temporal"][-1]
    assert last_row["hora"] == "17/mar 21:00"
    assert last_row["Ana Paula Renault"] == 21.72
    assert last_row["Breno"] == 54.66
    assert last_row["Leandro"] == 23.51

    metodologia = poll["metodologia"]
    assert metodologia["modo"] == "manual_vision_legacy_weighted"
    assert "0,3 x 0,7" in metodologia["formula_votalhada_exibida"]
    assert "ponderada pelo número de votos" in metodologia["formula_nossa"]


def test_p10_latest_manual_snapshot_keeps_weighted_consolidado_separate_from_displayed_3070():
    poll = _poll(10)

    assert poll["data_coleta"] == "2026-03-23T18:00:00-03:00"
    assert poll["consolidado"]["Gabriela"] == 11.62
    assert poll["consolidado"]["Jonas Sulzbach"] == 44.99
    assert poll["consolidado"]["Juliano Floss"] == 43.48
    assert poll["consolidado"]["total_votos"] == 8063703
    assert poll["consolidado"]["predicao_eliminado"] == "Jonas Sulzbach"

    assert poll["plataformas"]["sites"] == {
        "Gabriela": 7.43,
        "Jonas Sulzbach": 39.49,
        "Juliano Floss": 53.08,
        "votos": 2532063,
        "label": "Voto da Torcida",
    }
    assert poll["plataformas"]["youtube"] == {
        "Gabriela": 12.72,
        "Jonas Sulzbach": 37.28,
        "Juliano Floss": 50.55,
        "votos": 1361400,
    }
    assert poll["plataformas"]["twitter"] == {
        "Gabriela": 5.77,
        "Jonas Sulzbach": 55.60,
        "Juliano Floss": 38.63,
        "votos": 733804,
    }
    assert poll["plataformas"]["instagram"] == {
        "Gabriela": 15.53,
        "Jonas Sulzbach": 49.82,
        "Juliano Floss": 34.65,
        "votos": 3436436,
    }

    assert poll["serie_temporal"] == [
        {
            "hora": "23/mar 01:00",
            "Gabriela": 12.77,
            "Jonas Sulzbach": 47.92,
            "Juliano Floss": 39.37,
            "votos": 2373937,
        },
        {
            "hora": "23/mar 08:00",
            "Gabriela": 12.09,
            "Jonas Sulzbach": 46.64,
            "Juliano Floss": 41.41,
            "votos": 4800045,
        },
        {
            "hora": "23/mar 12:00",
            "Gabriela": 11.02,
            "Jonas Sulzbach": 43.70,
            "Juliano Floss": 45.39,
            "votos": 6046059,
        },
        {
            "hora": "23/mar 15:00",
            "Gabriela": 10.54,
            "Jonas Sulzbach": 44.51,
            "Juliano Floss": 45.08,
            "votos": 7353043,
        },
        {
            "hora": "23/mar 18:00",
            "Gabriela": 10.17,
            "Jonas Sulzbach": 45.15,
            "Juliano Floss": 44.82,
            "votos": 8063703,
        },
    ]

    metodologia = poll["metodologia"]
    assert metodologia["modo"] == "manual_vision_legacy_weighted"
    assert "0,3 x 0,7" in metodologia["formula_votalhada_exibida"]
    assert "ponderada pelo número de votos" in metodologia["formula_nossa"]


def test_formula_change_timeseries_gets_weighted_overlay_markers():
    from data_utils import make_poll_timeseries, setup_bbb_dark_theme

    setup_bbb_dark_theme()
    poll = {
        "participantes": ["A", "B", "C"],
        "serie_temporal": [
            {"hora": "23/mar 12:00", "A": 10.0, "B": 44.0, "C": 46.0, "votos": 1000},
            {"hora": "23/mar 15:00", "A": 10.5, "B": 44.5, "C": 45.0, "votos": 1200},
        ],
        "consolidado": {"A": 12.0, "B": 45.0, "C": 43.0, "total_votos": 1200},
        "metodologia": {
            "modo": "manual_vision_legacy_weighted",
            "formula_votalhada_exibida": "0,3 x 0,7: 0,3 * Sites + 0,7 * média simples de YouTube, Twitter e Instagram",
            "formula_nossa": "Média ponderada pelo número de votos de cada plataforma (fórmula anterior do Votalhada)",
        },
    }

    fig = make_poll_timeseries(poll)

    weighted_traces = [
        tr for tr in fig.data
        if getattr(getattr(tr, "marker", None), "symbol", None) == "square-open"
    ]
    assert len(weighted_traces) == 3
    assert all(len(tr.x) == 1 for tr in weighted_traces)
    assert "Janela:" in fig.layout.title.text


def test_formula_change_helpers_distinguish_formula_recalc_from_displayed_card_values():
    from data_utils import (
        calculate_votalhada_estimate_3070,
        calculate_votalhada_vote_weighted,
        get_latest_votalhada_displayed_values,
    )

    participantes = ["Gabriela", "Jonas Sulzbach", "Juliano Floss"]
    plataformas = {
        "sites": {
            "Gabriela": 7.43,
            "Jonas Sulzbach": 39.49,
            "Juliano Floss": 53.08,
            "votos": 2532063,
        },
        "youtube": {
            "Gabriela": 12.72,
            "Jonas Sulzbach": 37.28,
            "Juliano Floss": 50.55,
            "votos": 1361400,
        },
        "twitter": {
            "Gabriela": 5.77,
            "Jonas Sulzbach": 55.60,
            "Juliano Floss": 38.63,
            "votos": 733804,
        },
        "instagram": {
            "Gabriela": 15.53,
            "Jonas Sulzbach": 49.82,
            "Juliano Floss": 34.65,
            "votos": 3436436,
        },
    }

    estimate_3070 = calculate_votalhada_estimate_3070(plataformas, participantes)
    weighted = calculate_votalhada_vote_weighted(plataformas, participantes)
    displayed = get_latest_votalhada_displayed_values(
        {
            "participantes": participantes,
            "serie_temporal": [
                {
                    "hora": "23/mar 18:00",
                    "Gabriela": 10.17,
                    "Jonas Sulzbach": 45.15,
                    "Juliano Floss": 44.82,
                    "votos": 8063703,
                }
            ],
        }
    )

    assert estimate_3070 == {
        "Gabriela": 10.17,
        "Jonas Sulzbach": 45.14,
        "Juliano Floss": 44.82,
    }
    assert weighted == {
        "Gabriela": 11.62,
        "Jonas Sulzbach": 44.99,
        "Juliano Floss": 43.48,
    }
    assert displayed == {
        "Gabriela": 10.17,
        "Jonas Sulzbach": 45.15,
        "Juliano Floss": 44.82,
    }
