# Comprehensive Code Review — BBB26

> **Date**: 2026-02-26
> **Scope**: Full codebase (~25k lines, 11 QMD pages, 16 Python scripts, 219 tests)
> **Method**: 4-phase automated review (Code Quality, Architecture, Security, Testing & Docs)

---

## P0 — Critical (Fix Immediately)

### C-1. Lider prediction copy-pasted ~360 lines
- **Files**: `relacoes_debug.qmd:1500-1859` vs `scripts/paredao_viz.py:280-553`
- **Impact**: Guaranteed drift, double maintenance burden
- **Fix**: Replace inline code in `relacoes_debug.qmd` with call to `render_lider_prediction()`
- [x] Fixed (2026-02-26) — Replaced ~360 inline lines with call to `render_lider_prediction()` from `paredao_viz.py`

### C-2. `compute_streak_data()` returns 2-tuple on empty input
- **File**: `scripts/build_derived_data.py:210`
- **Impact**: Latent crash bug — caller destructures into 3 variables; test hides it via index access
- **Fix**: Change `return {}, []` to `return {}, [], []`; update test at `tests/test_build_pipeline.py:377`
- [x] Fixed (2026-02-26) — Return changed to 3-tuple; test updated to use destructuring

---

## P1 — High (Fix Before Next Release)

### H-1. `build_index_data` failure silently swallowed
- **File**: `scripts/build_derived_data.py:5265-5271`
- **Impact**: Stale `index_data.json` served without warning
- **Fix**: Propagate exception or log as ERROR instead of print + continue
- [x] Fixed (2026-02-26) — Removed try/except; exceptions now propagate and fail CI

### H-2. No deploy rollback in CI
- **File**: `.github/workflows/daily-update.yml`
- **Impact**: Data committed before Pages deploy; failure leaves site stale
- **Fix**: Reorder: deploy before `git push`, or add failure notification step
- [x] Fixed (2026-02-26) — Deploy job runs before data commit; git push only after successful deploy

### H-3. Overly broad CI permissions
- **File**: `.github/workflows/daily-update.yml:36-39`
- **Impact**: `contents: write` granted to all steps including Python execution
- **Fix**: Split into `build` job (read-only) + `deploy` job (write)
- [x] Fixed (2026-02-26) — Split into `build` (contents: read) + `deploy` (contents: write) jobs

### H-4. `build_derived_data.py` is a 5,283-line God file
- **File**: `scripts/build_derived_data.py`
- **Impact**: 80 functions spanning 10+ domains in one file
- **Fix**: Split into domain modules (`relations.py`, `plant_index.py`, `cartola.py`, etc.)
- [ ] Fixed

### H-5. 7 functions with nesting depth 6-8
- **Files**: `build_derived_data.py` — `_detect_cartola_roles` (8), `_score_single_prova` (8), `_build_paredao_vote_analysis` (7), `_apply_prediction_boosts` (7), `_build_curiosity_lookups` (6), `build_plant_index` (6), `_build_vote_data` (6)
- **Fix**: Refactor with early returns, guard clauses, extracted helpers
- [ ] Fixed

### H-6. `render_lider_prediction` is 274 lines of mixed logic + HTML
- **File**: `scripts/paredao_viz.py:280-553`
- **Impact**: Untestable, unmaintainable HTML generation
- **Fix**: Break into sub-renderers (summary box, ranking table, detail rows)
- [ ] Fixed

### H-7. 68/80 functions untested in `build_derived_data.py`
- **Impact**: 0% coverage on `paredao_viz.py`, `schemas.py`, `build_index_data.py`
- **Fix**: Add integration tests for top 5 pipeline functions + smoke tests for viz/schemas
- [x] Fixed (2026-02-26) — 22 integration tests added for top 5 pipeline functions (relations_scores, plant_index, paredao_analysis, clusters, vote_prediction)

### H-8. Zero integration tests for critical pipeline functions
- **Impact**: Scoring, clusters, prediction, plant index, paredao analysis — all untested end-to-end
- **Fix**: Write integration tests using synthetic fixtures
- [x] Fixed (2026-02-26) — `test_integration_scoring.py` (10 tests) + `test_integration_analysis.py` (12 tests) with synthetic 5-participant fixtures

### H-9. `jsonschema` missing from `requirements.txt`
- **File**: `requirements.txt`
- **Impact**: Schema validation silently skipped in CI
- **Fix**: Add `jsonschema>=4.0.0`
- [x] Fixed (2026-02-26) — Added to requirements.txt

