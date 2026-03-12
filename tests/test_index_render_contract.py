from __future__ import annotations

from functools import cache
from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[1]


@cache
def _rendered_index_html() -> str:
    subprocess.run(
        ["quarto", "render", "index.qmd"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return (REPO_ROOT / "_site" / "index.html").read_text(encoding="utf-8")


def test_rendered_index_uses_scoped_table_wrappers_without_inline_style_blocks():
    html = _rendered_index_html()

    assert 'class="index-cross-table scroll-x"' in html
    assert 'class="index-reaction-summary"' in html
    assert "<style>\n.cross-table {" not in html
    assert "<style>\n.summary-table {" not in html


def test_rendered_index_reaction_summary_has_instance_scoped_toggle_markup():
    html = _rendered_index_html()

    assert html.count('id="reaction-summary-table"') == 0
    assert "closest('.index-reaction-summary')" in html
    assert "querySelectorAll('.index-reaction-summary__row--collapsed')" in html
