#!/usr/bin/env python3
"""Local data polling scheduler for BBB26.

Fetches API data at true 15-minute intervals (or custom), optionally
builds derived data, commits, pushes, and triggers GitHub Actions deploy.

Why: GitHub Actions cron is unreliable (measured avg 67-min gaps instead
of the configured 15 min). This script runs on a dedicated machine
(Proxmox LXC or similar) for reliable polling.

Usage:
    # Preview schedule without executing
    python scripts/schedule_data_fetch.py --dry-run

    # Single immediate poll (useful for testing)
    python scripts/schedule_data_fetch.py --once --run-now

    # Full daemon: poll every 15 min, build + push + trigger deploy
    python scripts/schedule_data_fetch.py --build --trigger-deploy

    # Called by systemd timer (single shot)
    python scripts/schedule_data_fetch.py --once --build --trigger-deploy
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
FETCH_SCRIPT = REPO_ROOT / "scripts" / "fetch_data.py"
VOTALHADA_SCRIPT = REPO_ROOT / "scripts" / "fetch_votalhada_images.py"
PAREDOES_JSON = REPO_ROOT / "data" / "paredoes.json"
VOTALHADA_CODEX_EXTRACT = REPO_ROOT / "deploy" / "votalhada_codex_extract.sh"
VOTALHADA_VALIDATE_APPLY = REPO_ROOT / "deploy" / "votalhada_validate_apply.py"
VOTALHADA_CLAUDE_VERIFY = REPO_ROOT / "deploy" / "votalhada_claude_verify.sh"
# Legacy (kept for reference)
VOTALHADA_CLAUDE_SCRIPT = REPO_ROOT / "deploy" / "votalhada_claude_update.sh"
VOTALHADA_CODEX_VERIFY = REPO_ROOT / "deploy" / "votalhada_codex_verify.sh"


def _format_dt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S %Z")


def _format_delta(total_seconds: float) -> str:
    seconds = max(0, int(total_seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}h {minutes:02d}m {secs:02d}s"


def _next_slot(now_utc: datetime, interval_minutes: int) -> datetime:
    """Return the next aligned slot (e.g., :00, :15, :30, :45 for 15-min)."""
    minute = now_utc.minute
    next_min = ((minute // interval_minutes) + 1) * interval_minutes
    slot = now_utc.replace(second=0, microsecond=0)
    slot += timedelta(minutes=next_min - minute)
    return slot


def _has_git_changes(*paths: str) -> bool:
    """Check if any of the given paths have uncommitted changes."""
    result = subprocess.run(
        ["git", "status", "--porcelain", "--"] + list(paths),
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    return bool(result.stdout.strip())


def _run_cmd(cmd: list[str], label: str) -> int:
    """Run a command, log output, return exit code."""
    now = datetime.now(timezone.utc).astimezone()
    print(f"\n[{_format_dt(now)}] {label}:")
    print("  " + " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    if proc.stdout:
        for line in proc.stdout.splitlines():
            print(f"  [{label}] {line}")
    if proc.stderr:
        for line in proc.stderr.splitlines():
            print(f"  [{label}:err] {line}")
    if proc.returncode != 0:
        print(f"  [{label}] FAILED (exit {proc.returncode})")
    return proc.returncode


def _get_active_paredao() -> int | None:
    """Return the numero of the active paredão (em_andamento), or None."""
    if not PAREDOES_JSON.exists():
        return None
    try:
        data = json.loads(PAREDOES_JSON.read_text(encoding="utf-8"))
        for p in data.get("paredoes", []):
            if p.get("status") == "em_andamento":
                return p["numero"]
    except Exception:
        pass
    return None


def _get_votalhada_folder(paredao_num: int) -> str:
    """Return the votalhada folder name for a paredão (e.g., '2026_03_22')."""
    if not PAREDOES_JSON.exists():
        return ""
    try:
        data = json.loads(PAREDOES_JSON.read_text(encoding="utf-8"))
        for p in data.get("paredoes", []):
            if p["numero"] == paredao_num:
                date_str = p.get("data_formacao") or p.get("data", "")
                return date_str.replace("-", "_")
    except Exception:
        pass
    return ""


POLLS_JSON = REPO_ROOT / "data" / "votalhada" / "polls.json"


def _bootstrap_polls_entry(paredao_num: int) -> bool:
    """Create a skeleton polls.json entry for a paredão if one doesn't exist.

    Reads paredoes.json, calls get_final_nominees() to get the actual nominees
    (after Bate e Volta removal), and writes a skeleton entry with empty
    consolidado/plataformas/serie_temporal.

    Returns True if a new entry was created, False if it already existed.
    """
    # Load existing polls.json (or create structure)
    if POLLS_JSON.exists():
        try:
            polls_data = json.loads(POLLS_JSON.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"[bootstrap] polls.json has invalid JSON: {e}")
            return False
    else:
        polls_data = {
            "_description": "Poll aggregation data from Votalhada",
            "_source": "votalhada.blogspot.com",
            "_methodology": "Aggregates polls from multiple platforms (Sites, YouTube, Twitter, Instagram) collected before each elimination",
            "_last_updated": "",
            "paredoes": [],
        }

    # Check if entry already exists
    for entry in polls_data.get("paredoes", []):
        if entry.get("numero") == paredao_num:
            return False

    # Read paredoes.json to get nominees
    if not PAREDOES_JSON.exists():
        print(f"[bootstrap] paredoes.json not found — cannot bootstrap P{paredao_num}")
        return False

    paredoes_data = json.loads(PAREDOES_JSON.read_text(encoding="utf-8"))
    paredao_entry = None
    for p in paredoes_data.get("paredoes", []):
        if p["numero"] == paredao_num:
            paredao_entry = p
            break

    if paredao_entry is None:
        print(f"[bootstrap] P{paredao_num} not found in paredoes.json")
        return False

    # Import get_final_nominees from data_utils
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from data_utils import get_final_nominees

    nominees = get_final_nominees(paredao_entry)
    if not nominees:
        print(f"[bootstrap] P{paredao_num} has no nominees (indicados_finais empty or all escaped)")
        return False

    data_paredao = paredao_entry.get("data", "")

    skeleton = {
        "numero": paredao_num,
        "data_paredao": data_paredao,
        "participantes": nominees,
        "consolidado": {},
        "plataformas": {},
        "serie_temporal": [],
    }

    polls_data["paredoes"].append(skeleton)
    POLLS_JSON.parent.mkdir(parents=True, exist_ok=True)
    POLLS_JSON.write_text(
        json.dumps(polls_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[bootstrap] Created polls.json skeleton for P{paredao_num}: {nominees}")
    return True


def _votalhada_capture_complete(paredao_num: int) -> bool:
    """Check if the final Votalhada capture (21:00 on elimination day) is already recorded.

    Votalhada's last update is at 21:00 BRT on elimination night.
    Once we have a serie_temporal row ending in '21:00' on the paredão date,
    there's nothing more to fetch.
    """
    if not POLLS_JSON.exists():
        return False
    try:
        polls = json.loads(POLLS_JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False

    for entry in polls.get("paredoes", []):
        if entry.get("numero") != paredao_num:
            continue
        paredao_date = entry.get("data_paredao", "")  # e.g. "2026-03-24"
        if not paredao_date:
            return False
        # Parse date to DD/mmm format used in serie_temporal
        parts = paredao_date.split("-")
        if len(parts) != 3:
            return False
        day = parts[2].lstrip("0")
        month_map = {"01": "jan", "02": "fev", "03": "mar", "04": "abr", "05": "mai",
                     "06": "jun", "07": "jul", "08": "ago", "09": "set", "10": "out",
                     "11": "nov", "12": "dez"}
        mon = month_map.get(parts[1], "")
        target_hora = f"{day}/{mon} 21:00"  # e.g. "24/mar 21:00"

        series = entry.get("serie_temporal", [])
        return any(r.get("hora") == target_hora for r in series)

    return False


def _fetch_votalhada(paredao_num: int) -> bool:
    """Fetch Votalhada images for the given paredão. Returns True if new images saved."""
    rc = _run_cmd(
        [sys.executable, str(VOTALHADA_SCRIPT),
         "--paredao", str(paredao_num),
         "--dedupe", "size+sha256"],
        "votalhada-fetch",
    )
    if rc != 0:
        print(f"[votalhada] Fetch failed for P{paredao_num}.")
        return False
    return _has_git_changes("data/votalhada/")


def _poll_once(args: argparse.Namespace) -> dict:
    """Run one poll cycle. Returns status dict."""
    result = {"fetched": False, "data_changed": False, "built": False, "pushed": False, "deployed": False,
              "votalhada_fetched": False}

    # 1. Fetch
    rc = _run_cmd([sys.executable, str(FETCH_SCRIPT), "--fetch-only"], "fetch")
    result["fetched"] = rc == 0
    if rc != 0:
        print("[poll] Fetch failed, skipping rest of cycle.")
        return result

    # 2. Check for new API data
    if _has_git_changes("data/snapshots/", "data/latest.json"):
        result["data_changed"] = True
        print("[poll] New API data detected!")
    else:
        print("[poll] No API data changes — hash unchanged.")

    # 2b. Votalhada image fetch (optional, only when paredão is active)
    if args.votalhada:
        paredao_num = _get_active_paredao()
        if paredao_num and _votalhada_capture_complete(paredao_num):
            print(f"[poll] P{paredao_num} Votalhada final capture (21:00) already recorded — skipping.")
        elif paredao_num:
            # Bootstrap polls.json entry if it doesn't exist yet
            if _bootstrap_polls_entry(paredao_num):
                result["data_changed"] = True
            print(f"[poll] Active paredão P{paredao_num} — fetching Votalhada images.")
            if _fetch_votalhada(paredao_num):
                result["votalhada_fetched"] = True
                result["data_changed"] = True
                print(f"[poll] New Votalhada images for P{paredao_num}!")
            else:
                print("[poll] No new Votalhada images (unchanged or unavailable).")
        else:
            print("[poll] No active paredão — skipping Votalhada fetch.")

    # 2c. Auto-update polls.json: Codex extracts → validate → Claude verifies → apply
    if args.votalhada_auto_update and result["votalhada_fetched"]:
        paredao_num = _get_active_paredao()
        images_dir = str(REPO_ROOT / "data" / "votalhada" / _get_votalhada_folder(paredao_num)) if paredao_num else ""

        if paredao_num and VOTALHADA_CODEX_EXTRACT.exists():
            # Step 1: Codex extracts values from card images
            rc = _run_cmd(
                ["bash", str(VOTALHADA_CODEX_EXTRACT), str(paredao_num), images_dir],
                "codex-extract",
            )
            if rc != 0:
                print("[poll] Codex extraction failed.")
            else:
                # Step 2: Deterministic validation
                vrc = _run_cmd(
                    [sys.executable, str(VOTALHADA_VALIDATE_APPLY), str(paredao_num)],
                    "validate",
                )
                if vrc == 2:
                    print("[poll] Validation FAILED — not applying.")
                elif vrc == 0:
                    # Step 3: Claude verifies Codex's extraction (optional)
                    claude_ok = True
                    if VOTALHADA_CLAUDE_VERIFY.exists():
                        print("[poll] Claude verifying Codex extraction...")
                        crc = _run_cmd(
                            ["bash", str(VOTALHADA_CLAUDE_VERIFY), str(paredao_num), images_dir],
                            "claude-verify",
                        )
                        if crc == 2:
                            claude_ok = False
                            print("[poll] Claude DISAGREES with Codex — not applying.")
                        elif crc != 0:
                            print("[poll] Claude verify failed (error) — proceeding with Codex data.")

                    if claude_ok:
                        # Step 4: Apply validated extraction
                        arc = _run_cmd(
                            [sys.executable, str(VOTALHADA_VALIDATE_APPLY), str(paredao_num), "--apply"],
                            "apply",
                        )
                        if arc == 0 and _has_git_changes("data/votalhada/polls.json"):
                            result["votalhada_updated"] = True
                            print(f"[poll] polls.json updated for P{paredao_num} (Codex→validate→apply)!")
                        else:
                            print("[poll] Apply produced no changes.")
                    else:
                        print("[poll] Skipping apply due to Claude disagreement.")
        elif paredao_num:
            # Fallback: use legacy Claude-as-extractor if Codex scripts not available
            if VOTALHADA_CLAUDE_SCRIPT.exists():
                rc = _run_cmd(
                    ["bash", str(VOTALHADA_CLAUDE_SCRIPT), str(paredao_num), images_dir],
                    "votalhada-claude-legacy",
                )
                if rc == 0 and _has_git_changes("data/votalhada/polls.json"):
                    result["votalhada_updated"] = True
                    print(f"[poll] polls.json updated via Claude (legacy) for P{paredao_num}.")

    if not result["data_changed"]:
        return result

    # 3. Build derived data (optional)
    if args.build:
        rc = _run_cmd(
            [sys.executable, str(REPO_ROOT / "scripts" / "build_derived_data.py")],
            "build",
        )
        result["built"] = rc == 0
        if rc != 0:
            print("[poll] Build failed — committing snapshot only.")

    # 4. Git commit + push
    # Stash any unexpected unstaged changes before pull (safety net for revert leftovers)
    _run_cmd(["git", "stash", "--quiet"], "git-stash")
    _run_cmd(["git", "pull", "--rebase", "origin", "main"], "git-pull")
    _run_cmd(["git", "stash", "pop", "--quiet"], "git-stash-pop")  # restore if anything was stashed

    # Stage files
    add_paths = ["data/snapshots/", "data/latest.json"]
    if result["built"]:
        add_paths.extend(["data/derived/", "docs/MANUAL_EVENTS_AUDIT.md", "docs/SCORING_AND_INDEXES.md"])
    if result["votalhada_fetched"]:
        add_paths.append("data/votalhada/")
    if result.get("votalhada_updated"):
        add_paths.append("data/votalhada/polls.json")
    _run_cmd(["git", "add"] + add_paths, "git-add")

    if not _has_git_changes():
        print("[poll] Nothing to commit after staging.")
        return result

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
    msg_parts = []
    if result.get("data_changed") and _has_git_changes("data/snapshots/"):
        msg_parts.append(f"snapshot {timestamp} UTC")
    if result["votalhada_fetched"] or result.get("votalhada_updated"):
        paredao_num = _get_active_paredao()
        label = "votalhada P{} fetch".format(paredao_num)
        if result.get("votalhada_updated"):
            label += " + polls.json update"
        msg_parts.append(label)
    msg = "data: " + " + ".join(msg_parts) if msg_parts else f"data: snapshot {timestamp} UTC"
    _run_cmd(["git", "commit", "-m", msg], "git-commit")
    rc = _run_cmd(["git", "push", "origin", "main"], "git-push")
    result["pushed"] = rc == 0

    if rc != 0:
        # Retry once after rebase
        _run_cmd(["git", "pull", "--rebase", "origin", "main"], "git-pull-retry")
        rc = _run_cmd(["git", "push", "origin", "main"], "git-push-retry")
        result["pushed"] = rc == 0

    # 5. Trigger deploy (optional)
    if result["pushed"] and args.trigger_deploy:
        rc = _run_cmd(["gh", "workflow", "run", "daily-update.yml"], "deploy")
        result["deployed"] = rc == 0

    return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Local BBB26 data polling scheduler.",
    )
    parser.add_argument(
        "--interval", type=int, default=15,
        help="Minutes between polls (default: 15). Aligns to clock slots.",
    )
    parser.add_argument(
        "--build", action="store_true",
        help="Run build_derived_data.py after detecting new data.",
    )
    parser.add_argument(
        "--trigger-deploy", action="store_true",
        help="Dispatch daily-update.yml after push (requires gh CLI).",
    )
    parser.add_argument(
        "--votalhada", action="store_true",
        help="Fetch Votalhada poll images for the active paredão (deduped).",
    )
    parser.add_argument(
        "--votalhada-auto-update", action="store_true",
        help="Auto-update polls.json via Claude Code headless when new images are found.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print schedule without executing.",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Run a single poll cycle then exit.",
    )
    parser.add_argument(
        "--run-now", action="store_true",
        help="Poll immediately (skip sleep to next slot).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    print(f"BBB26 data polling scheduler")
    print(f"  interval: {args.interval} min")
    print(f"  build: {args.build}")
    print(f"  votalhada: {args.votalhada}")
    print(f"  trigger-deploy: {args.trigger_deploy}")
    print(f"  repo: {REPO_ROOT}")
    print(f"  now (UTC): {_format_dt(datetime.now(timezone.utc))}")
    print()

    if args.dry_run:
        now = datetime.now(timezone.utc)
        print("Upcoming slots (next 6):")
        slot = now
        for i in range(6):
            slot = _next_slot(slot, args.interval)
            print(f"  {i + 1}. {_format_dt(slot)}")
        print("\n(dry-run — no polling executed)")
        return 0

    cycle = 0
    while True:
        if not args.run_now or cycle > 0:
            now = datetime.now(timezone.utc)
            slot = _next_slot(now, args.interval)
            wait = (slot - now).total_seconds()
            print(f"\n[scheduler] Next poll at {_format_dt(slot)} (sleep {_format_delta(wait)})")
            time.sleep(max(0, wait))

        cycle += 1
        now = datetime.now(timezone.utc)
        print(f"\n{'='*60}")
        print(f"[scheduler] Poll cycle {cycle} at {_format_dt(now)}")
        print(f"{'='*60}")

        result = _poll_once(args)
        status_parts = []
        if result["data_changed"]:
            status_parts.append("NEW DATA")
            if result["built"]:
                status_parts.append("built")
            if result["pushed"]:
                status_parts.append("pushed")
            if result["deployed"]:
                status_parts.append("deploy triggered")
        if result.get("votalhada_fetched"):
            status_parts.append("votalhada images")
        if result.get("votalhada_updated"):
            verified = result.get("votalhada_verified")
            if verified is True:
                status_parts.append("polls.json updated (codex verified)")
            elif verified is False:
                status_parts.append("polls.json REVERTED (codex disagreed)")
            elif verified is None:
                status_parts.append("polls.json updated (codex unavailable)")
            else:
                status_parts.append("polls.json updated")
        if not status_parts:
            status_parts.append("no change")

        print(f"\n[scheduler] Cycle {cycle} done: {' · '.join(status_parts)}")

        if args.once:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
