# Refactor Pass 1 Report — Core Scripts

Generated during the `refactor-clean` session. Covers three files:
- `scripts/data_utils.py`
- `scripts/build_derived_data.py`
- `scripts/build_index_data.py`

---

## `scripts/data_utils.py`

**Severity**: LOW / POLISH

### Changes Applied

1. **`parse_roles`** (line ~1200): Converted list comprehension + loop into a single list-comp. Renamed single-letter variable `l` → `label` (shadows built-in `list`).

2. **`get_nominee_badge`**: Removed dead variable `sufixo` — computed but never used in the return value.

3. **`load_snapshots_full`**: Two `set()` calls wrapping generator expressions converted to set comprehensions `{...}`.

4. **`calculate_poll_accuracy`**: Eliminated two duplicated `round(abs(...), 1)` computations by extracting into a `deltas` dict, removing the repeated subtraction.

5. **`render_cronologia_html`**: Replaced string concatenation (`html += ...` in tight loop) with a `parts = []` / `"".join(parts)` pattern to avoid quadratic string growth.

---

## `scripts/build_derived_data.py`

**Severity**: MEDIUM / LOW

### Changes Applied

1. **Top-level `Counter` import**: Added `Counter` to the existing `from collections import ...` import at the top of the file. Removed four inline `from collections import Counter` statements scattered inside functions (`build_prova_rankings`, `build_cluster_evolution`, `build_game_timeline`, `build_plant_index`).

2. **Inline `datetime` import removed**: `from datetime import datetime` inside `build_cluster_evolution` was removed — `datetime` was already imported at module level.

3. **Duplicate `split_names()` removed**: `build_plant_index` defined its own local `split_names()` inner function that was identical to the module-level one. The inner definition was removed; the function now uses the module-level `split_names`.

4. **`CLUSTER_COLORS` extracted to module level** (~line 150): A `CLUSTER_COLORS` dict was defined inline inside `build_clusters_data`. Since it is a pure constant (no runtime dependencies), it was lifted to module level.

5. **`len(history) == 0` → `not history`**: Anti-pattern `len(x) == 0` changed to idiomatic truthiness check.

---

## `scripts/build_index_data.py`

**Severity**: LOW / POLISH

### Changes Applied

1. **`set(today_mat.keys()) & set(yesterday_mat.keys())`** (line 592): `dict.keys()` returns a `KeysView` which supports set operations directly. Simplified to `today_mat.keys() & yesterday_mat.keys()` — avoids two unnecessary `set()` materializations.

2. **`set(p["name"] for p in snap_parts)`** (line 1149): Generator expression inside `set()` converted to set comprehension `{p["name"] for p in snap_parts}` — idiomatic Python and marginally faster.

---

## Notes

- No business logic was changed in any file.
- All exported constants and functions used by QMD pages were preserved.
- Lazy imports for optional dependencies (`plotly`, `networkx`, `sklearn`, `numpy`) inside functions with `try/except` guards were intentionally left unchanged.
- Syntax verified after changes: all three files import cleanly with `python3 -c "import <module>"`.