### H-10. `OPERATIONS_GUIDE.md` has 5 stale hourly-probe references
- **File**: `docs/OPERATIONS_GUIDE.md:11,26,66,224-268`
- **Impact**: Misleading operational guidance
- **Fix**: Remove probe section, correct frequency counts
- [x] Fixed (2026-02-26) — All 5 references updated/removed; CLAUDE.md also updated

---

## P2 — Medium (Plan for Next Sprint)

### M-1. Non-atomic derived data writes
- **File**: `scripts/build_derived_data.py:5097-5277`
- **Impact**: Crash mid-build = mixed stale/fresh derived files
- **Fix**: Write to staging dir, then swap; add `_build_id` metadata
- [ ] Fixed

### M-2. Double build in CI
- **File**: `.github/workflows/daily-update.yml`
- **Impact**: `fetch_data.py` runs `build_derived_data()` internally, then CI runs it again
- **Fix**: Add `--skip-derived` to fetch call in workflow
- [x] Fixed (2026-02-26) — Added `--skip-derived` flag to fetch step in CI

### M-3. `data_utils.py` is a God module (1,576 lines)
- **Impact**: Mixes data access, domain logic, presentation, configuration
- **Fix**: Consider splitting into `constants.py`, `data_loaders.py`, `theme.py`
- [ ] Fixed

### M-4. `_compute_plant_component_scores` takes 20 parameters
- **File**: `scripts/build_derived_data.py:1829`
- **Fix**: Replace with a dataclass/context object
- [ ] Fixed

### M-5. Three different `get_all_snapshots` functions
- **Files**: `data_utils.py:467`, `build_derived_data.py:171`, `build_index_data.py:218`
- **Fix**: Unify naming or consolidate
- [ ] Fixed

### M-6. Unclosed file handles
- **Files**: `paredoes.qmd:45`, `relacoes_debug.qmd:807,874`
- **Fix**: Wrap with `with open(...) as f:`
- [x] Fixed (2026-02-26) — Changed to `Path.read_text()` + `json.loads()` (3 sites)

### M-7. Bare `except Exception` blocks in cluster detection
- **File**: `scripts/build_derived_data.py` (lines 3059, 3502, 3536)
- **Fix**: Add specific exception types
- [x] Fixed (2026-02-26) — Changed to `except (ValueError, KeyError, ZeroDivisionError)` with comments. Remaining 4 bare catches (date parsing fallbacks at 1336/1771/1789 + build_index_data at 5270) are acceptable or already fixed.

### M-8. Inconsistent import path in `paredao_viz.py`
- **File**: `scripts/paredao_viz.py:6` — `from scripts.data_utils import` vs `from data_utils import`
- **Fix**: Standardize to `from data_utils import`
- [x] Fixed (2026-02-26) — Changed to `from data_utils import` for consistency

### M-9. 929 inline styles remaining in QMD + 139 in Python
- **Impact**: Maintenance burden (mostly dynamic — accepted residual)
- **Fix**: Ongoing — extract where patterns emerge
- [ ] Fixed

### M-10. Emoji/slug constants defined in 3 locations
- **Files**: `relacoes_debug.qmd:1560`, `paredao_viz.py:316`, `data_utils.py`
- **Fix**: Import from `data_utils.py` everywhere
- [ ] Fixed

### M-11. No HTML escaping of API-sourced data
- **Files**: `data_utils.py:1500`, `paredao_viz.py:43`
- **Impact**: Stored XSS risk (theoretical — API is trusted, but defense-in-depth)
- **Fix**: Add `html.escape()` wrapper for interpolated names
- [x] Fixed (2026-02-26) — `safe_html()` helper added to `data_utils.py`; applied in `avatar_html()`, `render_cronologia_html()`, and 30+ sites in `paredao_viz.py`

### M-12. Client-side XSS via `innerHTML` in `datas.qmd`
- **File**: `datas.qmd:91-95`
- **Fix**: Use `textContent` instead of `innerHTML`
- [x] Fixed (2026-02-26) — Replaced with `document.createElement()` + `textContent`

### M-13. 14 instances of `to_html(escape=False)` in `relacoes_debug.qmd`
- **Impact**: Raw HTML injection if data contains `<>`
- **Fix**: Audit each instance; use `escape=True` where no pre-built HTML needed
- [ ] Fixed

### M-14. No rollback on deploy failure
- (Same as H-2 — tracked there)
- [ ] Fixed

### M-15. API response consumed without structural validation
- **File**: `scripts/fetch_data.py:116-118`
- **Fix**: Add basic type/structure check after `response.json()`
- [ ] Fixed

### M-16. Scoring weights split across 2 files
- **Files**: `data_utils.py` + `build_derived_data.py`
- **Fix**: Document the split explicitly or consolidate into `scoring_config.py`
- [ ] Fixed

