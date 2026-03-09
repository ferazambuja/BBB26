"""Regression tests for prova rankings completeness warnings."""

from __future__ import annotations

import logging

from build_derived_data import build_prova_rankings
from data_utils import load_provas_raw, load_participants_index


def test_real_provas_data_emits_no_completeness_warnings(caplog):
    provas_data = load_provas_raw()
    participants_index = load_participants_index()["participants"]

    with caplog.at_level(logging.WARNING, logger="builders.provas"):
        build_prova_rankings(provas_data, participants_index)

    warnings = [
        record.getMessage()
        for record in caplog.records
        if "classificacao completeness" in record.getMessage()
    ]
    assert warnings == []
