# Refactor QMD Secondary — Pass 1 Report

Processed files: `paredoes.qmd`, `cartola.qmd`, `provas.qmd`, `planta_debug.qmd`, `datas.qmd`, `clusters.qmd`, `relacoes_debug.qmd`

---

## paredoes.qmd

### Issues Found

| Priority | Issue |
|----------|-------|
| Medium | Unused `from datetime import datetime` import |
| Medium | Unused `n_daily` variable (assigned, never read) |
| Medium | Stale comment `# classify_relationship and genero imported from data_utils` (classify_relationship not imported or used) |
| Medium | `active_names` variable shadowed — outer set from `participants_index.json`, inner list from `snap_participants` |
| Medium | `indicacoes` variable shadowed — outer list for coherence analysis, inner `Counter()` for badge logic |
| Low | `from collections import Counter, defaultdict` re-imported inside `vote-map` block (already imported at top) |
| Low | `PAREDOES_FILE` module-level constant only used in `load_paredoes()` — unnecessary global |

### Fixes Applied

- Removed `from datetime import datetime` import
- Removed `n_daily = len(daily_snapshots)` unused variable
- Removed stale comment about `classify_relationship`
- Renamed inner `active_names` to `snap_active_names` to eliminate shadowing
- Renamed inner `indicacoes` Counter to `indicacoes_count` to eliminate shadowing
- Removed redundant `from collections import Counter, defaultdict` re-import in `vote-map` block
- Inlined `PAREDOES_FILE` into `load_paredoes()` as local variable `paredoes_file`

---

## cartola.qmd

### Issues Found

No significant issues found. The file:
- Has clean imports (all used)
- Follows the `require_clean_manual_events()` / `setup_bbb_dark_theme()` pattern
- Loads precomputed data correctly from `data/derived/cartola_data.json`
- Computations are visualization-only (no heavy logic in QMD)

### Fixes Applied

None required.

---

## provas.qmd

### Issues Found

No significant issues found. The file:
- Has minimal, clean imports
- Uses `participants_index.json` for avatar/group lookup (correct pattern)
- Helper functions `get_avatar()`, `get_grupo()`, `is_active()`, `get_status()` are short and appropriate for QMD display use
- Bracket rendering logic is self-contained and not reused elsewhere (appropriate as QMD-local)

### Fixes Applied

None required.

---

## planta_debug.qmd

### Issues Found

| Priority | Issue |
|----------|-------|
| Critical | `POWER_EVENT_LABELS` defined locally — duplicates constants from `data_utils.py` |
| Critical | `POWER_EVENT_EMOJI` defined locally — duplicates constants from `data_utils.py` |
| Low | Local definitions also missing some keys present in `data_utils.py` (newer event types) |

### Fixes Applied

- Added `POWER_EVENT_LABELS, POWER_EVENT_EMOJI` to import from `data_utils`
- Removed the 22-line local duplicate definitions of `POWER_EVENT_LABELS` and `POWER_EVENT_EMOJI`
- Added local extension dict (`_EXTRA_LABELS`, `_EXTRA_EMOJI`) for planta_debug-specific event types (`emparedado`, `volta_paredao`) not present in `data_utils.py`, merged via `{**POWER_EVENT_LABELS, **_EXTRA_LABELS}` to preserve correct display labels without modifying `data_utils.py`

---

## datas.qmd

### Issues Found

No issues found. This file is pure HTML + JavaScript with no Python code blocks. The JavaScript logic is clean and appropriate for a client-side date picker.

### Fixes Applied

None required.

---

## clusters.qmd

### Issues Found

| Priority | Issue |
|----------|-------|
| Medium | `import plotly.graph_objects as go` re-imported inside `cluster-evolution` block (already imported at top) |
| Medium | `from pathlib import Path` re-imported inside `cluster-evolution` block (already imported at top) |
| Low | `avatar_html` used as local string variable in `community-cards` block — potentially confusing name given `data_utils.avatar_html` function (not imported here, but still misleading) |
| Low | `avatar_html` also used as local variable in `polarizer-cards` block (same issue) |

### Fixes Applied

- Removed redundant `import plotly.graph_objects as go` from `cluster-evolution` block
- Removed redundant `from pathlib import Path` from `cluster-evolution` block
- Renamed `avatar_html` string variable to `members_html` in `community-cards` block
- Renamed `avatar_html` string variable to `avatar_img_html` in `polarizer-cards` block

---

## relacoes_debug.qmd

### Issues Found

| Priority | Issue |
|----------|-------|
| Medium | `import pandas as pd` re-imported inside `badge-vs-reality` block (already imported at top) |
| Medium | `from collections import Counter` imported inside `vote-prediction-enhanced` block — `Counter` not in top-level import |
| Medium | `relations_scores.json` re-loaded as `rel_data` in `big-fone-retro` block — already loaded as `relations` in setup |
| Medium | `data/paredoes.json` re-loaded as `paredoes_file` in `vote-prediction-retro` block — already loaded as `paredoes_data` in preceding block |

### Fixes Applied

- Removed `import pandas as pd` from `badge-vs-reality` block
- Moved `Counter` into top-level `from collections import defaultdict, Counter` import
- Removed redundant `from collections import Counter` from `vote-prediction-enhanced` block
- Replaced re-load of `relations_scores.json` with alias `pairs_daily = relations_pairs_daily` using already-loaded `relations` data
- Replaced re-load of `data/paredoes.json` with `paredoes_file = paredoes_data` reusing the variable from the preceding block
