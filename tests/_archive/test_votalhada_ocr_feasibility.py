"""Tests for votalhada_ocr_feasibility parser and validators."""

import shutil
from pathlib import Path

import pytest

requires_tesseract = pytest.mark.skipif(
    not shutil.which("tesseract"), reason="tesseract not installed"
)
requires_magick = pytest.mark.skipif(
    not shutil.which("magick"), reason="ImageMagick not installed"
)

from votalhada_ocr_feasibility import (
    _extract_top_right_hora_from_text,
    _apply_series_time_sanity,
    _clean_series_rows,
    _run_tesseract_text,
    classify_ocr_text,
    extract_top_right_hora_from_image,
    extract_series_rows_from_image,
    parse_consolidado_snapshot,
    select_best_consolidado_image,
    validate_snapshot,
)


SAMPLE_CONSOLIDADO_OCR = """
CONSOLIDADOS - Quem voce quer SALVAR?
CONSOLIDADOS A Cowboy Breno Jordana Votos
Sites 52,21 45,02 2,77 3.042.768
YouTube 53,14 43,55 3,25 1.351.500
Twitter 42,68 49,02 8,30 623.394
Instagram 41,21 53,57 5,21 1.742.373
Media Proporcional 48,68 47,30 4,01 Total 6.760.035
EMPATE TECNICO
VARIACAO DAS MEDIAS
02/mar 01:00 46,60 46,92 6,70 1.141.249
02/mar 08:00 47,59 46,36 6,05 2.452.648
03/mar 18:00 48,68 47,30 4,01 6.760.035
"""

SAMPLE_TWITTER_OCR = """
X Twitter - Quem voce quer SALVAR?
X-Twitter A Cowboy Breno Jordana N de Votos
@perfil 23,80 67,30 8,90 20.133
Media 42,68 49,02 8,30 623.394
"""

SAMPLE_NOISE_OCR = """
Pesquisa de Popularidade
"""

SAMPLE_OLD_LAYOUT_OCR = """
CONSOLIDADOS - Quem vai VENCER o BBB 25?
CONSOLIDADOS Guilherme Joao Pedro Renata Votos
Sites 47,11 10,68 42,21 2.134.081
YouTube 32,81 9,18 58,01 748.200
Twitter 55,07 8,59 36,35 246.024
Instagram 55,20 5,50 39,30 1.225.272
Media Proporcional 47,38 8,85 43,77 Total 4.353.577
EVOLUCAO DAS MEDIAS
21/abr 01:30 46,03 8,70 45,27 1.282.823
21/abr 08:00 46,33 7,48 46,19 2.111.939
21/abr 12:00 46,39 7,81 45,80 2.672.516
21/abr 15:00 46,67 7,83 45,50 3.242.706
21/abr 17:30 47,31 8,37 44,32 3.838.177
21/abr 21:00 47,38 8,85 43,77 4.353.577
"""

SAMPLE_MISSING_CONSOLIDADO_ROW_OCR = """
CONSOLIDADOS - Quem voce quer SALVAR?
CONSOLIDADOS A Cowboy Breno Jordana Votos
Sites 50,00 30,00 20,00 1.000
YouTube 50,00 30,00 20,00 1.000
Twitter 50,00 30,00 20,00 1.000
Instagram 50,00 30,00 20,00 1.000
VARIACAO DAS MEDIAS
02/mar 01:00 40,00 30,00 30,00 100.000
"""

SAMPLE_3_PLATFORM_OCR = """
CONSOLIDADOS - Quem voce quer ELIMINAR?
CONSOLIDADOS Aline Gabriel Vitoria Votos
Sites 13,49 44,82 41,70 1.919.655
YouTube 11,95 60,33 27,72 609.200
Twitter 11,72 72,21 16,07 269.206
Media Proporcional 12,98 50,83 36,19 Total 2.798.061
EVOLUCAO DAS MEDIAS
11/fev 21:00 12,98 50,83 36,19 2.798.061
"""

