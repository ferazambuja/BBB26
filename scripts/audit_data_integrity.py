#!/usr/bin/env python3
"""Aggregate detect-only integrity audit for the core BBB26 data pipeline."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from builders.paredao_exposure import (
    build_nunca_paredao_items,
    build_participant_windows,
    compute_house_vote_exposure,
)
from data_utils import get_all_snapshots, read_json_if_exists, stable_json_hash
from schemas import validate_input_files

ROOT = Path(__file__).parent.parent.resolve()
DATA_DIR = ROOT / "data"
DERIVED_DIR = DATA_DIR / "derived"
OUT_PATH = DERIVED_DIR / "integrity_audit.json"
AUDIT_VERSION = 1


@contextmanager
def _pushd(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _issue(
    issues: list[dict[str, Any]],
    issue_id: str,
    severity: str,
    layer: str,
    subject: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    issues.append({
        "id": issue_id,
        "severity": severity,
        "layer": layer,
        "subject": subject,
        "message": message,
        "details": details or {},
    })


def _load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _participants(payload: dict | list | None) -> list[dict]:
    if isinstance(payload, dict) and isinstance(payload.get("participants"), list):
        return [p for p in payload["participants"] if isinstance(p, dict)]
    if isinstance(payload, list):
        return [p for p in payload if isinstance(p, dict)]
    return []


def _participant_names(payload: dict | list | None) -> list[str]:
    return [p.get("name") for p in _participants(payload) if p.get("name")]


def _snapshot_paths(root: Path) -> list[Path]:
    return sorted((root / "data" / "snapshots").glob("*.json"))


def _snapshot_presence(root: Path) -> dict[str, list[str]]:
    presence: dict[str, list[str]] = {}
    for path, date in get_all_snapshots(root / "data" / "snapshots"):
        for name in _participant_names(_load_json(path)):
            presence.setdefault(name, []).append(date)
    return presence


def _active_names_from_latest(latest_payload: dict | list | None) -> set[str]:
    names: set[str] = set()
    for participant in _participants(latest_payload):
        name = participant.get("name")
        if not name:
            continue
        characteristics = participant.get("characteristics") or {}
        if characteristics.get("eliminated"):
            continue
        names.add(name)
    return names


def _presence_status(name: str, date_value: str, windows: dict[str, dict[str, str]]) -> tuple[bool, str]:
    window = windows.get(name)
    if not window:
        return False, "missing"
    first_seen = window.get("first_seen")
    last_seen = window.get("last_seen")
    if not first_seen or not last_seen:
        return False, "missing"
    return first_seen <= date_value <= last_seen, "outside"


def _severity_counts(issues: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "critical": sum(1 for issue in issues if issue["severity"] == "critical"),
        "warning": sum(1 for issue in issues if issue["severity"] == "warning"),
        "info": sum(1 for issue in issues if issue["severity"] == "info"),
    }


def _compare_card_items(
    issues: list[dict[str, Any]],
    *,
    card: dict | None,
    expected: dict[str, dict[str, int]],
    fields: list[str],
    issue_id: str,
    subject: str,
) -> None:
    if card is None:
        _issue(issues, issue_id, "critical", "derived", subject, "Card missing from index payload")
        return
    actual_by_name = {item["name"]: item for item in card.get("items_all", [])}
    for name, stats in expected.items():
        item = actual_by_name.get(name)
        if not item:
            _issue(issues, issue_id, "critical", "derived", subject, "Expected item missing from card", {"name": name})
            continue
        for field in fields:
            if item.get(field, 0) != stats.get(field, 0):
                _issue(
                    issues,
                    issue_id,
                    "critical",
                    "derived",
                    subject,
                    f"{name} has mismatched {field}",
                    {"name": name, "field": field, "actual": item.get(field, 0), "expected": stats.get(field, 0)},
                )


def build_integrity_audit(root: Path = ROOT) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    checks_run = 0

    latest_path = root / "data" / "latest.json"
    manual_path = root / "data" / "manual_events.json"
    paredoes_path = root / "data" / "paredoes.json"
    provas_path = root / "data" / "provas.json"
    participants_index_path = root / "data" / "derived" / "participants_index.json"
    index_data_path = root / "data" / "derived" / "index_data.json"
    validation_path = root / "data" / "derived" / "validation.json"
    manual_audit_path = root / "data" / "derived" / "manual_events_audit.json"
    exposure_stats_path = root / "data" / "derived" / "paredao_exposure_stats.json"

    required_files = [latest_path, manual_path, paredoes_path, provas_path]
    for path in required_files:
        if not path.exists():
            _issue(issues, "missing_required_file", "critical", "raw", str(path.relative_to(root)), "Required file is missing")
    if not _snapshot_paths(root):
        _issue(issues, "missing_required_file", "critical", "raw", "data/snapshots", "No snapshots found")

    checks_run += 1
    if not any(issue["id"] == "missing_required_file" for issue in issues):
        try:
            with _pushd(root):
                validate_input_files()
        except Exception as exc:  # jsonschema ValidationError or I/O
            _issue(
                issues,
                "schema_validation_failed",
                "critical",
                "raw",
                "input schemas",
                "Schema validation failed",
                {"error": str(exc)},
            )

    latest = _load_json(latest_path)
    manual_events = _load_json(manual_path) or {}
    paredoes_data = _load_json(paredoes_path) or {}
    provas_data = _load_json(provas_path) or {}
    participants_index = _load_json(participants_index_path) or {}
    index_data = _load_json(index_data_path) or {}
    validation = _load_json(validation_path)
    manual_audit = _load_json(manual_audit_path)
    exposure_stats_file = _load_json(exposure_stats_path)
    paredoes_list = paredoes_data.get("paredoes", []) if isinstance(paredoes_data, dict) else []

    checks_run += 1
    latest_names = _participant_names(latest)
    newest_snapshot_path = _snapshot_paths(root)[-1] if _snapshot_paths(root) else None
    newest_snapshot = _load_json(newest_snapshot_path) if newest_snapshot_path else None
    newest_snapshot_names = _participant_names(newest_snapshot)
    if latest_names and newest_snapshot_names and set(latest_names) != set(newest_snapshot_names):
        _issue(
            issues,
            "snapshot_latest_participant_mismatch",
            "critical",
            "raw",
            "latest vs newest snapshot",
            "latest.json participant set differs from newest snapshot",
            {"latest_only": sorted(set(latest_names) - set(newest_snapshot_names)),
             "snapshot_only": sorted(set(newest_snapshot_names) - set(latest_names))},
        )

    for subject, names in (("latest.json", latest_names), (str(newest_snapshot_path.relative_to(root)) if newest_snapshot_path else "snapshot", newest_snapshot_names)):
        duplicates = [name for name, count in Counter(names).items() if count > 1]
        if duplicates:
            _issue(
                issues,
                "duplicate_participant_names",
                "critical",
                "raw",
                subject,
                "Duplicate participant names found",
                {"duplicates": duplicates},
            )
    for snapshot_path in _snapshot_paths(root):
        snapshot_names = _participant_names(_load_json(snapshot_path))
        duplicates = [name for name, count in Counter(snapshot_names).items() if count > 1]
        if duplicates:
            _issue(
                issues,
                "duplicate_participant_names",
                "critical",
                "raw",
                str(snapshot_path.relative_to(root)),
                "Duplicate participant names found",
                {"duplicates": duplicates},
            )

    checks_run += 1
    snapshot_presence = _snapshot_presence(root)
    pi_entries = participants_index.get("participants", []) if isinstance(participants_index, dict) else []
    windows = build_participant_windows(
        participants_index,
        active_names=_active_names_from_latest(latest),
        manual_events=manual_events if isinstance(manual_events, dict) else {},
    )
    for entry in pi_entries:
        name = entry.get("name")
        if not name:
            continue
        dates = snapshot_presence.get(name, [])
        if not dates:
            continue
        if entry.get("first_seen") != dates[0] or entry.get("last_seen") != dates[-1]:
            _issue(
                issues,
                "participants_index_window_mismatch",
                "critical",
                "cross_source",
                name,
                "participants_index window does not match snapshot presence",
                {"first_seen": entry.get("first_seen"), "expected_first": dates[0], "last_seen": entry.get("last_seen"), "expected_last": dates[-1]},
            )

    seen_nums: set[int] = set()
    for paredao in paredoes_list:
        numero = paredao.get("numero")
        if numero in seen_nums:
            _issue(issues, "paredao_duplicate_numero", "critical", "cross_source", f"P{numero}", "Duplicate paredão number")
        seen_nums.add(numero)

        data = paredao.get("data")
        data_formacao = paredao.get("data_formacao") or data
        if data and data_formacao and data_formacao > data:
            _issue(issues, "paredao_date_order_invalid", "critical", "cross_source", f"P{numero}", "Formation date is after result date")

        if paredao.get("votos_casa") and not paredao.get("fontes"):
            _issue(issues, "paredao_missing_vote_provenance", "warning", "raw", f"P{numero}", "House votes exist without provenance sources")

        for fonte in paredao.get("fontes", []) or []:
            if not isinstance(fonte, dict):
                continue
            arquivo = fonte.get("arquivo")
            if arquivo and not (root / arquivo).exists():
                _issue(
                    issues,
                    "missing_source_file",
                    "critical",
                    "raw",
                    f"P{numero}",
                    "Referenced source file is missing",
                    {"arquivo": arquivo},
                )

        votes_resumo = paredao.get("votos_resumo")
        if votes_resumo is not None:
            actual_summary = Counter(
                target.strip()
                for target in (paredao.get("votos_casa") or {}).values()
                if isinstance(target, str)
            )
            if dict(actual_summary) != votes_resumo:
                _issue(
                    issues,
                    "paredao_votos_resumo_mismatch",
                    "critical",
                    "cross_source",
                    f"P{numero}",
                    "votos_resumo does not match votos_casa aggregation",
                    {"actual": dict(actual_summary), "expected": votes_resumo},
                )

        nominees = [
            ind["nome"] if isinstance(ind, dict) else ind
            for ind in paredao.get("indicados_finais", [])
        ]
        eliminated = (paredao.get("resultado") or {}).get("eliminado")
        if eliminated and eliminated not in nominees:
            _issue(
                issues,
                "paredao_eliminated_not_in_nominees",
                "critical",
                "cross_source",
                f"P{numero}",
                "Eliminated participant is not in indicados_finais",
                {"eliminated": eliminated},
            )

        if data_formacao:
            blocked_voters = set(paredao.get("impedidos_votar", []) or [])
            for nominee in nominees:
                present, reason = _presence_status(nominee, data_formacao, windows)
                if not present:
                    _issue(
                        issues,
                        "paredao_nominee_missing_from_windows" if reason == "missing" else "paredao_nominee_outside_window",
                        "critical",
                        "cross_source",
                        f"P{numero}",
                        "Nominee not present at formation date",
                        {"name": nominee, "data_formacao": data_formacao},
                    )
            for voter, target in (paredao.get("votos_casa") or {}).items():
                if voter in blocked_voters:
                    _issue(
                        issues,
                        "paredao_impedido_votou",
                        "critical",
                        "cross_source",
                        f"P{numero}",
                        "Blocked voter appears in votos_casa",
                        {"name": voter, "data_formacao": data_formacao},
                    )
                present, reason = _presence_status(voter, data_formacao, windows)
                if not present:
                    _issue(
                        issues,
                        "paredao_voter_missing_from_windows" if reason == "missing" else "paredao_voter_outside_window",
                        "critical",
                        "cross_source",
                        f"P{numero}",
                        "Voter not present at formation date",
                        {"name": voter, "data_formacao": data_formacao},
                    )
                if isinstance(target, str):
                    present, reason = _presence_status(target.strip(), data_formacao, windows)
                    if not present:
                        _issue(
                            issues,
                            "paredao_vote_target_missing_from_windows" if reason == "missing" else "paredao_vote_target_outside_window",
                            "critical",
                            "cross_source",
                            f"P{numero}",
                            "Vote target not present at formation date",
                            {"name": target.strip(), "data_formacao": data_formacao},
                        )

    checks_run += 1
    for prova in (provas_data.get("provas", []) if isinstance(provas_data, dict) else []):
        prova_date = prova.get("date")
        for field in ("vencedor",):
            name = prova.get(field)
            if isinstance(name, str) and name:
                present, reason = _presence_status(name, prova_date, windows)
                if not present:
                    _issue(
                        issues,
                        "prova_participant_outside_window" if reason == "outside" else "prova_participant_missing_from_windows",
                        "critical",
                        "cross_source",
                        f"prova {prova.get('numero')}",
                        "Prova participant missing or absent on event date",
                        {"field": field, "name": name, "date": prova_date},
                    )
        for field in ("vencedores", "vip", "xepa"):
            for name in prova.get(field, []) or []:
                present, reason = _presence_status(name, prova_date, windows)
                if not present:
                    _issue(
                        issues,
                        "prova_participant_outside_window" if reason == "outside" else "prova_participant_missing_from_windows",
                        "critical",
                        "cross_source",
                        f"prova {prova.get('numero')}",
                        "Prova participant missing or absent on event date",
                        {"field": field, "name": name, "date": prova_date},
                    )

    checks_run += 1
    required_derived = [
        participants_index_path,
        index_data_path,
        validation_path,
        manual_audit_path,
        exposure_stats_path,
    ]
    for path in required_derived:
        if not path.exists():
            _issue(
                issues,
                "missing_derived_artifact",
                "critical",
                "derived",
                str(path.relative_to(root)),
                "Expected derived artifact is missing",
            )

    if isinstance(index_data, dict):
        active_names = set(index_data.get("active_names", []))
        if active_names:
            expected_active = {entry["name"] for entry in pi_entries if entry.get("active")}
            if expected_active and active_names != expected_active:
                _issue(
                    issues,
                    "index_data_active_names_mismatch",
                    "critical",
                    "derived",
                    "index_data.active_names",
                    "active_names does not match participants_index active set",
                    {"actual": sorted(active_names), "expected": sorted(expected_active)},
                )

        member_of = index_data.get("member_of") or {}
        avatars = index_data.get("avatars") or {}
        pi_by_name = {entry["name"]: entry for entry in pi_entries if entry.get("name")}
        for name in active_names:
            if name in pi_by_name and member_of.get(name) != pi_by_name[name].get("grupo"):
                _issue(issues, "index_data_member_of_mismatch", "critical", "derived", name, "member_of differs from participants_index", {"actual": member_of.get(name), "expected": pi_by_name[name].get("grupo")})
            if name in pi_by_name and avatars.get(name) != pi_by_name[name].get("avatar"):
                _issue(issues, "index_data_avatar_mismatch", "warning", "derived", name, "avatars differs from participants_index", {"actual": avatars.get(name), "expected": pi_by_name[name].get("avatar")})

        exposure_stats = ((index_data.get("paredao_exposure") or {}).get("stats") if isinstance(index_data.get("paredao_exposure"), dict) else None)
        stats_payload = (exposure_stats_file or {}).get("stats") if isinstance(exposure_stats_file, dict) else None
        if exposure_stats is None:
            _issue(issues, "missing_paredao_exposure_stats", "critical", "derived", "index_data", "paredao_exposure.stats missing from index_data")
        elif stats_payload != exposure_stats:
            _issue(issues, "paredao_exposure_stats_mismatch", "critical", "derived", "paredao_exposure_stats.json", "Exposure stats file differs from index_data payload")

        cards = {card.get("type"): card for card in (index_data.get("highlights", {}) or {}).get("cards", []) if isinstance(card, dict)}
        active_set = set(index_data.get("active_names", [])) or {entry["name"] for entry in pi_entries if entry.get("active")}
        canonical_exposure = compute_house_vote_exposure(
            paredoes_list,
            build_participant_windows(participants_index, active_names=active_set, manual_events=manual_events if isinstance(manual_events, dict) else {}),
        )
        _compare_card_items(
            issues,
            card=cards.get("blindados"),
            expected={name: canonical_exposure[name] for name in active_set if name in canonical_exposure},
            fields=["votes_total", "votes_available", "available", "protected", "last_voted_paredao"],
            issue_id="blindados_exposure_mismatch",
            subject="blindados",
        )
        _compare_card_items(
            issues,
            card=cards.get("visados"),
            expected={name: canonical_exposure[name] for name in active_set if name in canonical_exposure},
            fields=["votes_total", "votes_recent", "votes_available", "available", "protected", "last_voted_paredao"],
            issue_id="visados_exposure_mismatch",
            subject="visados",
        )

        expected_nunca_items, expected_nunca_exited = build_nunca_paredao_items(
            {
                "active_set": active_set,
                "manual_events": manual_events if isinstance(manual_events, dict) else {},
                "participants_index": participants_index,
            },
            paredoes_list,
            canonical_exposure,
        )
        nunca_card = cards.get("nunca_paredao")
        if (expected_nunca_items or expected_nunca_exited) and nunca_card is None:
            _issue(
                issues,
                "nunca_paredao_missing_from_payload",
                "critical",
                "derived",
                "nunca_paredao",
                "Expected nunca_paredao card is missing from index payload",
            )
        elif nunca_card is not None:
            actual_active = {item["name"]: item for item in nunca_card.get("items_all", [])}
            actual_exited = {item["name"]: item for item in nunca_card.get("items_exited", [])}
            for item in expected_nunca_items:
                actual = actual_active.get(item["name"])
                if not actual:
                    _issue(issues, "nunca_paredao_exposure_mismatch", "critical", "derived", item["name"], "Missing active nunca_paredao item")
                    continue
                for field in ("votes_total", "votes_recent", "votes_available", "available", "protected", "last_voted_paredao"):
                    if actual.get(field, 0) != item.get(field, 0):
                        _issue(issues, "nunca_paredao_exposure_mismatch", "critical", "derived", item["name"], f"Active nunca_paredao mismatch on {field}", {"actual": actual.get(field, 0), "expected": item.get(field, 0)})
            for item in expected_nunca_exited:
                actual = actual_exited.get(item["name"])
                if not actual:
                    _issue(issues, "nunca_paredao_exposure_mismatch", "critical", "derived", item["name"], "Missing exited nunca_paredao item")
                    continue
                for field in ("votes_total", "votes_recent", "votes_available", "available", "protected", "last_voted_paredao"):
                    if actual.get(field, 0) != item.get(field, 0):
                        _issue(issues, "nunca_paredao_exposure_mismatch", "critical", "derived", item["name"], f"Exited nunca_paredao mismatch on {field}", {"actual": actual.get(field, 0), "expected": item.get(field, 0)})

    if validation is None:
        _issue(issues, "missing_derived_artifact", "critical", "derived", "data/derived/validation.json", "Expected derived artifact is missing")
    if manual_audit is None:
        _issue(issues, "missing_derived_artifact", "critical", "derived", "data/derived/manual_events_audit.json", "Expected derived artifact is missing")
    elif (manual_audit.get("issues_count") or 0) > 0:
        _issue(
            issues,
            "manual_events_audit_failed",
            "critical",
            "derived",
            "data/derived/manual_events_audit.json",
            "manual_events_audit.json reports issues",
            {
                "issues_count": manual_audit.get("issues_count", 0),
                "issues": manual_audit.get("issues", {}),
            },
        )

    severity = _severity_counts(issues)
    return {
        "_metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "audit_version": AUDIT_VERSION,
        },
        "summary": {
            "checks_run": checks_run,
            "critical_count": severity["critical"],
            "warning_count": severity["warning"],
            "info_count": severity["info"],
        },
        "issues": issues,
    }


def write_integrity_audit(report: dict[str, Any], out_path: Path = OUT_PATH) -> bool:
    content = {
        "summary": report["summary"],
        "issues": report["issues"],
        "audit_version": report["_metadata"]["audit_version"],
    }
    content_hash = stable_json_hash(content)
    previous = read_json_if_exists(out_path)
    previous_hash = (previous or {}).get("_metadata", {}).get("content_hash")
    if previous_hash == content_hash:
        return False
    payload = {
        "_metadata": {
            "generated_at": report["_metadata"]["generated_at"],
            "content_hash": content_hash,
            "audit_version": report["_metadata"]["audit_version"],
        },
        "summary": report["summary"],
        "issues": report["issues"],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def exit_code_for_report(report: dict[str, Any], *, fail_on: str) -> int:
    if fail_on == "critical" and report["summary"]["critical_count"] > 0:
        return 1
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fail-on", choices=("none", "critical"), default="none")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = build_integrity_audit(ROOT)
    write_integrity_audit(report, OUT_PATH)
    summary = report["summary"]
    print(
        "Integrity audit:"
        f" {summary['critical_count']} critical,"
        f" {summary['warning_count']} warning,"
        f" {summary['info_count']} info"
    )
    return exit_code_for_report(report, fail_on=args.fail_on)


if __name__ == "__main__":
    raise SystemExit(main())
