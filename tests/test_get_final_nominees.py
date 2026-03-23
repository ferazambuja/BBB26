"""Tests for get_final_nominees() in data_utils."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from data_utils import get_final_nominees


# --- Unit tests with synthetic data ---


def test_standard_3_nominees_no_bate_volta():
    """Standard 3-nominee paredao with no bate_volta returns all 3."""
    entry = {
        "indicados_finais": [
            {"nome": "Alice", "grupo": "Pipoca", "como": "Lider"},
            {"nome": "Bob", "grupo": "Camarote", "como": "Mais votado"},
            {"nome": "Carol", "grupo": "Pipoca", "como": "Contragolpe"},
        ],
        "formacao": {
            "resumo": "Test paredao",
        },
    }
    result = get_final_nominees(entry)
    assert result == ["Alice", "Bob", "Carol"]


def test_4_nominees_with_bate_volta_winner():
    """P10-style: 4 indicados_finais + bate_volta.vencedor removes the winner."""
    entry = {
        "indicados_finais": [
            {"nome": "Jordana", "grupo": "Pipoca", "como": "Dinamica"},
            {"nome": "Floss", "grupo": "Pipoca", "como": "Lider"},
            {"nome": "Jonas", "grupo": "Camarote", "como": "Mais votado"},
            {"nome": "Gabriela", "grupo": "Pipoca", "como": "Contragolpe"},
        ],
        "formacao": {
            "bate_volta": {
                "participantes": ["Jordana", "Jonas", "Gabriela"],
                "vencedor": "Jordana",
            },
        },
    }
    result = get_final_nominees(entry)
    assert len(result) == 3
    assert "Jordana" not in result
    assert result == ["Floss", "Jonas", "Gabriela"]


def test_no_formacao_key():
    """No formacao key returns all indicados_finais."""
    entry = {
        "indicados_finais": [
            {"nome": "Alice", "grupo": "Pipoca", "como": "Lider"},
            {"nome": "Bob", "grupo": "Camarote", "como": "Mais votado"},
        ],
    }
    result = get_final_nominees(entry)
    assert result == ["Alice", "Bob"]


def test_bate_volta_vencedor_is_none():
    """bate_volta exists but vencedor is None returns all indicados_finais."""
    entry = {
        "indicados_finais": [
            {"nome": "Alice", "grupo": "Pipoca", "como": "Lider"},
            {"nome": "Bob", "grupo": "Camarote", "como": "Mais votado"},
            {"nome": "Carol", "grupo": "Pipoca", "como": "Contragolpe"},
        ],
        "formacao": {
            "bate_volta": {
                "participantes": ["Alice", "Bob", "Carol"],
                "vencedor": None,
            },
        },
    }
    result = get_final_nominees(entry)
    assert result == ["Alice", "Bob", "Carol"]


def test_empty_indicados_finais():
    """Empty indicados_finais returns empty list."""
    entry = {
        "indicados_finais": [],
        "formacao": {
            "bate_volta": {
                "vencedor": "Nobody",
            },
        },
    }
    result = get_final_nominees(entry)
    assert result == []


def test_missing_indicados_finais_key():
    """Missing indicados_finais key returns empty list."""
    entry = {"formacao": {"resumo": "Test"}}
    result = get_final_nominees(entry)
    assert result == []


# --- Integration test with real paredoes.json ---


@pytest.fixture
def real_paredoes():
    """Load real paredoes.json if available."""
    path = Path("data/paredoes.json")
    if not path.exists():
        pytest.skip("data/paredoes.json not available")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def test_p10_real_data(real_paredoes):
    """P10 should return 3 nominees (Gabriela, Jonas Sulzbach, Juliano Floss)."""
    p10 = next(
        (p for p in real_paredoes["paredoes"] if p["numero"] == 10),
        None,
    )
    if p10 is None:
        pytest.skip("P10 not in paredoes.json")
    result = get_final_nominees(p10)
    assert len(result) == 3
    assert "Jordana" not in result
    assert set(result) == {"Gabriela", "Jonas Sulzbach", "Juliano Floss"}


def test_all_paredoes_have_nominees(real_paredoes):
    """Every paredao with indicados_finais should return at least 1 nominee."""
    for p in real_paredoes["paredoes"]:
        if not p.get("indicados_finais"):
            continue
        result = get_final_nominees(p)
        assert len(result) >= 1, f"P{p['numero']} returned no nominees"


def test_bate_volta_winners_excluded(real_paredoes):
    """For paredoes with bate_volta.vencedor, the winner should not be in nominees."""
    for p in real_paredoes["paredoes"]:
        bv = p.get("formacao", {}).get("bate_volta") or {}
        vencedor = bv.get("vencedor")
        if not vencedor:
            continue
        result = get_final_nominees(p)
        assert vencedor not in result, (
            f"P{p['numero']}: bate_volta winner {vencedor} should not be in nominees"
        )