SAMPLE_OUTRAS_REDES_OCR = """
CONSOLIDADOS - Quem voce quer ELIMINAR?
CONSOLIDADOS Aline Diego Maike Votos
Sites 47,81 3,21 48,98 4.973.460
YouTube 59,98 6,49 33,53 1.156.400
Twitter 32,24 3,09 64,67 482.132
Outras Redes 52,40 5,73 41,87 90.582
Media Proporcional 48,85 3,80 47,34 Total 6.702.574
EVOLUCAO DAS MEDIAS
25/mar 21:00 48,85 3,80 47,34 6.702.574
"""

SAMPLE_THREADS_SPLIT_OCR = """
CONSOLIDADOS - Quem voce quer ELIMINAR?
CONSOLIDADOS Guilherme Joselma Renata Votos
Sites 6,19 46,71 47,10 4.023.595
YouTube 8,91 71,25 19,84 1.128.900
Twitter 2,66 64,98 32,36 216.479
Media Threads 4,55 65,91 29,55 13.345
Media Instagram 3,33 63,78 32,89 1.180.274
Media Proporcional 6,15 54,85 39,01 Total 6.562.593
EVOLUCAO DAS MEDIAS
15/abr 21:00 6,15 54,85 39,01 6.562.593
"""

SAMPLE_CONSOLIDADO_SUM_DRIFT_OCR = """
CONSOLIDADOS - Quem voce quer ELIMINAR?
CONSOLIDADOS P1 P2 P3 Votos
Sites 41,41 48,52 10,07 3.767.883
YouTube 60,47 33,00 6,53 1.014.100
Twitter 34,42 57,30 8,28 319.329
Outras Redes 45,00 47,65 7,35 1.139.492
Media Proporcional 44,31 46,29 8,91 Total 6.240.808
EVOLUCAO DAS MEDIAS
06/abr 21:00 44,80 46,29 8,91 6.240.808
"""

SAMPLE_MISSING_LEADING_TWITTER_VALUE_OCR = """
CONSOLIDADOS - Quem voce quer eliminar?
CONSOLIDADOS Babu Chaiany Milena Votos
Sites 43,27 1,60 55,14 566.849
YouTube 58,36 5,14 37,05 257.004
Twitter 3,52 16,52 272.481
Instagram 71,42 2,33 26,25 684.309
Media Proporcional 60,13 5,05 34,90 Total 1.838.009
VARIACAO DAS MEDIAS
09/mar 01:00 60,13 5,05 34,90 1.838.009
"""

SAMPLE_DUPLICATE_YOUTUBE_FULL_AND_MISSING_OCR = """
CONSOLIDADOS - Quem voce quer eliminar?
CONSOLIDADOS Babu Chaiany Milena Votos
Sites 45,11 1,92 52,97 1.224.702
YouTube 58,67 4,79 36,90 581.336
YouTube 4,79 36,90 581.336
Twitter 78,89 3,19 17,93 405.746
Instagram 72,50 2,00 25,50 1.183.200
Media Proporcional 60,10 3,85 36,11 Total 3.452.350
VARIACAO DAS MEDIAS
09/mar 08:00 60,10 3,85 36,11 3.452.350
"""

SAMPLE_SERIES_ROW_WITHOUT_VOTES_OCR = """
CONSOLIDADOS - Quem voce quer eliminar?
CONSOLIDADOS Babu Chaiany Milena Votos
Sites 43,27 1,60 55,14 566.849
YouTube 58,36 5,14 37,05 257.004
Twitter 79,97 3,52 16,52 272.481
Instagram 71,42 2,33 26,25 684.309
Media Proporcional 60,13 5,05 34,90 Total 1.838.009
VARIACAO DAS MEDIAS
09/mar 01:00 60,13 5,05 34,90
"""


def test_classify_ocr_text_consolidado():
    label, score = classify_ocr_text(SAMPLE_CONSOLIDADO_OCR)
    assert label == "consolidado_data"
    assert score > 0


def test_classify_ocr_text_noise_banner():
    label, score = classify_ocr_text(SAMPLE_NOISE_OCR)
    assert label == "noise"
    assert score > 0


