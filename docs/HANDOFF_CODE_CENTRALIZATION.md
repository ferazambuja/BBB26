# Handoff: Code Centralization (Jan 2026)

## What happened

The codebase had a severe duplication problem: **7 QMD files and 3 Python scripts** each defined their own copies of the same constants, functions, and Plotly theme. A single change (e.g., adjusting a sentiment weight) required editing up to 9 files. A codebase audit identified ~700 lines of duplicated code.

### What was done

1. **Deleted dead code**: `scripts/compute_metrics.py` and `data/daily_metrics.json` (root). These were superseded by `build_derived_data.py` and `data/derived/daily_metrics.json`. Also removed the CI step from `.github/workflows/daily-update.yml`.

2. **Centralized everything into `scripts/data_utils.py`**:
   - Constants: `REACTION_EMOJI`, `REACTION_SLUG_TO_LABEL`, `SENTIMENT_WEIGHTS`, `POSITIVE`, `MILD_NEGATIVE`, `STRONG_NEGATIVE`, `GROUP_COLORS`, `POWER_EVENT_EMOJI`, `POWER_EVENT_LABELS`
   - Theme: `PLOT_BG`, `PAPER_BG`, `GRID_COLOR`, `TEXT_COLOR`, `BBB_COLORWAY`, and `setup_bbb_dark_theme()` function
   - Functions: `calc_sentiment()` (was duplicated in 7 files)

3. **Updated all consumers** to import from `data_utils.py`:
   - 8 QMD files: `index.qmd`, `mudancas.qmd`, `trajetoria.qmd`, `paredao.qmd`, `paredoes.qmd`, `clusters.qmd`, `cartola.qmd`, `planta.qmd`
   - 2 scripts: `build_index_data.py`, `build_derived_data.py`

4. **Updated `CLAUDE.md`** with a "Code Architecture Rules" section documenting the pattern.

### Files changed

| File | Change |
|------|--------|
| `scripts/data_utils.py` | Added all shared constants, `calc_sentiment()`, `setup_bbb_dark_theme()` |
| `scripts/build_index_data.py` | Removed local copies of `load_snapshot`, `parse_roles`, `build_reaction_matrix`, `calc_sentiment`, all constants; now imports from `data_utils` |
| `scripts/build_derived_data.py` | Removed local `SENTIMENT_WEIGHTS` and `calc_sentiment`; now imports from `data_utils` |
| `scripts/compute_metrics.py` | **Deleted** (dead code) |
| `data/daily_metrics.json` | **Deleted** (root-level dead file; `data/derived/daily_metrics.json` is the real one) |
| `.github/workflows/daily-update.yml` | Removed `compute_metrics.py` step |
| `index.qmd` | Replaced ~90 lines of constants/theme with 8-line import block |
| `mudancas.qmd` | Same pattern + removed local `calc_sentiment` |
| `trajetoria.qmd` | Same pattern + removed local `calc_sentiment` |
| `paredao.qmd` | Same pattern + removed local `calc_sentiment` |
| `paredoes.qmd` | Same pattern + removed local `calc_sentiment` |
| `clusters.qmd` | Same pattern (no local `calc_sentiment` to remove) |
| `cartola.qmd` | Replaced custom theme (rgba-based) with shared theme |
| `planta.qmd` | Replaced local `REACTION_EMOJI` with import |
| `CLAUDE.md` | Added "Code Architecture Rules" section |

---

## The principle: scripts compute, QMD pages render

### The problem with computing inside Quarto

Quarto `.qmd` files execute Python cells during render. Each page runs in its **own isolated Python process** -- there is no shared state between pages. This creates two problems:

1. **Duplication**: Every page that needs `calc_sentiment()` or `REACTION_EMOJI` must define it locally, because pages cannot share Python state. Before centralization, this meant 7 identical copies of each constant.

2. **Performance**: If a page loads all 15+ snapshots to compute a ranking, that I/O and computation happens on every render. Multiply that by 8 pages and rendering becomes slow.

### The solution: two-layer architecture

```
Layer 1: Scripts (compute)          Layer 2: QMD pages (render)
─────────────────────────           ────────────────────────────
scripts/build_derived_data.py  ──>  data/derived/*.json
scripts/build_index_data.py    ──>  data/derived/index_data.json
                                         │
                                         ▼
                                    *.qmd loads JSON, renders charts
```

