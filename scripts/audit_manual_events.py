#!/usr/bin/env python3
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

ROOT = Path(__file__).parent.parent
MANUAL = ROOT / "data/manual_events.json"
AUTO = ROOT / "data/derived/auto_events.json"
PARTICIPANTS = ROOT / "data/derived/participants_index.json"
ELIMS = ROOT / "data/derived/eliminations_detected.json"
OUT = ROOT / "docs/MANUAL_EVENTS_AUDIT.md"
OUT_JSON = ROOT / "data/derived/manual_events_audit.json"

SYSTEM_ACTORS = {"Prova do Líder", "Prova do Anjo", "Big Fone", "Dinâmica da casa", "Caixas-Surpresa", "Prova Bate e Volta"}


def load(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def split_names(value):
    if not value or not isinstance(value, str):
        return []
    if " + " in value:
        return [v.strip() for v in value.split(" + ") if v.strip()]
    return [value.strip()]


def run_audit():
    manual = load(MANUAL, {})
    auto = load(AUTO, {})
    participants = load(PARTICIPANTS, {}).get("participants", [])
    elim_events = load(ELIMS, {}).get("events", [])

    names = {p.get("name") for p in participants if p.get("name")}

    power_events = manual.get("power_events", [])
    auto_events = auto.get("events", [])

    issues = defaultdict(list)

    # Missing fields / fontes
    for i, ev in enumerate(power_events):
        missing = [k for k in ["date", "week", "type", "target", "origem", "impacto"] if not ev.get(k)]
        if missing:
            issues["missing_fields"].append((i, missing, ev))
        fontes = ev.get("fontes")
        if not fontes or not isinstance(fontes, list):
            issues["missing_sources"].append((i, ev))

        # Unknown actors/targets
        actors = split_names(ev.get("actor"))
        targets = split_names(ev.get("target"))
        for a in actors:
            if a not in names and a not in SYSTEM_ACTORS:
                issues["unknown_actor"].append((i, a, ev))
        for t in targets:
            if t not in names:
                issues["unknown_target"].append((i, t, ev))

        # Self-inflicted flag missing
        if ev.get("actor") and ev.get("target") and ev.get("actor") == ev.get("target"):
            if not ev.get("self") or not ev.get("self_inflicted"):
                issues["self_flag_missing"].append((i, ev))

    # Manual vs Auto duplicates
    auto_index = defaultdict(list)
    for ev in auto_events:
        key = (ev.get("week"), ev.get("type"), ev.get("target"))
        auto_index[key].append(ev)

    # Types where manual events intentionally complement auto-detection
    # (e.g., imunidade: auto detects role, manual records who granted it)
    manual_complement_types = {"imunidade"}
    for i, ev in enumerate(power_events):
        if ev.get("type") in manual_complement_types:
            continue
        key = (ev.get("week"), ev.get("type"), ev.get("target"))
        if key in auto_index:
            issues["manual_vs_auto"].append((i, ev, auto_index[key]))

    # Duplicate manual entries
    seen = defaultdict(list)
    for i, ev in enumerate(power_events):
        key = (ev.get("week"), ev.get("type"), ev.get("actor"), ev.get("target"), ev.get("date"))
        seen[key].append(i)
    for key, idxs in seen.items():
        if len(idxs) > 1:
            issues["duplicate_manual"].append((key, idxs))

    # Sincerão integrity
    for i, weekly in enumerate(manual.get("weekly_events", [])):
        sinc = weekly.get("sincerao")
        if not sinc:
            continue
        if not sinc.get("fontes"):
            issues["sinc_missing_sources"].append((i, weekly.get("week"), sinc))
        if not sinc.get("date"):
            issues["sinc_missing_date"].append((i, weekly.get("week"), sinc))

    # Eliminations detected by API vs manual log
    manual_participants = manual.get("participants", {}) if isinstance(manual.get("participants"), dict) else {}
    for ev in elim_events:
        missing = ev.get("missing", [])
        for name in missing:
            status = (manual_participants.get(name) or {}).get("status")
            if status not in {"eliminado", "eliminada", "desistente", "desclassificado"}:
                issues["elimination_missing_manual"].append((ev.get("date"), name))

    # Write report
    lines = []
    lines.append("# Manual Events Audit")
    lines.append("")
    lines.append(f"Manual power_events: {len(power_events)}")
    lines.append(f"Auto events: {len(auto_events)}")
    lines.append("")

    def section(title, entries):
        lines.append(f"## {title}")
        if not entries:
            lines.append("(nenhum problema detectado)")
            lines.append("")
            return
        for item in entries:
            lines.append(f"- {item}")
        lines.append("")

    section("Missing required fields", [f"index {i} missing {missing} — {ev.get('type')} {ev.get('actor')} → {ev.get('target')}" for i, missing, ev in issues.get("missing_fields", [])])
    section("Missing sources (fontes)", [f"index {i} — {ev.get('type')} {ev.get('actor')} → {ev.get('target')}" for i, ev in issues.get("missing_sources", [])])
    section("Unknown actors", [f"index {i} actor {a} — {ev.get('type')}" for i, a, ev in issues.get("unknown_actor", [])])
    section("Unknown targets", [f"index {i} target {t} — {ev.get('type')}" for i, t, ev in issues.get("unknown_target", [])])
    section("Self-inflicted missing flags", [f"index {i} — {ev.get('type')} {ev.get('actor')} → {ev.get('target')}" for i, ev in issues.get("self_flag_missing", [])])
    section("Manual vs Auto potential duplicates", [f"index {i} — manual {ev.get('type')} {ev.get('target')} week {ev.get('week')}" for i, ev, _ in issues.get("manual_vs_auto", [])])
    section("Duplicate manual entries", [f"{key} indexes {idxs}" for key, idxs in issues.get("duplicate_manual", [])])
    section("Sincerão missing sources", [f"weekly idx {i} week {wk}" for i, wk, _ in issues.get("sinc_missing_sources", [])])
    section("Sincerão missing date", [f"weekly idx {i} week {wk}" for i, wk, _ in issues.get("sinc_missing_date", [])])
    section("Elimination missing in manual_events participants", [f"{date} — {name}" for date, name in issues.get("elimination_missing_manual", [])])

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT}")

    issues_count = sum(len(v) for v in issues.values())
    status = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "issues_count": issues_count,
        "issues": {k: len(v) for k, v in issues.items()},
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUT_JSON}")

    return issues_count


def main():
    issues_count = run_audit()
    if issues_count:
        raise SystemExit(f"Manual events audit failed: {issues_count} issue(s). See {OUT}")


if __name__ == "__main__":
    main()
