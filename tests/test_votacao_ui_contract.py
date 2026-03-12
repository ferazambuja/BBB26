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


def test_votacao_css_defines_scoped_components_for_all_evidence_modules():
    css = _read(VOTACAO_CSS)

    assert "body.votacao-page" in css
    assert ".votacao-section" in css
    assert ".votacao-compare-table" in css
    assert ".votacao-buffer-grid" in css
    assert ".votacao-health-grid" in css
    assert ".votacao-retro-cards" in css
    assert ".votacao-badge" in css
    assert ".votacao-status-chip" in css
    assert "@media (max-width: 575.98px)" in css
