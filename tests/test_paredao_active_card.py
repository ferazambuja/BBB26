"""Tests for the shared active/finalized paredao card payload and renderers."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from builders.index_data_builder import build_index_data
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


def _latest_entry_as_active(repo_data: dict) -> dict:
    # Find the latest finalized paredão (to simulate it as active with full data)
    finalized = [p for p in repo_data["paredoes"] if p.get("status") == "finalizado"]
    current = copy.deepcopy(finalized[-1])
    current["status"] = "em_andamento"
    current.pop("resultado", None)
    for participant in current.get("participantes", []):
        participant.pop("resultado", None)
        participant.pop("voto_unico", None)
        participant.pop("voto_torcida", None)
        participant.pop("voto_total", None)
    return current


def test_active_payload_uses_model_order_and_two_facts(_repo_data):
    current = _latest_entry_as_active(_repo_data)
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
    assert "acertou todos os paredões" in payload["trust_badge"]["text"]
    assert "Votalhada errou 1" in payload["trust_badge"]["text"]
    assert payload["trust_badge"]["href"] == "paredoes.html#nosso-modelo-back-test"
    assert len(payload["fact_lines"]) == 2
    assert any("Babu" in fact for fact in payload["fact_lines"])
    assert any("Milena" in fact for fact in payload["fact_lines"])
    assert payload["curiosity_line"]
    if "encerramento da votação atingido" not in payload["curiosity_line"].lower():
        assert "%" in payload["curiosity_line"] or "p.p." in payload["curiosity_line"] or "pontos percentuais" in payload["curiosity_line"].lower()
    assert "janela" not in payload["curiosity_line"].lower()
    assert payload.get("curiosity_chips")
    if "encerramento da votação atingido" in payload["curiosity_line"].lower():
        assert any("Diferença no fechamento" in str(c.get("label", "")) for c in payload["curiosity_chips"])
        assert any("Ritmo final" in str(c.get("label", "")) for c in payload["curiosity_chips"])
    else:
        assert any("Ritmo atual" in str(c.get("label", "")) for c in payload["curiosity_chips"])
        assert any("Ritmo necessário" in str(c.get("label", "")) for c in payload["curiosity_chips"])
    assert any("p.p./h" in str(c.get("value", "")) for c in payload["curiosity_chips"])


def test_curiosity_after_close_freezes_projection(_repo_data):
    current = _latest_entry_as_active(_repo_data)
    history = build_paredao_history(_repo_data["raw_paredoes"], current["numero"])
    poll = get_poll_for_paredao(_repo_data["polls_data"], current["numero"])
    closed_poll = copy.deepcopy(poll)
    closed_poll["fechamento_votacao"] = "2000-01-01T22:45:00-03:00"

    payload = build_paredao_card_payload(current, closed_poll, _repo_data["polls_data"], history)

    assert payload["curiosity_line"]
    assert "encerramento da votação atingido" in payload["curiosity_line"].lower()
    assert payload.get("curiosity_chips")
    assert any("Diferença no fechamento" in str(c.get("label", "")) for c in payload["curiosity_chips"])


def test_curiosity_after_close_freezes_even_without_positive_momentum(_repo_data):
    current = _latest_entry_as_active(_repo_data)
    history = build_paredao_history(_repo_data["raw_paredoes"], current["numero"])
    poll = get_poll_for_paredao(_repo_data["polls_data"], current["numero"])
    closed_poll = copy.deepcopy(poll)
    closed_poll["fechamento_votacao"] = "2000-01-01T22:45:00-03:00"
    serie = closed_poll.get("serie_temporal", [])
    assert len(serie) >= 3

    participants = closed_poll.get("participantes", [])
    consolidado = closed_poll.get("consolidado", {})
    ranked = sorted(
        [(name, float(consolidado.get(name, 0) or 0)) for name in participants],
        key=lambda x: (-x[1], x[0]),
    )
    assert len(ranked) >= 2
    lead = ranked[0][0]
    runner = ranked[1][0]
    # Force near-zero momentum so the close-state text is not gated by "closing > 0.25".
    serie[-1][lead] = serie[-3][lead]
    serie[-1][runner] = serie[-3][runner]

    payload = build_paredao_card_payload(current, closed_poll, _repo_data["polls_data"], history)

    assert payload["curiosity_line"]
    assert "encerramento da votação atingido" in payload["curiosity_line"].lower()
    assert payload.get("curiosity_chips")
    assert any("Diferença no fechamento" in str(c.get("label", "")) for c in payload["curiosity_chips"])


def test_active_payload_without_model_prediction_stays_neutral(_repo_data):
    current = _latest_entry_as_active(_repo_data)
    history = build_paredao_history(_repo_data["raw_paredoes"], current["numero"])

    payload = build_paredao_card_payload(current, None, {"paredoes": []}, history)

    assert payload["state"] == "active"
    assert payload["trust_badge"]["visible"] is False
    assert all(n.get("model_pct") is None for n in payload["nominees"])
    assert all(n["color_role"] == "neutral" for n in payload["nominees"])
    assert payload["curiosity_line"] is None


def test_finalized_payload_uses_official_results_and_grayscale(_repo_data):
    finalized = next(p for p in reversed(_repo_data["paredoes"]) if p.get("status") == "finalizado" and not p.get("paredao_falso"))
    history = build_paredao_history(_repo_data["raw_paredoes"], finalized["numero"])
    poll = get_poll_for_paredao(_repo_data["polls_data"], finalized["numero"])

    payload = build_paredao_card_payload(finalized, poll, _repo_data["polls_data"], history)

    assert payload["state"] == "finalized"
    eliminated = next(n for n in payload["nominees"] if n["is_eliminated"])
    assert eliminated["name"] == "Babu Santana"
    assert eliminated["display_pct"] == pytest.approx(68.62)
    assert eliminated["use_grayscale"] is True
    assert payload["memory_line"]
    assert "Nosso Modelo" in payload["memory_line"]


def test_build_index_data_paredao_card_reflects_current_state():
    data = build_index_data()

    card = next(card for card in data["highlights"]["cards"] if card["type"] == "paredao")

    # Card state depends on whether the latest paredão is active or finalized
    if card["payload"]["state"] == "active":
        assert card["title"] == "Paredão Ativo"
    else:
        assert card["payload"]["state"] == "finalized"
        assert card["title"] == "Último Paredão"


def test_live_and_index_renderers_share_the_new_card_language(_repo_data):
    current = _latest_entry_as_active(_repo_data)
    history = build_paredao_history(_repo_data["raw_paredoes"], current["numero"])
    poll = get_poll_for_paredao(_repo_data["polls_data"], current["numero"])
    payload = build_paredao_card_payload(current, poll, _repo_data["polls_data"], history)

    live_html = render_paredao_live_card(payload, _repo_data["avatars"])
    index_html = render_paredao_index_card(payload, _repo_data["avatars"])

    assert 'class="paredao-live-card' in live_html
    assert "Nosso Modelo" in live_html
    assert "Votalhada" in live_html
    assert 'href="paredoes.html#nosso-modelo-back-test"' in live_html
    assert "acertou todos os paredões" in live_html
    assert 'class="paredao-card-curiosity"' in live_html
    assert 'class="paredao-curiosity-chips' in live_html
    assert "p.p./h = pontos percentuais por hora" in live_html
    assert 'class="paredao-index-card' in index_html
    assert "Babu" in index_html
    assert 'href="paredoes.html#nosso-modelo-back-test"' in index_html
    assert 'class="paredao-index-note' in index_html
    assert 'class="paredao-index-curiosity"' in index_html
    assert 'class="paredao-curiosity-chips' in index_html
    assert "p.p./h = pontos percentuais por hora" in index_html


def test_repeat_nominees_render_top_right_appearance_badges(_repo_data):
    current = _latest_entry_as_active(_repo_data)
    history = build_paredao_history(_repo_data["raw_paredoes"], current["numero"])
    poll = get_poll_for_paredao(_repo_data["polls_data"], current["numero"])
    payload = build_paredao_card_payload(current, poll, _repo_data["polls_data"], history)

    expected_badges = sum(1 for n in payload["nominees"] if n.get("appearance_count", 1) > 1)
    assert expected_badges > 0

    live_html = render_paredao_live_card(payload, _repo_data["avatars"])
    index_html = render_paredao_index_card(payload, _repo_data["avatars"])

    assert live_html.count("paredao-card-appearance-badge") == expected_badges
    assert index_html.count("paredao-card-appearance-badge") == expected_badges
    assert ">1x<" not in live_html
    assert ">1x<" not in index_html


def test_poll_comparison_payload_includes_confidence_and_delta(_repo_data):
    current = next(p for p in reversed(_repo_data["paredoes"]) if p.get("status") == "finalizado" and not p.get("paredao_falso"))
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
    current = next(p for p in reversed(_repo_data["paredoes"]) if p.get("status") == "finalizado" and not p.get("paredao_falso"))
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
    assert 'href="paredoes.html#precisão-das-enquetes-votalhada"' in html
    assert "Babu" in html
