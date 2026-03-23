from pathlib import Path

from fetch_votalhada_images import (
    REPO_ROOT,
    extract_image_urls,
    _display_path,
    _find_duplicate_capture,
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


def test_extract_image_urls_prefers_data_original_over_src():
    html = """
    <div>
      <img
        src="https://blogger.googleusercontent.com/img/b/x/placeholder/000.jpg"
        data-original="https://blogger.googleusercontent.com/img/b/x/real/2026-03-17_194618.png"
      />
    </div>
    """
    urls = extract_image_urls(html)
    assert urls == ["https://blogger.googleusercontent.com/img/b/x/real/2026-03-17_194618.png"]


def test_extract_image_urls_falls_back_to_data_src():
    html = """
    <div>
      <img
        src="https://blogger.googleusercontent.com/img/b/x/placeholder/000.jpg"
        data-src="https://blogger.googleusercontent.com/img/b/x/real/2026-03-17_194643.png"
      />
    </div>
    """
    urls = extract_image_urls(html)
    assert urls == ["https://blogger.googleusercontent.com/img/b/x/real/2026-03-17_194643.png"]


def test_extract_image_urls_uses_srcset_first_candidate():
    html = """
    <div>
      <img
        src="https://example.com/ignore.png"
        srcset="
          https://blogger.googleusercontent.com/img/b/x/real/2026-03-17_194999.png 1x,
          https://blogger.googleusercontent.com/img/b/x/real/2026-03-17_195000.png 2x
        "
      />
    </div>
    """
    urls = extract_image_urls(html)
    assert urls == ["https://blogger.googleusercontent.com/img/b/x/real/2026-03-17_194999.png"]