**Scripts** do heavy computation (loading all snapshots, building matrices, computing sentiment, etc.) and write results to `data/derived/*.json`.

**QMD pages** load the precomputed JSON and focus on visualization. They import constants and small utility functions from `data_utils.py` for things that must happen at render time (e.g., formatting emoji, applying the Plotly theme).

### What goes where

| Location | Purpose | Examples |
|----------|---------|---------|
| `scripts/data_utils.py` | Shared constants, small functions, theme | `REACTION_EMOJI`, `calc_sentiment()`, `setup_bbb_dark_theme()` |
| `scripts/build_derived_data.py` | Heavy computation -> JSON | roles_daily, auto_events, daily_metrics, plant_index |
| `scripts/build_index_data.py` | Precompute index tables -> JSON | profiles, rankings, highlights, cross-table |
| `*.qmd` pages | Load JSON + render | Charts, tables, HTML cards |

### When to use which approach

**Put it in a script** if:
- It processes multiple snapshots (I/O heavy)
- Multiple pages need the same result
- It computes derived metrics (sentiment per day, reaction counts)
- The result can be serialized as JSON

**Put it in a QMD page** if:
- It's purely about rendering/formatting (HTML generation, chart configuration)
- It's page-specific logic that no other page needs
- It needs the full Plotly/pandas environment for visualization

**Put it in `data_utils.py`** if:
- It's a constant or enum used by both scripts and pages
- It's a small utility function (< 20 lines) used in 2+ places
- It's the Plotly theme setup

### The QMD import pattern

Every `.qmd` file follows this pattern in its setup cell:

```python
import sys
sys.path.append(str(Path("scripts").resolve()))
from data_utils import (
    require_clean_manual_events, setup_bbb_dark_theme,
    calc_sentiment, REACTION_EMOJI, SENTIMENT_WEIGHTS,
    POSITIVE, MILD_NEGATIVE, STRONG_NEGATIVE, GROUP_COLORS,
    # ... other imports as needed by this specific page
)

require_clean_manual_events()  # Fail fast if manual data has issues
setup_bbb_dark_theme()         # Register + activate Plotly dark theme
```

Pages that load from `data/derived/index_data.json` (like `index.qmd`) don't need snapshot loaders. Pages that work directly with snapshots (like `trajetoria.qmd`, `paredao.qmd`) also import `load_snapshot`, `get_all_snapshots`, `build_reaction_matrix`, etc.

### Anti-patterns to avoid

| Don't do this | Do this instead |
|---------------|-----------------|
| Define `calc_sentiment()` in a QMD cell | `from data_utils import calc_sentiment` |
| Copy-paste `REACTION_EMOJI = {...}` | `from data_utils import REACTION_EMOJI` |
| Define `bbb_dark` template inline (30 lines) | `from data_utils import setup_bbb_dark_theme; setup_bbb_dark_theme()` |
| Load all snapshots in a QMD to compute a ranking | Precompute in `build_index_data.py`, load JSON in QMD |
| Add a new constant in one QMD file | Add to `data_utils.py`, import everywhere |

### Adding new shared items

1. Add the constant/function to `scripts/data_utils.py`
2. Import it in the QMD pages or scripts that need it
3. If it's a heavy computation, put it in `build_derived_data.py` or `build_index_data.py` instead, and output to `data/derived/`
4. Run `python scripts/build_derived_data.py` to regenerate derived data
5. Render the affected QMD pages to verify

---

## Verification

All scripts and pages were verified after the refactoring:

```bash
python scripts/build_derived_data.py   # OK
python scripts/build_index_data.py     # OK
quarto render index.qmd                # OK
quarto render mudancas.qmd             # OK
quarto render trajetoria.qmd           # OK
quarto render paredao.qmd              # OK
quarto render paredoes.qmd             # OK
quarto render clusters.qmd             # OK
quarto render cartola.qmd              # OK
quarto render planta.qmd               # OK
```

## Remaining opportunities

These were identified in the audit but not implemented yet:

- **Priority 4**: Extract Cartola computation from `cartola.qmd` into `build_derived_data.py` -> `data/derived/cartola_data.json`. Currently ~400 lines of role tracking and point calculation run inside the QMD page on every render.
- **`analyze_snapshots.py`**: Still has its own `POSITIVE`/`MILD_NEGATIVE`/`STRONG_NEGATIVE` definitions. It's a one-off audit script so lower priority, but could import from `data_utils.py`.
