"""Tests for mobile viewport slice capture helpers."""

from capture_mobile_slices import compute_slice_positions, extract_result_block


def test_extract_result_block_returns_text_between_markers():
    output = """
some logs
### Result
125300
### Ran Playwright code
await page.evaluate('...');
""".strip()
    assert extract_result_block(output) == "125300"


def test_compute_slice_positions_returns_top_mid_bottom():
    positions = compute_slice_positions(scroll_height=5000, viewport_height=844)
    assert positions == [("top", 0), ("mid", 2078), ("bottom", 4156)]


def test_compute_slice_positions_deduplicates_small_pages():
    positions = compute_slice_positions(scroll_height=800, viewport_height=844)
    assert positions == [("top", 0)]