def test_classify_ocr_text_consolidado_old_layout_evolucao():
    label, score = classify_ocr_text(SAMPLE_OLD_LAYOUT_OCR)
    assert label == "consolidado_data"
    assert score > 0


def test_select_best_consolidado_image_by_content_not_filename_index():
    images = [
        Path("consolidados_6_2026-03-03_22-39.png"),  # noise by content
        Path("consolidados_2026-03-03_22-39.png"),    # platform
        Path("consolidados_5_2026-03-03_22-39.png"),  # actual consolidated
    ]

    by_name = {
        images[0].name: SAMPLE_NOISE_OCR,
        images[1].name: SAMPLE_TWITTER_OCR,
        images[2].name: SAMPLE_CONSOLIDADO_OCR,
    }

    def fake_ocr(path: Path) -> str:
        return by_name[path.name]

    selected, diag = select_best_consolidado_image(images, ocr_func=fake_ocr)
    assert selected.name == "consolidados_5_2026-03-03_22-39.png"
    assert diag[images[0].name]["label"] == "noise"
    assert diag[images[2].name]["label"] == "consolidado_data"


def test_select_best_consolidado_prefers_latest_timestamp_when_scores_tie():
    images = [
        Path("consolidados_5_2026-03-03_11-06.png"),
        Path("consolidados_5_2026-03-03_22-39.png"),
    ]

    def fake_ocr(_: Path) -> str:
        return SAMPLE_CONSOLIDADO_OCR

    selected, _ = select_best_consolidado_image(images, ocr_func=fake_ocr)
    assert selected.name == "consolidados_5_2026-03-03_22-39.png"


def test_select_best_consolidado_prefers_latest_timestamp_when_seconds_are_present():
    images = [
        Path("consolidados_5_2026-03-09_06-40.png"),
        Path("consolidados_5_2026-03-09_18-06-00.png"),
    ]

    def fake_ocr(_: Path) -> str:
        return SAMPLE_CONSOLIDADO_OCR

    selected, _ = select_best_consolidado_image(images, ocr_func=fake_ocr)
    assert selected.name == "consolidados_5_2026-03-09_18-06-00.png"


def test_parse_consolidado_snapshot_extracts_expected_fields():
    participants = ["Alberto Cowboy", "Breno", "Jordana"]
    aliases = {"A Cowboy": "Alberto Cowboy"}

    parsed = parse_consolidado_snapshot(SAMPLE_CONSOLIDADO_OCR, participants, aliases=aliases)

    assert parsed["consolidado"]["Alberto Cowboy"] == 48.68
    assert parsed["consolidado"]["Breno"] == 47.30
    assert parsed["consolidado"]["Jordana"] == 4.01
    assert parsed["consolidado"]["total_votos"] == 6760035
    assert parsed["consolidado"]["nota"] == "EMPATE TECNICO"

    assert parsed["plataformas"]["sites"]["votos"] == 3042768
    assert parsed["plataformas"]["youtube"]["Breno"] == 43.55
    assert parsed["plataformas"]["twitter"]["Jordana"] == 8.30
    assert parsed["plataformas"]["instagram"]["Alberto Cowboy"] == 41.21

    assert len(parsed["serie_temporal"]) == 3
    assert parsed["serie_temporal"][-1]["hora"] == "03/mar 18:00"
    assert parsed["capture_hora"] == "03/mar 18:00"
    assert parsed["capture_hora_top"] is None
    assert parsed["capture_hora_bottom"] == "03/mar 18:00"
    assert parsed["capture_hora_resolved"] == "03/mar 18:00"
    assert parsed["capture_hora_conflict"] is False
    assert "time_corrections" in parsed
    assert "time_warnings" in parsed


def test_extract_top_right_hora_from_text_normalizes_common_patterns():
    assert _extract_top_right_hora_from_text("08:00") == "08:00"
    assert _extract_top_right_hora_from_text(" 8h00 ") == "08:00"
    assert _extract_top_right_hora_from_text("0800") == "08:00"


