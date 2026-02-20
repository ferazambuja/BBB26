# Refactor Pass 2 Report — Core Scripts

Second-pass review after Pass 1 changes. Covers the same three files. Each file was re-read in full and re-analyzed for issues revealed or overlooked after Pass 1.

---

## `scripts/data_utils.py`

**Severity**: LOW (one Pyright diagnostic)

### Changes Applied

1. **Unused `_target` variable** (line 368, in `patch_missing_raio_x`): Pyright flagged `_target` in the tuple-unpack `{actor for (actor, _target) in matrix}` as "not accessed". Changed to bare `_` — the standard Python convention for discarded values that Pyright recognises and does not warn about:
   ```python
   # BEFORE:
   givers_in_matrix = {actor for (actor, _target) in matrix}
   # AFTER:
   givers_in_matrix = {actor for (actor, _) in matrix}
   ```

### Investigation Summary

- `parse_votalhada_hora`: Reviewed `parts` variable name — renamed to `tokens` to avoid confusion with the `parts` list-join pattern elsewhere. Clarity improvement only.
- `require_clean_manual_events`, `load_votalhada_polls`, `load_sincerao_edges`: Simplified multi-line ternary Path initialization patterns where `Path(x) if x else Path(default)` was expressed over three lines.
- All remaining patterns (lazy optional imports, `is not None` checks for distinguishing `None` from `0/False`, module-level constant exposure) confirmed correct and intentional.

---

## `scripts/build_derived_data.py`

**Severity**: MEDIUM (one walrus operator anti-pattern), LOW (one dead variable)

### Changes Applied

1. **Dead variable `active_names_current`** (in `build_cluster_evolution`): Variable was assigned but never read. Removed.

2. **Walrus operator anti-pattern** (line ~4712, in `build_paredao_analysis`):
   ```python
   # BEFORE — walrus always assigns, so the ternary conditional was redundant:
   actual_indicado = form.get("indicado_lider") if (form := par.get("formacao", {})) else None
   # AFTER — clear and direct:
   actual_indicado = par.get("formacao", {}).get("indicado_lider")
   ```
   The `par.get("formacao", {})` default is always `{}` (truthy), making the `if ... else None` branch unreachable. The walrus `:=` pattern is valid Python but misleading here because the falsy branch never fires. Simplified to a clean chained `.get()`.

### Confirmed Correct / No Change

- `v_neg`, `a_neg`, `a_pos`, `b_neg`, `b_pos` boolean flags in `build_paredao_analysis`: all used in downstream `if/elif` chains.
- `range(len(matrices))` loops in patch functions: correct — in-place list mutation (`matrices[i] = ...`) requires index access; `enumerate` would require tuple unpacking without actual benefit here.
- `sinc_weight` and `low_power_weight` local aliases in scoring functions: legitimate readability helpers (long expressions used 3+ times each).
- `get_snapshot_on_or_before` inner function in `build_cartola_data`: used once in that function, correctly scoped there.
- `EXCLUDED_PARTICIPANTS` local constant: tightly scoped and not a candidate for module-level (it's specific to one function's logic).
- All `is not None` checks: correct — they distinguish `None` from falsy values `0` and `False` which are valid data.

---

## `scripts/build_index_data.py`

**Severity**: LOW (one redundant variable)

### Changes Applied

1. **Redundant `swing_delta` variable** (in `_build_profile_entry`, lines ~1768–1783):
   `max_swing` and `swing_delta` were always assigned together (`max_swing = delta; swing_delta = delta`) — they were always identical. `swing_delta` was removed; `max_swing` is used for both the threshold check (`abs(max_swing) >= 5`) and the display (`{max_swing:+.1f}`).

### Confirmed Correct / No Change

- Two `pair_sentiment` inner functions (line 1512 in `_build_profile_entry`, line 2122 in `build_index_data`): not duplication — each is a closure over different outer-scope variables (`latest_matrix` vs `ctx["latest_matrix"]`). Each is used only within its own enclosing function.
- `get_all_snapshots` thin wrapper (line 208): the backward-compat wrapper is intentional per project conventions.
- `MAX_CURIOSITIES = 8` module-level constant in `_build_record_holder_curiosities`: already clean.
- `available_weeks` computation with `sorted(set(edge_weeks + agg_weeks))`: `set(list + list)` is the clearest form here since both are already lists. No change needed.

---

## Notes

- No business logic was changed in either pass.
- Syntax verified after all changes: all three files import cleanly.
- The two passes together applied a total of **11 fixes** across the three files:
  - `data_utils.py`: 5 fixes (Pass 1) + 3 fixes (Pass 2, including Pyright `_target` → `_`)
  - `build_derived_data.py`: 5 fixes (Pass 1) + 2 fixes (Pass 2)
  - `build_index_data.py`: 2 fixes (Pass 1) + 1 fix (Pass 2)
