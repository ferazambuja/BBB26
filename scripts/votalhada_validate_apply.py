#!/usr/bin/env python3
"""Validate Codex extraction and apply to polls.json.

Deterministic checks:
  1. Platform percentages sum ~100 per platform
  2. CPF sum (YT+TW+IG votos) matches cpf_media_total if present
  3. Sites votos + CPF sum = total
  4. Serie temporal is monotonic
  5. Card5 ESTIMATIVA ↔ Card6 last row cross-validation
  6. Historical serie_temporal immutability across captures

If validation passes, updates polls.json with:
  - consolidado (vote-weighted from platforms)
  - plataformas (from extraction)
  - serie_temporal (last row from series card, append-only)
  - data_coleta

Usage:
  python scripts/votalhada_validate_apply.py <paredao_num> [--apply] [--extraction-file path]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
POLLS_JSON = REPO_ROOT / "data" / "votalhada" / "polls.json"
DEFAULT_EXTRACTION = REPO_ROOT / "tmp" / "votalhada_extraction.json"

# Cross-validation thresholds
ESTIMATIVA_ERROR_PP = 1.0    # Card5↔Card6 mismatch → error
ESTIMATIVA_WARN_PP = 0.3     # Card5↔Card6 minor drift → warning
HISTORY_DRIFT_WARN_PP = 0.3  # Historical row changed → warning
HISTORY_DRIFT_ERROR_PP = 1.0 # Historical row changed significantly → error
VOTOS_MISMATCH_ABS = 1000    # Total votos card5↔card6 → error


def validate(ext: dict, participants: list[str]) -> tuple[list[str], list[str]]:
    """Validate extraction. Returns (errors, warnings)."""
    errors = []
    warnings = []
    short_to_full: dict[str, str] = {}
    for name in participants:
        short = name.split()[0]
        if short in short_to_full:
            raise ValueError(f"Duplicate short name '{short}': {short_to_full[short]} and {name}")
        short_to_full[short] = name

    # 1. Platform sums ~100
    for plat in ["sites", "youtube", "twitter", "instagram"]:
        pd = ext.get(plat, {})
        pct_vals = [pd.get(s, 0) for s in short_to_full]
        s = sum(pct_vals)
        if abs(s - 100.0) > 1.5:
            errors.append(f"{plat} sum={s:.2f} (expected ~100)")
        elif abs(s - 100.0) > 0.7:
            warnings.append(f"{plat} sum={s:.2f}")

    # 2. CPF sum matches cpf_media_total
    cpf_votos = sum(ext.get(p, {}).get("votos", 0) for p in ["youtube", "twitter", "instagram"])
    cpf_media = ext.get("cpf_media_total")
    if cpf_media and cpf_votos > 0:
        if abs(cpf_votos - cpf_media) > max(1000, cpf_media * 0.01):
            warnings.append(f"CPF sum={cpf_votos} vs cpf_media_total={cpf_media} (Votalhada display lag?)")

    # 3. Sites + CPF = total (using platform votos, not card Total)
    sites_votos = ext.get("sites", {}).get("votos", 0)
    computed_total = sites_votos + cpf_votos
    card_total = ext.get("total_votos_card", 0)
    if card_total and computed_total > 0:
        if abs(computed_total - card_total) > max(1000, computed_total * 0.01):
            warnings.append(f"Sites+CPF={computed_total} vs card Total={card_total} (Votalhada display lag)")

    # 4. Serie temporal monotonic
    series = ext.get("serie_temporal", [])
    for i in range(1, len(series)):
        v_prev = series[i - 1].get("votos", 0)
        v_curr = series[i].get("votos", 0)
        if v_curr < v_prev:
            errors.append(f"non-monotonic: {series[i-1].get('hora')} ({v_prev:,}) → {series[i].get('hora')} ({v_curr:,})")

    # 5. Check we have series data (warning — first extraction may lack card 6)
    if not series:
        warnings.append("serie_temporal empty — first extraction, no historical card yet")

    # 6. Card5↔Card6 ESTIMATIVA cross-check
    if series:
        est_series = ext.get("estimativa_series_last", {})
        est_card = ext.get("estimativa_consolidado", {})
        if est_series and est_card:
            for s in short_to_full:
                diff = abs((est_series.get(s) or 0) - (est_card.get(s) or 0))
                if diff > ESTIMATIVA_ERROR_PP:
                    errors.append(f"Card5↔Card6 mismatch: {s} card5={est_card.get(s)} card6={est_series.get(s)} Δ={diff:.2f}")
                elif diff > ESTIMATIVA_WARN_PP:
                    warnings.append(f"ESTIMATIVA drift: {s} card5={est_card.get(s)} card6={est_series.get(s)} Δ={diff:.2f}")

        # Card5 total_votos vs Card6 last row votos
        card_total = ext.get("total_votos_card", 0)
        series_total = series[-1].get("votos", 0)
        if card_total and series_total and abs(card_total - series_total) > VOTOS_MISMATCH_ABS:
            errors.append(f"Total votos: card5={card_total:,} ≠ card6={series_total:,}")

    return errors, warnings


def cross_validate_history(
    ext: dict, existing_series: list[dict], short_to_full: dict[str, str],
) -> tuple[list[str], list[str]]:
    """Cross-validate new extraction against previously stored serie_temporal.

    Checks that historical rows haven't changed between captures.
    Returns (errors, warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []
    series = ext.get("serie_temporal", [])
    if not series or not existing_series:
        return errors, warnings

    existing_by_hora = {r["hora"]: r for r in existing_series}
    for row in series:
        hora = row.get("hora", "")
        if hora not in existing_by_hora:
            continue
        prev = existing_by_hora[hora]
        for short, full in short_to_full.items():
            old_val = prev.get(full, 0) or 0
            new_val = row.get(short, 0) or 0
            diff = abs(old_val - new_val)
            if diff > HISTORY_DRIFT_ERROR_PP:
                errors.append(f"History mismatch {hora}: {short} was={old_val} now={new_val} Δ={diff:.2f}")
            elif diff > HISTORY_DRIFT_WARN_PP:
                warnings.append(f"History drift {hora}: {short} Δ={diff:.2f}")

    return errors, warnings


def apply_to_polls(ext: dict, paredao_num: int, participants: list[str]) -> None:
    """Apply validated extraction to polls.json."""
    polls = json.loads(POLLS_JSON.read_text(encoding="utf-8"))
    p = next(x for x in polls["paredoes"] if x.get("numero") == paredao_num)

    short_to_full = {}
    for name in participants:
        short_to_full[name.split()[0]] = name

    # Update plataformas
    for plat in ["sites", "youtube", "twitter", "instagram"]:
        pd = ext.get(plat, {})
        new_plat = {}
        for short, full in short_to_full.items():
            new_plat[full] = pd.get(short, 0)
        new_plat["votos"] = pd.get("votos", 0)
        if plat == "sites":
            new_plat["label"] = "Voto da Torcida"
        p["plataformas"][plat] = new_plat

    # Compute vote-weighted consolidado
    plats = p["plataformas"]
    total_v = sum(plats[pl].get("votos", 0) for pl in plats if "votos" in plats[pl])
    cons = {}
    for full in participants:
        weighted = sum(plats[pl].get(full, 0) * plats[pl].get("votos", 0) / 100 for pl in plats)
        cons[full] = round(weighted / total_v * 100, 2) if total_v > 0 else 0
    cons["total_votos"] = total_v
    cons["predicao_eliminado"] = max(participants, key=lambda n: cons.get(n, 0))
    p["consolidado"] = cons

    # Update serie_temporal: use series card last row as authoritative ESTIMATIVA
    series = ext.get("serie_temporal", [])
    if series:
        existing_horas = {r["hora"] for r in p.get("serie_temporal", [])}
        for row in series:
            hora = row.get("hora", "")
            if hora and hora not in existing_horas:
                new_row = {"hora": hora}
                for short, full in short_to_full.items():
                    new_row[full] = row.get(short, 0)
                new_row["votos"] = row.get("votos", 0)
                p["serie_temporal"].append(new_row)
        p["serie_temporal"].sort(key=lambda r: r["hora"])

    # Update data_coleta from card hora
    card_hora = ext.get("card_hora", "")
    if card_hora and series:
        last_hora = series[-1].get("hora", "")
        # Extract date from last serie row (DD/mmm) and combine with card_hora
        if "/" in last_hora:
            date_part = last_hora.split()[0]  # "24/mar"
            day, mon = date_part.split("/")
            month_map = {"jan": "01", "fev": "02", "mar": "03", "abr": "04", "mai": "05",
                         "jun": "06", "jul": "07", "ago": "08", "set": "09", "out": "10",
                         "nov": "11", "dez": "12"}
            mm = month_map.get(mon)
            if not mm:
                print(f"[validate] WARNING: unrecognized month '{mon}' — skipping data_coleta")
            else:
                year = datetime.now().year
                p["data_coleta"] = f"{year}-{mm}-{day.zfill(2)}T{card_hora}:00-03:00"

    # Add image paths
    # (handled by the scheduler, not here)

    polls["_last_updated"] = p.get("data_coleta", "")
    POLLS_JSON.write_text(json.dumps(polls, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Validate and apply Codex extraction")
    parser.add_argument("paredao", type=int)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--extraction-file", type=Path, default=DEFAULT_EXTRACTION)
    args = parser.parse_args()

    ext = json.loads(args.extraction_file.read_text(encoding="utf-8"))

    # Get participants
    polls = json.loads(POLLS_JSON.read_text(encoding="utf-8"))
    p = next((x for x in polls["paredoes"] if x.get("numero") == args.paredao), None)
    if not p:
        print(f"P{args.paredao} not in polls.json")
        sys.exit(1)
    participants = p["participantes"]

    errors, warnings = validate(ext, participants)

    # Cross-validate against existing serie_temporal
    short_to_full = {name.split()[0]: name for name in participants}
    existing_series = p.get("serie_temporal", [])
    hist_errors, hist_warnings = cross_validate_history(ext, existing_series, short_to_full)
    errors.extend(hist_errors)
    warnings.extend(hist_warnings)

    print(f"[validate] P{args.paredao}: {len(errors)} errors, {len(warnings)} warnings")
    for e in errors:
        print(f"  ERROR: {e}")
    for w in warnings:
        print(f"  WARN: {w}")

    if errors:
        print("[validate] FAILED — not applying")
        sys.exit(2)

    if args.apply:
        apply_to_polls(ext, args.paredao, participants)
        print(f"[validate] Applied to polls.json")
        # Show summary
        polls = json.loads(POLLS_JSON.read_text(encoding="utf-8"))
        p = next(x for x in polls["paredoes"] if x.get("numero") == args.paredao)
        cons = p["consolidado"]
        for n in participants:
            print(f"  {n}: {cons.get(n, 0):.2f}%")
        print(f"  Total: {cons.get('total_votos', 0):,}")
        print(f"  Prediction: {cons.get('predicao_eliminado')}")
        print(f"  Serie: {len(p.get('serie_temporal', []))} rows")
    else:
        print("[validate] PASSED (dry run — use --apply to write)")


if __name__ == "__main__":
    main()
