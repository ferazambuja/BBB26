from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import shutil
import subprocess

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    shutil.which("quarto") is None,
    reason="quarto not installed — render contract tests require quarto CLI",
)
RENDER_RESIDUE = [
    ".quarto/project-cache",
    "cartola.html",
    "economia.html",
    "evolucao.html",
    "paredao.html",
    "votacao.html",
    "site_libs",
    "_site",
]


@contextmanager
def _preserve_generated_paths(root: Path, names: list[str]):
    """Rename render residue aside (same filesystem = instant), restore after."""
    backup_root = root / ".test-backup"
    backup_root.mkdir(exist_ok=True)
    preserved: list[str] = []
    for name in names:
        path = root / name
        if not path.exists():
            continue
        backup_path = backup_root / name
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        path.rename(backup_path)
        preserved.append(name)
    try:
        yield
    finally:
        for name in names:
            path = root / name
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            elif path.exists():
                path.unlink()
        for name in preserved:
            backup_path = backup_root / name
            restore_path = root / name
            if restore_path.exists():
                if restore_path.is_dir():
                    shutil.rmtree(restore_path, ignore_errors=True)
                else:
                    restore_path.unlink()
            backup_path.rename(restore_path)
        shutil.rmtree(backup_root, ignore_errors=True)


@pytest.fixture(scope="module")
def rendered_index_html(tmp_path_factory: pytest.TempPathFactory) -> str:
    output_dir = tmp_path_factory.mktemp("index-render-contract")
    with _preserve_generated_paths(REPO_ROOT, RENDER_RESIDUE):
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


def test_rendered_index_does_not_emit_literal_fence_paragraphs(rendered_index_html: str):
    html = rendered_index_html

    assert "<p>:::</p>" not in html
