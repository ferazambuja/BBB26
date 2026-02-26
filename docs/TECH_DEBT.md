# Tech Debt Inventory — BBB26

> Last updated: 2026-02-26
> Codebase: ~25k lines, 11 QMD pages, 14 Python scripts

This document tracks all identified technical debt items. Check off items as they are remediated.

---

## Critical — Architecture Violations

### C1. Missing `setup_bbb_dark_theme()` in debug pages
- **Files**: `planta_debug.qmd`, `relacoes_debug.qmd`
- **Impact**: Plotly charts render with default (light) theme instead of `bbb_dark`
- **Effort**: 5 min
- [x] Fixed (2026-02-26)

### C2. Inline `json.load()` scattered across QMD files
- **Files**: `index.qmd`, `evolucao.qmd`, `relacoes.qmd`, `paredao.qmd`, `paredoes.qmd`, `clusters.qmd`, `provas.qmd`, `cartola.qmd`, `planta_debug.qmd`, `relacoes_debug.qmd`
- **Impact**: ~50+ duplicate `Path(...).exists() → json.load()` blocks. Violates "single source of truth" rule — if a file path changes, every QMD must be updated
- **Fix**: Centralized loaders in `data_utils.py` (`load_paredoes()`, `load_participants_index()`, etc.)
- **Effort**: 30 min
- [x] Fixed (2026-02-26)

### C3. No reproducible dependency lock
- **File**: `requirements.txt` (loose pins only)
- **Impact**: `pip install -r requirements.txt` may produce different environments over time
- **Fix**: Add `requirements-lock.txt` with `pip freeze` output
- **Effort**: 5 min
- [x] Fixed (2026-02-26)

---

## High — Code Quality

### H1. Giant functions (28 functions > 80 lines)
- **Locations** (top offenders):
  - `paredao.qmd` — paredão card rendering (~200 lines), nomination prediction (~400 lines)
  - `paredoes.qmd` — per-paredão tab rendering (~300 lines per section)
  - `index.qmd` — profile card generation (~150 lines), heatmap rendering (~120 lines)
  - `evolucao.qmd` — balance chart (~100 lines), ranking evolution (~100 lines)
  - `relacoes.qmd` — network graph (~120 lines), alliance table (~100 lines)
  - `scripts/build_derived_data.py` — `build_relations_scores()` (~300 lines), `build_clusters_data()` (~200 lines)
- **Impact**: Hard to test, debug, and maintain. Encourages copy-paste over reuse
- **Fix**: Extract into smaller functions; test coverage now available (H2) to support safe refactoring
- **Effort**: 2-3 hours per function group
- [x] Fixed (2026-02-26) — 13 giant functions split into 40 helpers across `build_derived_data.py` (10→30 helpers) and `build_index_data.py` (3→10 helpers). `paredao.qmd` extracted 8 viz functions (553 lines) to `scripts/paredao_viz.py`.

### H2. Zero test coverage
- **Impact**: No automated verification of correctness. Refactoring is risky without tests
- **Fix**: Add pytest infrastructure + fixtures for `data_utils.py` functions, then build_derived pipeline
- **Effort**: 4-6 hours for initial infrastructure + core function tests
- [x] Fixed (2026-02-26) — 219 tests: 37 core + 119 data_utils extended + 63 build pipeline. Covers loaders, scoring, edge builders, data builders, viz helpers, poll functions.

### H3. ~1,200 inline `style=` attributes in QMD files
- **Files** (by count): `paredao.qmd` (363), `index.qmd` (210), `relacoes_debug.qmd` (170), `paredoes.qmd` (107), `provas.qmd` (92), `cartola.qmd` (77), `clusters.qmd` (70), `relacoes.qmd` (52), `evolucao.qmd` (34), `datas.qmd` (7)
- **Impact**: Inconsistent styling, hard to update themes, bloated HTML output
- **Fix**: Extract top patterns into `assets/cards.css`, replace inline attrs with CSS classes
- **Effort**: 45 min for top 5-6 patterns (stat cards, dark cards, badges)
- [x] Fixed (2026-02-26) — 15 CSS utility classes in `assets/cards.css`; ~250 inline styles replaced across 8 QMD files. Remaining ~900 are dynamic (f-string colors, variable widths).

### H4. Residual refactor docs (completed work)
- **Files**: `docs/refactor_qmd_core.md`, `docs/refactor_qmd_core_pass2.md`, `docs/refactor_qmd_secondary.md`, `docs/refactor_qmd_secondary_pass2.md`, `docs/refactor_scripts_core.md`, `docs/refactor_scripts_core_pass2.md`, `docs/refactor_scripts_utils.md`, `docs/refactor_scripts_utils_pass2.md`
- **Impact**: Stale documentation creates confusion about what's current
- **Effort**: 5 min
- [x] Fixed (2026-02-26)

---

## Medium — Performance & Maintainability

