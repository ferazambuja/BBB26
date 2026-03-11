from pathlib import Path


def test_ranking_highlight_grid_has_mobile_single_column_override_after_last_desktop_rule():
    css_path = Path(__file__).resolve().parents[1] / "assets" / "cards.css"
    css = css_path.read_text(encoding="utf-8")

    desktop_marker = ".u-s370 { display:grid;grid-template-columns:repeat(3, minmax(0, 1fr));"
    desktop_idx = css.rfind(desktop_marker)
    assert desktop_idx != -1, "Expected final desktop .u-s370 rule not found"

    mobile_media_idx = css.find("@media (max-width: 767.98px)", desktop_idx)
    assert mobile_media_idx != -1, (
        "Expected a mobile media query after the final desktop .u-s370 rule"
    )

    mobile_window = css[mobile_media_idx: mobile_media_idx + 600]
    assert ".u-s370" in mobile_window and "grid-template-columns: 1fr;" in mobile_window, (
        "Expected .u-s370 to switch to 1 column in mobile media query after final desktop rule"
    )


def test_ranking_mobile_limits_each_column_to_top_3_items():
    qmd_path = Path(__file__).resolve().parents[1] / "index.qmd"
    qmd = qmd_path.read_text(encoding="utf-8")
    assert 'class="dark-card ranking-highlight-card"' in qmd

    css_path = Path(__file__).resolve().parents[1] / "assets" / "cards.css"
    css = css_path.read_text(encoding="utf-8")
    assert ".ranking-highlight-card .u-s065 > :nth-child(n+4)" in css
    assert ".ranking-highlight-card details.sinc-more" in css
