from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import textwrap

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "quarto_render_safe.py"

pytestmark = pytest.mark.skipif(
    shutil.which("quarto") is None,
    reason="quarto not installed — render locking tests require quarto CLI",
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")


def _init_minimal_project(tmp_path: Path) -> Path:
    project = tmp_path / "quarto-race"
    project.mkdir()

    _write(
        project / "_quarto.yml",
        """
        project:
          type: website
          output-dir: _site
          resources:
            - data/derived/*.json
          render:
            - index.qmd
            - other.qmd
        """,
    )
    _write(
        project / "index.qmd",
        """
        ---
        title: Repro Index
        ---

        # Repro Index
        """,
    )
    _write(
        project / "other.qmd",
        """
        ---
        title: Repro Other
        ---

        # Repro Other
        """,
    )
    _write(
        project / "data" / "derived" / "repro.json",
        """
        {"ok": true}
        """,
    )
    return project


def test_safe_quarto_wrapper_serializes_concurrent_project_renders(tmp_path: Path) -> None:
    project = _init_minimal_project(tmp_path)

    proc1 = subprocess.Popen(
        [sys.executable, str(SCRIPT), "index.qmd"],
        cwd=project,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    proc2 = subprocess.Popen(
        [sys.executable, str(SCRIPT), "other.qmd"],
        cwd=project,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    out1, err1 = proc1.communicate(timeout=60)
    out2, err2 = proc2.communicate(timeout=60)

    assert proc1.returncode == 0, out1 + err1
    assert proc2.returncode == 0, out2 + err2
    assert (project / "_site" / "index.html").exists()
    assert (project / "_site" / "other.html").exists()
    assert (project / "_site" / "data" / "derived" / "repro.json").exists()
