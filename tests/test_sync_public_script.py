from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "sync_public.sh"


def _run(
    cmd: list[str],
    cwd: Path,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=check,
        text=True,
        capture_output=True,
        env=env,
    )


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return _run(["git", *args], cwd=repo, check=check)


def _write(repo: Path, rel: str, content: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "test")

    _write(repo, "README.md", "base\n")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "base")

    # Normalize to "main", independent from local git init default.
    default_branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if default_branch != "main":
        _git(repo, "branch", "-m", default_branch, "main")

    _git(repo, "remote", "add", "origin", ".")
    _git(repo, "checkout", "-b", "local/private-main")
    return repo


def _path_without_rg(path: str) -> str:
    rg_name = "rg.exe" if os.name == "nt" else "rg"
    entries = []
    for entry in path.split(os.pathsep):
        if not entry:
            continue
        if (Path(entry) / rg_name).exists():
            continue
        entries.append(entry)
    return os.pathsep.join(entries)


def test_sync_public_default_mode_generates_report(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)

    _write(repo, "public.txt", "v1\n")
    _git(repo, "add", "public.txt")
    _git(repo, "commit", "-m", "public: add public marker")
    _git(repo, "checkout", "main")

    report = tmp_path / "report.md"
    result = _run(
        [
            str(SCRIPT),
            "--source",
            "local/private-main",
            "--target",
            "main",
            "--remote",
            "origin",
            "--report",
            str(report),
        ],
        cwd=repo,
        check=True,
    )

    assert report.exists(), result.stdout + result.stderr
    content = report.read_text(encoding="utf-8")
    assert "safe_to_proceed: yes" in content


def test_sync_public_report_mode_works_without_rg_in_path(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)

    _write(repo, "public.txt", "v1\n")
    _git(repo, "add", "public.txt")
    _git(repo, "commit", "-m", "public: add public marker")
    _git(repo, "checkout", "main")

    report = tmp_path / "report_no_rg.md"
    env = dict(os.environ)
    env["PATH"] = _path_without_rg(env.get("PATH", ""))
    bash_bin = shutil.which("bash")
    assert bash_bin is not None

    result = _run(
        [
            bash_bin,
            str(SCRIPT),
            "--source",
            "local/private-main",
            "--target",
            "main",
            "--remote",
            "origin",
            "--report",
            str(report),
        ],
        cwd=repo,
        check=True,
        env=env,
    )

    assert report.exists(), result.stdout + result.stderr
    content = report.read_text(encoding="utf-8")
    assert "safe_to_proceed: yes" in content


def test_sync_public_report_flags_manual_critical_conflicts(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)

    _write(repo, "data/manual_events.json", '{"version": "source"}\n')
    _git(repo, "add", "data/manual_events.json")
    _git(repo, "commit", "-m", "public: update manual events from source")

    _git(repo, "checkout", "main")
    _write(repo, "data/manual_events.json", '{"version": "target"}\n')
    _git(repo, "add", "data/manual_events.json")
    _git(repo, "commit", "-m", "public: update manual events on target")

    report = tmp_path / "conflict_report.md"
    _run(
        [
            str(SCRIPT),
            "--source",
            "local/private-main",
            "--target",
            "main",
            "--remote",
            "origin",
            "--report",
            str(report),
        ],
        cwd=repo,
        check=True,
    )

    content = report.read_text(encoding="utf-8")
    assert "manual-critical" in content
    assert "safe_to_proceed: no" in content


def test_sync_public_apply_requires_report_path(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)

    _write(repo, "public.txt", "v1\n")
    _git(repo, "add", "public.txt")
    _git(repo, "commit", "-m", "public: add public marker")
    _git(repo, "checkout", "main")

    result = _run(
        [
            str(SCRIPT),
            "--apply",
            "--source",
            "local/private-main",
            "--target",
            "main",
            "--remote",
            "origin",
        ],
        cwd=repo,
        check=False,
    )

    assert result.returncode != 0
    assert "--report" in (result.stdout + result.stderr)
