from pathlib import Path

from fetch_votalhada_images import (
    REPO_ROOT,
    _display_path,
    _find_duplicate_capture,
    _format_platform_audit_lines,
)


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


def test_format_platform_audit_lines_includes_anomaly_details():
    report = {
        "summary": {
            "total_platform_cards": 4,
            "ok": 3,
            "anomaly": 1,
            "inconclusive": 0,
            "high_confidence": 4,
        },
        "cards": [
            {
                "image": "data/votalhada/2026_03_08/consolidados_2_2026-03-09_18-06-00.png",
                "platform": "youtube",
                "status": "anomaly",
                "rows_count": 24,
                "declared_media": {"sum": 100.37},
                "declared_vs_unweighted_delta": {"max": 0.37},
            }
        ],
    }
    lines = _format_platform_audit_lines(report)
    joined = "\n".join(lines)
    assert "Platform consistency audit: 4 cards" in joined
    assert "anomaly 1" in joined
    assert "youtube" in joined
    assert "sum=100.37" in joined
    assert "max_delta=0.37" in joined
