# Refactor Report: Utility Scripts — Pass 1

Files processed: `fetch_data.py`, `audit_manual_events.py`, `audit_snapshots.py`,
`update_programa_doc.py`, `analyze_capture_timing.py`, `analyze_snapshots.py`,
`compare_sameday.py`, `build_jan18_snapshot.py`

---

## 1. `scripts/fetch_data.py`

### Issues Found
- **Medium** — Redundant `DATA_DIR.mkdir(parents=True, exist_ok=True)` call inside
  `get_latest_snapshot()`. The directory is created again in `fetch_and_save()` before
  writing; the one in the reader is never needed.
- **Medium** — `datetime.now(timezone.utc)` called twice in `fetch_and_save()`: once
  for the filename timestamp and again for `captured_at` in metadata. These can differ
  by a few milliseconds, introducing a subtle inconsistency.
- **Low** — `change_types if latest_data else ["initial"]` condition in the metadata
  dict was redundant: by the time we reach the save block, `change_types` is always
  `["initial"]` when `latest_data` is falsy (set unconditionally in the else branch).

### Fixes Applied
1. Removed `DATA_DIR.mkdir()` from `get_latest_snapshot()`.
2. Captured `datetime.now(timezone.utc)` once into `now_utc`, used for both the
   filename and `captured_at`.
3. Simplified `"change_types": change_types if latest_data else ["initial"]` →
   `"change_types": change_types`.

---

## 2. `scripts/audit_manual_events.py`

### Issues Found
- **Low** — Missing module-level docstring (all other scripts in the project have one).

### Fixes Applied
1. Added a concise module docstring describing the script's purpose and outputs.

---

## 3. `scripts/audit_snapshots.py`

### Issues Found
- **High** — Relative `Path("data/snapshots")` etc. in `main()` break when the script
  is run from any directory other than the project root. All other scripts use
  `Path(__file__).resolve().parent.parent` for absolute paths.
- **Low** — Several `print(f"=" * 70)` used an f-string prefix with no interpolation
  (unnecessary).

### Fixes Applied
1. Added `ROOT = Path(__file__).resolve().parent.parent` at module level.
2. Replaced all three `Path("...")` source paths with `ROOT / "data" / "snapshots"`,
   `ROOT / "_legacy" / "archive_duplicates"`, and `ROOT / "_audit" / "git_recovered"`.
3. Removed spurious `f` prefix from constant string prints.

---

## 4. `scripts/update_programa_doc.py`

### Issues Found
- No issues. The file is clean, well-structured, and consistent with project conventions.

### Fixes Applied
- None.

---

## 5. `scripts/analyze_capture_timing.py`

### Issues Found
- **Low** — `slot_counts` was initialized with a two-statement loop (create empty dict,
  then loop to set each key to 0) instead of a single dict comprehension.

### Fixes Applied
1. Replaced the loop with `slot_counts = {name: 0 for name, _, _ in SLOTS}`.

---

## 6. `scripts/analyze_snapshots.py`

### Issues Found
- **Low** — `load_snapshot as _load_snapshot` imported with a private-style underscore
  alias that shadowed the local wrapper's name poorly. The local function is named
  `load_snapshot` but the import is `_load_snapshot` — renaming to
  `_data_utils_load_snapshot` makes the wrapper intent clearer.
- **Low** — Missing blank line between `load_snapshot()` and `get_sorted_snapshots()`
  (PEP 8: two blank lines between top-level definitions).
- **Low** — Missing blank line between `get_sorted_snapshots()` and `main()`.

### Fixes Applied
1. Renamed import alias to `_data_utils_load_snapshot` for clarity.
2. Added two blank lines between top-level function definitions.

---

## 7. `scripts/compare_sameday.py`

### Issues Found
- **Critical** — `r['reactionType']` used to key reactions on lines 100–101, but the
  API snapshot format uses `'label'` as the key (confirmed in CLAUDE.md, data_utils.py,
  and every other script). This would raise `KeyError` when the diff-printing branch
  is reached.
- **High** — `r.get('givers', [])` used to get givers list, but the API field is
  `'participants'` (not `'givers'`). This would silently produce empty giver lists.
- **Medium** — Used `import os` and `os.path.join` / `os.path.dirname` for path
  handling; all other scripts use `pathlib.Path`.
- **Low** — Missing `encoding="utf-8"` in `open()` in `load_participants()`.
- **Low** — Several `print(f"\n--- LABEL ---")` used f-string prefix without any
  interpolation.
- **Low** — Missing blank lines between top-level function definitions (PEP 8).

### Fixes Applied
1. Replaced `r['reactionType']` with `r['label']` in both `ra_by_type` and
   `rb_by_type` dicts.
2. Replaced `r.get('givers', [])` with `r.get('participants', [])`.
3. Removed `import os`, added `from pathlib import Path`.
4. Changed `SNAPSHOTS_DIR` from `os.path.join(...)` to
   `Path(__file__).resolve().parent.parent / "data" / "snapshots"`.
5. Updated `compare_pair()` path construction from `os.path.join()` to `SNAPSHOTS_DIR / file`.
6. Added `encoding="utf-8"` to `open()` in `load_participants()`.
7. Removed unnecessary `f` prefix from constant string prints.
8. Added two blank lines between top-level function definitions.

---

## 8. `scripts/build_jan18_snapshot.py`

### Issues Found
- **Low** — `"captured_at": "2026-01-18T12:00:00"` is a naive ISO timestamp (no
  timezone suffix). CLAUDE.md specifies that `_metadata.captured_at` must use the
  `+00:00` UTC suffix format for consistency across all snapshots.

### Fixes Applied
1. Changed `"2026-01-18T12:00:00"` → `"2026-01-18T12:00:00+00:00"`.

---

## Summary

| File | Severity | Issues | Fixed |
|------|----------|--------|-------|
| `fetch_data.py` | Medium/Low | 3 | 3 |
| `audit_manual_events.py` | Low | 1 | 1 |
| `audit_snapshots.py` | High/Low | 2 | 2 |
| `update_programa_doc.py` | — | 0 | — |
| `analyze_capture_timing.py` | Low | 1 | 1 |
| `analyze_snapshots.py` | Low | 3 | 3 |
| `compare_sameday.py` | Critical/High/Medium/Low | 6 | 6 |
| `build_jan18_snapshot.py` | Low | 1 | 1 |

All 8 files pass `python3 -m py_compile` after fixes.
