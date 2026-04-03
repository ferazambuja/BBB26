from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from audit_data_integrity import (
    build_integrity_audit,
    exit_code_for_report,
)
from builders.paredao_exposure import (
    build_nunca_paredao_items,
    build_participant_windows,
    compute_house_vote_exposure,
)


def _write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_snapshot(names: list[str]) -> dict:
    return {
        "participants": [{"name": name, "group": "Pipoca", "avatar": f"https://img/{name}.png"} for name in names]
    }


def _make_repo(tmp_path: Path) -> Path:
    root = tmp_path
    data = root / "data"
    derived = data / "derived"
    snapshots = data / "snapshots"
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    snapshots.mkdir(parents=True, exist_ok=True)
    derived.mkdir(parents=True, exist_ok=True)

    names = ["Ana", "Breno", "Caio"]
    _write_json(data / "latest.json", _make_snapshot(names))
    _write_json(snapshots / "2026-01-13.json", _make_snapshot(names))
    _write_json(snapshots / "2026-01-20.json", _make_snapshot(names))
    _write_json(data / "manual_events.json", {"participants": {}})
    _write_json(data / "provas.json", {"provas": []})
    _write_json(
        data / "paredoes.json",
        {
            "paredoes": [
                {
                    "numero": 1,
                    "status": "finalizado",
                    "data": "2026-01-19",
                    "data_formacao": "2026-01-18",
                    "titulo": "P1",
                    "indicados_finais": [{"nome": "Caio", "como": "Líder"}],
                    "votos_casa": {"Ana": "Breno"},
                    "resultado": {"eliminado": "Caio"},
                    "fontes": [{"url": "https://example.com", "arquivo": "docs/source.md"}],
                    "votos_resumo": {"Breno": 1},
                    "formacao": {"lider": "Ana", "indicado_lider": "Caio"},
                }
            ]
        },
    )
    (docs / "source.md").write_text("source", encoding="utf-8")
    participants_index = {
        "participants": [
            {"name": "Ana", "grupo": "Pipoca", "avatar": "https://img/Ana.png", "first_seen": "2026-01-13", "last_seen": "2026-01-20", "active": True},
            {"name": "Breno", "grupo": "Pipoca", "avatar": "https://img/Breno.png", "first_seen": "2026-01-13", "last_seen": "2026-01-20", "active": True},
            {"name": "Caio", "grupo": "Pipoca", "avatar": "https://img/Caio.png", "first_seen": "2026-01-13", "last_seen": "2026-01-20", "active": True},
        ]
    }
    _write_json(
        derived / "participants_index.json",
        participants_index,
    )
    windows = build_participant_windows(participants_index, active_names=set(names), manual_events={})
    paredoes_list = json.loads((data / "paredoes.json").read_text(encoding="utf-8"))["paredoes"]
    exposure = compute_house_vote_exposure(paredoes_list, windows)
    nunca_items, nunca_exited = build_nunca_paredao_items(
        {"active_set": set(names), "manual_events": {}, "participants_index": participants_index},
        paredoes_list,
        exposure,
    )
    _write_json(
        derived / "index_data.json",
        {
            "active_names": names,
            "member_of": {name: "Pipoca" for name in names},
            "avatars": {name: f"https://img/{name}.png" for name in names},
            "highlights": {
                "cards": [
                    {
                        "type": "blindados",
                        "items_all": [
                            {
                                "name": name,
                                "votes_total": exposure[name]["votes_total"],
                                "votes_available": exposure[name]["votes_available"],
                                "voted_paredoes": exposure[name]["voted_paredoes"],
                                "available": exposure[name]["available"],
                                "protected": exposure[name]["protected"],
                                "last_voted_paredao": exposure[name]["last_voted_paredao"],
                            }
                            for name in names
                        ],
                    },
                    {
                        "type": "visados",
                        "items_all": [
                            {
                                "name": name,
                                "votes_total": exposure[name]["votes_total"],
                                "votes_recent": exposure[name]["votes_recent"],
                                "votes_available": exposure[name]["votes_available"],
                                "available": exposure[name]["available"],
                                "protected": exposure[name]["protected"],
                                "last_voted_paredao": exposure[name]["last_voted_paredao"],
                            }
                            for name in names
                        ],
                    },
                    {
                        "type": "nunca_paredao",
                        "items_all": nunca_items,
                        "items_exited": nunca_exited,
                    },
                ]
            },
            "paredao_exposure": {"stats": {"metrics": {}, "facts": {}}},
        },
    )
    _write_json(derived / "validation.json", {"warnings": []})
    _write_json(derived / "manual_events_audit.json", {"issues_count": 0})
    _write_json(derived / "paredao_exposure_stats.json", {"_metadata": {"content_hash": "x"}, "stats": {"metrics": {}, "facts": {}}})
    return root


def _issue_ids(report: dict) -> set[str]:
    return {issue["id"] for issue in report["issues"]}