def test_validate_snapshot_accepts_valid_data():
    participants = ["Alberto Cowboy", "Breno", "Jordana"]
    aliases = {"A Cowboy": "Alberto Cowboy"}
    parsed = parse_consolidado_snapshot(SAMPLE_CONSOLIDADO_OCR, participants, aliases=aliases)
    errors = validate_snapshot(parsed, participants)
    assert errors == []


def test_validate_snapshot_rejects_non_monotonic_series_votes():
    participants = ["Alberto Cowboy", "Breno", "Jordana"]
    aliases = {"A Cowboy": "Alberto Cowboy"}
    parsed = parse_consolidado_snapshot(SAMPLE_CONSOLIDADO_OCR, participants, aliases=aliases)

    parsed["serie_temporal"][1]["votos"] = 1000  # break monotonic order
    errors = validate_snapshot(parsed, participants)

    assert any("non-monotonic" in e for e in errors)


def test_validate_snapshot_rejects_capture_hora_conflict():
    participants = ["Alberto Cowboy", "Breno", "Jordana"]
    parsed = parse_consolidado_snapshot(SAMPLE_CONSOLIDADO_OCR, participants)
    parsed["capture_hora_top"] = "03/mar 08:00"
    parsed["capture_hora_bottom"] = "03/mar 18:00"
    parsed["capture_hora_conflict"] = True

    errors = validate_snapshot(parsed, participants)
    assert any("capture_hora mismatch" in e for e in errors)


def test_validate_snapshot_rejects_bad_consolidado_sum():
    participants = ["Alberto Cowboy", "Breno", "Jordana"]
    aliases = {"A Cowboy": "Alberto Cowboy"}
    parsed = parse_consolidado_snapshot(SAMPLE_CONSOLIDADO_OCR, participants, aliases=aliases)

    parsed["consolidado"]["Jordana"] = 8.01  # sum becomes invalid
    errors = validate_snapshot(parsed, participants)

    assert any("sum mismatch" in e for e in errors)


def test_validate_snapshot_rejects_bad_series_row_sum():
    participants = ["Alberto Cowboy", "Breno", "Jordana"]
    aliases = {"A Cowboy": "Alberto Cowboy"}
    parsed = parse_consolidado_snapshot(SAMPLE_CONSOLIDADO_OCR, participants, aliases=aliases)

    parsed["serie_temporal"][0]["Alberto Cowboy"] = 60.0
    parsed["serie_temporal"][0]["Breno"] = 35.0
    parsed["serie_temporal"][0]["Jordana"] = 3.0
    errors = validate_snapshot(parsed, participants)

    assert any("series row sum mismatch" in e for e in errors)


def test_validate_snapshot_allows_small_total_vote_gap():
    participants = ["Alberto Cowboy", "Breno", "Jordana"]
    aliases = {"A Cowboy": "Alberto Cowboy"}
    parsed = parse_consolidado_snapshot(SAMPLE_CONSOLIDADO_OCR, participants, aliases=aliases)

    # 50k gap over ~6.7M total (~0.74%) should be tolerated.
    parsed["consolidado"]["total_votos"] = parsed["consolidado"]["total_votos"] + 50000
    errors = validate_snapshot(parsed, participants)

    assert not any("total votes mismatch" in e for e in errors)


def test_validate_snapshot_rejects_large_total_vote_gap():
    participants = ["Alberto Cowboy", "Breno", "Jordana"]
    aliases = {"A Cowboy": "Alberto Cowboy"}
    parsed = parse_consolidado_snapshot(SAMPLE_CONSOLIDADO_OCR, participants, aliases=aliases)

    # 300k gap over ~6.7M total (~4.4%) should fail.
    parsed["consolidado"]["total_votos"] = parsed["consolidado"]["total_votos"] + 300000
    errors = validate_snapshot(parsed, participants)

    assert any("total votes mismatch" in e for e in errors)


@requires_tesseract
@requires_magick
def test_extract_series_rows_from_real_p7_consolidado_image():
    image = Path("data/votalhada/2026_03_01/consolidados_5_2026-03-03_22-39.png")
    if not image.exists():
        pytest.skip("Real P7 test image not available")

    participants = ["Alberto Cowboy", "Breno", "Jordana"]
    rows = extract_series_rows_from_image(image, participants)

    assert len(rows) >= 8
    assert rows[-1]["hora"] == "03/mar 18:00"
    assert rows[-1]["votos"] > rows[0]["votos"]


