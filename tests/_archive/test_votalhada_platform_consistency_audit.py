from votalhada_platform_consistency_audit import (
    _candidate_score,
    evaluate_platform_card,
    parse_platform_card_text,
)


SAMPLE_YOUTUBE_ANOMALY_TEXT = """
YouTube - Quem voce quer eliminar?
8º Paredao 9/marco 15:00
YouTube Babu Chaiany Milena Nº de votos
Canal A 68,00 4,00 28,00 100.000
Canal B 54,00 5,00 41,00 100.000
Canal C 60,00 5,00 35,00 100.000
Média 60,67 4,67 35,04 300.000
"""


SAMPLE_SITES_OK_TEXT = """
Sites - Quem voce quer eliminar?
8º Paredao 9/marco 15:00
Sites Babu Chaiany Milena Nº de votos
Fonte A 40,00 10,00 50,00 100.000
Fonte B 50,00 5,00 45,00 100.000
Fonte C 45,00 5,00 50,00 100.000
Média Proporcional 45,00 6,67 48,33 300.000
"""


def test_parse_platform_card_text_extracts_media_and_rows():
    parsed = parse_platform_card_text(SAMPLE_YOUTUBE_ANOMALY_TEXT)
    assert parsed is not None
    assert parsed["platform"] == "youtube"
    assert len(parsed["rows"]) == 3
    assert parsed["media"]["p1"] == 60.67
    assert parsed["media"]["p2"] == 4.67
    assert parsed["media"]["p3"] == 35.04
    assert parsed["media"]["votes"] == 300000


def test_evaluate_platform_card_flags_high_confidence_source_anomaly():
    parsed = parse_platform_card_text(SAMPLE_YOUTUBE_ANOMALY_TEXT)
    result = evaluate_platform_card(
        parsed,
        min_rows_high_conf=3,
        vote_gap_ratio_high_conf=0.01,
        declared_sum_tolerance=0.25,
        declared_vs_rows_tolerance=0.20,
        check_row_mean_drift=True,
    )

    assert result["status"] == "anomaly"
    assert result["high_confidence"] is True
    assert "declared_sum_drift" in result["anomalies"]
    assert "declared_vs_rows_mean_drift" in result["anomalies"]


def test_evaluate_platform_card_passes_consistent_card():
    parsed = parse_platform_card_text(SAMPLE_SITES_OK_TEXT)
    result = evaluate_platform_card(
        parsed,
        min_rows_high_conf=3,
        vote_gap_ratio_high_conf=0.01,
    )

    assert result["status"] == "ok"
    assert result["high_confidence"] is True
    assert result["anomalies"] == []


def test_evaluate_platform_card_uses_inconclusive_for_low_confidence():
    parsed = parse_platform_card_text(SAMPLE_SITES_OK_TEXT)
    parsed["rows"] = parsed["rows"][:2]
    result = evaluate_platform_card(parsed, min_rows_high_conf=3)

    assert result["status"] == "inconclusive"
    assert result["high_confidence"] is False
    assert result["anomalies"] == []


def test_evaluate_platform_card_inconclusive_payload_has_stable_keys():
    result = evaluate_platform_card({"platform": "youtube", "media": None, "rows": []})

    assert result["status"] == "inconclusive"
    assert result["vote_gap_ratio"] is None
    assert result["declared_media"] is None
    assert result["declared_vs_unweighted_delta"] is None


def test_candidate_score_handles_cards_without_media_row():
    score = _candidate_score({"platform": "youtube", "media": None, "rows": []})
    assert isinstance(score, tuple)


def test_declared_sum_drift_flags_anomaly_even_with_low_row_confidence():
    parsed = parse_platform_card_text(SAMPLE_YOUTUBE_ANOMALY_TEXT)
    parsed["rows"] = parsed["rows"][:2]
    result = evaluate_platform_card(parsed, min_rows_high_conf=3)

    assert result["status"] == "anomaly"
    assert "declared_sum_drift" in result["anomalies"]
