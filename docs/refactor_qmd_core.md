# Refactor-Clean: Core QMD Files — Pass 1 Report

**Files processed:** `index.qmd`, `evolucao.qmd`, `relacoes.qmd`, `paredao.qmd`

**Date:** 2026-02-20

---

## index.qmd

### Issues Fixed

**Dead imports removed:**
- `import matplotlib.pyplot as plt` — never used after template copy
- `import matplotlib.colors as mcolors` — never used
- `import seaborn as sns` — never used
- `from plotly.subplots import make_subplots` — never used
- `from collections import Counter` — never used
- `from collections import defaultdict` — never used (moved to Pass 2)
- `OrderedDict` removed from inside `build_rxn_detail_html` (was imported inside a function body)

**Dead plt/sns config block removed (3 lines):**
```python
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 11
sns.set_theme(style="whitegrid", palette="husl")
```

**Unused variables removed:**
- `MEMBER_OF = {}` — pre-init overwritten immediately by `load_snapshots_full()`
- `current_cycle_week` — loaded but never referenced
- `rxn_summary` and `given_summary` — computed inside profile loop, never used

**Dead function removed:**
- `make_negative_givers_chart()` — ~55-line function defined but never called anywhere in the file

**Unused parameter removed from `build_rxn_detail_html`:**
- `label_prefix` parameter was accepted but never used inside the function body
- Updated both call sites: `build_rxn_detail_html(received_detail, "De")` → `build_rxn_detail_html(received_detail)` and similarly for given_detail

**Import-inside-function antipatterns fixed:**
- `from datetime import datetime as _dt` inside a for loop → use top-level `datetime` import
- `from collections import OrderedDict` inside `build_rxn_detail_html` → moved to top-level imports

**Constant hoisted out of loop:**
- `COMP_LABELS = {...}` — was redefined every iteration of a loop; moved above the loop as a module-level constant
- `medals = ["🥇", "🥈", "🥉"]` — was redefined inside nested loop; hoisted as `_medals3`

---

## evolucao.qmd

### Issues Fixed

**Dead imports removed:**
- `from plotly.subplots import make_subplots` — never used
- `from collections import defaultdict` — never used
- `build_reaction_matrix` from data_utils — never used
- `avatar_html` from data_utils — never used
- `REACTION_SLUG_TO_LABEL` from data_utils — never used
- `POWER_EVENT_EMOJI` and `POWER_EVENT_LABELS` from data_utils — never used
- `POSITIVE`, `MILD_NEGATIVE`, `STRONG_NEGATIVE` — never used (evolucao only uses raw sentiment values)

**Undefined variable risk fixed:**
- `auto_payload` was only defined inside `if AUTO_EVENTS_FILE.exists():` block; added `auto_payload = {}` before the if-block

**Fragile runtime check removed:**
- `if 'auto_payload' in dir() and isinstance(auto_payload, dict)` → `auto_payload.get("power_summary", {})` (safe since always initialized)

**Duplicate function definition removed:**
- `_get_ranking(snap)` was defined in destaques block — exact duplicate of `get_ranking(snap)` defined earlier in fatos-rapidos block; replaced calls with `get_ranking(snap)`

**Duplicate data loads consolidated:**
- `leader_periods` was loaded 3 separate times in VIP tab blocks; moved to load-data block as single load

**Constant extracted from repeated inline dict:**
- `icon_map = {'big fone': '📞', ...}` appeared twice inside `render_person_cell`; extracted as `_DYNAMIC_ICON_MAP` constant above the function

**Dead code removed:**
- `if not items: return '—'` inside an `if items:` block — the outer condition guarantees `items` is truthy, making the inner check unreachable

---

## relacoes.qmd

### Issues Fixed

**Dead imports removed:**
- `from plotly.subplots import make_subplots` — never used
- `from datetime import datetime` — never used (all date parsing uses `pd.to_datetime()`)
- `import numpy as np` — never used
- `import plotly.express as px` — never used (all charts use `go` API)
- `REACTION_SLUG_TO_LABEL` from data_utils — never used
- `SENTIMENT_WEIGHTS` from data_utils — never used
- `MILD_NEGATIVE`, `STRONG_NEGATIVE` from data_utils — never used (negative reactions detected by exclusion from `POSITIVE`)
- `avatar_html`, `avatar_img` from data_utils — never called anywhere in the file

**Unused variable removed:**
- `pairs_all = relations_data.get("pairs_all", [])` — never referenced after assignment

**Import-inside-conditional antipattern fixed:**
- `from IPython.display import Markdown, display as ipy_display` was inside `if df_fav:` block → moved to setup block at top of file

---

## paredao.qmd

### Issues Fixed

**Dead imports removed:**
- `import matplotlib.pyplot as plt` — only used for `plt.rcParams` config; no matplotlib figures are created
- `import matplotlib.colors as mcolors` — `mcolors` never referenced in file body
- `import seaborn as sns` — only used for `sns.set_theme()` config; no seaborn figures are created
- `import plotly.express as px` — never used
- `from plotly.subplots import make_subplots` — never called directly (only `make_poll_timeseries` is used)
- `import numpy as np` — never used
- `from datetime import datetime` — never used

**Dead plt/sns config block removed (3 lines):**
```python
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 11
sns.set_theme(style="whitegrid", palette="husl")
```

**Dead import removed from data_utils:**
- `REACTION_SLUG_TO_LABEL` — never referenced in file body

**Unused variable removed:**
- `n_snapshots = len(snapshots)` — assigned but never used

**Inline import antipattern fixed:**
- `from data_utils import load_votalhada_polls, get_poll_for_paredao, calculate_poll_accuracy` was on line 170 inside the paredao-results code block → moved to the setup block alongside all other data_utils imports

---

## Summary

| File | Dead imports | Unused vars | Dead functions | Dead code | Antipatterns |
|------|-------------|-------------|----------------|-----------|--------------|
| `index.qmd` | 5 removed | 5 removed | 1 removed (`make_negative_givers_chart`) | plt/sns config | 3 imports-inside-scope, 1 unused param, 2 hoisted constants |
| `evolucao.qmd` | 8 removed | 0 | 1 deduped (`_get_ranking`) | 1 unreachable branch | `auto_payload` undefined risk, 3× data load deduped, constant extracted |
| `relacoes.qmd` | 9 removed | 1 removed (`pairs_all`) | 0 | 0 | 1 import-inside-conditional |
| `paredao.qmd` | 7 removed | 1 removed (`n_snapshots`) | 0 | plt/sns config | 1 inline import moved to setup |

All files passed AST syntax check after edits.