@requires_tesseract
@requires_magick
def test_extract_series_rows_from_real_p6_consolidado_image():
    image = Path("data/votalhada/2026_02_22/consolidados_5_2026-02-25_01-35.png")
    if not image.exists():
        pytest.skip("Real P6 test image not available")

    participants = ["Chaiany", "Maxiane", "Milena"]
    rows = extract_series_rows_from_image(image, participants)

    # OCR density varies by environment; require the stable minimum recovered rows.
    assert len(rows) >= 8
    assert rows[-1]["hora"].endswith("21:00")
    assert rows[-1]["votos"] > rows[0]["votos"]


def test_parse_consolidado_snapshot_old_layout_extracts_series():
    participants = ["Guilherme", "Joao Pedro", "Renata"]
    parsed = parse_consolidado_snapshot(SAMPLE_OLD_LAYOUT_OCR, participants)

    assert len(parsed["serie_temporal"]) >= 6
    assert parsed["capture_hora"] == "21/abr 21:00"
    assert parsed["consolidado"]["total_votos"] == 4353577


def test_parse_consolidado_snapshot_prefers_weighted_total_when_series_total_is_off():
    participants = ["Alberto Cowboy", "Breno", "Jordana"]
    aliases = {"A Cowboy": "Alberto Cowboy"}
    parsed = parse_consolidado_snapshot(
        SAMPLE_MISSING_CONSOLIDADO_ROW_OCR,
        participants,
        aliases=aliases,
    )

    assert parsed["consolidado"]["total_votos"] == 4000


def test_parse_consolidado_snapshot_three_platform_schema():
    participants = ["Aline", "Gabriel", "Vitoria"]
    parsed = parse_consolidado_snapshot(SAMPLE_3_PLATFORM_OCR, participants)
    errors = validate_snapshot(parsed, participants)

    assert parsed["plataformas"]["sites"]["votos"] == 1919655
    assert parsed["plataformas"]["twitter"]["votos"] == 269206
    assert "instagram" not in parsed["plataformas"]
    assert errors == []


def test_parse_consolidado_snapshot_outras_redes_schema():
    participants = ["Aline", "Diego", "Maike"]
    parsed = parse_consolidado_snapshot(SAMPLE_OUTRAS_REDES_OCR, participants)
    errors = validate_snapshot(parsed, participants)

    assert parsed["plataformas"]["outras_redes"]["votos"] == 90582
    assert errors == []


def test_parse_consolidado_snapshot_threads_instagram_split_schema():
    participants = ["Guilherme", "Joselma", "Renata"]
    parsed = parse_consolidado_snapshot(SAMPLE_THREADS_SPLIT_OCR, participants)
    errors = validate_snapshot(parsed, participants)

    assert parsed["plataformas"]["threads"]["votos"] == 13345
    assert parsed["plataformas"]["instagram"]["votos"] == 1180274
    assert errors == []


def test_parse_consolidado_snapshot_recomputes_weighted_when_sum_drift_exceeds_tolerance():
    participants = ["P1", "P2", "P3"]
    parsed = parse_consolidado_snapshot(SAMPLE_CONSOLIDADO_SUM_DRIFT_OCR, participants)

    cons = parsed["consolidado"]
    assert cons["P1"] == pytest.approx(44.80, abs=0.10)
    assert cons["P2"] == pytest.approx(46.29, abs=0.10)
    assert cons["P3"] == pytest.approx(8.91, abs=0.10)
    assert abs((cons["P1"] + cons["P2"] + cons["P3"]) - 100.0) <= 0.25


def test_clean_series_rows_drops_sum_outliers_above_validation_tolerance():
    participants = ["P1", "P2", "P3"]
    rows = [
        {"hora": "07/abr 08:00", "P1": 40.02, "P2": 54.97, "P3": 5.02, "votos": 1531567},
        {"hora": "07/abr 12:00", "P1": 40.08, "P2": 55.40, "P3": 5.76, "votos": 2210559},
        {"hora": "07/abr 15:00", "P1": 41.47, "P2": 52.88, "P3": 5.65, "votos": 2529210},
    ]

    cleaned = _clean_series_rows(rows, participants)
    horas = [row["hora"] for row in cleaned]

    assert "07/abr 12:00" not in horas


