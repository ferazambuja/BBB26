"""Contracts and regressions for the Votacao page overhaul."""

from __future__ import annotations

from pathlib import Path
import re
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
VOTACAO_QMD = REPO_ROOT / "votacao.qmd"
VOTACAO_CSS = REPO_ROOT / "assets" / "votacao.css"
sys.path.append(str((REPO_ROOT / "scripts").resolve()))

from votacao_viz import (  # type: ignore  # module created by this change
    build_retro_vote_summary,
    build_voting_health_summary,
    render_votacao_retro_section,
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.fixture()
def sample_paredoes() -> list[dict]:
    return [
        {
            "numero": 1,
            "paredao_falso": False,
            "participantes": [
                {
                    "nome": "Aline",
                    "voto_unico": 60.0,
                    "voto_torcida": 20.0,
                    "voto_total": 48.0,
                },
                {
                    "nome": "Milena",
                    "voto_unico": 30.0,
                    "voto_torcida": 70.0,
                    "voto_total": 42.0,
                },
                {
                    "nome": "Ana Paula",
                    "voto_unico": 10.0,
                    "voto_torcida": 10.0,
                    "voto_total": 10.0,
                },
            ],
        },
        {
            "numero": 2,
            "paredao_falso": True,
            "participantes": [
                {
                    "nome": "Jonas",
                    "voto_unico": 55.0,
                    "voto_torcida": 50.0,
                    "voto_total": 53.5,
                },
                {
                    "nome": "Babu",
                    "voto_unico": 30.0,
                    "voto_torcida": 40.0,
                    "voto_total": 33.0,
                },
                {
                    "nome": "Sol",
                    "voto_unico": 15.0,
                    "voto_torcida": 10.0,
                    "voto_total": 13.5,
                },
            ],
        },
    ]


def test_retro_vote_summary_keeps_winners_deltas_and_change_flags(sample_paredoes):
    summary = build_retro_vote_summary(sample_paredoes)

    assert summary["n_changed"] == 1
    assert summary["avg_delta"] == pytest.approx(4.5)
    assert len(summary["rows"]) == 2

    first = summary["rows"][0]
    assert first["paredao"] == 1
    assert first["winner_7030"]["nome"] == "Aline"
    assert first["winner_5050"]["nome"] == "Milena"
    assert first["mudou"] is True
    assert first["participants"][0]["delta"] == pytest.approx(8.0)

    second = summary["rows"][1]
    assert second["paredao"] == 2
    assert second["is_falso"] is True
    assert second["winner_7030"]["nome"] == "Jonas"
    assert second["winner_5050"]["nome"] == "Jonas"
    assert second["mudou"] is False


def test_voting_health_summary_keeps_danger_and_ranking_inversion(sample_paredoes):
    summary = build_voting_health_summary(sample_paredoes)

    assert summary["max_danger"] == pytest.approx(40.0)
    assert summary["max_danger_num"] == 1
    assert summary["max_flip_7030"] == pytest.approx(17.142857, rel=1e-6)
    assert summary["n_above_3"] == 2
    assert len(summary["rows"]) == 2

    first = summary["rows"][0]
    assert first["num"] == 1
    assert first["ranking_invertido"] is True
    assert first["povo_decidiu"] is True
    assert first["surv_nome"] == "Milena"
    assert first["elim_nome"] == "Aline"

    second = summary["rows"][1]
    assert second["num"] == 2
    assert second["is_falso"] is True
    assert second["ranking_invertido"] is False
    assert second["povo_decidiu"] is True


def test_retro_renderer_uses_semantic_classes_without_legacy_utilities(sample_paredoes):
    summary = build_retro_vote_summary(sample_paredoes)
    html = render_votacao_retro_section(summary)

    assert "votacao-retro" in html
    assert 'class="votacao-retro-cards votacao-mobile-only"' in html
    assert 'class="votacao-retro-table-wrap votacao-desktop-only"' in html
    assert 'class="votacao-compare-table votacao-retro-table"' in html
    assert "<caption>" in html
    assert 'scope="col"' in html
    assert 'votacao-badge votacao-badge--same' in html
    assert 'votacao-status-chip votacao-status-chip--elim' in html
    assert 'votacao-status-chip votacao-status-chip--saved' in html
    assert "u-s007" not in html
    assert "u-s009" not in html
    assert "u-s154" not in html
    assert "u-s155" not in html


def test_votacao_page_uses_scoped_css_and_helper_module():
    content = _read(VOTACAO_QMD)

    assert "body-classes: votacao-page" in content
    assert "assets/votacao.css" in content
    assert "from votacao_viz import (" in content
    assert "build_retro_vote_summary" in content
    assert "build_voting_health_summary" in content
    assert "render_votacao_retro_section" in content


def test_votacao_page_avoids_inline_page_style_and_legacy_utility_classes():
    content = _read(VOTACAO_QMD)

    assert "print('<style>')" not in content
    assert "print('</style>')" not in content
    assert not re.search(r"u-s\d{3}", content)


def test_votacao_page_centers_bbb26_safety_and_keeps_key_quote():
    content = _read(VOTACAO_QMD)

    assert (
        'subtitle: "BBB 26: o 70/30 protege o suficiente? O que os paredões já mostram"'
        in content
    )
    assert "## 🛡️ O 70/30 está protegendo o BBB 26?" in content
    assert "## 🩺 Onde o BBB 26 já mostra pressão" in content
    assert "o resultado final era uma média de <strong>50% Voto Único (CPF) e 50% Voto Torcida</strong>" in content
    assert "No BBB 26, a conta mudou para <strong>70% Voto Único (CPF) e 30% Voto Torcida</strong>" in content
    assert "essa diferença bastou para inverter o desfecho indicado pelo CPF e dar a vitória na média final" in content
    assert "Voto Torcida</strong>, que permite votos ilimitados" in content
    assert "quando a média entrega um vencedor diferente do apontado pelo CPF, o Voto Torcida deixa de ser complemento e passa a distorcer o resultado" in content
    assert "o outro lado ainda pode virar se abrir cerca de <strong>11,7 pontos</strong> no Voto Torcida" in content
    assert "o 70/30 reduz a distorção, mas ainda não impede que o Voto Torcida derrube o resultado indicado pelo CPF" in content
    assert "segue curto para impedir que uma minoria organizada imponha um resultado diferente daquele escolhido pelo CPF" in content
    assert '"Renata passa por cima do público e vira campeã do BBB 25"' in content
    assert "Pipoca Moderna" in content


def test_votacao_page_prefers_voto_torcida_and_uses_ilimitado_only_to_explain():
    content = _read(VOTACAO_QMD)

    assert "Voto Torcida" in content
    assert "Voto da Torcida" not in content
    assert content.count("votos ilimitados") == 1
    assert "voto ilimitado" not in content


def test_votacao_page_drops_old_inflammatory_copy_and_follower_proof():
    content = _read(VOTACAO_QMD)

    removed_phrases = [
        "não quer que você calcule",
        "A prova do astroturfing",
        "atores de má-fé",
        "É a marca da manipulação",
        "O buffer de 9 pontos: proteção real ou ilusão?",
        "sequestre o resultado",
        "quase 3x mais seguidores",
        "@faahlso",
        "torcida muito mobilizada",
        "metade da conta vinha do CPF e metade do voto ilimitado",
        "O retrato da final do BBB 25",
        "o CPF estava sinalizando",
        "deixa de ser detalhe e passa a interferir no desfecho",
        "o outro lado ainda pode encostar",
        "A pergunta mais útil agora não é se o 70/30 melhorou o sistema.",
        "Melhorou.",
        "pode ser pressionada",
        "alguns pontos já mudam o clima do paredão",
        "Isso mostra bem o papel do 70/30",
        "é um bom teste de estresse",
        "Isso é bom sinal para o presente",
        "já melhora bastante a proteção do CPF",
        "mas ainda deixa espaço",
        "Voto da Torcida",
        "o voto ilimitado deixa de ser complemento e passa a distorcer o resultado",
        "o voto ilimitado derrube o resultado indicado pelo CPF",
    ]

    for phrase in removed_phrases:
        assert phrase not in content

    assert "mas ainda não impede que o Voto Torcida derrube o resultado indicado pelo CPF" in content


def test_votacao_css_defines_scoped_components_for_all_evidence_modules():
    css = _read(VOTACAO_CSS)

    assert "body.votacao-page" in css
    assert ".votacao-section" in css
    assert ".votacao-card-grid--results" in css
    assert ".votacao-card--results" in css
    assert ".votacao-card-stat" in css
    assert ".votacao-compare-table" in css
    assert ".votacao-buffer-grid" in css
    assert ".votacao-health-grid" in css
    assert ".votacao-retro-cards" in css
    assert ".votacao-badge" in css
    assert ".votacao-status-chip" in css
    assert "@media (max-width: 575.98px)" in css


def test_bbb25_cards_use_compact_result_layout():
    content = _read(VOTACAO_QMD)

    assert 'print(\'<div class="votacao-card-grid votacao-card-grid--results">\')' in content
    assert 'print(f\'<div class="votacao-card votacao-card--results votacao-card--{tone}">\')' in content
    assert 'print(\'<div class="votacao-card-stat votacao-card-stat--vu">\')' in content
    assert 'print(\'<div class="votacao-card-stat votacao-card-stat--vt">\')' in content
    assert 'print(\'<div class="votacao-card-stat votacao-card-stat--avg">\')' in content


def test_bbb25_cards_define_outcome_tinted_result_styles():
    css = _read(VOTACAO_CSS)

    assert ".votacao-card--winner" in css
    assert ".votacao-card--runnerup" in css
    assert ".votacao-card--third" in css
    assert ".votacao-card-stat--vu" in css
    assert ".votacao-card-stat--vt" in css
    assert ".votacao-card-stat--avg" in css
    assert "box-shadow: inset 3px" not in css
    assert "border-radius: 10px;" not in css
