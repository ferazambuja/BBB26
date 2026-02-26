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
- [ ] Not started — requires incremental function-by-function splitting

### H2. Zero test coverage
- **Impact**: No automated verification of correctness. Refactoring is risky without tests
- **Fix**: Add pytest infrastructure + fixtures for `data_utils.py` functions, then build_derived pipeline
- **Effort**: 4-6 hours for initial infrastructure + core function tests
- [x] Fixed (2026-02-26) — pytest infrastructure + 37 tests covering 6 core functions

### H3. ~1,200 inline `style=` attributes in QMD files
- **Files** (by count): `paredao.qmd` (363), `index.qmd` (210), `relacoes_debug.qmd` (170), `paredoes.qmd` (107), `provas.qmd` (92), `cartola.qmd` (77), `clusters.qmd` (70), `relacoes.qmd` (52), `evolucao.qmd` (34), `datas.qmd` (7)
- **Impact**: Inconsistent styling, hard to update themes, bloated HTML output
- **Fix**: Extract top patterns into `assets/cards.css`, replace inline attrs with CSS classes
- **Effort**: 45 min for top 5-6 patterns (stat cards, dark cards, badges)
- [x] Partially fixed — top patterns extracted (2026-02-26)

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
- [x] Partially fixed (2026-02-26) — `make_horizontal_bar()` + `make_sentiment_heatmap()` added; 2 QMD charts migrated

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
- **Fix**: Add `-> dict`, `-> list[dict]`, etc. to all public functions
- **Effort**: 1 hour
- [x] Fixed (2026-02-26) — `from __future__ import annotations` + type hints on all 35 public functions

### L3. Hardcoded magic numbers in scoring
- **Current**: Weights like `0.7` (Sincerão decay), `0.10`/`0.35`/`0.25`/`0.15`/`0.15` (Planta Index) are inline in `build_derived_data.py`
- **Impact**: Hard to tune without reading through code
- **Fix**: Extract to named constants at module level (already documented in `SCORING_AND_INDEXES.md`)
- **Effort**: 30 min
- [x] Fixed (2026-02-26) — 6 named constants (`STREAK_*`, `REACTIVE_WINDOW_WEIGHTS`) replace all inline numbers

---

## Summary

| Severity | Total | Fixed | Partial | Remaining |
|----------|-------|-------|---------|-----------|
| Critical | 3 | 3 | 0 | 0 |
| High | 4 | 2 | 1 | 1 |
| Medium | 4 | 3 | 1 | 0 |
| Low | 3 | 3 | 0 | 0 |
| **Total** | **14** | **11** | **2** | **1** |

**Not started**: H1 (giant functions — needs incremental splitting, now unblocked by H2 tests)
**Partially fixed**: H3 (inline styles — top CSS patterns extracted), M2 (viz helpers — 2 functions created, 2 charts migrated, remaining charts incremental)
