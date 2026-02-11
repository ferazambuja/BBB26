#!/usr/bin/env python3
"""
Update docs/PROGRAMA_BBB26.md weekly timeline table from data/manual_events.json.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUAL_EVENTS = ROOT / "data" / "manual_events.json"
DOC_PATH = ROOT / "docs" / "PROGRAMA_BBB26.md"

START = "<!-- AUTO:WEEKLY_TIMELINE_START -->"
END = "<!-- AUTO:WEEKLY_TIMELINE_END -->"

KEY_LABELS = {
    "big_fone": "Big Fone",
    "quarto_secreto": "Quarto Secreto",
    "caixas_surpresa": "Caixas‑Surpresa",
    "ganha_ganha": "Ganha‑Ganha",
    "sincerao": "Sincerão",
    "anjo_escolha": "Anjo",
    "lider": "Líder",
    "paredao": "Paredão",
}


def _fmt_date(d: str | None) -> str:
    return d or "—"


def _fmt_value(v) -> str | None:
    if v is None:
        return None
    if isinstance(v, list):
        items = [str(i) for i in v if i]
        return ", ".join(items) if items else None
    return str(v)


def summarize_value(key: str, value) -> str | None:
    if not value:
        return None
    label = KEY_LABELS.get(key, key.replace("_", " ").title())
    if isinstance(value, str):
        return f"{label}: {value}"
    if isinstance(value, list):
        items = [str(i) for i in value if i]
        if not items:
            return None
        return f"{label}: " + "; ".join(items)
    if isinstance(value, dict):
        parts = []
        date = value.get("date")
        if date:
            parts.append(date)
        for field in ("format", "participacao", "atendeu", "resultado", "consequencia", "detalhe", "descricao"):
            if field in value:
                txt = _fmt_value(value.get(field))
                if txt:
                    parts.append(txt)
        parts = [p for p in parts if p]
        if parts:
            return f"{label}: " + " — ".join(parts)
        return f"{label}"
    return f"{label}: {value}"


def build_table(manual_events: dict) -> str:
    rows = []
    rows.append("| Semana | Datas (aprox.) | Dinâmicas/ocorrências | Observações |")
    rows.append("|-------:|----------------|-----------------------|-------------|")

    weekly = manual_events.get("weekly_events", [])
    if not weekly:
        rows.append("| — | — | — | — |")
        return "\n".join(rows)

    weekly_sorted = sorted(weekly, key=lambda x: x.get("week", 0))
    for entry in weekly_sorted:
        week = entry.get("week", "—")
        dates = f"{_fmt_date(entry.get('start_date'))} – {_fmt_date(entry.get('end_date'))}"

        dynamics = []
        for key, value in entry.items():
            if key in {"week", "start_date", "end_date", "notes", "fontes"}:
                continue
            line = summarize_value(key, value)
            if line:
                dynamics.append(line)

        dyn_text = "<br>".join(dynamics) if dynamics else "—"
        notes = entry.get("notes") or "—"
        rows.append(f"| {week} | {dates} | {dyn_text} | {notes} |")

    return "\n".join(rows)


def update_doc():
    if not MANUAL_EVENTS.exists() or not DOC_PATH.exists():
        raise SystemExit("Missing manual_events.json or PROGRAMA_BBB26.md")

    manual_events = json.loads(MANUAL_EVENTS.read_text(encoding="utf-8"))
    content = DOC_PATH.read_text(encoding="utf-8")

    if START not in content or END not in content:
        raise SystemExit("Markers not found in PROGRAMA_BBB26.md")

    table = build_table(manual_events)
    new_block = f"{START}\n{table}\n{END}"

    before = content.split(START)[0]
    after = content.split(END)[1]
    DOC_PATH.write_text(before + new_block + after, encoding="utf-8")


if __name__ == "__main__":
    update_doc()
    print("Updated docs/PROGRAMA_BBB26.md")