def test_parse_consolidado_snapshot_recovers_missing_leading_twitter_percentage():
    participants = ["Babu Santana", "Chaiany", "Milena"]
    parsed = parse_consolidado_snapshot(SAMPLE_MISSING_LEADING_TWITTER_VALUE_OCR, participants)

    tw = parsed["plataformas"]["twitter"]
    assert tw["Babu Santana"] == pytest.approx(79.96, abs=0.1)
    assert tw["Chaiany"] == pytest.approx(3.52, abs=0.01)
    assert tw["Milena"] == pytest.approx(16.52, abs=0.01)


def test_validate_snapshot_allows_small_platform_rounding_drift():
    participants = ["Babu Santana", "Chaiany", "Milena"]
    parsed = parse_consolidado_snapshot(SAMPLE_MISSING_LEADING_TWITTER_VALUE_OCR, participants)

    # Mirrors real card behavior: displayed rounded values may sum to >100 by ~0.4.
    parsed["plataformas"]["youtube"]["Babu Santana"] = 58.08
    parsed["plataformas"]["youtube"]["Chaiany"] = 4.67
    parsed["plataformas"]["youtube"]["Milena"] = 37.62
    errors = validate_snapshot(parsed, participants)

    assert not any("youtube sum mismatch" in e for e in errors)


def test_validate_snapshot_allows_real_card_rounding_drift_100_55():
    participants = ["Babu Santana", "Chaiany", "Milena"]
    parsed = parse_consolidado_snapshot(SAMPLE_MISSING_LEADING_TWITTER_VALUE_OCR, participants)

    # Real card values can sum to 100.55 due display rounding.
    parsed["plataformas"]["youtube"]["Babu Santana"] = 58.36
    parsed["plataformas"]["youtube"]["Chaiany"] = 5.14
    parsed["plataformas"]["youtube"]["Milena"] = 37.05
    errors = validate_snapshot(parsed, participants)

    assert not any("youtube sum mismatch" in e for e in errors)


def test_parse_consolidado_snapshot_prefers_full_youtube_row_over_reconstructed_row():
    participants = ["Babu Santana", "Chaiany", "Milena"]
    parsed = parse_consolidado_snapshot(SAMPLE_DUPLICATE_YOUTUBE_FULL_AND_MISSING_OCR, participants)
    yt = parsed["plataformas"]["youtube"]

    assert yt["Babu Santana"] == pytest.approx(58.67, abs=0.01)
    assert yt["Chaiany"] == pytest.approx(4.79, abs=0.01)
    assert yt["Milena"] == pytest.approx(36.90, abs=0.01)


def test_parse_consolidado_snapshot_recovers_series_row_without_votes_value():
    participants = ["Babu Santana", "Chaiany", "Milena"]
    parsed = parse_consolidado_snapshot(SAMPLE_SERIES_ROW_WITHOUT_VOTES_OCR, participants)

    assert len(parsed["serie_temporal"]) == 1
    assert parsed["capture_hora"] == "09/mar 01:00"
    assert parsed["serie_temporal"][0]["votos"] == 1838009


@requires_tesseract
@requires_magick
def test_regression_2026_01_20_series_not_empty():
    image = Path("data/votalhada/2026_01_20/consolidados_final.png")
    if not image.exists():
        pytest.skip("Regression image 2026_01_20 not available")

    participants = ["Aline", "Ana Paula", "Milena"]
    text = _run_tesseract_text(image, psm=6)
    alt = _run_tesseract_text(image, psm=4)
    parsed = parse_consolidado_snapshot(text, participants, alt_text=alt, source_image=image)

    assert len(parsed["serie_temporal"]) >= 8
    assert parsed["capture_hora"] is not None


