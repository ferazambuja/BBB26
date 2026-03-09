"""Regression checks for the week-8 spotlight on paredoes.qmd."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PAREDOES_QMD = REPO_ROOT / "paredoes.qmd"
PAREDAO_QMD = REPO_ROOT / "paredao.qmd"
PAREDAO_VIZ = REPO_ROOT / "scripts" / "paredao_viz.py"
CARDS_CSS = REPO_ROOT / "assets" / "cards.css"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_paredoes_has_milena_spotlight_render_hook():
    content = _read(PAREDOES_QMD)
    helper = _read(PAREDAO_VIZ)
    assert 'featured_story = _pa_entry.get("featured_story")' in content
    assert "render_featured_story" in content
    assert 'class="paredao-spotlight"' in helper
    assert "Voto Único" in helper
    assert "Motivo salvo" not in helper
    assert "Queridômetro no domingo da formação" in helper
    assert "🔒 Queridômetro secreto" in helper
    assert "Quando o poder caiu na mão deles" in helper
    assert "🎯 Ataques diretos e Sincerão" in helper
    assert "↩️ Respostas da Milena" in helper
    assert "private_signal_note" in helper
    assert 'story.get("caveat"' in helper
    assert "Agora:" not in helper


def test_paredao_live_page_has_milena_spotlight_render_hook():
    content = _read(PAREDAO_QMD)
    assert 'featured_story = pa_entry.get("featured_story")' in content
    assert "render_featured_story" in content


def test_paredoes_spotlight_has_mobile_first_styles():
    css = _read(CARDS_CSS)
    assert ".paredao-spotlight" in css
    assert ".paredao-spotlight-grid" in css
    assert "@media (max-width: 768px)" in css


def test_paredoes_tabs_include_current_open_week():
    content = _read(PAREDOES_QMD)
    assert "paredoes_visiveis = [p for p in paredoes if p.get('status') in ('finalizado', 'em_andamento')]" in content
    assert "for i, paredao in enumerate(reversed(paredoes_visiveis))" in content
