"""Tests for Mais Blindados card: resolve_leaders, BV counting, vote counting, nomination classification."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from data_utils import resolve_leaders
from builders.index_data_builder import _compute_static_cards
from builders.vote_prediction import extract_paredao_eligibility


# ── resolve_leaders() ────────────────────────────────────────────────────────

class TestResolveLeaders:
    def test_single(self):
        assert resolve_leaders({"lider": "A"}) == ["A"]

    def test_dual(self):
        assert resolve_leaders({"lider": "A + B", "lideres": ["A", "B"]}) == ["A", "B"]

    def test_none(self):
        assert resolve_leaders({}) == []

    def test_lideres_takes_precedence(self):
        assert resolve_leaders({"lider": "X", "lideres": ["A", "B"]}) == ["A", "B"]

    def test_empty_lideres_falls_back(self):
        assert resolve_leaders({"lider": "A", "lideres": []}) == ["A"]

    def test_null_lideres_falls_back(self):
        assert resolve_leaders({"lider": "A", "lideres": None}) == ["A"]

    def test_no_lider_no_lideres(self):
        assert resolve_leaders({"anjo": "X"}) == []


# ── extract_paredao_eligibility() dual leadership ────────────────────────────

class TestExtractEligibilityDualLeaders:
    def test_both_in_cant_be_voted(self):
        entry = {
            "formacao": {"lider": "A + B", "lideres": ["A", "B"]},
            "indicados_finais": [],
        }
        result = extract_paredao_eligibility(entry)
        assert "A" in result["cant_be_voted"]
        assert "B" in result["cant_be_voted"]
        assert "A + B" not in result["cant_be_voted"]

    def test_both_in_cant_vote(self):
        entry = {
            "formacao": {"lider": "A + B", "lideres": ["A", "B"]},
            "indicados_finais": [],
        }
        result = extract_paredao_eligibility(entry)
        assert "A" in result["cant_vote"]
        assert "B" in result["cant_vote"]

    def test_lider_names_in_result(self):
        entry = {
            "formacao": {"lider": "A + B", "lideres": ["A", "B"]},
            "indicados_finais": [],
        }
        result = extract_paredao_eligibility(entry)
        assert result["lider_names"] == ["A", "B"]

    def test_single_leader_compat(self):
        entry = {
            "formacao": {"lider": "Jonas"},
            "indicados_finais": [],
        }
        result = extract_paredao_eligibility(entry)
        assert "Jonas" in result["cant_be_voted"]
        assert result["lider_names"] == ["Jonas"]
        assert result["lider"] == "Jonas"


class TestExtractEligibilityPreVoteDynamics:
    def test_consenso_anjo_monstro_target_in_cant_be_voted(self):
        entry = {
            "formacao": {
                "lider": "L",
                "consenso_anjo_monstro": {"target": "Babu"},
            },
            "indicados_finais": [{"nome": "Babu", "como": "Consenso Anjo+Monstro"}],
        }
        result = extract_paredao_eligibility(entry)
        assert "Babu" in result["cant_be_voted"]
        assert result["ineligible_reasons"]["Babu"] == "Consenso Anjo+Monstro"

    def test_duelo_de_risco_emparedado_in_cant_be_voted(self):
        entry = {
            "formacao": {
                "lider": "L",
                "duelo_de_risco": {"emparedado": "Chaiany"},
            },
            "indicados_finais": [{"nome": "Chaiany", "como": "Duelo de Risco"}],
        }
        result = extract_paredao_eligibility(entry)
        assert "Chaiany" in result["cant_be_voted"]
        assert result["ineligible_reasons"]["Chaiany"] == "Duelo de Risco"

    def test_exilado_indicado_in_cant_be_voted(self):
        entry = {
            "formacao": {
                "lider": "L",
                "exilado": {"indicado": "Alberto Cowboy"},
            },
            "indicados_finais": [{"nome": "Alberto Cowboy", "como": "Exilado"}],
        }
        result = extract_paredao_eligibility(entry)
        assert "Alberto Cowboy" in result["cant_be_voted"]
        assert result["ineligible_reasons"]["Alberto Cowboy"] == "Exilado"

    def test_fallback_bloco_do_paredao_from_como(self):
        entry = {
            "formacao": {"lider": "L"},
            "indicados_finais": [{"nome": "Solange Couto", "como": "Bloco do Paredão (sem consenso)"}],
        }
        result = extract_paredao_eligibility(entry)
        assert "Solange Couto" in result["cant_be_voted"]
        assert result["ineligible_reasons"]["Solange Couto"] == "Bloco do Paredão"

    def test_house_vote_nominee_remains_votable(self):
        entry = {
            "formacao": {"lider": "L"},
            "indicados_finais": [{"nome": "Leandro", "como": "Casa (10 votos)"}],
        }
        result = extract_paredao_eligibility(entry)
        assert "Leandro" not in result["cant_be_voted"]

    def test_mais_votada_nominee_remains_votable(self):
        entry = {
            "formacao": {"lider": "L"},
            "indicados_finais": [{"nome": "Samira", "como": "Mais votada pela casa (3 votos)"}],
        }
        result = extract_paredao_eligibility(entry)
        assert "Samira" not in result["cant_be_voted"]

    def test_contragolpe_quem_variant_in_cant_be_voted(self):
        entry = {
            "formacao": {
                "lider": "L",
                "contragolpe": {"por": "Chaiany", "quem": "Maxiane"},
            },
            "indicados_finais": [{"nome": "Maxiane", "como": "Contragolpe (indicada por Chaiany)"}],
        }
        result = extract_paredao_eligibility(entry)
        assert "Maxiane" in result["cant_be_voted"]
        assert result["ineligible_reasons"]["Maxiane"] == "Contragolpe"


# ── BV escape counting ──────────────────────────────────────────────────────

def _make_paredao(num, lider, indicados, bv_vencedor=None, bv_vencedores=None, votos_casa=None):
    """Build a synthetic paredão entry for testing."""
    bv = {}
    if bv_vencedor:
        bv["vencedor"] = bv_vencedor
    if bv_vencedores:
        bv["vencedores"] = bv_vencedores
    return {
        "numero": num,
        "formacao": {"lider": lider, "bate_volta": bv if bv else None},
        "indicados_finais": [{"nome": n, "como": "test"} for n in indicados],
        "votos_casa": votos_casa or {},
    }


class TestBvEscapeCounting:
    """Test BV escape detection logic extracted from _compute_static_cards."""

    def _count_bv_escapes(self, paredoes):
        """Replicate the BV counting logic from _compute_static_cards."""
        bv_escape_count: Counter = Counter()
        for par in paredoes:
            form = par.get("formacao", {})
            indicados = {(ind["nome"] if isinstance(ind, dict) else ind)
                         for ind in par.get("indicados_finais", [])}
            bv = form.get("bate_volta", {}) or {}
            bv_winners = bv.get("vencedores") or ([bv["vencedor"]] if bv.get("vencedor") else [])
            for bw in bv_winners:
                if bw and bw not in indicados:
                    bv_escape_count[bw] += 1
        return bv_escape_count

    def test_single_winner_escaped(self):
        paredoes = [_make_paredao(1, "L", ["X", "Y"], bv_vencedor="Z")]
        counts = self._count_bv_escapes(paredoes)
        assert counts["Z"] == 1

    def test_single_winner_still_in_indicados(self):
        """Winner appears in indicados_finais (lost BV) — not an escape."""
        paredoes = [_make_paredao(1, "L", ["X", "Z"], bv_vencedor="Z")]
        counts = self._count_bv_escapes(paredoes)
        assert counts.get("Z", 0) == 0

    def test_multiple_winners_p5_pattern(self):
        """P5 pattern: 3 BV winners escape via vencedores array."""
        paredoes = [_make_paredao(5, "Jonas", ["Milena", "Leandro"],
                                  bv_vencedores=["Jordana", "Alberto", "Breno"])]
        counts = self._count_bv_escapes(paredoes)
        assert counts["Jordana"] == 1
        assert counts["Alberto"] == 1
        assert counts["Breno"] == 1

    def test_cumulative_across_paredoes(self):
        """Alberto escapes BV in two separate paredões."""
        paredoes = [
            _make_paredao(5, "Jonas", ["Milena"], bv_vencedores=["Alberto"]),
            _make_paredao(6, "Jonas", ["Samira"], bv_vencedor="Alberto"),
        ]
        counts = self._count_bv_escapes(paredoes)
        assert counts["Alberto"] == 2

    def test_no_bv(self):
        paredoes = [_make_paredao(2, "Babu", ["X", "Y"])]
        counts = self._count_bv_escapes(paredoes)
        assert len(counts) == 0


# ── Vote counting (Bug 3) ───────────────────────────────────────────────────

class TestVotesCounting:
    """Test that ALL house votes are counted regardless of participant status."""

    def _count_all_votes(self, paredoes, active_set):
        """Replicate the all-votes pre-pass from _compute_static_cards."""
        all_house_votes: Counter = Counter()
        last_voted_paredao: dict = {}
        for par in paredoes:
            num = par.get("numero", 0)
            for _voter, target in (par.get("votos_casa") or {}).items():
                t = target.strip()
                if t in active_set:
                    all_house_votes[t] += 1
                    last_voted_paredao[t] = max(last_voted_paredao.get(t, 0), num)
        return all_house_votes, last_voted_paredao

    def test_votes_counted_on_paredao(self):
        """Leandro P3 pattern: in indicados_finais AND receives votes → both counted."""
        paredoes = [_make_paredao(3, "Maxiane",
                                  ["Leandro", "X"],
                                  votos_casa={"A": "Leandro", "B": "Leandro", "C": "X"})]
        votes, last = self._count_all_votes(paredoes, {"Leandro", "X", "A", "B", "C", "Maxiane"})
        assert votes["Leandro"] == 2
        assert votes["X"] == 1
        assert last["Leandro"] == 3

    def test_votes_counted_when_available(self):
        paredoes = [_make_paredao(1, "L", ["X"],
                                  votos_casa={"A": "Y", "B": "Y"})]
        votes, _ = self._count_all_votes(paredoes, {"X", "Y", "A", "B", "L"})
        assert votes["Y"] == 2

    def test_unknown_target_skipped(self):
        """Targets not in active_set are silently skipped."""
        paredoes = [_make_paredao(1, "L", [],
                                  votos_casa={"A": "Unknown Person"})]
        votes, _ = self._count_all_votes(paredoes, {"A", "L"})
        assert votes.get("Unknown Person", 0) == 0

    def test_last_voted_paredao_tracks_max(self):
        paredoes = [
            _make_paredao(1, "L", [], votos_casa={"A": "X"}),
            _make_paredao(3, "L", [], votos_casa={"B": "X"}),
        ]
        _, last = self._count_all_votes(paredoes, {"X", "A", "B", "L"})
        assert last["X"] == 3


# ── Nomination classification ────────────────────────────────────────────────

class TestNominationClassification:
    def _classify(self, paredoes, active_set):
        """Replicate nomination classification from _compute_static_cards."""
        by_lider: Counter = Counter()
        by_casa: Counter = Counter()
        by_dynamic: Counter = Counter()
        for par in paredoes:
            for ind in par.get("indicados_finais", []):
                nome = ind.get("nome", "") if isinstance(ind, dict) else ind
                como = (ind.get("como", "") if isinstance(ind, dict) else "").lower()
                if not nome or nome not in active_set:
                    continue
                if "líder" in como:
                    by_lider[nome] += 1
                elif "casa" in como or "mais votad" in como:
                    by_casa[nome] += 1
                else:
                    by_dynamic[nome] += 1
        return by_lider, by_casa, by_dynamic

    def test_lider_nomination(self):
        paredoes = [{"indicados_finais": [{"nome": "X", "como": "Líder"}], "votos_casa": {}}]
        by_l, by_c, by_d = self._classify(paredoes, {"X"})
        assert by_l["X"] == 1
        assert by_c.get("X", 0) == 0

    def test_lider_with_parenthetical(self):
        paredoes = [{"indicados_finais": [{"nome": "X", "como": "Líder (indicada por Jonas)"}], "votos_casa": {}}]
        by_l, _, _ = self._classify(paredoes, {"X"})
        assert by_l["X"] == 1

    def test_casa_nomination(self):
        paredoes = [{"indicados_finais": [{"nome": "X", "como": "Casa (6 votos)"}], "votos_casa": {}}]
        _, by_c, _ = self._classify(paredoes, {"X"})
        assert by_c["X"] == 1

    def test_mais_votado(self):
        paredoes = [{"indicados_finais": [{"nome": "X", "como": "Mais votado pela casa"}], "votos_casa": {}}]
        _, by_c, _ = self._classify(paredoes, {"X"})
        assert by_c["X"] == 1

    def test_dynamic_nomination(self):
        paredoes = [{"indicados_finais": [{"nome": "X", "como": "Contragolpe (Y)"}], "votos_casa": {}}]
        _, _, by_d = self._classify(paredoes, {"X"})
        assert by_d["X"] == 1


# ── Contract test (uses real data if available) ──────────────────────────────

class TestBlindadosContract:
    """Contract tests verifying the blindados card in index_data.json."""

    @pytest.fixture
    def blindados_card(self):
        path = Path(__file__).resolve().parents[1] / "data" / "derived" / "index_data.json"
        if not path.exists():
            pytest.skip("index_data.json not built yet")
        with open(path) as f:
            data = json.load(f)
        cards = {c["type"]: c for c in data.get("highlights", {}).get("cards", [])}
        card = cards.get("blindados")
        if not card:
            pytest.skip("blindados card not present")
        return card

    def test_fields_present(self, blindados_card):
        required = {"name", "paredao", "bv_escapes", "exposure", "protected",
                     "available", "votes_total", "votes_available", "by_lider",
                     "by_casa", "by_dynamic", "nom_text", "prot_text", "bv_text",
                     "last_voted_paredao", "total", "votes", "bv_escape"}
        for item in blindados_card["items_all"]:
            missing = required - set(item.keys())
            assert not missing, f"{item['name']} missing fields: {missing}"

    def test_exposure_invariant(self, blindados_card):
        for item in blindados_card["items_all"]:
            assert item["exposure"] == item["paredao"] + item["bv_escapes"], \
                f"{item['name']}: exposure should be paredao + bv_escapes"

    def test_votes_total_ge_votes_available(self, blindados_card):
        for item in blindados_card["items_all"]:
            assert item["votes_total"] >= item["votes_available"], \
                f"{item['name']}: votes_total should be >= votes_available"

    def test_sort_order_deterministic(self, blindados_card):
        items = blindados_card["items_all"]
        for i in range(len(items) - 1):
            a, b = items[i], items[i + 1]
            key_a = (a["exposure"], -a["protected"], a["votes_total"], a["name"])
            key_b = (b["exposure"], -b["protected"], b["votes_total"], b["name"])
            assert key_a <= key_b, f"Sort violation: {a['name']} should come before {b['name']}"

    def test_backward_compat_fields(self, blindados_card):
        for item in blindados_card["items_all"]:
            assert "votes" in item
            assert "bv_escape" in item
            assert item["votes"] == item["votes_total"]
            assert item["bv_escape"] == (item["bv_escapes"] > 0)


class TestExtractEligibilityRealCases:
    def test_real_paredoes_dynamic_and_house_vote_cases(self):
        path = Path(__file__).resolve().parents[1] / "data" / "paredoes.json"
        if not path.exists():
            pytest.skip("paredoes.json not available")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        by_num = {p.get("numero"): p for p in data.get("paredoes", [])}

        p3 = extract_paredao_eligibility(by_num[3])
        p5 = extract_paredao_eligibility(by_num[5])
        p6 = extract_paredao_eligibility(by_num[6])
        p7 = extract_paredao_eligibility(by_num[7])
        p8 = extract_paredao_eligibility(by_num[8])

        # Pre-vote dynamic nominees should be excluded from house target pool.
        assert "Solange Couto" in p5["cant_be_voted"]   # Bloco do Paredão
        assert "Chaiany" in p6["cant_be_voted"]         # Duelo de Risco
        assert "Maxiane" in p6["cant_be_voted"]         # Contragolpe (quem)
        assert "Alberto Cowboy" in p7["cant_be_voted"]  # Exilado
        assert "Babu Santana" in p8["cant_be_voted"]    # Consenso Anjo+Monstro

        # House-vote nominees remain part of eligible target pool pre-vote.
        assert "Samira" not in p5["cant_be_voted"]      # Mais votada pela casa
        assert "Leandro" not in p3["cant_be_voted"]     # Casa (10 votos)


class TestStaticCardsEligibilityAccounting:
    def test_available_matches_pre_vote_eligibility(self):
        root = Path(__file__).resolve().parents[1]
        paredoes_path = root / "data" / "paredoes.json"
        latest_path = root / "data" / "latest.json"
        if not paredoes_path.exists() or not latest_path.exists():
            pytest.skip("required data files not available")

        with open(paredoes_path, encoding="utf-8") as f:
            paredoes = json.load(f).get("paredoes", [])
        with open(latest_path, encoding="utf-8") as f:
            latest = json.load(f)
        participants = latest.get("participants", latest if isinstance(latest, list) else [])
        active_set = {
            p.get("name")
            for p in participants
            if p.get("name") and not p.get("characteristics", {}).get("eliminated")
        }
        if not active_set:
            pytest.skip("no active participants in latest.json")

        _highlights, cards = _compute_static_cards({"active_set": active_set, "paredoes": {"paredoes": paredoes}})
        blindados = next(card for card in cards if card.get("type") == "blindados")
        items = {item["name"]: item for item in blindados.get("items_all", [])}

        expected_available: dict[str, int] = {name: 0 for name in active_set}
        for par in paredoes:
            if not par.get("votos_casa"):
                continue
            elig = extract_paredao_eligibility(par)
            cant_be_voted = elig.get("cant_be_voted", set())
            for name in active_set:
                if name not in cant_be_voted:
                    expected_available[name] += 1

        for name in active_set:
            if name not in items:
                continue
            assert items[name]["available"] == expected_available[name], (
                f"{name}: available={items[name]['available']} expected={expected_available[name]}"
            )


class TestBlindadosDisplayDetails:
    def test_builder_emits_split_protection_tags_and_autoimune_label(self):
        ctx = {
            "active_set": {"Jonas", "Milena", "Breno", "Ana"},
            "paredoes": {
                "paredoes": [
                    {
                        "numero": 3,
                        "formacao": {"lider": "Ana", "bate_volta": {"vencedor": "Jonas"}},
                        "indicados_finais": [{"nome": "Milena", "como": "Casa"}],
                        "votos_casa": {"Breno": "Milena"},
                    },
                    {
                        "numero": 4,
                        "formacao": {"lider": "Jonas"},
                        "indicados_finais": [{"nome": "Milena", "como": "Casa"}],
                        "votos_casa": {"Ana": "Milena"},
                    },
                    {
                        "numero": 5,
                        "formacao": {"lider": "Ana", "imunizado": {"quem": "Jonas"}},
                        "indicados_finais": [{"nome": "Milena", "como": "Casa"}],
                        "votos_casa": {"Breno": "Milena"},
                    },
                    {
                        "numero": 6,
                        "formacao": {"lider": "Ana", "anjo": "Jonas", "anjo_autoimune": True},
                        "indicados_finais": [{"nome": "Milena", "como": "Casa"}],
                        "votos_casa": {"Breno": "Milena"},
                    },
                ]
            },
        }

        _highlights, cards = _compute_static_cards(ctx)
        blindados = next(card for card in cards if card["type"] == "blindados")
        jonas = next(item for item in blindados["items_all"] if item["name"] == "Jonas")

        assert jonas["bv_text"] == "Escapou Bate-Volta 1x (3º)"
        assert "🚄" not in jonas["bv_text"]
        assert jonas["prot_text"] == "Autoimune 1x, Líder 1x, Imune 1x"
        assert jonas["protection_tags"] == [
            {"label": "Autoimune", "count": 1, "nums": [6], "text": "Autoimune 1x (6º)"},
            {"label": "Líder", "count": 1, "nums": [4], "text": "Líder 1x (4º)"},
            {"label": "Imune", "count": 1, "nums": [5], "text": "Imune 1x (5º)"},
        ]
