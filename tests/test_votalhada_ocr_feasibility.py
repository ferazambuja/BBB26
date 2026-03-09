"""Tests for votalhada_ocr_feasibility parser and validators."""

from pathlib import Path

import pytest

from votalhada_ocr_feasibility import (
    _clean_series_rows,
    _run_tesseract_text,
    classify_ocr_text,
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


def test_extract_series_rows_from_real_p7_consolidado_image():
    image = Path("data/votalhada/2026_03_01/consolidados_5_2026-03-03_22-39.png")
    if not image.exists():
        pytest.skip("Real P7 test image not available")

    participants = ["Alberto Cowboy", "Breno", "Jordana"]
    rows = extract_series_rows_from_image(image, participants)

    assert len(rows) >= 8
    assert rows[-1]["hora"] == "03/mar 18:00"
    assert rows[-1]["votos"] > rows[0]["votos"]


def test_extract_series_rows_from_real_p6_consolidado_image():
    image = Path("data/votalhada/2026_02_22/consolidados_5_2026-02-25_01-35.png")
    if not image.exists():
        pytest.skip("Real P6 test image not available")

    participants = ["Chaiany", "Maxiane", "Milena"]
    rows = extract_series_rows_from_image(image, participants)

    assert len(rows) >= 10
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
