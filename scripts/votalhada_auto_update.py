#!/usr/bin/env python3
"""Local Votalhada OCR auto-update runner.

Flow: optional fetch -> OCR parse/validate -> gated apply to polls.json -> optional build/render.
Default mode is validate-only (no tracked file mutation).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from votalhada_ocr_feasibility import (
    DEFAULT_NAME_ALIASES,
    MONTH_MAP_PT,
    _parse_hora_pt,
    _run_tesseract_text,
    parse_consolidado_snapshot,
    select_best_consolidado_image,
    validate_snapshot,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
POLLS_PATH = REPO_ROOT / "data" / "votalhada" / "polls.json"
FETCH_SCRIPT = REPO_ROOT / "scripts" / "fetch_votalhada_images.py"
BRT_TZ = timezone(timedelta(hours=-3))


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}")


def _load_polls() -> dict:
    if not POLLS_PATH.exists():
        raise FileNotFoundError(f"polls.json not found: {POLLS_PATH}")
    return json.loads(POLLS_PATH.read_text(encoding="utf-8"))


def _find_entry(polls: dict, numero: int) -> dict:
    for entry in polls.get("paredoes", []):
        if int(entry.get("numero", -1)) == numero:
            return entry
    raise ValueError(f"paredao {numero} not found in polls.json")


def _resolve_images_dir(entry: dict, explicit: Path | None) -> Path:
    if explicit is not None:
        if not explicit.exists():
            raise FileNotFoundError(f"images-dir does not exist: {explicit}")
        return explicit

    candidate_dirs: list[Path] = []
    for p in entry.get("imagens", []) or []:
        d = (REPO_ROOT / p).parent
        if d.exists():
            candidate_dirs.append(d)
    if candidate_dirs:
        return sorted(set(candidate_dirs), key=lambda x: x.name)[-1]

    dirs = sorted(p for p in (REPO_ROOT / "data" / "votalhada").glob("2026_*") if p.is_dir())
    if not dirs:
        raise FileNotFoundError("No data/votalhada/YYYY_MM_DD folder found")
    return dirs[-1]


def _extract_capture_suffix(path: Path) -> str | None:
    m = re.search(r"_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}(?:-\d{2})?)\.png$", path.name)
    return m.group(1) if m else None


def _year_hint_from_selected(path: Path) -> int:
    suffix = _extract_capture_suffix(path)
    if not suffix:
        return datetime.now(BRT_TZ).year
    return int(suffix.split("-")[0])


def _parse_capture_hora_pt(hora: str, year: int) -> datetime:
    day_month, hhmm = hora.split()
    day_str, month_str = day_month.split("/")
    hh, mm = hhmm.split(":")
    month = MONTH_MAP_PT[month_str.lower()]
    return datetime(year, month, int(day_str), int(hh), int(mm), tzinfo=BRT_TZ)


def _iso_brt(dt: datetime) -> str:
    return dt.astimezone(BRT_TZ).replace(microsecond=0).isoformat()


def _resolve_predicted_eliminado(consolidado: dict, participants: list[str]) -> str:
    return max(participants, key=lambda name: float(consolidado.get(name, 0.0)))


def _collect_capture_set_images(images: list[Path], selected: Path, diagnostics: dict) -> list[str]:
    suffix = _extract_capture_suffix(selected)
    if suffix is None:
        sel_full = selected if selected.is_absolute() else (REPO_ROOT / selected)
        return [str(sel_full.relative_to(REPO_ROOT))]

    allowed_labels = {"consolidado_data", "platform_breakdown"}
    capture_set = []
    for image in sorted(images):
        if not image.name.endswith(f"_{suffix}.png"):
            continue
        label = (diagnostics.get(image.name) or {}).get("label")
        if label not in allowed_labels:
            continue
        full = image if image.is_absolute() else (REPO_ROOT / image)
        capture_set.append(str(full.relative_to(REPO_ROOT)))
    return capture_set


def _apply_update(
    polls: dict,
    entry: dict,
    parsed: dict,
    participants: list[str],
    capture_dt: datetime,
    capture_set_images: list[str],
) -> None:
    entry["data_coleta"] = _iso_brt(capture_dt)

    consolidado = dict(parsed["consolidado"])
    consolidado["predicao_eliminado"] = _resolve_predicted_eliminado(consolidado, participants)
    entry["consolidado"] = consolidado

    existing_platforms = entry.get("plataformas", {})
    new_platforms: dict[str, dict] = {}
    for key, row in parsed["plataformas"].items():
        merged = dict(row)
        prev = existing_platforms.get(key, {})
        if isinstance(prev, dict) and "fontes_count" in prev:
            merged["fontes_count"] = prev["fontes_count"]
        new_platforms[key] = merged
    entry["plataformas"] = new_platforms

    existing_series = entry.get("serie_temporal", []) or []
    by_hora = {row["hora"]: dict(row) for row in existing_series}
    for row in parsed.get("serie_temporal", []) or []:
        by_hora.setdefault(row["hora"], dict(row))
    entry["serie_temporal"] = sorted(by_hora.values(), key=lambda r: _parse_hora_pt(r["hora"]))

    existing_images = entry.get("imagens", []) or []
    seen = set(existing_images)
    for image_path in capture_set_images:
        if image_path not in seen:
            existing_images.append(image_path)
            seen.add(image_path)
    entry["imagens"] = existing_images


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run Votalhada OCR auto-update locally.")
    p.add_argument("--paredao", type=int, required=True)
    p.add_argument("--images-dir", type=Path, help="Optional explicit folder with fetched PNGs.")
    p.add_argument("--fetch", action="store_true", help="Run fetch_votalhada_images.py before OCR.")
    p.add_argument("--apply", action="store_true", help="Apply updates to data/votalhada/polls.json.")
    p.add_argument("--build", action="store_true", help="Run scripts/build_derived_data.py after apply.")
    p.add_argument("--render", action="store_true", help="Run quarto render paredao.qmd after apply/build.")
    p.add_argument("--dry-run", action="store_true", help="Alias for validate-only report (no apply).")
    p.add_argument("--output", type=Path, help="Optional JSON report output path.")
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    if args.fetch:
        fetch_cmd = [sys.executable, str(FETCH_SCRIPT), "--paredao", str(args.paredao), "--dedupe", "size+sha256"]
        if args.images_dir is not None:
            fetch_cmd += ["--out-dir", str(args.images_dir)]
        _run(fetch_cmd)

    polls = _load_polls()
    entry = _find_entry(polls, args.paredao)
    participants = list(entry.get("participantes", []))
    if len(participants) != 3:
        raise ValueError(f"Expected exactly 3 participants, got {participants}")

    images_dir = _resolve_images_dir(entry, args.images_dir)
    images = sorted(images_dir.glob("*.png"))
    if not images:
        raise FileNotFoundError(f"No PNG files found in {images_dir}")

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

    gates: list[str] = []
    if not parsed.get("serie_temporal"):
        gates.append("series_empty")
    if bool(parsed.get("capture_hora_conflict")):
        gates.append(
            f"capture_hora_conflict: top={parsed.get('capture_hora_top')} bottom={parsed.get('capture_hora_bottom')}"
        )

    capture_hora = parsed.get("capture_hora")
    capture_dt = None
    if capture_hora:
        capture_dt = _parse_capture_hora_pt(capture_hora, _year_hint_from_selected(selected))
        old_data_coleta = entry.get("data_coleta")
        if old_data_coleta:
            old_dt = datetime.fromisoformat(old_data_coleta)
            if capture_dt <= old_dt:
                gates.append(
                    f"capture_not_newer: parsed={capture_dt.isoformat()} <= current={old_dt.isoformat()}"
                )
    else:
        gates.append("capture_hora_missing")

    capture_set_images = _collect_capture_set_images(images, selected, diagnostics)

    result = {
        "paredao": args.paredao,
        "images_dir": str(images_dir),
        "image_selected": str(selected),
        "participants": participants,
        "parsed": parsed,
        "validation_errors": errors,
        "gate_errors": gates,
        "capture_set_images": capture_set_images,
        "applied": False,
    }

    should_apply = args.apply and not args.dry_run
    if should_apply:
        if errors or gates:
            result["apply_skipped_reason"] = "validation_or_gate_failed"
        else:
            assert capture_dt is not None
            _apply_update(polls, entry, parsed, participants, capture_dt, capture_set_images)
            POLLS_PATH.write_text(json.dumps(polls, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            result["applied"] = True

            if args.build:
                _run([sys.executable, "scripts/build_derived_data.py"])
                result["build_ran"] = True
            if args.render:
                _run(["quarto", "render", "paredao.qmd"])
                result["render_ran"] = True

    out_text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(out_text + "\n", encoding="utf-8")
    print(out_text)

    if errors or gates:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