@requires_tesseract
@requires_magick
def test_regression_2026_02_03_total_votes_gap_resolved():
    image = Path("data/votalhada/2026_02_03/consolidados_final.png")
    if not image.exists():
        pytest.skip("Regression image 2026_02_03 not available")

    participants = ["Ana Paula", "Brigido", "Leandro"]
    text = _run_tesseract_text(image, psm=6)
    alt = _run_tesseract_text(image, psm=4)
    parsed = parse_consolidado_snapshot(text, participants, alt_text=alt, source_image=image)
    errors = validate_snapshot(parsed, participants)

    assert not any("total votes mismatch" in e for e in errors)


@requires_tesseract
@requires_magick
def test_regression_2026_02_10_series_monotonic_after_time_repair():
    image = Path("data/votalhada/2026_02_10/consolidados_final.png")
    if not image.exists():
        pytest.skip("Regression image 2026_02_10 not available")

    participants = ["Babu", "Sarah", "Sol"]
    text = _run_tesseract_text(image, psm=6)
    alt = _run_tesseract_text(image, psm=4)
    parsed = parse_consolidado_snapshot(text, participants, alt_text=alt, source_image=image)
    errors = validate_snapshot(parsed, participants)
    horas = [row["hora"] for row in parsed["serie_temporal"]]

    assert not any("non-monotonic" in e for e in errors)
    assert "09/fev 08:00" in horas
    assert "09/fev 18:00" in horas


@requires_tesseract
@requires_magick
def test_regression_2026_02_22_twitter_sum_mismatch_resolved():
    image = Path("data/votalhada/2026_02_22/consolidados_5.png")
    if not image.exists():
        pytest.skip("Regression image 2026_02_22 not available")

    participants = ["Chaiany", "Maxiane", "Milena"]
    text = _run_tesseract_text(image, psm=6)
    alt = _run_tesseract_text(image, psm=4)
    parsed = parse_consolidado_snapshot(text, participants, alt_text=alt, source_image=image)
    errors = validate_snapshot(parsed, participants)

    assert not any("twitter sum mismatch" in e for e in errors)


@requires_tesseract
@requires_magick
def test_regression_2026_03_01_instagram_row_parse_resolved():
    image = Path("data/votalhada/2026_03_01/consolidados_5_2026-03-02_10-38.png")
    if not image.exists():
        pytest.skip("Regression image 2026_03_01 not available")

    participants = ["A Cowboy", "Breno", "Jordana"]
    text = _run_tesseract_text(image, psm=6)
    alt = _run_tesseract_text(image, psm=4)
    parsed = parse_consolidado_snapshot(text, participants, alt_text=alt, source_image=image)
    errors = validate_snapshot(parsed, participants)

    assert parsed["plataformas"]["instagram"]["Jordana"] > 0
    assert not any("sum mismatch" in e for e in errors)


@requires_tesseract
@requires_magick
def test_regression_2026_03_08_06_40_single_row_series_recovers_correct_capture_date():
    image = Path("data/votalhada/2026_03_08/consolidados_5_2026-03-09_06-40.png")
    if not image.exists():
        pytest.skip("Regression image 2026_03_08 06:40 not available")

    participants = ["Babu Santana", "Chaiany", "Milena"]
    text = _run_tesseract_text(image, psm=6)
    alt = _run_tesseract_text(image, psm=4)
    parsed = parse_consolidado_snapshot(text, participants, alt_text=alt, source_image=image)
    errors = validate_snapshot(parsed, participants)

    assert not any("series empty" in e for e in errors)
    assert parsed["capture_hora"] == "09/mar 01:00"


def test_apply_series_time_sanity_repairs_rollover_03_00_to_08_00():
    rows = [
        {"hora": "24/mar 21:00", "P1": 50.0, "P2": 20.0, "P3": 30.0, "votos": 1000},
        {"hora": "25/mar 03:00", "P1": 49.0, "P2": 20.0, "P3": 31.0, "votos": 1500},
        {"hora": "25/mar 12:00", "P1": 48.0, "P2": 20.0, "P3": 32.0, "votos": 2000},
    ]

    repaired, corrections, warnings = _apply_series_time_sanity(rows, ["P1", "P2", "P3"])
    horas = [row["hora"] for row in repaired]
    assert "25/mar 08:00" in horas
    assert "25/mar 03:00" not in horas
    assert any(c["to"].endswith("08:00") for c in corrections)
    assert warnings == []