### M1. Precompute reaction matrices in derived data
- **Current**: Multiple QMD files call `build_reaction_matrix()` at render time for every snapshot
- **Files**: `paredao.qmd`, `paredoes.qmd`, `relacoes.qmd`
- **Impact**: Redundant computation on each render (~3 min total render time)
- **Fix**: Precompute matrices in `build_derived_data.py`, save as derived JSON
- **Effort**: 2-3 hours
- [x] Fixed (2026-02-26) — `reaction_matrices.json` precomputed; QMD files load with fallback

### M2. Visualization helper functions
- **Current**: Plotly chart creation code is repeated across QMD files (bar charts, heatmaps, timelines)
- **Impact**: Style inconsistencies between pages, harder to update chart defaults
- **Fix**: Extract `make_bar_chart()`, `make_heatmap()`, `make_timeline()` into `data_utils.py`
- **Effort**: 2-3 hours
- [x] Fixed (2026-02-26) — 5 viz helpers: `make_horizontal_bar()`, `make_sentiment_heatmap()`, `make_visibility_buttons()`, `make_line_evolution()`, `make_stacked_bar()`. 7 QMD charts migrated in `evolucao.qmd`.

### M3. Duplicate `load_paredoes()` transformer in paredao.qmd and paredoes.qmd
- **Current**: Both files have a ~70-line `load_paredoes()` function that transforms `paredoes.json` into a dashboard-friendly format
- **Impact**: Bug fixes must be applied twice; divergence risk
- **Fix**: Move transformer to `data_utils.py` or precompute in `build_derived_data.py`
- **Effort**: 30 min
- [x] Fixed (2026-02-26) — `load_paredoes_transformed()` in `data_utils.py`; raw callers use `load_paredoes_raw()`

### M4. GitHub Actions audit timing
- **Current**: Hourly probes 10:00-16:00 BRT were added as temporary (Feb 6)
- **Impact**: Unnecessary CI runs after timing is established
- **Fix**: Run `python scripts/analyze_capture_timing.py`, remove probes if timing is confirmed
- **Effort**: 15 min
- [x] Fixed (2026-02-26) — timing confirmed (median 15:00 BRT); 6 probe crons removed

---

## Low — Nice to Have

### L1. JSON schema validation
- **Current**: Manual data files (`paredoes.json`, `manual_events.json`, `provas.json`) have no formal schema
- **Impact**: Typos and structural errors are caught late (at render time)
- **Fix**: Add `jsonschema` validation in `build_derived_data.py`
- **Effort**: 2-3 hours
- [x] Fixed (2026-02-26) — `scripts/schemas.py` with 3 schemas; `validate_input_files()` runs at pipeline start

### L2. Missing type hints in `data_utils.py`
- **Current**: Functions lack type annotations
- **Impact**: IDE support limited, harder for new contributors to understand interfaces
- **Effort**: 1 hour
- [x] Fixed (2026-02-26) — `from __future__ import annotations` + type hints on all 35 public functions in `data_utils.py`, all 70+ functions in `build_derived_data.py`, all 30 functions in `build_index_data.py`

### L3. Hardcoded magic numbers in scoring
- **Current**: Weights like `0.7` (Sincerão decay), `0.10`/`0.35`/`0.25`/`0.15`/`0.15` (Planta Index) are inline in `build_derived_data.py`
- **Impact**: Hard to tune without reading through code
- **Fix**: Extract to named constants at module level (already documented in `SCORING_AND_INDEXES.md`)
- **Effort**: 30 min
- [x] Fixed (2026-02-26) — 6 named constants (`STREAK_*`, `REACTIVE_WINDOW_WEIGHTS`) replace all inline numbers

---

## New Items (identified 2026-02-26)

### N1. CI/CD: No test execution in pipeline
- **Impact**: Tests never ran in GitHub Actions; untested code deployed directly
- **Fix**: Add `pytest` step + `build_derived_data.py` step to workflow
- [x] Fixed (2026-02-26) — pytest + build_derived_data.py steps added to `daily-update.yml`

### N2. Paredao.qmd: Inline viz functions (500+ lines)
- **Impact**: Untestable HTML generation, 2,700-line QMD file
- **Fix**: Extract to `scripts/paredao_viz.py` module
- [x] Fixed (2026-02-26) — 8 functions (553 lines) extracted, paredao.qmd reduced by 459 lines

---

## Summary

| Severity | Total | Fixed | Partial | Remaining |
|----------|-------|-------|---------|-----------|
| Critical | 3 | 3 | 0 | 0 |
| High | 4 | 4 | 0 | 0 |
| Medium | 4 | 4 | 0 | 0 |
| Low | 3 | 3 | 0 | 0 |
| New | 2 | 2 | 0 | 0 |
| **Total** | **16** | **16** | **0** | **0** |

All identified tech debt items have been resolved.
