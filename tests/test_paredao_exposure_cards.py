"""Unit tests for paredão exposure card payloads (synthetic fixtures)."""
from __future__ import annotations

import pytest
from collections import Counter

from builders.paredao_exposure import (
    build_nunca_paredao_items,
    build_figurinha_repetida_items,
)
from builders.index_data_builder import _build_figurinha_stat_line


# ── Shared test helpers ──────────────────────────────────────────────────


def _make_paredao(
    numero: int,
    indicados: list[dict],
    *,
    status: str = "finalizado",
    votos_casa: dict | None = None,
    resultado: dict | None = None,
    paredao_falso: bool = False,
    formacao: dict | None = None,
) -> dict:
    p: dict = {"numero": numero, "status": status, "indicados_finais": indicados}
    if votos_casa is not None:
        p["votos_casa"] = votos_casa
    if resultado:
        p["resultado"] = resultado
    if paredao_falso:
        p["paredao_falso"] = True
    if formacao:
        p["formacao"] = formacao
    return p


def _make_indicado(nome: str, como: str = "Líder") -> dict:
    return {"nome": nome, "como": como}


def _make_resultado(eliminado: str, votos: dict | None = None) -> dict:
    return {"eliminado": eliminado, "votos": votos or {}}


def _synthetic_ctx(paredoes_list: list[dict], active_set: set[str] | None = None,
                   manual_events: dict | None = None) -> dict:
    if active_set is None:
        active_set = {"Ana", "Breno", "Caio"}
    return {
        "paredoes": {"paredoes": paredoes_list},
        "active_set": active_set,
        "manual_events": manual_events or {},
    }


# ── Nunca Paredão ────────────────────────────────────────────────────────


class TestNuncaParedaoItems:

    def test_active_untouchables(self):
        paredoes = [_make_paredao(1, [_make_indicado("Ana")],
                                  votos_casa={"V1": "Breno", "V2": "Caio"})]
        items, _ = build_nunca_paredao_items(
            _synthetic_ctx(paredoes), paredoes,
            Counter({"Breno": 1, "Caio": 1}), Counter({"Breno": 1, "Caio": 1}),
        )
        names = [i["name"] for i in items]
        assert "Breno" in names and "Caio" in names
        assert "Ana" not in names

    def test_sort_order(self):
        paredoes = [_make_paredao(1, [_make_indicado("Ana")], votos_casa={"V1": "Breno"})]
        items, _ = build_nunca_paredao_items(
            _synthetic_ctx(paredoes), paredoes,
            Counter({"Caio": 3, "Breno": 1}), Counter({"Caio": 5, "Breno": 2}),
        )
        assert items[0]["name"] == "Caio"
        assert items[1]["name"] == "Breno"

    def test_exited_non_eliminados(self):
        paredoes = [_make_paredao(1, [_make_indicado("Ana")])]
        manual = {"participants": {
            "Henri": {"status": "desistente", "exit_date": "2026-01-15"},
            "Pedro": {"status": "desistente", "exit_date": "2026-01-19"},
            "Ana": {"status": "eliminada", "exit_date": "2026-01-21"},
        }}
        _, exited = build_nunca_paredao_items(
            _synthetic_ctx(paredoes, manual_events=manual), paredoes, Counter(), Counter(),
        )
        names = [i["name"] for i in exited]
        assert "Henri" in names and "Pedro" in names
        assert "Ana" not in names

    def test_exited_nominees_excluded(self):
        paredoes = [_make_paredao(1, [_make_indicado("Sol")])]
        manual = {"participants": {"Sol": {"status": "desclassificado", "exit_date": "2026-02-11"}}}
        _, exited = build_nunca_paredao_items(
            _synthetic_ctx(paredoes, manual_events=manual), paredoes, Counter(), Counter(),
        )
        assert not any(i["name"] == "Sol" for i in exited)

    def test_empty_when_all_went(self):
        paredoes = [_make_paredao(1, [_make_indicado("Ana"), _make_indicado("Breno"),
                                      _make_indicado("Caio")])]
        items, _ = build_nunca_paredao_items(_synthetic_ctx(paredoes), paredoes, Counter(), Counter())
        assert items == []

    def test_minimal_ctx_no_manual_events(self):
        paredoes = [_make_paredao(1, [_make_indicado("Ana")])]
        ctx = {"active_set": {"Breno", "Caio"}, "paredoes": {"paredoes": paredoes}}
        items, exited = build_nunca_paredao_items(ctx, paredoes, Counter(), Counter())
        assert len(items) == 2
        assert exited == []

    def test_n_paredoes_scope(self):
        paredoes = [_make_paredao(1, [_make_indicado("Ana")]), _make_paredao(2, [])]
        items, _ = build_nunca_paredao_items(_synthetic_ctx(paredoes), paredoes, Counter(), Counter())
        assert items[0]["n_paredoes"] == 1
        assert items[0]["n_paredoes_scope"] == "with_indicados"


