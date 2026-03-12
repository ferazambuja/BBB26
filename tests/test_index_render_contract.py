from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def rendered_index_html() -> str:
    output_dir = REPO_ROOT / "tmp" / "pytest-index-render-contract"
    output_dir_arg = Path("tmp/pytest-index-render-contract")
    output_dir.mkdir(parents=True, exist_ok=True)
    (REPO_ROOT / "index_files" / "execute-results").mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["quarto", "render", "index.qmd", "--output-dir", str(output_dir_arg)],
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
