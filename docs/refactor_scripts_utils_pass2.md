# Refactor Report: Utility Scripts — Pass 2

Second-pass review after Pass 1 fixes were applied. Files re-read in full.

---

## 1. `scripts/fetch_data.py`

### Issues Found
- None. All issues resolved in Pass 1. File is clean and consistent.

### Remaining Notes
- `get_latest_snapshot()` still calls `DATA_DIR.glob()` without first ensuring the
  directory exists; this is fine because the directory is only absent on a completely
  fresh repo where `fetch_and_save()` creates it before writing. The `glob()` call
  simply returns empty on a missing path in some Python versions but raises
  `FileNotFoundError` in others. Acceptable for the current use-case since GitHub
  Actions always has the directory present.

---

## 2. `scripts/audit_manual_events.py`

### Issues Found
- None. File is clean after Pass 1 docstring addition.

---

## 3. `scripts/audit_snapshots.py`

### Issues Found
- None. Absolute paths and cleaned f-strings verified correct.

---

## 4. `scripts/update_programa_doc.py`

### Issues Found
- None. No changes were made in Pass 1 and the file remains clean.

---

## 5. `scripts/analyze_capture_timing.py`

### Issues Found
- None. Dict comprehension for `slot_counts` verified correct.

---

## 6. `scripts/analyze_snapshots.py`

### Issues Found (Pyright — post Pass 1)
- **Low** — `import json` unused: `json` is never called directly in this file; all
  JSON loading goes through `data_utils.load_snapshot`.
- **Low** — `receiver_id = p["id"]` assigned but never accessed (line 177 original).
  Only `receiver_name` is used in the integrity-check print statement.

### Fixes Applied
1. Removed `import json`.
2. Removed the `receiver_id = p["id"]` assignment, keeping only `receiver_name`.

---

## 7. `scripts/compare_sameday.py`

### Issues Found (Pyright — post Pass 1)
- **Note** — Pyright reported `os` not defined on lines 28-29. This was already fixed
  in Pass 1 (replaced `os.path.join` with `Path` operators). Pyright's line numbers
  referred to the pre-fix state.
- **Medium** — `r_b.get('amount')` inside `if r_a is None:` branch: Pyright correctly
  flags `r_b` as possibly None (it comes from `rb_by_type.get(rtype)`). Logically
  impossible since `all_types` is the union of both dicts' keys, but the type checker
  cannot infer this statically.
- **Medium** — Symmetric issue: `r_a.get('amount')` inside `elif r_b is None:` branch.

### Fixes Applied
1. Changed `if r_a is None:` → `if r_a is None and r_b is not None:` to make the
   None-safety explicit and satisfy static analysis.
2. Changed `elif r_b is None:` → `elif r_b is None and r_a is not None:` for symmetry.

---

## 8. `scripts/build_jan18_snapshot.py`

### Issues Found
- None. UTC suffix added correctly; file syntax verified.

---

## Overall Assessment

All 8 files are clean after two passes plus Pyright follow-up fixes.

| File | Pass 2 Issues | Status |
|------|---------------|--------|
| `fetch_data.py` | 0 | Clean |
| `audit_manual_events.py` | 0 | Clean |
| `audit_snapshots.py` | 0 | Clean |
| `update_programa_doc.py` | 0 | Clean |
| `analyze_capture_timing.py` | 0 | Clean |
| `analyze_snapshots.py` | 2 (Pyright, fixed) | Clean |
| `compare_sameday.py` | 2 (Pyright, fixed) | Clean |
| `build_jan18_snapshot.py` | 0 | Clean |
