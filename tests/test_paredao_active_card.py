"""Tests for the shared active/finalized paredao card payload and renderers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from data_utils import (
    calculate_precision_weights,
    get_poll_for_paredao,
    load_paredoes_transformed,
    load_snapshots_full,
    load_votalhada_polls,
    predict_precision_weighted,
)
from paredao_viz import (
    build_paredao_card_payload,
    build_paredao_history,
    build_poll_comparison_payload,
    render_paredao_index_card,
    render_paredao_live_card,
    render_poll_comparison_card,
)


@pytest.fixture(scope="module")
def _repo_data():
    snapshots, member_of, avatars, daily_snapshots, late_entrants = load_snapshots_full()
    polls_data = load_votalhada_polls()
    paredoes = load_paredoes_transformed(member_of=member_of)
    raw_paredoes = json.loads((Path(__file__).resolve().parents[1] / "data" / "paredoes.json").read_text(encoding="utf-8"))
    return {
        "member_of": member_of,
        "avatars": avatars,
        "polls_data": polls_data,
        "paredoes": paredoes,
        "raw_paredoes": raw_paredoes["paredoes"],
    }


def test_active_payload_uses_model_order_and_two_facts(_repo_data):
    current = _repo_data["paredoes"][-1]
    assert current["status"] == "em_andamento"
    history = build_paredao_history(_repo_data["raw_paredoes"], current["numero"])
    poll = get_poll_for_paredao(_repo_data["polls_data"], current["numero"])

    payload = build_paredao_card_payload(current, poll, _repo_data["polls_data"], history)

    assert payload["state"] == "active"
    assert payload["primary_source"] == "Nosso Modelo"
    assert payload["vote_mode"] == "eliminate"
    assert [n["name"] for n in payload["nominees"]] == ["Babu Santana", "Milena", "Chaiany"]
    assert payload["nominees"][0]["color_role"] == "danger"
    assert payload["nominees"][1]["color_role"] == "warning"
    assert payload["nominees"][2]["color_role"] == "safe"
    assert payload["trust_badge"]["visible"] is True
    assert "mais preciso" in payload["trust_badge"]["text"]
    assert "teste retrospectivo" in payload["trust_badge"]["text"]
    assert payload["trust_badge"]["href"] == "paredoes.html#nosso-modelo-back-test"
    assert len(payload["fact_lines"]) == 2
    assert any("Babu" in fact for fact in payload["fact_lines"])
    assert any("Milena" in fact for fact in payload["fact_lines"])


def test_active_payload_without_model_prediction_stays_neutral(_repo_data):
    current = _repo_data["paredoes"][-1]
    history = build_paredao_history(_repo_data["raw_paredoes"], current["numero"])

    payload = build_paredao_card_payload(current, None, {"paredoes": []}, history)

    assert payload["state"] == "active"
    assert payload["trust_badge"]["visible"] is False
    assert all(n.get("model_pct") is None for n in payload["nominees"])
    assert all(n["color_role"] == "neutral" for n in payload["nominees"])


def test_finalized_payload_uses_official_results_and_grayscale(_repo_data):
    finalized = next(p for p in reversed(_repo_data["paredoes"]) if p.get("status") == "finalizado" and not p.get("paredao_falso"))
    history = build_paredao_history(_repo_data["raw_paredoes"], finalized["numero"])
    poll = get_poll_for_paredao(_repo_data["polls_data"], finalized["numero"])

    payload = build_paredao_card_payload(finalized, poll, _repo_data["polls_data"], history)

    assert payload["state"] == "finalized"
    eliminated = next(n for n in payload["nominees"] if n["is_eliminated"])
    assert eliminated["name"] == "Maxiane"
    assert eliminated["display_pct"] == pytest.approx(63.21)
    assert eliminated["use_grayscale"] is True
    assert payload["memory_line"]
    assert "Nosso Modelo" in payload["memory_line"]


def test_live_and_index_renderers_share_the_new_card_language(_repo_data):
    current = _repo_data["paredoes"][-1]
    history = build_paredao_history(_repo_data["raw_paredoes"], current["numero"])
    poll = get_poll_for_paredao(_repo_data["polls_data"], current["numero"])
    payload = build_paredao_card_payload(current, poll, _repo_data["polls_data"], history)

    live_html = render_paredao_live_card(payload, _repo_data["avatars"])
    index_html = render_paredao_index_card(payload, _repo_data["avatars"])

    assert 'class="paredao-live-card' in live_html
    assert "Nosso Modelo" in live_html
    assert "Votalhada" in live_html
    assert 'href="paredoes.html#nosso-modelo-back-test"' in live_html
    assert "teste retrospectivo" in live_html
    assert 'class="paredao-index-card' in index_html
    assert "Babu" in index_html
    assert 'href="paredoes.html#nosso-modelo-back-test"' in index_html
    assert 'class="paredao-index-note' in index_html


def test_poll_comparison_payload_includes_confidence_and_delta(_repo_data):
    current = _repo_data["paredoes"][-1]
    poll = get_poll_for_paredao(_repo_data["polls_data"], current["numero"])
    precision = calculate_precision_weights(_repo_data["polls_data"])
    model_prediction = predict_precision_weighted(poll, precision)

    payload = build_poll_comparison_payload(poll, model_prediction)

    assert payload["agreement"] is True
    assert payload["vote_mode"] == "eliminate"
    assert payload["votalhada"]["name"] == "Babu Santana"
    assert payload["model"]["name"] == "Babu Santana"
    assert payload["model"]["pct"] == pytest.approx(model_prediction["prediction"]["Babu Santana"], abs=1e-6)
    assert payload["votalhada"]["pct"] == pytest.approx(poll["consolidado"]["Babu Santana"], abs=1e-6)
    assert payload["winner_delta_pp"] == pytest.approx(
        model_prediction["prediction"]["Babu Santana"] - poll["consolidado"]["Babu Santana"],
        abs=1e-6,
    )
    assert payload["model_top2_gap_pp"] > payload["votalhada_top2_gap_pp"]
    assert len(payload["rows"]) == len(poll.get("participantes", []))
    assert {row["name"] for row in payload["rows"]} == set(poll.get("participantes", []))


def test_poll_comparison_renderer_outputs_unified_compare_card(_repo_data):
    current = _repo_data["paredoes"][-1]
    poll = get_poll_for_paredao(_repo_data["polls_data"], current["numero"])
    precision = calculate_precision_weights(_repo_data["polls_data"])
    model_prediction = predict_precision_weighted(poll, precision)
    payload = build_poll_comparison_payload(poll, model_prediction)

    html = render_poll_comparison_card(payload, _repo_data["avatars"])

    assert 'class="poll-compare-card' in html
    assert "Concordam" in html
    assert "Confiança" in html
    assert "Diferença no líder" in html
    assert "Média por volume de votos" in html
    assert "ponderadas por histórico de acerto" in html
    assert "Babu" in html