def test_report_schema_and_summary(tmp_path: Path):
    root = _make_repo(tmp_path)
    report = build_integrity_audit(root)
    assert set(report.keys()) == {"_metadata", "summary", "issues"}
    assert set(report["summary"].keys()) == {"checks_run", "critical_count", "warning_count", "info_count"}
    assert report["summary"]["critical_count"] == 0


def test_detects_latest_snapshot_mismatch(tmp_path: Path):
    root = _make_repo(tmp_path)
    _write_json(root / "data" / "latest.json", _make_snapshot(["Ana", "Breno"]))
    report = build_integrity_audit(root)
    assert "snapshot_latest_participant_mismatch" in _issue_ids(report)


def test_detects_duplicate_names_in_any_snapshot(tmp_path: Path):
    root = _make_repo(tmp_path)
    _write_json(root / "data" / "snapshots" / "2026-01-15.json", _make_snapshot(["Ana", "Ana", "Breno"]))
    report = build_integrity_audit(root)
    duplicate_issues = [issue for issue in report["issues"] if issue["id"] == "duplicate_participant_names"]
    assert duplicate_issues
    assert any(issue["subject"].endswith("2026-01-15.json") for issue in duplicate_issues)


def test_detects_presence_window_mismatch(tmp_path: Path):
    root = _make_repo(tmp_path)
    _write_json(
        root / "data" / "derived" / "participants_index.json",
        {
            "participants": [
                {"name": "Ana", "grupo": "Pipoca", "avatar": "https://img/Ana.png", "first_seen": "2026-02-01", "last_seen": "9999-12-31", "active": True},
                {"name": "Breno", "grupo": "Pipoca", "avatar": "https://img/Breno.png", "first_seen": "2026-01-13", "last_seen": "9999-12-31", "active": True},
                {"name": "Caio", "grupo": "Pipoca", "avatar": "https://img/Caio.png", "first_seen": "2026-01-13", "last_seen": "9999-12-31", "active": True},
            ]
        },
    )
    report = build_integrity_audit(root)
    assert "participants_index_window_mismatch" in _issue_ids(report)


def test_detects_votos_resumo_mismatch(tmp_path: Path):
    root = _make_repo(tmp_path)
    payload = json.loads((root / "data" / "paredoes.json").read_text())
    payload["paredoes"][0]["votos_resumo"] = {"Caio": 1}
    _write_json(root / "data" / "paredoes.json", payload)
    report = build_integrity_audit(root)
    assert "paredao_votos_resumo_mismatch" in _issue_ids(report)


def test_detects_invalid_fonte_arquivo(tmp_path: Path):
    root = _make_repo(tmp_path)
    payload = json.loads((root / "data" / "paredoes.json").read_text())
    payload["paredoes"][0]["fontes"][0]["arquivo"] = "docs/missing.md"
    _write_json(root / "data" / "paredoes.json", payload)
    report = build_integrity_audit(root)
    assert "missing_source_file" in _issue_ids(report)


def test_detects_presence_window_violation(tmp_path: Path):
    root = _make_repo(tmp_path)
    payload = json.loads((root / "data" / "paredoes.json").read_text())
    payload["paredoes"][0]["votos_casa"] = {"Ana": "Fantasma"}
    _write_json(root / "data" / "paredoes.json", payload)
    report = build_integrity_audit(root)
    assert "paredao_vote_target_missing_from_windows" in _issue_ids(report)


def test_detects_impedidos_votar_contradiction(tmp_path: Path):
    root = _make_repo(tmp_path)
    payload = json.loads((root / "data" / "paredoes.json").read_text())
    payload["paredoes"][0]["impedidos_votar"] = ["Ana"]
    payload["paredoes"][0]["votos_casa"] = {"Ana": "Breno"}
    _write_json(root / "data" / "paredoes.json", payload)
    report = build_integrity_audit(root)
    assert "paredao_impedido_votou" in _issue_ids(report)


def test_propagates_manual_events_audit_issues(tmp_path: Path):
    root = _make_repo(tmp_path)
    _write_json(
        root / "data" / "derived" / "manual_events_audit.json",
        {"issues_count": 5, "issues": {"missing_sources": 5}},
    )
    report = build_integrity_audit(root)
    issue = next(issue for issue in report["issues"] if issue["id"] == "manual_events_audit_failed")
    assert issue["severity"] == "critical"
    assert issue["details"]["issues_count"] == 5


def test_missing_derived_artifact_is_critical(tmp_path: Path):
    root = _make_repo(tmp_path)
    (root / "data" / "derived" / "index_data.json").unlink()
    report = build_integrity_audit(root)
    issue = next(issue for issue in report["issues"] if issue["id"] == "missing_derived_artifact")
    assert issue["severity"] == "critical"


def test_fail_on_critical_exit_code(tmp_path: Path):
    root = _make_repo(tmp_path)
    (root / "data" / "derived" / "index_data.json").unlink()
    report = build_integrity_audit(root)
    assert exit_code_for_report(report, fail_on="critical") == 1
    assert exit_code_for_report(report, fail_on="none") == 0
