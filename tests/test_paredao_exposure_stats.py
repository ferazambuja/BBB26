"""Unit tests for paredão exposure stats computation (synthetic fixtures)."""
from __future__ import annotations

import pytest
from builders.paredao_exposure import compute_paredao_exposure_stats


# ── Helpers (duplicated from test_paredao_exposure_cards for isolation) ──


def _make_paredao(numero, indicados, *, status="finalizado", resultado=None,
                  paredao_falso=False, formacao=None):
    p = {"numero": numero, "status": status, "indicados_finais": indicados}
    if resultado:
        p["resultado"] = resultado
    if paredao_falso:
        p["paredao_falso"] = True
    if formacao:
        p["formacao"] = formacao
    return p


def _ind(nome, como="Líder"):
    return {"nome": nome, "como": como}


def _res(eliminado):
    return {"eliminado": eliminado, "votos": {}}


def _ctx(paredoes_list):
    return {"paredoes": {"paredoes": paredoes_list}, "active_set": set(), "manual_events": {}}


# ── First-timer ──────────────────────────────────────────────────────────


class TestFirstTimerMetric:

    def test_first_timers_counted(self):
        paredoes = [
            _make_paredao(1, [_ind("Ana"), _ind("Breno")], resultado=_res("Ana")),
            _make_paredao(2, [_ind("Breno"), _ind("Caio")], resultado=_res("Caio")),
            _make_paredao(3, [_ind("Breno"), _ind("Dani")], resultado=_res("Breno")),
        ]
        ft = compute_paredao_exposure_stats(_ctx(paredoes))["metrics"]["first_timer"]
        assert ft["n"] == 2 and ft["total"] == 3
        assert ft["rate"] == pytest.approx(2 / 3, abs=0.001)

    def test_repeater_not_counted(self):
        paredoes = [
            _make_paredao(1, [_ind("Ana"), _ind("Breno")], resultado=_res("Ana")),
            _make_paredao(2, [_ind("Breno"), _ind("Caio")], resultado=_res("Breno")),
        ]
        assert compute_paredao_exposure_stats(_ctx(paredoes))["metrics"]["first_timer"]["n"] == 1

    def test_fake_excluded(self):
        paredoes = [
            _make_paredao(1, [_ind("Ana")], resultado=_res("Ana")),
            _make_paredao(2, [_ind("Breno")], resultado=_res("Breno"), paredao_falso=True),
        ]
        stats = compute_paredao_exposure_stats(_ctx(paredoes))
        assert stats["metrics"]["first_timer"]["total"] == 1
        assert stats["facts"]["scope_sizes"]["real_only"] == 1
        assert stats["facts"]["scope_sizes"]["all_finalized"] == 2

    def test_zero_denominators(self):
        paredoes = [_make_paredao(1, [_ind("Ana")], status="em_andamento")]
        ft = compute_paredao_exposure_stats(_ctx(paredoes))["metrics"]["first_timer"]
        assert ft["rate"] is None and ft["total"] == 0


# ── Route metrics ────────────────────────────────────────────────────────


class TestRouteMetrics:

    def test_multi_sample_in_metrics(self):
        paredoes = [
            _make_paredao(1, [_ind("Ana", "Casa (3 votos)"), _ind("Breno", "Líder")],
                          resultado=_res("Ana")),
            _make_paredao(2, [_ind("Caio", "Casa (5 votos)"), _ind("Dani", "Líder")],
                          resultado=_res("Caio")),
        ]
        m = compute_paredao_exposure_stats(_ctx(paredoes))["metrics"]
        assert m["route_casa"]["total"] == 2 and m["route_casa"]["n"] == 2
        assert m["route_lider"]["total"] == 2 and m["route_lider"]["n"] == 0

    def test_single_sample_in_facts(self):
        paredoes = [
            _make_paredao(1, [_ind("Ana", "Big Fone (Ana)"), _ind("Breno", "Casa (3 votos)")],
                          resultado=_res("Ana")),
        ]
        stats = compute_paredao_exposure_stats(_ctx(paredoes))
        singles = [s["route"] for s in stats["facts"]["single_sample_routes"]]
        assert "Big Fone" in singles
        assert "route_big_fone" not in stats["metrics"]

    def test_single_sample_definition(self):
        """Route with total==1 across all real_only goes to facts, not metrics."""
        paredoes = [
            _make_paredao(1, [_ind("Ana", "Casa (3 votos)"), _ind("Breno", "Big Fone (Breno)")],
                          resultado=_res("Ana")),
            _make_paredao(2, [_ind("Caio", "Casa (5 votos)"), _ind("Dani", "Contragolpe")],
                          resultado=_res("Caio")),
        ]
        stats = compute_paredao_exposure_stats(_ctx(paredoes))
        assert "route_casa" in stats["metrics"]
        singles = [s["route"] for s in stats["facts"]["single_sample_routes"]]
        assert "Big Fone" in singles and "Contragolpe" in singles

    def test_unknown_route_in_facts(self):
        paredoes = [
            _make_paredao(1, [_ind("Ana", "Roleta Maluca (test)"), _ind("Breno", "Líder")],
                          resultado=_res("Ana")),
        ]
        assert "Roleta Maluca (test)" in \
            compute_paredao_exposure_stats(_ctx(paredoes))["facts"]["unknown_routes"]


# ── BV metrics ───────────────────────────────────────────────────────────


class TestBvMetrics:

    def test_bv_counts(self):
        paredoes = [
            _make_paredao(1, [_ind("Ana"), _ind("Breno"), _ind("Caio")],
                          resultado=_res("Breno"),
                          formacao={"bate_volta": {"participantes": ["Ana", "Breno", "Caio"],
                                                   "vencedor": "Ana"}}),
            _make_paredao(2, [_ind("Dani"), _ind("Eva")], resultado=_res("Eva")),
        ]
        stats = compute_paredao_exposure_stats(_ctx(paredoes))
        m = stats["metrics"]
        assert m["bv_presence_by_paredao"]["n"] == 1 and m["bv_presence_by_paredao"]["total"] == 2
        assert m["bv_winners_escaped"]["n"] == 1
        assert m["bv_losers_eliminated"]["n"] == 1 and m["bv_losers_survived"]["n"] == 1
        assert "bv_total_participants" not in m
        assert stats["facts"]["bv_total_participants"] == 3


# ── Scopes + schema ─────────────────────────────────────────────────────


class TestScopesAndSchema:

    def test_em_andamento_in_with_indicados(self):
        paredoes = [
            _make_paredao(1, [_ind("Ana")], resultado=_res("Ana")),
            _make_paredao(2, [_ind("Breno")], status="em_andamento"),
        ]
        sizes = compute_paredao_exposure_stats(_ctx(paredoes))["facts"]["scope_sizes"]
        assert sizes["with_indicados"] == 2 and sizes["real_only"] == 1

    def test_metric_schema(self):
        paredoes = [
            _make_paredao(1, [_ind("Ana"), _ind("Breno")], resultado=_res("Ana"),
                          formacao={"bate_volta": {"participantes": ["Ana", "Breno"],
                                                   "vencedor": "Breno"}}),
        ]
        required = {"rate", "n", "total", "scope"}
        valid_scopes = {"real_only", "all_finalized", "with_indicados"}
        for key, metric in compute_paredao_exposure_stats(_ctx(paredoes))["metrics"].items():
            assert set(metric.keys()) == required, f"{key}"
            assert isinstance(metric["n"], int) and isinstance(metric["total"], int)
            assert metric["scope"] in valid_scopes
