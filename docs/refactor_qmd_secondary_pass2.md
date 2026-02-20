# Refactor QMD Secondary — Pass 2 Report

Processed files: `paredoes.qmd`, `cartola.qmd`, `provas.qmd`, `planta_debug.qmd`, `datas.qmd`, `clusters.qmd`, `relacoes_debug.qmd`

---

## relacoes_debug.qmd

### Issues Found

| Priority | Issue |
|----------|-------|
| Medium | `defaultdict` imported at top level — never used anywhere in the file |
| Medium | `with open("data/paredoes.json")` re-load inside `vote-prediction-enhanced` block — `paredoes_data` already loaded in `badge-vs-reality` block |

### Fixes Applied

- Removed `defaultdict` from top-level `from collections import defaultdict, Counter` → now `from collections import Counter`
- Removed `with open("data/paredoes.json") as f: paredoes_data = json.load(f)` inside `vote-prediction-enhanced` block; replaced with `paredoes_list = paredoes_data.get("paredoes", [])` reusing the already-loaded variable

---

## paredoes.qmd

### Issues Found

| Priority | Issue |
|----------|-------|
| Medium | `REACTION_EMOJI` imported from `data_utils` — never used in the file body |
| Medium | `SENTIMENT_WEIGHTS` imported from `data_utils` — never used in the file body |
| Medium | `artigo` imported from `data_utils` — never used (`genero` is used, but `artigo` is not) |
| Low | `MONTH_MAP_PT` imported from `data_utils` — never used (internal to `parse_votalhada_hora` / `make_poll_timeseries`) |
| Low | `parse_votalhada_hora` imported from `data_utils` — never used (only `make_poll_timeseries` is called directly) |

### Fixes Applied

- Removed `REACTION_EMOJI`, `SENTIMENT_WEIGHTS` from import line
- Removed `artigo` from import line (kept `genero` which is used)
- Removed `MONTH_MAP_PT`, `parse_votalhada_hora` from import line (kept `make_poll_timeseries`)

```python
# Before:
from data_utils import (
    load_snapshots_full, build_reaction_matrix,
    load_votalhada_polls, get_poll_for_paredao, calculate_poll_accuracy,
    require_clean_manual_events, calc_sentiment, setup_bbb_dark_theme,
    genero, artigo, get_nominee_badge,
    MONTH_MAP_PT, parse_votalhada_hora, make_poll_timeseries,
    avatar_html, avatar_img,
    REACTION_EMOJI, SENTIMENT_WEIGHTS,
    POSITIVE, MILD_NEGATIVE, STRONG_NEGATIVE, GROUP_COLORS,
)
# After:
from data_utils import (
    load_snapshots_full, build_reaction_matrix,
    load_votalhada_polls, get_poll_for_paredao, calculate_poll_accuracy,
    require_clean_manual_events, calc_sentiment, setup_bbb_dark_theme,
    genero, get_nominee_badge,
    make_poll_timeseries,
    avatar_html, avatar_img,
    POSITIVE, MILD_NEGATIVE, STRONG_NEGATIVE, GROUP_COLORS,
)
```

---

## clusters.qmd

### Issues Found

| Priority | Issue |
|----------|-------|
| Medium | `GROUP_COLORS` imported from `data_utils` — never used in the file (participant coloring uses `cluster_colors` from the precomputed JSON, not `GROUP_COLORS`) |

### Fixes Applied

- Removed `GROUP_COLORS` from import

```python
# Before:
from data_utils import (
    require_clean_manual_events, setup_bbb_dark_theme,
    GROUP_COLORS,
)
# After:
from data_utils import (
    require_clean_manual_events, setup_bbb_dark_theme,
)
```

---

## planta_debug.qmd

### Issues Found

| Priority | Issue |
|----------|-------|
| Medium | `import plotly.express as px` — `px` never used (all charts use `go` from `plotly.graph_objects` loaded indirectly, but `px` itself is never referenced) |

### Fixes Applied

- Removed `import plotly.express as px`

---

## cartola.qmd

### Issues Found

No additional issues found in Pass 2. All imports verified as used.

---

## provas.qmd

### Issues Found

No additional issues found in Pass 2. All imports verified as used.

---

## datas.qmd

### Issues Found

No issues (pure HTML + JavaScript, no Python code blocks).

---

## Summary

| File | Pass 2 Fixes |
|------|-------------|
| `relacoes_debug.qmd` | Removed unused `defaultdict` import; eliminated re-load of `paredoes.json` |
| `paredoes.qmd` | Removed 5 unused imports: `REACTION_EMOJI`, `SENTIMENT_WEIGHTS`, `artigo`, `MONTH_MAP_PT`, `parse_votalhada_hora` |
| `clusters.qmd` | Removed unused `GROUP_COLORS` import |
| `planta_debug.qmd` | Removed unused `import plotly.express as px` |
| `cartola.qmd` | No changes |
| `provas.qmd` | No changes |
| `datas.qmd` | No changes (no Python) |
