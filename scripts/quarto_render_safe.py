#!/usr/bin/env python3
"""Serialize Quarto renders within a project to avoid cache/output races."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


def _parse_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description="Run `quarto render` under a project-wide lock.",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help="Optional QMD/document targets. Omit to render the whole project.",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Explicit Quarto project root. Defaults to nearest parent with _quarto.yml.",
    )
    parser.add_argument(
        "--quarto-bin",
        default="quarto",
        help="Quarto executable to invoke (default: quarto).",
    )
    return parser.parse_known_args(argv)


def _find_project_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "_quarto.yml").exists():
            return candidate
    raise FileNotFoundError(f"Could not find _quarto.yml above {start}")


class _RenderLock:
    def __init__(self, path: Path):
        self.path = path
        self.handle = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+", encoding="utf-8")
        self.handle.seek(0)
        self.handle.truncate()
        self.handle.write(f"pid={os.getpid()}\n")
        self.handle.flush()

        if os.name == "nt":  # pragma: no cover - CI/dev env is POSIX today
            import msvcrt

            msvcrt.locking(self.handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, tb):
        assert self.handle is not None
        try:
            if os.name == "nt":  # pragma: no cover - CI/dev env is POSIX today
                import msvcrt

                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()


def _run_one(quarto_bin: str, project_root: Path, target: str | None, extra_args: list[str]) -> int:
    cmd = [quarto_bin, "render"]
    if target:
        cmd.append(target)
    cmd.extend(extra_args)
    proc = subprocess.run(cmd, cwd=project_root)
    return int(proc.returncode)


def main(argv: list[str] | None = None) -> int:
    args, extra_args = _parse_args(argv or sys.argv[1:])
    cwd = Path.cwd().resolve()
    project_root = (args.project_root or _find_project_root(cwd)).resolve()
    lock = _RenderLock(project_root / ".quarto" / "render.lock")

    with lock:
        targets = args.targets or [None]
        for target in targets:
            code = _run_one(args.quarto_bin, project_root, target, extra_args)
            if code != 0:
                return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
