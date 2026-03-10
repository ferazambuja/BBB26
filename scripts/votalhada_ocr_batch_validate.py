#!/usr/bin/env python3
"""Batch validation runner for Votalhada consolidado OCR."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from votalhada_ocr_feasibility import (
    _load_participants_for_paredao,
    _make_bottom_table_crop,
    _make_top_right_time_crop,
    _run_tesseract_text,
    classify_ocr_text,
    parse_consolidado_snapshot,
    validate_snapshot,
)


def _load_polls() -> dict:
    polls_path = Path("data/votalhada/polls.json")
    if not polls_path.exists():
        return {"paredoes": []}
    return json.loads(polls_path.read_text(encoding="utf-8"))


def _participants_for_folder(folder: Path, polls_data: dict, paredao: int | None) -> list[str] | None:
    if paredao is not None:
        return _load_participants_for_paredao(paredao)

    needle = f"data/votalhada/{folder.name}/"
    for entry in polls_data.get("paredoes", []):
        imgs = entry.get("imagens", []) or []
        if any(str(p).startswith(needle) for p in imgs):
            parts = entry.get("participantes", [])
            if len(parts) == 3:
                return list(parts)
    return None


def _save_vision_crops(image_path: Path, out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: dict[str, str] = {}

    try:
        top = _make_top_right_time_crop(image_path)
        top_out = out_dir / f"{image_path.stem}__top_time.png"
        shutil.move(str(top), str(top_out))
        saved["top_time_crop"] = str(top_out)
    except Exception:
        pass

    try:
        bottom = _make_bottom_table_crop(image_path)
        bottom_out = out_dir / f"{image_path.stem}__bottom_table.png"
        shutil.move(str(bottom), str(bottom_out))
        saved["bottom_table_crop"] = str(bottom_out)
    except Exception:
        pass

    return saved


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Batch-validate consolidado OCR over Votalhada folders.")
    p.add_argument("--images-root", type=Path, default=Path("data/votalhada"))
    p.add_argument("--folder-glob", type=str, default="2026_*")
    p.add_argument("--folders", nargs="*", help="Optional explicit folder names under images root.")
    p.add_argument("--paredao", type=int, help="Force participant names by paredao number.")
    p.add_argument("--output", type=Path, default=Path("tmp/votalhada_ocr/batch_validate.json"))
    p.add_argument("--vision-dir", type=Path, default=Path("tmp/votalhada_vision"))
    p.add_argument("--no-vision-crops", action="store_true", help="Do not emit vision helper crops.")
    p.add_argument("--fail-on-errors", action="store_true", help="Exit 2 when failed/conflict images are found.")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    polls_data = _load_polls()

    if args.folders:
        folders = [args.images_root / name for name in args.folders]
    else:
        folders = sorted(p for p in args.images_root.glob(args.folder_glob) if p.is_dir())

    summary = {
        "folders": [str(f) for f in folders],
        "total_png": 0,
        "labels": {"consolidado_data": 0, "platform_breakdown": 0, "noise": 0, "unknown": 0},
        "consolidado_total": 0,
        "consolidado_passed": 0,
        "consolidado_failed": 0,
        "capture_hora_conflicts": 0,
    }
    results: list[dict] = []

    for folder in folders:
        participants = _participants_for_folder(folder, polls_data, args.paredao)
        images = sorted(folder.glob("*.png"))
        summary["total_png"] += len(images)

        if not participants:
            results.append(
                {
                    "folder": str(folder),
                    "status": "skipped",
                    "reason": "participants_not_resolved",
                }
            )
            continue

        for image in images:
            text = _run_tesseract_text(image, psm=6)
            label, score = classify_ocr_text(text)
            summary["labels"][label if label in summary["labels"] else "unknown"] += 1

            record = {
                "folder": str(folder),
                "image": str(image),
                "label": label,
                "score": score,
            }

            if label != "consolidado_data":
                results.append(record)
                continue

            summary["consolidado_total"] += 1
            try:
                alt_text = _run_tesseract_text(image, psm=4)
                parsed = parse_consolidado_snapshot(text, participants, alt_text=alt_text, source_image=image)
                errors = validate_snapshot(parsed, participants)
                conflict = bool(parsed.get("capture_hora_conflict"))

                record.update(
                    {
                        "participants": participants,
                        "capture_hora": parsed.get("capture_hora"),
                        "capture_hora_top": parsed.get("capture_hora_top"),
                        "capture_hora_bottom": parsed.get("capture_hora_bottom"),
                        "capture_hora_conflict": conflict,
                        "series_len": len(parsed.get("serie_temporal", [])),
                        "errors": errors,
                    }
                )

                if errors:
                    summary["consolidado_failed"] += 1
                else:
                    summary["consolidado_passed"] += 1
                if conflict:
                    summary["capture_hora_conflicts"] += 1

                if (errors or conflict) and not args.no_vision_crops:
                    crop_dir = args.vision_dir / folder.name
                    record.update(_save_vision_crops(image, crop_dir))

            except Exception as exc:
                summary["consolidado_failed"] += 1
                record["errors"] = [f"parse_exception: {exc}"]
                if not args.no_vision_crops:
                    crop_dir = args.vision_dir / folder.name
                    record.update(_save_vision_crops(image, crop_dir))

            results.append(record)

    payload = {"summary": summary, "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False))
    print(f"details={args.output}")

    if args.fail_on_errors and (
        summary["consolidado_failed"] > 0 or summary["capture_hora_conflicts"] > 0
    ):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
