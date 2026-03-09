from pathlib import Path

from fetch_votalhada_images import REPO_ROOT, _display_path, _find_duplicate_capture


def test_display_path_inside_repo_is_relative():
    path = REPO_ROOT / "tmp" / "sample.png"
    shown = _display_path(path)
    assert shown == "tmp/sample.png"


def test_display_path_accepts_relative_input():
    path = Path("tmp/sample.png")
    shown = _display_path(path)
    assert shown == "tmp/sample.png"


def test_find_duplicate_capture_by_size_and_hash(tmp_path):
    out_dir = tmp_path / "votalhada"
    out_dir.mkdir()

    existing = out_dir / "consolidados_2026-03-09_12-00-00.png"
    incoming = out_dir / "consolidados_2026-03-09_13-00-00.png"
    existing.write_bytes(b"same-bytes")
    incoming.write_bytes(b"same-bytes")

    dup = _find_duplicate_capture(out_dir, "consolidados", incoming, mode="size+sha256")
    assert dup == existing


def test_find_duplicate_capture_ignores_other_slots(tmp_path):
    out_dir = tmp_path / "votalhada"
    out_dir.mkdir()

    # Should not collide with consolidados base.
    other = out_dir / "consolidados_2_2026-03-09_12-00-00.png"
    incoming = out_dir / "consolidados_2026-03-09_13-00-00.png"
    other.write_bytes(b"same-bytes")
    incoming.write_bytes(b"same-bytes")

    dup = _find_duplicate_capture(out_dir, "consolidados", incoming, mode="size+sha256")
    assert dup is None