# ── Exited Vote Stats (bugfix) ───────────────────────────────────────────


class TestExitedVoteStats:
    """Tests for _compute_exited_vote_stats via _build_exited_untouchables."""

    def test_exited_votes_from_paredoes(self):
        """Exited target in votos_casa → votes_total > 0."""
        paredoes = [_make_paredao(
            1, [_make_indicado("Ana")],
            votos_casa={"V1": "Henri", "V2": "Henri", "V3": "Ana"},
            formacao={"lider": "Zé", "indicado_lider": "Ana"},
        )]
        paredoes[0]["data_formacao"] = "2026-01-16"
        manual = {"participants": {
            "Henri": {"status": "desistente", "exit_date": "2026-01-20"},
        }}
        ctx = _synthetic_ctx(paredoes, manual_events=manual)
        ctx["participants_index"] = {
            "participants": [{"name": "Henri", "first_seen": "2026-01-13", "last_seen": "2026-01-19"}],
        }
        _, exited = build_nunca_paredao_items(ctx, paredoes, Counter(), Counter())
        henri = next(i for i in exited if i["name"] == "Henri")
        assert henri["votes_total"] == 2

    def test_exited_eligibility_gated_by_exit_date(self):
        """Present for P1 but gone before P2 → available=1."""
        paredoes = [
            _make_paredao(1, [_make_indicado("Ana")],
                          votos_casa={"V1": "Ana"},
                          formacao={"lider": "Zé", "indicado_lider": "Ana"}),
            _make_paredao(2, [_make_indicado("Breno")],
                          votos_casa={"V1": "Breno"},
                          formacao={"lider": "Zé", "indicado_lider": "Breno"}),
        ]
        paredoes[0]["data_formacao"] = "2026-01-18"
        paredoes[1]["data_formacao"] = "2026-01-25"
        manual = {"participants": {
            "Pedro": {"status": "desistente", "exit_date": "2026-01-19"},
        }}
        ctx = _synthetic_ctx(paredoes, manual_events=manual)
        ctx["participants_index"] = {
            "participants": [{"name": "Pedro", "first_seen": "2026-01-13", "last_seen": "2026-01-18"}],
        }
        _, exited = build_nunca_paredao_items(ctx, paredoes, Counter(), Counter())
        pedro = next(i for i in exited if i["name"] == "Pedro")
        assert pedro["available"] == 1

    def test_exited_protected_counted(self):
        """Imunizado → protected == 1."""
        paredoes = [_make_paredao(
            1, [_make_indicado("Ana")],
            votos_casa={"V1": "Ana"},
            formacao={
                "lider": "Zé", "indicado_lider": "Ana",
                "imunizado": {"por": "Anjo", "quem": "Edi"},
            },
        )]
        paredoes[0]["data_formacao"] = "2026-01-18"
        manual = {"participants": {
            "Edi": {"status": "desclassificado", "exit_date": "2026-02-14"},
        }}
        ctx = _synthetic_ctx(paredoes, manual_events=manual)
        ctx["participants_index"] = {
            "participants": [{"name": "Edi", "first_seen": "2026-01-13", "last_seen": "2026-02-13"}],
        }
        _, exited = build_nunca_paredao_items(ctx, paredoes, Counter(), Counter())
        edi = next(i for i in exited if i["name"] == "Edi")
        assert edi["protected"] == 1

    def test_exited_only_card_emitted(self):
        """items=[] but items_exited non-empty → card should be emittable."""
        paredoes = [_make_paredao(
            1, [_make_indicado("Ana"), _make_indicado("Breno"), _make_indicado("Caio")],
            votos_casa={"V1": "Ana"},
            formacao={"lider": "Zé", "indicado_lider": "Ana"},
        )]
        paredoes[0]["data_formacao"] = "2026-01-18"
        manual = {"participants": {
            "Henri": {"status": "desistente", "exit_date": "2026-01-15"},
        }}
        ctx = _synthetic_ctx(paredoes, manual_events=manual)
        ctx["participants_index"] = {
            "participants": [{"name": "Henri", "first_seen": "2026-01-13", "last_seen": "2026-01-14"}],
        }
        items, exited = build_nunca_paredao_items(ctx, paredoes, Counter(), Counter())
        assert items == []
        assert len(exited) == 1
        # Emission gate: card should emit when items is empty but exited is not
        assert items or exited  # mimics the fixed gate


# ── Figurinha Repetida ───────────────────────────────────────────────────