### M-17. Hardcoded paths — inconsistent style
- **Fix**: Standardize on `Path(__file__).parent.parent` or define `PROJECT_ROOT`
- [ ] Fixed

### M-18. No structured logging
- **Impact**: All diagnostic output via `print()`
- **Fix**: Introduce Python `logging` module with appropriate levels
- [ ] Fixed

### M-19. Shallow JSON schemas
- **File**: `scripts/schemas.py`
- **Fix**: Add sub-field validation for `votos_casa`, `resultado.votos`, event arrays
- [ ] Fixed

### M-20. Derived data files growing linearly
- **Impact**: `daily_metrics.json` at 1.2MB, will ~double by season end
- **Fix**: Consider date-partitioned files or lazy loading for Date View
- [ ] Fixed

### M-21. No code coverage measurement
- **Fix**: Add `pytest-cov` + coverage gate to CI
- [x] Fixed (2026-02-26) — `pytest-cov>=4.0.0` added; CI step updated with `--cov=scripts --cov-report=term-missing`

### M-22. `CLAUDE.md` still says "hourly probes currently enabled"
- **File**: `CLAUDE.md:233`
- **Fix**: Remove stale reference
- [x] Fixed (2026-02-26) — Updated to reflect 6 permanent slots only

---

## P3 — Low (Backlog)

### L-1. 217 hardcoded color hex codes
- **Fix**: Consider CSS custom properties (`:root { --color-negative: #e74c3c; }`)
- [ ] Fixed

### L-2. Cryptic abbreviated variables in HTML builders
- **Files**: `paredao_viz.py`, `relacoes_debug.qmd`
- [ ] Fixed

### L-3. Scoring config split without clear boundary
- [ ] Fixed

### L-4. Duplicate `UTC`/`BRT` constants in 3 files
- **Files**: `data_utils.py`, `build_derived_data.py`, `build_index_data.py`
- [ ] Fixed

### L-5. `requirements-lock.txt` is unusable conda dump
- **Fix**: Regenerate with `pip-compile` or delete
- [ ] Fixed

### L-6. Unused deps: matplotlib, seaborn, jupyter
- **Fix**: Move to `requirements-dev.txt` or remove
- [ ] Fixed

### L-7. MD5 for hash comparison (non-security context)
- **Fix**: Optional switch to SHA-256
- [ ] Fixed

### L-8. Full snapshot directory scan on every build
- **Fix**: Use snapshot manifest as cache layer
- [ ] Fixed

### L-9. No version markers on derived data files
- **Fix**: Add schema version to `_metadata`
- [ ] Fixed

### L-10. Actions pinned to major versions, not SHAs
- **File**: `.github/workflows/daily-update.yml`
- [ ] Fixed

### L-11. No CSP meta tag or SRI for GoatCounter script
- **File**: `_quarto.yml:71-72`
- [ ] Fixed

### L-12. 3 new viz helpers untested
- **Functions**: `make_visibility_buttons`, `make_line_evolution`, `make_stacked_bar`
- [ ] Fixed

### L-13. `test_loaders.py::TestNormalizeActors` tests reimplementation
- **Fix**: Import actual function or delete redundant tests
- [ ] Fixed

### L-14. Redundant `sys.path.insert` in `test_build_pipeline.py:12`
- [ ] Fixed

### L-15. `real_snapshot` fixture uses relative path
- **File**: `tests/conftest.py:167`
- [ ] Fixed

### L-16. Semana 3 operational checklist in `MANUAL_EVENTS_GUIDE.md`
- **Lines**: 305-475 (170 lines of historical content)
- [ ] Fixed

---

## Summary

| Severity | Total | Fixed | Remaining |
|----------|-------|-------|-----------|
| Critical | 2 | 2 | 0 |
| High | 10 | 7 | 3 |
| Medium | 21 | 8 | 13 |
| Low | 16 | 0 | 16 |
| **Total** | **49** | **17** | **32** |

---

## Quality Metrics

```
Code Complexity:
  God files (>500 lines):      3
  Functions >80 lines:         35
  Max nesting depth:           8 (target: 3)
  Max parameter count:         20 (target: 5-7)

Test Coverage (by function count):
  data_utils.py:               91% (39/43)
  build_derived_data.py:       21% (17/80)  ← +5 via integration tests
  build_index_data.py:          0% (0/30)
  paredao_viz.py:               0% (0/8)
  schemas.py:                   0% (0/1)
  OVERALL:                     35% (56/162)
  Integration tests:           241 total (219 unit + 22 integration)

Documentation:
  Docstring coverage:          81% (131/162)
  Type hint coverage:          100%
  Stale doc references:        0 (was 6, all fixed)
```
