from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RENDER_RESIDUE = [
    "cartola.html",
    "economia.html",
    "evolucao.html",
    "paredao.html",
    "votacao.html",
    "site_libs",
    "_site",
]


@pytest.fixture(scope="module")
def rendered_index_html(tmp_path_factory: pytest.TempPathFactory) -> str:
    output_dir = tmp_path_factory.mktemp("index-render-contract")
    shutil.rmtree(REPO_ROOT / ".quarto" / "project-cache", ignore_errors=True)
    for name in RENDER_RESIDUE:
        path = REPO_ROOT / name
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.exists():
            path.unlink()
    subprocess.run(
        ["quarto", "render", "index.qmd", "--output-dir", str(output_dir)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return (output_dir / "index.html").read_text(encoding="utf-8")


def test_rendered_index_uses_scoped_table_wrappers_without_inline_style_blocks(rendered_index_html: str):
    html = rendered_index_html

    assert 'class="index-cross-table scroll-x"' in html
    assert 'class="index-reaction-summary"' in html
    assert "<style>\n.cross-table {" not in html
    assert "<style>\n.summary-table {" not in html


def test_rendered_index_reaction_summary_has_instance_scoped_toggle_markup(rendered_index_html: str):
    html = rendered_index_html

    assert html.count('id="reaction-summary-table"') == 0
    assert "closest('.index-reaction-summary')" in html
    assert "querySelectorAll('.index-reaction-summary__row--collapsed')" in html
