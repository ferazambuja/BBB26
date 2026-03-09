#!/usr/bin/env python3
"""Feasibility parser for Votalhada Consolidado OCR.

This script intentionally focuses on OCR parsing quality and validation only.
It does NOT mutate polls.json or trigger any git automation.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import io
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable


MONTH_MAP_PT = {
    "jan": 1,
    "fev": 2,
    "mar": 3,
    "abr": 4,
    "mai": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "set": 9,
    "out": 10,
    "nov": 11,
    "dez": 12,
}

DEFAULT_NAME_ALIASES = {
    "A COWBOY": "Alberto Cowboy",
    "COWBOY": "Alberto Cowboy",
    "A COWBO": "Alberto Cowboy",
}

CONSOLIDADO_SUM_TOLERANCE = 0.25
SERIES_SUM_TOLERANCE = 0.75


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _norm(text: str) -> str:
    text = _strip_accents(text).upper()
    return re.sub(r"\s+", " ", text).strip()


def _as_float_percent(token: str) -> float | None:
    token = token.strip().replace(" ", "")
    if not token:
        return None

    # Keep only digits + separators.
    cleaned = re.sub(r"[^0-9,\.]", "", token)
    cleaned = cleaned.strip(".,")
    if not cleaned:
        return None

    # If token looks like "4121" (OCR dropped comma), assume 41,21.
    if cleaned.isdigit() and len(cleaned) == 4:
        return round(int(cleaned) / 100.0, 2)
    # If token looks like "468", assume 4,68.
    if cleaned.isdigit() and len(cleaned) == 3:
        return round(int(cleaned) / 100.0, 2)

    # Percentages should not use thousands separators; commas usually decimal.
    if "," in cleaned:
        candidate = cleaned.replace(".", "").replace(",", ".")
    else:
        candidate = cleaned
    if candidate.count(".") > 1:
        parts = candidate.split(".")
        candidate = parts[0] + "." + "".join(parts[1:])
    try:
        return round(float(candidate), 2)
    except ValueError:
        return None


def _as_int_votes(token: str) -> int | None:
    digits = re.sub(r"\D", "", token)
    if not digits:
        return None
    return int(digits)


def _repair_triplet(values: list[float]) -> list[float]:
    """Repair obvious OCR scale mistakes (e.g. 27 -> 2.7) when sum explodes."""
    if len(values) != 3:
        return values
    total = sum(values)
    if total <= 101.5:
        return values

    repaired = values[:]
    for idx, value in enumerate(repaired):
        for divisor in (10.0, 100.0):
            new_value = round(value / divisor, 2)
            if sum(repaired) - value + new_value <= 101.5:
                repaired[idx] = new_value
                return repaired
    return repaired


def classify_ocr_text(text: str) -> tuple[str, int]:
    """Classify OCR content into consolidated/platform/noise buckets."""
    n = _norm(text)
    score = 0

    if "PESQUISA DE POPULARIDADE" in n or "POPULARIDADE" in n:
        return "noise", 100

    if "CONSOLIDADOS" in n:
        score += 3
    if "VARIACAO DAS MEDIAS" in n:
        score += 5
    elif "EVOLUCAO DAS MEDIAS" in n:
        score += 5
    elif "EVOLU" in n and "MEDIAS" in n:
        score += 5
    if "MEDIA PROPORCIONAL" in n or ("MEDIA" in n and "PROPORCIONAL" in n):
        score += 2
    if "TOTAL DE VOTOS" in n or "TOTALDEVOTOS" in n or " TOTAL " in f" {n} ":
        score += 1

    if score >= 6:
        return "consolidado_data", score

    if any(k in n for k in ("X TWITTER", "YOUTUBE", "INSTAGRAM", " SITES ", "SITES -")):
        return "platform_breakdown", max(score, 1)

    return "unknown", score


def _run_tesseract_text(image_path: Path, psm: int = 6) -> str:
    cmd = [
        "tesseract",
        str(image_path),
        "stdout",
        "-l",
        "eng",
        "--psm",
        str(psm),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout


def select_best_consolidado_image(
    image_paths: Iterable[Path],
    ocr_func: Callable[[Path], str] | None = None,
) -> tuple[Path, dict[str, dict[str, int | str]]]:
    """Pick the best consolidated image using content signatures."""
    ocr = ocr_func or _run_tesseract_text
    best_path: Path | None = None
    best_score = -1
    best_ts: datetime | None = None
    diagnostics: dict[str, dict[str, int | str]] = {}

    def _extract_ts(path: Path) -> datetime | None:
        m = re.search(r"_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}(?:-\d{2})?)\.png$", path.name)
        if not m:
            return None
        raw = m.group(1)
        for fmt in ("%Y-%m-%d_%H-%M-%S", "%Y-%m-%d_%H-%M"):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
        return None

    for path in image_paths:
        text = ocr(path)
        label, score = classify_ocr_text(text)
        diagnostics[path.name] = {"label": label, "score": score}
        if label != "consolidado_data":
            continue

        ts = _extract_ts(path)
        should_replace = False
        if score > best_score:
            should_replace = True
        elif score == best_score:
            if ts is not None and (best_ts is None or ts > best_ts):
                should_replace = True
            elif ts is None and best_ts is None and (best_path is None or path.name > best_path.name):
                should_replace = True

        if should_replace:
            best_path = path
            best_score = score
            best_ts = ts

    if best_path is None:
        raise ValueError("No consolidated image detected in batch.")

    return best_path, diagnostics


def _extract_row_values(lines: list[str], label: str) -> tuple[list[float], int]:
    label_norm = _norm(label)
    candidates: list[tuple[float, int, list[float], int]] = []
    for line in lines:
        if label_norm not in _norm(line):
            continue
        tokens = re.findall(r"\d[\d\.,]*", line)
        if len(tokens) < 4:
            continue
        p1 = _as_float_percent(tokens[0])
        p2 = _as_float_percent(tokens[1])
        p3 = _as_float_percent(tokens[2])
        votes = _as_int_votes(tokens[3])
        if None in (p1, p2, p3, votes):
            continue
        repaired = _repair_triplet([p1, p2, p3])
        if any(v < 0 or v > 100 for v in repaired):
            continue
        sum_gap = abs(sum(repaired) - 100.0)
        candidates.append((sum_gap, -int(votes), repaired, int(votes)))
    if candidates:
        candidates.sort(key=lambda item: (item[0], item[1]))
        _, _, best_pcts, best_votes = candidates[0]
        return best_pcts, best_votes
    raise ValueError(f"Could not parse row for label '{label}'")


def _extract_row_values_any(lines: list[str], labels: list[str]) -> tuple[list[float], int] | None:
    for label in labels:
        try:
            return _extract_row_values(lines, label)
        except ValueError:
            continue
    return None


def _extract_consolidado_row(text: str) -> tuple[list[float], int]:
    flat = re.sub(r"\s+", " ", text)
    pattern = (
        r"(?:M[ÉE]DIA\s+PROPORCIONAL|PROPORCIONAL)\s+"
        r"(\d[\d,\.]*)\s+(\d[\d,\.]*)\s+(\d[\d,\.]*)\s+"
        r"(?:TOTAL\s+)?(\d[\d,\.]*)"
    )
    m = re.search(pattern, flat, flags=re.IGNORECASE)
    if not m:
        raise ValueError("Could not parse 'Média Proporcional' row")
    pcts = [_as_float_percent(m.group(i)) for i in (1, 2, 3)]
    votes = _as_int_votes(m.group(4))
    if any(v is None for v in pcts) or votes is None:
        raise ValueError("Invalid values in consolidated row")
    return _repair_triplet([pcts[0], pcts[1], pcts[2]]), int(votes)


def _platform_keys_for_totals(plataformas: dict) -> list[str]:
    keys = [k for k, v in plataformas.items() if isinstance(v, dict) and "votos" in v]
    if not keys:
        return []

    core = [k for k in ("sites", "youtube", "twitter") if k in keys]
    extra = []
    if "outras_redes" in keys:
        extra = ["outras_redes"]
    elif "instagram" in keys and "threads" in keys:
        extra = ["instagram", "threads"]
    elif "instagram" in keys:
        extra = ["instagram"]
    elif "threads" in keys:
        extra = ["threads"]

    selected = core + extra
    if selected:
        return selected
    return keys


def _compute_weighted_consolidado(plataformas: dict, participants: list[str]) -> tuple[list[float], int]:
    platform_keys = _platform_keys_for_totals(plataformas)
    total_votes = sum(int(plataformas[p]["votos"]) for p in platform_keys)
    if total_votes <= 0:
        raise ValueError("Cannot compute weighted consolidado: zero total votes")

    weighted = []
    for name in participants:
        acc = 0.0
        for p in platform_keys:
            acc += float(plataformas[p][name]) * int(plataformas[p]["votos"])
        weighted.append(round(acc / total_votes, 2))
    return weighted, total_votes


def _extract_note(text: str) -> str | None:
    for line in text.splitlines():
        clean = _norm(line)
        if "EMPATE" in clean:
            return clean
    return None


def _normalize_hora_token(token: str) -> str | None:
    token = token.strip()

    hh = mm = None
    if re.fullmatch(r"\d{2}:\d{2}", token):
        hh, mm = map(int, token.split(":"))
    elif re.fullmatch(r"\d{4}", token):
        hh = int(token[:2])
        mm = int(token[2:])
    elif re.fullmatch(r"\d{3}", token):
        hh = int(token[0])
        mm = int(token[1:])
    elif re.fullmatch(r"\d{5,8}", token):
        # OCR may merge time + next numeric token; keep first HHMM.
        hh = int(token[:2])
        mm = int(token[2:4])
    else:
        return None

    # Common OCR repairs:
    # 45:00 -> 15:00, 43:00 -> 13:00, etc.
    if 40 <= hh <= 49:
        hh -= 30
    elif 30 <= hh <= 33:
        hh -= 30

    if hh < 0 or hh > 23:
        return None
    if mm < 0 or mm > 59:
        return None
    if mm not in {0, 30}:
        # Keep only expected minute slots for this dataset.
        return None
    return f"{hh:02d}:{mm:02d}"


def _coerce_time_progression(time_str: str, previous: str | None) -> str:
    """Coerce likely OCR time slips to the nearest plausible scheduled slot."""
    schedule = ["01:00", "01:30", "08:00", "12:00", "15:00", "17:30", "18:00", "21:00"]

    def to_minutes(t: str) -> int:
        hh, mm = map(int, t.split(":"))
        return hh * 60 + mm

    if previous is None:
        return time_str

    cur = to_minutes(time_str)
    prev = to_minutes(previous)
    if cur > prev and time_str in schedule:
        return time_str

    candidates = [t for t in schedule if to_minutes(t) > prev]
    if not candidates:
        return time_str
    preferred = [t for t in candidates if t[3:] == time_str[3:]] or candidates
    return min(preferred, key=lambda t: abs(to_minutes(t) - cur))


def _parse_hora_pt(hora: str, year: int = 2026) -> datetime:
    day_month, time_part = hora.split()
    day_str, month_str = day_month.split("/")
    hh, mm = time_part.split(":")
    month = MONTH_MAP_PT[month_str.lower()]
    return datetime(year, month, int(day_str), int(hh), int(mm))


def _normalize_day_month_token(token: str) -> str | None:
    raw = _strip_accents(token).lower().strip()
    raw = raw.replace("o", "0")
    raw = raw.replace("l", "1")

    m = re.match(r"^([0-9]{2})[\/f]?([a-z]{3,6})$", re.sub(r"[^0-9a-z/]", "", raw))
    if not m:
        # Try to recover tokens like "02%fmar"
        m2 = re.search(r"([0-9]{2}).*?([a-z]{3,6})", raw)
        if not m2:
            return None
        day = int(m2.group(1))
        month_token = m2.group(2)
    else:
        day = int(m.group(1))
        month_token = m.group(2)

    if day < 1 or day > 31:
        return None

    month_token = re.sub(r"[^a-z]", "", month_token)
    aliases = {
        "few": "fev",
        "fey": "fev",
        "fer": "fev",
        "fevv": "fev",
        "marg": "mar",
        "margo": "mar",
    }
    month_token = aliases.get(month_token, month_token)

    month = None
    if month_token in MONTH_MAP_PT:
        month = month_token
    else:
        close = difflib.get_close_matches(month_token, MONTH_MAP_PT.keys(), n=1, cutoff=0.4)
        if close:
            month = close[0]
    if month is None:
        return None

    return f"{day:02d}/{month}"


def _run_tesseract_tsv(image_path: Path, psm: int = 6) -> list[dict]:
    cmd = [
        "tesseract",
        str(image_path),
        "stdout",
        "-l",
        "eng",
        "--psm",
        str(psm),
        "tsv",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    words: list[dict] = []
    reader = csv.DictReader(io.StringIO(result.stdout), delimiter="\t")
    for row in reader:
        if row.get("level") != "5":
            continue
        text = (row.get("text") or "").strip()
        if not text:
            continue
        try:
            conf = float(row.get("conf") or -1)
        except ValueError:
            conf = -1.0
        words.append(
            {
                "block_num": int(row["block_num"]),
                "par_num": int(row["par_num"]),
                "line_num": int(row["line_num"]),
                "left": int(row["left"]),
                "top": int(row["top"]),
                "conf": conf,
                "text": text,
            }
        )
    return words


def _is_series_header(norm_line: str) -> bool:
    if "VARIACAO DAS MEDIAS" in norm_line:
        return True
    if "EVOLUCAO DAS MEDIAS" in norm_line:
        return True
    return ("VARIAC" in norm_line and "MEDIAS" in norm_line) or ("EVOLU" in norm_line and "MEDIAS" in norm_line)


def _make_top_table_crop(image_path: Path, start_ratio: float = 0.12, end_ratio: float = 0.62) -> Path:
    identify = subprocess.run(
        ["magick", "identify", "-format", "%w %h", str(image_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    width_str, height_str = identify.stdout.strip().split()
    width, height = int(width_str), int(height_str)
    top = int(height * start_ratio)
    bottom = int(height * end_ratio)
    crop_h = max(1, bottom - top)

    with tempfile.NamedTemporaryFile(
        prefix="ocr_top_",
        suffix=".png",
        dir=Path.cwd(),
        delete=False,
    ) as tmp:
        out_path = Path(tmp.name)

    subprocess.run(
        [
            "magick",
            str(image_path),
            "-crop",
            f"{width}x{crop_h}+0+{top}",
            "+repage",
            "-colorspace",
            "Gray",
            "-contrast-stretch",
            "0x10%",
            "-resize",
            "220%",
            str(out_path),
        ],
        check=True,
    )
    return out_path


def _extract_top_table_lines(image_path: Path) -> list[str]:
    temp_crop = _make_top_table_crop(image_path)
    try:
        text_psm6 = _run_tesseract_text(temp_crop, psm=6)
        text_psm4 = _run_tesseract_text(temp_crop, psm=4)
    finally:
        temp_crop.unlink(missing_ok=True)
    lines = [line.strip() for line in (text_psm6 + "\n" + text_psm4).splitlines() if line.strip()]
    return lines


def _make_bottom_table_crop(image_path: Path, top_ratio: float = 0.40) -> Path:
    identify = subprocess.run(
        ["magick", "identify", "-format", "%w %h", str(image_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    width_str, height_str = identify.stdout.strip().split()
    width, height = int(width_str), int(height_str)
    top = int(height * top_ratio)
    crop_h = height - top

    with tempfile.NamedTemporaryFile(
        prefix="ocr_bottom_",
        suffix=".png",
        dir=Path.cwd(),
        delete=False,
    ) as tmp:
        out_path = Path(tmp.name)

    subprocess.run(
        [
            "magick",
            str(image_path),
            "-crop",
            f"{width}x{crop_h}+0+{top}",
            "+repage",
            "-colorspace",
            "Gray",
            "-contrast-stretch",
            "0x10%",
            "-resize",
            "200%",
            str(out_path),
        ],
        check=True,
    )
    return out_path


def _parse_series_row_from_tokens(
    tokens: list[dict],
    current_date: str | None,
    participants: list[str],
    current_time: str | None,
) -> tuple[dict | None, str | None, str | None]:
    row_tokens = sorted(tokens, key=lambda t: t["left"])
    row_text = " ".join(tok["text"] for tok in row_tokens)
    if "TOTAL DE VOTOS" in _norm(row_text) and "HORA" in _norm(row_text):
        return None, current_date, current_time
    if not re.search(r"\d", row_text):
        return None, current_date, current_time

    for tok in row_tokens:
        date_norm = _normalize_day_month_token(tok["text"])
        if date_norm:
            current_date = date_norm
            break

    time_token = None
    for tok in row_tokens:
        maybe_time = _normalize_hora_token(tok["text"])
        if maybe_time:
            time_token = maybe_time
            break
    if current_date is None or time_token is None:
        return None, current_date, current_time
    time_token = _coerce_time_progression(time_token, current_time)

    numeric = []
    for tok in row_tokens:
        txt = tok["text"]
        if not re.search(r"\d", txt):
            continue
        if _normalize_hora_token(txt):
            continue
        if _normalize_day_month_token(txt):
            continue
        numeric.append(tok)

    if not numeric:
        return None, current_date, current_time

    votes_left = None
    votes_value = None
    vote_candidates = []
    for tok in numeric:
        val = _as_int_votes(tok["text"])
        if val is None:
            continue
        if val >= 100000 and tok["left"] >= 620:
            vote_candidates.append((tok["left"], val))
    if vote_candidates:
        votes_left, votes_value = sorted(vote_candidates, key=lambda x: x[0])[-1]
    else:
        fallback_votes = []
        for tok in numeric:
            val = _as_int_votes(tok["text"])
            if val is not None and val >= 10000:
                fallback_votes.append((tok["left"], val))
        if fallback_votes:
            votes_left, votes_value = sorted(fallback_votes, key=lambda x: x[0])[-1]

    if votes_value is None:
        return None, current_date, current_time

    pct_tokens = []
    for tok in numeric:
        if tok["left"] < 220:
            continue
        if votes_left is not None and tok["left"] >= votes_left - 20:
            continue
        val = _as_float_percent(tok["text"])
        if val is None:
            continue
        if val < 0 or val > 100:
            continue
        pct_tokens.append((tok["left"], val))

    if len(pct_tokens) < 3:
        return None, current_date, current_time

    pct_tokens.sort(key=lambda x: x[0])
    pcts = _repair_triplet([pct_tokens[0][1], pct_tokens[1][1], pct_tokens[2][1]])

    row = {
        "hora": f"{current_date} {time_token}",
        participants[0]: pcts[0],
        participants[1]: pcts[1],
        participants[2]: pcts[2],
        "votos": int(votes_value),
    }
    return row, current_date, time_token


def extract_series_rows_from_image(image_path: Path, participants: list[str]) -> list[dict]:
    """Extract series rows from the bottom table using crop + TSV parsing."""
    temp_crop = _make_bottom_table_crop(image_path)
    try:
        words = _run_tesseract_tsv(temp_crop, psm=6)
        text_fallback_psm6 = _run_tesseract_text(temp_crop, psm=6)
        text_fallback_psm4 = _run_tesseract_text(temp_crop, psm=4)
    finally:
        temp_crop.unlink(missing_ok=True)

    by_line: dict[tuple[int, int, int], list[dict]] = {}
    for word in words:
        key = (word["block_num"], word["par_num"], word["line_num"])
        by_line.setdefault(key, []).append(word)

    lines = sorted(
        by_line.values(),
        key=lambda toks: (min(tok["top"] for tok in toks), min(tok["left"] for tok in toks)),
    )

    rows: list[dict] = []
    in_series = False
    current_date: str | None = None
    current_time: str | None = None

    for toks in lines:
        line_text = " ".join(tok["text"] for tok in sorted(toks, key=lambda t: t["left"]))
        norm_line = _norm(line_text)
        if _is_series_header(norm_line):
            in_series = True
            continue
        if not in_series:
            continue
        row, current_date, current_time = _parse_series_row_from_tokens(
            toks,
            current_date,
            participants,
            current_time,
        )
        if row is not None:
            rows.append(row)

    by_hora: dict[str, dict] = {}
    for row in rows:
        by_hora[row["hora"]] = row
    rows_tsv = sorted(by_hora.values(), key=lambda r: _parse_hora_pt(r["hora"]))

    # Fallback parsers from cropped OCR text across multiple PSMs.
    rows_text_6 = _parse_series_rows(text_fallback_psm6.splitlines(), participants)
    rows_text_4 = _parse_series_rows(text_fallback_psm4.splitlines(), participants)
    rows_text_combined = _parse_series_rows(
        (text_fallback_psm6 + "\n" + text_fallback_psm4).splitlines(),
        participants,
    )

    candidates = [
        _clean_series_rows(rows_tsv, participants),
        _clean_series_rows(rows_text_6, participants),
        _clean_series_rows(rows_text_4, participants),
        _clean_series_rows(rows_text_combined, participants),
    ]
    return max(candidates, key=_series_quality)


def _parse_series_rows(lines: list[str], participants: list[str]) -> list[dict]:
    rows: list[dict] = []
    in_series = False
    current_date: str | None = None
    current_time: str | None = None

    for raw in lines:
        line = raw.strip()
        norm_line = _norm(line)

        if _is_series_header(norm_line):
            in_series = True
            continue
        if not in_series:
            continue
        if not re.search(r"\d", line):
            continue

        tokens = line.split()
        date_token = None
        time_token_raw = None
        for tok in tokens:
            if date_token is None:
                d = _normalize_day_month_token(tok)
                if d:
                    date_token = tok
                    current_date = d
                    continue
            if time_token_raw is None:
                t = _normalize_hora_token(tok)
                if t:
                    time_token_raw = t
                    continue

        if current_date is None or time_token_raw is None:
            continue
        time_token = _coerce_time_progression(time_token_raw, current_time)
        current_time = time_token

        numeric_tokens = []
        for tok in tokens:
            if tok == date_token:
                continue
            if _normalize_hora_token(tok):
                continue
            if not re.search(r"\d", tok):
                continue
            numeric_tokens.append(tok)

        if len(numeric_tokens) < 4:
            continue

        vote_idx = len(numeric_tokens) - 1
        votos = _as_int_votes(numeric_tokens[vote_idx])
        if votos is None:
            continue

        pct_values = []
        for tok in numeric_tokens[:vote_idx]:
            val = _as_float_percent(tok)
            if val is None:
                continue
            if 0 <= val <= 100:
                pct_values.append(val)
        if len(pct_values) < 3:
            continue

        pcts_fixed = _repair_triplet(pct_values[:3])
        row = {
            "hora": f"{current_date} {time_token}",
            participants[0]: pcts_fixed[0],
            participants[1]: pcts_fixed[1],
            participants[2]: pcts_fixed[2],
            "votos": int(votos),
        }
        rows.append(row)

    # Dedupe by hora, keeping latest occurrence.
    by_hora: dict[str, dict] = {}
    for row in rows:
        by_hora[row["hora"]] = row

    return sorted(by_hora.values(), key=lambda r: _parse_hora_pt(r["hora"]))


def _is_series_row_sane(row: dict, participants: list[str], sum_tolerance: float = 1.5) -> bool:
    try:
        pcts = [float(row.get(name, 0.0)) for name in participants]
        votos = int(row.get("votos", 0))
    except (TypeError, ValueError):
        return False
    if votos <= 0:
        return False
    if any(v < 0.0 or v > 100.0 for v in pcts):
        return False
    if abs(sum(pcts) - 100.0) > sum_tolerance:
        return False
    return True


def _clean_series_rows(rows: list[dict], participants: list[str]) -> list[dict]:
    if not rows:
        return []
    ordered = sorted(rows, key=lambda r: _parse_hora_pt(r["hora"]))

    cleaned: list[dict] = []
    prev_votes = -1
    for row in ordered:
        if not _is_series_row_sane(row, participants, sum_tolerance=SERIES_SUM_TOLERANCE):
            continue
        votos = int(row["votos"])
        if votos < prev_votes:
            continue
        cleaned.append(row)
        prev_votes = votos

    by_hora: dict[str, dict] = {}
    for row in cleaned:
        by_hora[row["hora"]] = row
    return sorted(by_hora.values(), key=lambda r: _parse_hora_pt(r["hora"]))


def _series_quality(rows: list[dict]) -> tuple[int, int]:
    if not rows:
        return (0, 0)
    return (len(rows), int(rows[-1].get("votos", 0)))


def _extract_platform_rows(lines: list[str], participants: list[str]) -> dict:
    rows: dict[str, dict] = {}

    def put_row(key: str, labels: list[str]) -> None:
        extracted = _extract_row_values_any(lines, labels)
        if extracted is None:
            return
        vals, votes = extracted
        rows[key] = {
            participants[0]: vals[0],
            participants[1]: vals[1],
            participants[2]: vals[2],
            "votos": votes,
        }

    # Core rows expected in both legacy and current layouts.
    put_row("sites", ["Sites"])
    put_row("youtube", ["YouTube"])
    put_row("twitter", ["Twitter", "X - Twitter", "X-Twitter"])

    # Dynamic extra schemas:
    # - old 3-platform layout: none of these appears
    # - "Outras Redes" aggregate replaces Instagram in many BBB25 snapshots
    # - split layout may expose separate "Média Threads"/"Média Instagram" lines
    put_row("instagram", ["Instagram", "Média Instagram", "Media Instagram"])
    put_row("outras_redes", ["Outras Redes", "Média Geral", "Media Geral"])
    put_row("threads", ["Média Threads", "Media Threads"])

    required = [k for k in ("sites", "youtube", "twitter") if k not in rows]
    if required:
        missing = ", ".join(required)
        raise ValueError(f"Could not parse core platform rows: {missing}")
    return rows


def parse_consolidado_snapshot(
    text: str,
    participants: list[str],
    aliases: dict[str, str] | None = None,  # kept for forward compatibility
    alt_text: str | None = None,
    source_image: Path | None = None,
) -> dict:
    """Parse consolidated OCR text into normalized structured data."""
    if len(participants) != 3:
        raise ValueError("Expected exactly 3 participants for consolidated parsing.")

    _ = aliases or {}
    lines_primary = [line.strip() for line in text.splitlines() if line.strip()]
    lines_alt = [line.strip() for line in (alt_text or "").splitlines() if line.strip()]
    lines = lines_primary + lines_alt
    if source_image is not None:
        try:
            lines.extend(_extract_top_table_lines(source_image))
        except Exception:
            # Keep parser resilient when optional crop OCR fails.
            pass

    plataformas_payload = _extract_platform_rows(lines, participants)
    note = _extract_note(text)
    series = _clean_series_rows(_parse_series_rows(lines_primary, participants), participants)
    if source_image is not None:
        series_from_image = _clean_series_rows(
            extract_series_rows_from_image(source_image, participants),
            participants,
        )
        if _series_quality(series_from_image) > _series_quality(series):
            series = series_from_image
    capture_hora = series[-1]["hora"] if series else None

    try:
        cons_vals, cons_votes = _extract_consolidado_row(text + "\n" + (alt_text or ""))
    except ValueError:
        if series:
            last = series[-1]
            cons_vals = [float(last[participants[0]]), float(last[participants[1]]), float(last[participants[2]])]
            cons_votes = int(last["votos"])
        else:
            cons_vals, cons_votes = _compute_weighted_consolidado(plataformas_payload, participants)

    # Final safeguard: if row sum drifts beyond accepted validation tolerance,
    # recompute from weighted platform rows.
    if abs(sum(cons_vals) - 100.0) > CONSOLIDADO_SUM_TOLERANCE:
        cons_vals, cons_votes = _compute_weighted_consolidado(plataformas_payload, participants)
    else:
        platform_total = sum(
            int(plataformas_payload[p]["votos"])
            for p in _platform_keys_for_totals(plataformas_payload)
        )
        allowed_gap = max(5, int(platform_total * 0.01))
        if abs(int(cons_votes) - platform_total) > allowed_gap:
            cons_vals, cons_votes = _compute_weighted_consolidado(plataformas_payload, participants)

    payload = {
        "capture_hora": capture_hora,
        "consolidado": {
            participants[0]: cons_vals[0],
            participants[1]: cons_vals[1],
            participants[2]: cons_vals[2],
            "total_votos": cons_votes,
        },
        "plataformas": plataformas_payload,
        "serie_temporal": series,
    }
    if note:
        payload["consolidado"]["nota"] = note
    return payload


def validate_snapshot(
    parsed: dict,
    participants: list[str],
    sum_tolerance: float = 0.25,
    vote_tolerance: int = 5,
) -> list[str]:
    """Validate parsed snapshot and return a list of errors."""
    errors: list[str] = []

    consolidado = parsed.get("consolidado", {})
    plataformas = parsed.get("plataformas", {})
    serie = parsed.get("serie_temporal", [])

    # Sum checks.
    cons_sum = sum(float(consolidado.get(name, 0.0)) for name in participants)
    if abs(cons_sum - 100.0) > sum_tolerance:
        errors.append(f"consolidado sum mismatch: {cons_sum:.2f}")

    platform_keys = _platform_keys_for_totals(plataformas)
    if not platform_keys:
        platform_keys = [k for k, v in plataformas.items() if isinstance(v, dict) and "votos" in v]

    for plat_name in platform_keys:
        pdata = plataformas.get(plat_name, {})
        s = sum(float(pdata.get(name, 0.0)) for name in participants)
        if abs(s - 100.0) > sum_tolerance:
            errors.append(f"{plat_name} sum mismatch: {s:.2f}")

    # Total-vote reconciliation.
    platform_total = sum(int(plataformas.get(p, {}).get("votos", 0)) for p in platform_keys)
    cons_total = int(consolidado.get("total_votos", 0))
    vote_gap = abs(platform_total - cons_total)
    allowed_gap = max(vote_tolerance, int(cons_total * 0.01))
    if vote_gap > allowed_gap:
        errors.append(
            f"total votes mismatch: consolidado={cons_total} vs platforms={platform_total} (gap={vote_gap})"
        )

    # Participant coverage checks.
    for name in participants:
        if name not in consolidado:
            errors.append(f"missing participant in consolidado: {name}")
        for plat_name in platform_keys:
            if name not in plataformas.get(plat_name, {}):
                errors.append(f"missing participant in {plat_name}: {name}")

    # Time-series monotonic votes.
    if serie:
        ordered = sorted(serie, key=lambda row: _parse_hora_pt(row["hora"]))
        prev_votes = -1
        for row in ordered:
            if not _is_series_row_sane(row, participants, sum_tolerance=SERIES_SUM_TOLERANCE):
                row_sum = sum(float(row.get(name, 0.0)) for name in participants)
                errors.append(f"series row sum mismatch at {row.get('hora')}: {row_sum:.2f}")
                break
            votos = int(row.get("votos", 0))
            if votos < prev_votes:
                errors.append(
                    f"non-monotonic series votes at {row.get('hora')}: {votos} < {prev_votes}"
                )
                break
            prev_votes = votos
    else:
        errors.append("series empty: no time-series rows parsed")

    return errors


def _load_participants_for_paredao(numero: int) -> list[str]:
    polls_path = Path("data/votalhada/polls.json")
    if polls_path.exists():
        with open(polls_path, encoding="utf-8") as f:
            polls = json.load(f)
        for entry in polls.get("paredoes", []):
            if entry.get("numero") == numero and entry.get("participantes"):
                return list(entry["participantes"])

    paredoes_path = Path("data/paredoes.json")
    if paredoes_path.exists():
        with open(paredoes_path, encoding="utf-8") as f:
            paredoes = json.load(f)
        for entry in paredoes.get("paredoes", []):
            if entry.get("numero") == numero:
                indicados = entry.get("indicados_finais", [])
                names = [x.get("nome", "").strip() for x in indicados if x.get("nome")]
                if names:
                    return names

    raise ValueError(f"Could not resolve participants for paredão {numero}")


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Votalhada Consolidado OCR feasibility parser.")
    p.add_argument("--images-dir", type=Path, required=True, help="Directory containing Votalhada PNGs.")
    p.add_argument("--paredao", type=int, help="Paredão number used to resolve participant names.")
    p.add_argument(
        "--participants",
        type=str,
        help="Comma-separated participant names (overrides --paredao lookup).",
    )
    p.add_argument("--output", type=Path, help="Output JSON file path.")
    p.add_argument("--debug", action="store_true", help="Include per-image diagnostics in stdout.")
    return p


def main() -> int:
    args = _build_arg_parser().parse_args()

    if args.participants:
        participants = [x.strip() for x in args.participants.split(",") if x.strip()]
    elif args.paredao:
        participants = _load_participants_for_paredao(args.paredao)
    else:
        raise SystemExit("Provide either --participants or --paredao.")

    if len(participants) != 3:
        raise SystemExit(f"Expected 3 participants, got {len(participants)}: {participants}")

    if not args.images_dir.exists():
        raise SystemExit(f"Images directory not found: {args.images_dir}")

    images = sorted(args.images_dir.glob("*.png"))
    if not images:
        raise SystemExit(f"No PNG files found in {args.images_dir}")

    selected, diagnostics = select_best_consolidado_image(images)
    text = _run_tesseract_text(selected, psm=6)
    alt_text = _run_tesseract_text(selected, psm=4)
    parsed = parse_consolidado_snapshot(
        text,
        participants,
        aliases=DEFAULT_NAME_ALIASES,
        alt_text=alt_text,
        source_image=selected,
    )
    errors = validate_snapshot(parsed, participants)

    result = {
        "image_selected": str(selected),
        "participants": participants,
        "parsed": parsed,
        "validation_errors": errors,
    }
    if args.debug:
        result["diagnostics"] = diagnostics

    out_json = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(out_json + "\n", encoding="utf-8")
    print(out_json)

    return 2 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