class TestFigurinhaRepetidaItems:

    def test_ranked_by_count(self):
        paredoes = [
            _make_paredao(1, [_make_indicado("Ana"), _make_indicado("Breno")]),
            _make_paredao(2, [_make_indicado("Ana"), _make_indicado("Breno")]),
            _make_paredao(3, [_make_indicado("Ana"), _make_indicado("Caio")]),
        ]
        items = build_figurinha_repetida_items(_synthetic_ctx(paredoes), paredoes)
        assert items[0]["name"] == "Ana" and items[0]["appearance_count"] == 3
        assert items[1]["name"] == "Breno" and items[1]["appearance_count"] == 2

    def test_route_summary(self):
        paredoes = [
            _make_paredao(1, [_make_indicado("Ana", "Líder")]),
            _make_paredao(2, [_make_indicado("Ana", "Líder (indicada por X)")]),
            _make_paredao(3, [_make_indicado("Ana", "Casa (3 votos)")]),
        ]
        ana = build_figurinha_repetida_items(_synthetic_ctx(paredoes), paredoes)[0]
        assert ana["route_summary"]["Líder"] == 2
        assert ana["route_summary"]["Casa"] == 1

    def test_fake_paredao_flagged(self):
        paredoes = [_make_paredao(1, [_make_indicado("Ana")], paredao_falso=True,
                                  resultado=_make_resultado("Ana"))]
        ana = build_figurinha_repetida_items(_synthetic_ctx(paredoes), paredoes)[0]
        assert ana["fake_paredao_count"] == 1
        assert ana["fake_paredao_nums"] == [1]
        assert ana["history"][0]["falso"] is True

    def test_returned_via_later_appearance(self):
        paredoes = [
            _make_paredao(1, [_make_indicado("Ana")], paredao_falso=True,
                          resultado=_make_resultado("Ana")),
            _make_paredao(2, [_make_indicado("Ana")]),
        ]
        ana = build_figurinha_repetida_items(_synthetic_ctx(paredoes), paredoes)[0]
        assert ana["returned"] is True
        assert ana["history"][0]["resultado"] == "quarto_secreto"

    def test_returned_via_active_set(self):
        paredoes = [_make_paredao(1, [_make_indicado("Ana")], paredao_falso=True,
                                  resultado=_make_resultado("Ana"))]
        ana = build_figurinha_repetida_items(
            _synthetic_ctx(paredoes, active_set={"Ana", "Breno", "Caio"}), paredoes)[0]
        assert ana["returned"] is True

    def test_returned_via_last_seen(self):
        paredoes = [_make_paredao(1, [_make_indicado("Ana")], paredao_falso=True,
                                  resultado=_make_resultado("Ana"))]
        paredoes[0]["data"] = "2026-03-03"
        ctx = _synthetic_ctx(paredoes, active_set=set())
        ctx["participants_index"] = {"participants": [{"name": "Ana", "last_seen": "2026-03-07"}]}
        assert build_figurinha_repetida_items(ctx, paredoes)[0]["returned"] is True

    def test_not_returned_when_last_seen_before(self):
        paredoes = [_make_paredao(1, [_make_indicado("Ana")], paredao_falso=True,
                                  resultado=_make_resultado("Ana"))]
        paredoes[0]["data"] = "2026-03-03"
        ctx = _synthetic_ctx(paredoes, active_set=set())
        ctx["participants_index"] = {"participants": [{"name": "Ana", "last_seen": "2026-03-01"}]}
        assert build_figurinha_repetida_items(ctx, paredoes)[0]["returned"] is False

    def test_eliminated_grayscale(self):
        paredoes = [_make_paredao(1, [_make_indicado("Ana"), _make_indicado("Breno")],
                                  resultado=_make_resultado("Ana"))]
        items = build_figurinha_repetida_items(
            _synthetic_ctx(paredoes, active_set={"Breno", "Caio"}), paredoes)
        ana = next(i for i in items if i["name"] == "Ana")
        assert ana["use_grayscale"] is True and ana["active"] is False
        breno = next(i for i in items if i["name"] == "Breno")
        assert breno["use_grayscale"] is False and breno["active"] is True

    def test_sort_tiebreaker(self):
        paredoes = [_make_paredao(1, [_make_indicado("Breno"), _make_indicado("Ana")])]
        items = build_figurinha_repetida_items(_synthetic_ctx(paredoes), paredoes)
        assert items[0]["name"] == "Ana"  # name ASC
        assert items[1]["name"] == "Breno"


# ── Stat line helper ─────────────────────────────────────────────────────


class TestStatLine:

    def test_with_both_metrics(self):
        stats = {"metrics": {
            "first_timer": {"rate": 0.7143, "n": 5, "total": 7, "scope": "real_only"},
            "bv_losers_eliminated": {"rate": 0.4, "n": 4, "total": 10, "scope": "real_only"},
        }}
        line = _build_figurinha_stat_line(stats)
        assert "71%" in line and "40%" in line

    def test_with_zero_denominator(self):
        stats = {"metrics": {
            "first_timer": {"rate": None, "n": 0, "total": 0, "scope": "real_only"},
            "bv_losers_eliminated": {"rate": None, "n": 0, "total": 0, "scope": "real_only"},
        }}
        assert _build_figurinha_stat_line(stats) == ""
