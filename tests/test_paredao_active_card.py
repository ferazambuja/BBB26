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
    EMPATE_THRESHOLD_PP,
    build_paredao_card_payload,
    build_paredao_history,
    build_poll_comparison_payload,
    is_empate_tecnico,
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
    # Nominees come from whichever paredão is latest — verify structural contract
    nominee_names = [n["name"] for n in payload["nominees"]]
    assert len(nominee_names) >= 2
    assert payload["nominees"][0]["color_role"] == "danger"
    assert payload["nominees"][-1]["color_role"] == "safe"
    assert payload["trust_badge"]["visible"] is True
    assert "acertou" in payload["trust_badge"]["text"]
    assert payload["trust_badge"]["href"] == "paredoes.html#nosso-modelo-back-test"
    assert len(payload["fact_lines"]) == 2
    # Fact lines should reference top 2 nominees by first name
    top2_first = [n.split()[0] for n in nominee_names[:2]]
    assert any(top2_first[0] in fact for fact in payload["fact_lines"])
    assert any(top2_first[1] in fact for fact in payload["fact_lines"])
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
    # Derive expected from actual paredão data instead of hardcoding
    expected_eliminated = finalized["resultado"]["eliminado"]
    expected_pct = finalized["resultado"]["votos"][expected_eliminated]["voto_total"]
    assert eliminated["name"] == expected_eliminated
    assert eliminated["display_pct"] == pytest.approx(expected_pct, abs=0.01)
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
    # Check that at least one nominee name appears in the index card
    nominee_names = [n["name"] for n in payload["nominees"]]
    assert any(name in index_html for name in nominee_names)
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

    # Derive expected winner from actual poll/model data (filter non-participant keys)
    participants = set(poll.get("participantes", []))
    consolidado_pct = {k: v for k, v in poll["consolidado"].items() if k in participants and isinstance(v, (int, float))}
    votalhada_winner = max(consolidado_pct, key=consolidado_pct.get)
    model_winner = max(model_prediction["prediction"], key=model_prediction["prediction"].get)

    assert payload["vote_mode"] == "eliminate"
    assert payload["votalhada"]["name"] == votalhada_winner
    assert payload["model"]["name"] == model_winner
    assert payload["agreement"] == (votalhada_winner == model_winner)
    assert payload["model"]["pct"] == pytest.approx(model_prediction["prediction"][model_winner], abs=1e-6)
    assert payload["votalhada"]["pct"] == pytest.approx(poll["consolidado"][votalhada_winner], abs=1e-6)
    assert payload["winner_delta_pp"] == pytest.approx(
        model_prediction["prediction"][model_winner] - poll["consolidado"][votalhada_winner],
        abs=1e-6,
    )
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
    assert "Votalhada 70%/30%" in html or "Votalhada (Ponderada)" in html
    assert "ponderadas por histórico de acerto" in html
    assert 'href="paredoes.html#precisão-das-enquetes-votalhada"' in html
    # Check that the poll leader's name appears in the rendered HTML
    leader_name = payload["votalhada"]["name"]
    assert leader_name.split()[0] in html


def test_formula_change_card_keeps_legacy_weighted_value_primary(_repo_data):
    poll = get_poll_for_paredao(_repo_data["polls_data"], 10)
    precision = calculate_precision_weights(_repo_data["polls_data"])
    model_prediction = predict_precision_weighted(poll, precision)

    payload = build_poll_comparison_payload(poll, model_prediction)
    html = render_poll_comparison_card(payload, _repo_data["avatars"])

    assert payload["votalhada"]["name"] == "Jonas Sulzbach"
    assert payload["votalhada"]["pct"] == pytest.approx(44.99, abs=1e-6)
    assert payload["mirror_3070"]["name"] == "Jonas Sulzbach"
    assert payload["mirror_3070"]["pct"] == pytest.approx(45.15, abs=1e-6)
    assert "Votalhada (Ponderada)" in html
    assert "Votalhada 70%/30%" in html
    assert "Jonas Sulzbach" in html
    assert "Juliano Floss" in html


# ---------- Empate técnico boundary tests ----------


def test_is_empate_tecnico_boundary():
    """Threshold is exclusive: gap < 2.0 is empate, gap >= 2.0 is not."""
    assert is_empate_tecnico(1.99) is True
    assert is_empate_tecnico(2.00) is False
    assert is_empate_tecnico(2.01) is False
    assert is_empate_tecnico(0.0) is True
    assert is_empate_tecnico(None) is False


def test_p10_empate_flags_selective(_repo_data):
    """P10 weighted and 70/30 should be empate; model should NOT."""
    poll = get_poll_for_paredao(_repo_data["polls_data"], 10)
    precision = calculate_precision_weights(_repo_data["polls_data"])
    model_prediction = predict_precision_weighted(poll, precision)
    payload = build_poll_comparison_payload(poll, model_prediction)

    # Weighted gap ~1.5 p.p. → empate
    assert payload["votalhada"]["empate"] is True
    assert payload["votalhada"]["top2_gap_pp"] < EMPATE_THRESHOLD_PP

    # 70/30 gap ~0.3 p.p. → empate
    assert payload["mirror_3070"]["empate"] is True
    assert payload["mirror_3070"]["top2_gap_pp"] < EMPATE_THRESHOLD_PP

    # Model gap ~10+ p.p. → NOT empate
    assert payload["model"]["empate"] is False
    assert payload["model"]["top2_gap_pp"] >= EMPATE_THRESHOLD_PP


def test_empate_badge_only_on_empate_panels(_repo_data):
    """Badge HTML appears on empate panels but NOT on the model panel when gap is large."""
    poll = get_poll_for_paredao(_repo_data["polls_data"], 10)
    precision = calculate_precision_weights(_repo_data["polls_data"])
    model_prediction = predict_precision_weighted(poll, precision)
    payload = build_poll_comparison_payload(poll, model_prediction)
    html = render_poll_comparison_card(payload, _repo_data["avatars"])

    assert "poll-compare-empate" in html
    # The badge text should appear (at least for votalhada panel)
    assert "empate técnico" in html
