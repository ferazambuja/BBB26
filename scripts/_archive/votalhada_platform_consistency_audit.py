#!/usr/bin/env python3
"""Audit consistency of Votalhada platform cards against source rows.

This audit focuses on platform-specific cards (Sites/YouTube/Twitter/Instagram)
and checks whether the displayed "Média" values reconcile with individual rows.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from votalhada_ocr_feasibility import (
    _as_float_percent,
    _as_int_votes,
    _norm,
    _run_tesseract_text,
    classify_ocr_text,
)

PLATFORM_ORDER = ("sites", "youtube", "twitter", "instagram")
MEDIA_ROW_SUM_TOLERANCE = 0.25
DECLARED_VS_ROWS_TOLERANCE = 0.20
MIN_ROWS_HIGH_CONFIDENCE = 8
VOTE_GAP_RATIO_HIGH_CONFIDENCE = 0.03


def detect_platform(text: str) -> str | None:
    n = _norm(text)
    if "YOUTUBE -" in n:
        return "youtube"
    if "X TWITTER" in n or "TWITTER -" in n:
        return "twitter"
    if "INSTAGRAM -" in n:
        return "instagram"
    if "SITES -" in n:
        return "sites"
    return None


def _extract_media_row(lines: list[str]) -> dict[str, Any] | None:
    best: tuple[float, dict[str, Any]] | None = None
    for line in lines:
        n = _norm(line)
        if "MEDIA" not in n:
            continue
        if "PROPORCIONAL" in n and "MÉDIA PROPORCIONAL" not in n and "MEDIA PROPORCIONAL" not in n:
            # Keep compatibility but don't overfit consolidated rows.
            pass
        tokens = re.findall(r"\d[\d\.,]*", line)
        if len(tokens) < 3:
            continue
        for i in range(0, len(tokens) - 2):
            p1 = _as_float_percent(tokens[i])
            p2 = _as_float_percent(tokens[i + 1])
            p3 = _as_float_percent(tokens[i + 2])
            if None in (p1, p2, p3):
                continue
            if any(v < 0 or v > 100 for v in (p1, p2, p3)):
                continue
            row = {
                "p1": float(p1),
                "p2": float(p2),
                "p3": float(p3),
                "votes": _as_int_votes(tokens[i + 3]) if i + 3 < len(tokens) else None,
            }
            gap = abs((row["p1"] + row["p2"] + row["p3"]) - 100.0)
            if best is None or gap < best[0]:
                best = (gap, row)
    return best[1] if best is not None else None


def _looks_like_platform_data_row(norm_line: str) -> bool:
    blocked = (
        "PAREDAO",
        "PAREDÃO",
        "BABU",
        "CHAIANY",
        "MILENA",
        "N DE VOTOS",
        "N2DEVOTOS",
        "N? DE VOTOS",
        "MÉDIA",
        "MEDIA",
        "QUEM",
        "ELIMINAR",
        "CONSOLIDADOS",
        "VOTALHADA.COM.BR",
    )
    return not any(tok in norm_line for tok in blocked)


def _parse_source_rows(lines: list[str]) -> list[dict[str, Any]]:
    by_source: dict[str, dict[str, Any]] = {}
    for line in lines:
        if not re.search(r"\d", line):
            continue
        n = _norm(line)
        if not _looks_like_platform_data_row(n):
            continue
        tokens = re.findall(r"\d[\d\.,]*", line)
        if len(tokens) < 4:
            continue
        p1 = _as_float_percent(tokens[0])
        p2 = _as_float_percent(tokens[1])
        p3 = _as_float_percent(tokens[2])
        votes = _as_int_votes(tokens[-1])
        if None in (p1, p2, p3, votes):
            continue
        if any(v < 0 or v > 100 for v in (p1, p2, p3)):
            continue
        if abs((float(p1) + float(p2) + float(p3)) - 100.0) > 2.5:
            continue
        first_num_pos = re.search(r"\d", line)
        if first_num_pos is None:
            continue
        source = line[: first_num_pos.start()].strip(" ↓|-")
        source = re.sub(r"^[^\w@]+", "", source).strip()
        source_key = re.sub(r"\s+", " ", _norm(source))
        if len(source_key) < 2:
            continue
        row = {
            "source": source.strip(),
            "p1": float(p1),
            "p2": float(p2),
            "p3": float(p3),
            "votes": int(votes),
        }
        prev = by_source.get(source_key)
        if prev is None or row["votes"] > int(prev["votes"]):
            by_source[source_key] = row
    rows = sorted(by_source.values(), key=lambda r: str(r["source"]).lower())
    return rows


def parse_platform_card_text(text: str) -> dict[str, Any] | None:
    platform = detect_platform(text)
    if platform is None:
        return None
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    media = _extract_media_row(lines)
    rows = _parse_source_rows(lines)
    return {
        "platform": platform,
        "media": media,
        "rows": rows,
    }


def _round2(value: float) -> float:
    return round(float(value) + 1e-9, 2)


def evaluate_platform_card(
    parsed_card: dict[str, Any],
    *,
    min_rows_high_conf: int = MIN_ROWS_HIGH_CONFIDENCE,
    vote_gap_ratio_high_conf: float = VOTE_GAP_RATIO_HIGH_CONFIDENCE,
    declared_sum_tolerance: float = MEDIA_ROW_SUM_TOLERANCE,
    declared_vs_rows_tolerance: float = DECLARED_VS_ROWS_TOLERANCE,
    check_row_mean_drift: bool = False,
) -> dict[str, Any]:
    rows = list(parsed_card.get("rows", []))
    media = parsed_card.get("media")
    result: dict[str, Any] = {
        "platform": parsed_card.get("platform"),
        "rows_count": len(rows),
        "status": "inconclusive",
        "high_confidence": False,
        "anomalies": [],
        "reasons": [],
        "vote_gap_ratio": None,
        "declared_media": None,
        "recomputed_unweighted": None,
        "recomputed_weighted": None,
        "declared_vs_unweighted_delta": None,
    }

    if not media:
        result["reasons"].append("missing_media_row")
        return result
    if not rows:
        result["reasons"].append("no_source_rows")
        return result

    rows_votes_total = sum(int(row["votes"]) for row in rows)
    media_votes = media.get("votes")
    vote_gap_ratio: float | None = None
    if media_votes is not None and int(media_votes) > 0:
        vote_gap_ratio = abs(rows_votes_total - int(media_votes)) / int(media_votes)

    p1_mean = sum(float(r["p1"]) for r in rows) / len(rows)
    p2_mean = sum(float(r["p2"]) for r in rows) / len(rows)
    p3_mean = sum(float(r["p3"]) for r in rows) / len(rows)

    if rows_votes_total > 0:
        p1_w = sum(float(r["p1"]) * int(r["votes"]) for r in rows) / rows_votes_total
        p2_w = sum(float(r["p2"]) * int(r["votes"]) for r in rows) / rows_votes_total
        p3_w = sum(float(r["p3"]) * int(r["votes"]) for r in rows) / rows_votes_total
    else:
        p1_w, p2_w, p3_w = p1_mean, p2_mean, p3_mean

    declared = [_round2(media["p1"]), _round2(media["p2"]), _round2(media["p3"])]
    recomputed_unweighted = [_round2(p1_mean), _round2(p2_mean), _round2(p3_mean)]
    recomputed_weighted = [_round2(p1_w), _round2(p2_w), _round2(p3_w)]
    deltas = [abs(declared[i] - recomputed_unweighted[i]) for i in range(3)]

    high_confidence = len(rows) >= min_rows_high_conf
    if vote_gap_ratio is not None and vote_gap_ratio > vote_gap_ratio_high_conf:
        high_confidence = False
        result["reasons"].append(
            f"vote_gap_ratio_too_high:{vote_gap_ratio:.4f}>{vote_gap_ratio_high_conf:.4f}"
        )
    if len(rows) < min_rows_high_conf:
        result["reasons"].append(f"too_few_rows:{len(rows)}<{min_rows_high_conf}")

    declared_sum = _round2(sum(declared))
    anomalies: list[str] = []
    if abs(declared_sum - 100.0) > declared_sum_tolerance:
        # This is directly visible on the card media row; does not depend on
        # parsing all individual source lines.
        anomalies.append("declared_sum_drift")
    if check_row_mean_drift and high_confidence and max(deltas) > declared_vs_rows_tolerance:
        anomalies.append("declared_vs_rows_mean_drift")

    if anomalies:
        status = "anomaly"
    elif high_confidence:
        status = "ok"
    else:
        status = "inconclusive"

    result.update(
        {
            "status": status,
            "high_confidence": high_confidence,
            "anomalies": anomalies,
            "declared_media": {
                "p1": declared[0],
                "p2": declared[1],
                "p3": declared[2],
                "sum": declared_sum,
                "votes": int(media_votes) if media_votes is not None else None,
            },
            "recomputed_unweighted": {
                "p1": recomputed_unweighted[0],
                "p2": recomputed_unweighted[1],
                "p3": recomputed_unweighted[2],
                "sum": _round2(sum(recomputed_unweighted)),
            },
            "recomputed_weighted": {
                "p1": recomputed_weighted[0],
                "p2": recomputed_weighted[1],
                "p3": recomputed_weighted[2],
                "sum": _round2(sum(recomputed_weighted)),
                "votes_total_rows": rows_votes_total,
            },
            "declared_vs_unweighted_delta": {
                "p1": _round2(deltas[0]),
                "p2": _round2(deltas[1]),
                "p3": _round2(deltas[2]),
                "max": _round2(max(deltas)),
            },
            "vote_gap_ratio": vote_gap_ratio,
        }
    )
    return result


def _candidate_score(candidate: dict[str, Any]) -> tuple[int, int, float, int]:
    evaluation = evaluate_platform_card(candidate)
    conf = 1 if evaluation["high_confidence"] else 0
    rows_count = int(evaluation["rows_count"])
    vote_gap = float(evaluation["vote_gap_ratio"]) if evaluation["vote_gap_ratio"] is not None else 9.0
    declared_media = evaluation.get("declared_media") or {}
    has_media_votes = 1 if declared_media.get("votes") is not None else 0
    return (conf, rows_count, -vote_gap, has_media_votes)


def _best_parse_from_ocr_texts(texts: list[str]) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    for text in texts:
        parsed = parse_platform_card_text(text)
        if parsed is None:
            continue
        candidates.append(parsed)
    if not candidates:
        return None
    return max(candidates, key=_candidate_score)


def audit_platform_cards_in_dir(images_dir: Path) -> dict[str, Any]:
    images = sorted(images_dir.glob("*.png"))
    cards = []
    for image in images:
        text6 = _run_tesseract_text(image, psm=6)
        label, score = classify_ocr_text(text6)
        if label != "platform_breakdown":
            continue

        text4 = _run_tesseract_text(image, psm=4)
        best = _best_parse_from_ocr_texts([text6, text4, text6 + "\n" + text4])
        if best is None:
            cards.append(
                {
                    "image": str(image),
                    "ocr_label": label,
                    "ocr_score": score,
                    "status": "inconclusive",
                    "high_confidence": False,
                    "anomalies": [],
                    "reasons": ["unparsed_platform_card"],
                }
            )
            continue

        evaluation = evaluate_platform_card(best)
        cards.append(
            {
                "image": str(image),
                "platform": best["platform"],
                "ocr_label": label,
                "ocr_score": score,
                **evaluation,
            }
        )

    summary = {
        "total_platform_cards": len(cards),
        "ok": sum(1 for c in cards if c.get("status") == "ok"),
        "anomaly": sum(1 for c in cards if c.get("status") == "anomaly"),
        "inconclusive": sum(1 for c in cards if c.get("status") == "inconclusive"),
        "high_confidence": sum(1 for c in cards if c.get("high_confidence")),
    }
    return {
        "images_dir": str(images_dir),
        "summary": summary,
        "cards": cards,
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Audit Votalhada platform-card consistency.")
    p.add_argument("--images-dir", type=Path, required=True, help="Directory containing fetched Votalhada PNGs.")
    p.add_argument("--output", type=Path, help="Optional JSON output path.")
    p.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 2 when high-confidence anomalies are found.",
    )
    return p


def main() -> int:
    args = _build_arg_parser().parse_args()
    if not args.images_dir.exists():
        raise SystemExit(f"Images directory not found: {args.images_dir}")

    report = audit_platform_cards_in_dir(args.images_dir)
    out = json.dumps(report, ensure_ascii=False, indent=2)
    print(out)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(out + "\n", encoding="utf-8")

    if args.strict and report["summary"]["anomaly"] > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