@requires_tesseract
@requires_magick
def test_regression_bbb25_p4_repairs_rollover_03_30_to_08_30():
    image = Path("tmp/bbb25_batch/pesquisa-4-paredao-quem-voce-quer/consolidados.png")
    if not image.exists():
        pytest.skip("Regression image BBB25 P4 not available")

    participants = ["Aline", "Gabriel", "Vitoria"]
    text = _run_tesseract_text(image, psm=6)
    alt = _run_tesseract_text(image, psm=4)
    parsed = parse_consolidado_snapshot(text, participants, alt_text=alt, source_image=image)

    horas = [row["hora"] for row in parsed["serie_temporal"]]
    assert "10/fev 08:30" in horas
    assert "10/fev 03:30" not in horas
    assert any(c["to"].endswith("08:30") for c in parsed["time_corrections"])


@requires_tesseract
@requires_magick
def test_regression_2026_02_17_keeps_real_22_00_slot():
    image = Path("data/votalhada/2026_02_17/consolidados_final.png")
    if not image.exists():
        pytest.skip("Regression image 2026_02_17 not available")

    participants = ["Marcelo", "Samira", "Solange"]
    text = _run_tesseract_text(image, psm=6)
    alt = _run_tesseract_text(image, psm=4)
    parsed = parse_consolidado_snapshot(text, participants, alt_text=alt, source_image=image)

    horas = [row["hora"] for row in parsed["serie_temporal"]]
    assert "15/fev 22:00" in horas


@requires_tesseract
@requires_magick
def test_extract_top_right_hora_from_real_2026_03_10_11_06_image():
    image = Path("data/votalhada/2026_03_08/consolidados_5_2026-03-10_11-06-00.png")
    if not image.exists():
        pytest.skip("Regression image 2026-03-10 11:06 not available")

    hora = extract_top_right_hora_from_image(image)
    assert hora == "08:00"


@requires_tesseract
@requires_magick
def test_regression_2026_03_10_11_06_flags_capture_hora_conflict():
    image = Path("data/votalhada/2026_03_08/consolidados_5_2026-03-10_11-06-00.png")
    if not image.exists():
        pytest.skip("Regression image 2026-03-10 11:06 not available")

    participants = ["Babu Santana", "Chaiany", "Milena"]
    text = _run_tesseract_text(image, psm=6)
    alt = _run_tesseract_text(image, psm=4)
    parsed = parse_consolidado_snapshot(text, participants, alt_text=alt, source_image=image)
    errors = validate_snapshot(parsed, participants)

    assert parsed["capture_hora_top"] == "10/mar 08:00"
    assert parsed["capture_hora_bottom"] == "10/mar 22:00"
    assert parsed["capture_hora_conflict"] is True
    assert any("capture_hora mismatch" in e for e in errors)


@requires_tesseract
@requires_magick
def test_regression_2026_03_10_16_06_flags_capture_hora_conflict():
    image = Path("data/votalhada/2026_03_08/consolidados_5_2026-03-10_16-06-00.png")
    if not image.exists():
        pytest.skip("Regression image 2026-03-10 16:06 not available")

    participants = ["Babu Santana", "Chaiany", "Milena"]
    text = _run_tesseract_text(image, psm=6)
    alt = _run_tesseract_text(image, psm=4)
    parsed = parse_consolidado_snapshot(text, participants, alt_text=alt, source_image=image)
    errors = validate_snapshot(parsed, participants)

    assert parsed["capture_hora_top"] == "10/mar 12:00"
    # After the day-boundary fix, the bottom series correctly reads 12:00
    # instead of the old garbled 23:30 (coercion artifact from cross-day time regression).
    assert parsed["capture_hora_bottom"] == "10/mar 12:00"
    assert parsed["capture_hora_conflict"] is False
    assert not any("capture_hora mismatch" in e for e in errors)
