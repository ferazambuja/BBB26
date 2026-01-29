# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Critical: Take Responsibility for Issues

**When Claude introduces bugs, warnings, or errors in code, Claude must:**
1. Take full responsibility — do not blame pre-existing issues or external factors
2. Investigate and fix the issue immediately
3. Never deflect with statements like "this wasn't from my edit" when Claude is the only one editing files

**This is non-negotiable.** If there's an error after Claude's changes, it's Claude's responsibility to fix it.

## Project Overview

BBB26 is a data analysis project that tracks **participant reaction data** from Big Brother Brasil 26 using the GloboPlay API. The main dashboard is `index.qmd` (Quarto), which loads all snapshots, processes reactions, and generates interactive Plotly visualizations.

## Program Reference (non-analytical)

General information about the TV show lives in a dedicated file:
- `docs/PROGRAMA_BBB26.md` — rules, format, selection, dynamics (kept separate from analysis)

## Environment Setup

```bash
pip install -r requirements.txt  # Python 3.10+; main deps: plotly, pandas, requests
# Quarto must be installed separately: https://quarto.org/docs/get-started/
```

## Key Commands

```bash
# Fetch new data (saves only if data changed)
python scripts/fetch_data.py

# Build derived data files (auto events, roles, participant index, index_data, cartola)
python scripts/build_derived_data.py
# Also generates docs/MANUAL_EVENTS_AUDIT.md and data/derived/manual_events_audit.json automatically (hard-fail on issues).

# Update program guide weekly timeline
python scripts/update_programa_doc.py

# Audit all snapshots (find duplicates, unique states)
python scripts/audit_snapshots.py

# Render the dashboard
quarto render index.qmd

# Preview with hot reload
quarto preview
```

## Script Usage (when to run)

- `scripts/fetch_data.py` — **daily** (or before key events); updates snapshots + derived data.
- `scripts/build_derived_data.py` — **after any manual edits** in `data/manual_events.json` or `data/paredoes.json`.
  - Também gera `data/derived/index_data.json` (tabelas leves para `index.qmd`) e `data/derived/cartola_data.json` (pontuação Cartola).
- `scripts/update_programa_doc.py` — **after weekly manual updates** (keeps `docs/PROGRAMA_BBB26.md` table in sync).
- `scripts/audit_snapshots.py` / `scripts/analyze_snapshots.py` / `scripts/compare_sameday.py` — **one-off audits**.

**Votalhada polls (manual):**
- Update `data/votalhada/polls.json` **Tuesday ~21:00 BRT** (before elimination).
- After elimination, fill `resultado_real`.
- See `docs/HANDOFF_VOTALHADA.md` and `data/votalhada/README.md`.

## Code Architecture Rules

### Single Source of Truth: `scripts/data_utils.py`

All shared constants, functions, and the Plotly theme live in **`scripts/data_utils.py`**. QMD pages and scripts import from it.

**What lives in `data_utils.py`:**
- Reaction constants: `REACTION_EMOJI`, `REACTION_SLUG_TO_LABEL`, `SENTIMENT_WEIGHTS`, `POSITIVE`, `MILD_NEGATIVE`, `STRONG_NEGATIVE`
- Visual constants: `GROUP_COLORS`, `POWER_EVENT_EMOJI`, `POWER_EVENT_LABELS`
- Cartola constants: `CARTOLA_POINTS`, `POINTS_LABELS`, `POINTS_EMOJI`
- Theme colors: `PLOT_BG`, `PAPER_BG`, `GRID_COLOR`, `TEXT_COLOR`, `BBB_COLORWAY`
- Theme setup: `setup_bbb_dark_theme()` — registers and activates the Plotly dark theme
- Shared functions: `calc_sentiment()`, `load_snapshot()`, `get_all_snapshots()`, `parse_roles()`, `build_reaction_matrix()`, `get_week_number()`
- Data loaders: `load_votalhada_polls()`, `load_sincerao_edges()`, `get_poll_for_paredao()`, `calculate_poll_accuracy()`
- Audit: `require_clean_manual_events()`

**QMD setup pattern** (every `.qmd` file follows this):
```python
import sys
sys.path.append(str(Path("scripts").resolve()))
from data_utils import (
    require_clean_manual_events, calc_sentiment, setup_bbb_dark_theme,
    REACTION_EMOJI, SENTIMENT_WEIGHTS, POSITIVE, MILD_NEGATIVE, STRONG_NEGATIVE,
    GROUP_COLORS, # ... other imports as needed
)

require_clean_manual_events()
setup_bbb_dark_theme()
```

### Calculations in Scripts, Not QMD Pages

**Rule**: Heavy computation should happen in Python scripts (`scripts/`) that output to `data/derived/`. QMD pages should load precomputed data and render visualizations.

| Location | Purpose | Examples |
|----------|---------|---------|
| `scripts/data_utils.py` | Shared constants, functions, theme | `calc_sentiment()`, `REACTION_EMOJI`, `CARTOLA_POINTS` |
| `scripts/build_derived_data.py` | Heavy computation → JSON | roles_daily, auto_events, daily_metrics, plant_index, cartola_data |
| `scripts/build_index_data.py` | Precompute index page data → JSON | profiles, rankings, highlights, cross-table |
| `*.qmd` pages | Load JSON + render visualizations | Charts, tables, HTML output |

**Anti-patterns to avoid:**
- Defining `calc_sentiment()` locally in a QMD file (import from `data_utils`)
- Copy-pasting `REACTION_EMOJI`, `GROUP_COLORS`, `POSITIVE/MILD_NEGATIVE/STRONG_NEGATIVE` (import from `data_utils`)
- Defining the Plotly `bbb_dark` template inline (call `setup_bbb_dark_theme()`)
- Computing in QMD what could be precomputed in a script (use `data/derived/`)

**Documented exception (temporary):**
- `planta.qmd` ainda monta algumas listas por participante (ex.: eventos por pessoa e edges do Sincerão) **para facilitar a leitura**.
  Se essas listas começarem a ser reutilizadas em outras páginas, migrar para `build_derived_data.py` e salvar em `data/derived/`.

## Known Issues

### Quarto render warnings in trajetoria.qmd

When rendering `trajetoria.qmd`, Pandoc reports warnings about unclosed divs:
```
[WARNING] Div at line 437 column 1 unclosed at line 2493...
[WARNING] The following string was found in the document: :::
```

**Cause**: Pandoc/Quarto processing quirk with complex documents containing fenced divs and dynamic markdown output.

**Impact**: None — the final HTML is valid and renders correctly. The TOC works properly.

## Data Architecture

### API Source
- **Endpoint**: `https://apis-globoplay.globo.com/mve-api/globo-play/realities/bbb/participants/`
- **Returns**: Complete state snapshot — NOT cumulative, NOT additive
- **No timestamp**: API provides no `Last-Modified` header or update timestamp
- **Update frequency**: Data changes daily at unpredictable times, with intraday changes possible
- **Eliminação**: o participante **some da lista**; o campo `eliminated` na API não é confiável (geralmente sempre `false`). Exit detection is automatic via `data/derived/eliminations_detected.json`.

### Critical: Reactions Are Reassigned Daily

The API returns the **current state** of all reactions, not a history. Participants **change** their reactions to others daily. **Every snapshot is a unique complete game state** and must be kept.

### Snapshot Format
- New format wraps data: `{ "_metadata": {...}, "participants": [...] }`; old format is just the raw array.
- `scripts/fetch_data.py` handles both formats and saves only when data hash changes.
- **Synthetic snapshots** have `_metadata.synthetic = true`.

### Data Sources (auto vs manual vs derived)

**Auto (from API snapshots)** — produced by `scripts/fetch_data.py`:
- `data/snapshots/*.json` — daily state of reactions + roles + groups (source of truth)
- `data/latest.json` — copy of most recent snapshot

**Manual (human-maintained):**
- `data/manual_events.json` — power events + weekly events not in API. See `docs/MANUAL_EVENTS_GUIDE.md`.
- `data/paredoes.json` — paredão formation + votos da casa + resultado + % público. See `docs/HANDOFF_PAREDAO.md`.
- `data/votalhada/polls.json` — poll aggregation from Votalhada. See `docs/HANDOFF_VOTALHADA.md`.

**Derived** (`data/derived/`, built by `scripts/build_derived_data.py`):
- `roles_daily.json` — roles + VIP per day
- `auto_events.json` — auto power events (Líder/Anjo/Monstro/Imune)
- `daily_metrics.json` — sentiment + reaction totals per day
- `participants_index.json` — canonical participant list (name, avatar, active, first/last seen)
- `index_data.json` — precomputed tables for `index.qmd`
- `plant_index.json` — Planta Index per week + rolling averages
- `cartola_data.json` — Cartola BBB points (leaderboard, weekly breakdown, stats)
- `relations_scores.json` — pairwise sentiment scores (A→B) with **daily** and **paredão** versions
- `sincerao_edges.json` — Sincerão aggregates + optional edges
- `snapshots_index.json` — manifest of available dates for the Date View
- `validation.json`, `manual_events_audit.json`, `eliminations_detected.json` — sanity checks

### Reaction Categories
```python
POSITIVE = ['Coração']  # ❤️
MILD_NEGATIVE = ['Planta', 'Mala', 'Biscoito', 'Coração partido']  # 🌱💼🍪💔
STRONG_NEGATIVE = ['Cobra', 'Alvo', 'Vômito', 'Mentiroso']  # 🐍🎯🤮🤥
```

Sentiment weights: positive = +1, mild_negative = -0.5, strong_negative = -1

**Note**: 💔 Coração partido is classified as **mild negative** (disappointment, not hostility).

### Important: Queridômetro is SECRET

**Participants do NOT see each other's reactions.** The queridômetro is only visible to the TV audience and participants after they leave.

**Language to AVOID**: "traíram a amizade declarada", "inimigos declarados", "demonstravam afeto público"
**Correct language**: "davam ❤️" (factual), "contradição entre reação e voto", "hostilidade mútua" (secretly mutual)

### Hostility Analysis

**Two-sided (mutual) hostility**: Both A and B give each other negative reactions — both secretly dislike each other.

**One-sided (unilateral) hostility**: A gives B negative, but B gives A ❤️ — creates **blind spots** where B may be surprised when A votes against them.

**Vulnerability ratio**: `(hearts given to enemies) / (attacks on friends + 1)` — high ratio = major blind spots.

### Data Update Timing

| Data Type | Update Time (BRT) | Stability |
|-----------|-------------------|-----------|
| **Reactions (Queridômetro)** | ~10h-12h daily | Stable after morning Raio-X |
| **Balance (Estalecas)** | Any time | Changes with purchases, rewards, punishments |
| **Roles** | During/after episodes | Líder, Anjo, Monstro, Paredão ceremonies |

### Multi-Capture Strategy

GitHub Actions runs **4x daily**: 06:00, 12:00 (primary), 18:00, 00:00 BRT.
`fetch_data.py` saves **only if data hash changed**. Multiple snapshots per day are normal.

### Two Data Views in Dashboard

1. **All captures** (`snapshots`) — Balance timelines, role tracking, intraday analysis
2. **Daily captures** (`daily_snapshots`) — One per date (last capture). Reaction-based charts, day-over-day comparisons, sentiment evolution

### Volatile Fields (change daily)
- `balance`, `roles`, `group` (Vip ↔ Xepa), `receivedReactions` (amounts AND givers)
- `eliminated` — **always false in practice**; participants who leave simply disappear

### Synthetic Snapshots

When a date is missed, build a synthetic snapshot from GShow's queridômetro article using `scripts/build_jan18_snapshot.py` as template. Hearts are inferred (complete directed graph). Mark with `_metadata.synthetic = true`.

### Participant Timeline

| Date | Count | Event |
|------|-------|-------|
| Jan 13 | 21 | Initial cast |
| Jan 15 | 20 | Henri Castelli **desistiu** (quit) |
| Jan 18 | 24 | Chaiany, Gabriela, Leandro, Matheus enter |
| Jan 19 | 23 | Pedro **desistiu** (quit) |
| Jan 21 | 22 | Aline Campos **eliminada** (1º Paredão) |

## Scoring & Indexes (summary)

All scoring formulas, weights, and detailed specifications are in **`docs/SCORING_AND_INDEXES.md`**. Key concepts:

- **Sentiment Index (A → B)**: directional score combining queridômetro (3-day window) + all accumulated events (power, Sincerão, VIP, votos) at full weight (no decay). Two modes: `pairs_daily` (today's queridômetro) and `pairs_paredao` (formation-date queridômetro); events are identical in both.
- **Planta Index**: weekly score (0–100) quantifying low visibility + low participation. Weights: 0.45 power activity + 0.35 Sincerão exposure + 0.20 🌱 emoji ratio. Computed in `data/derived/plant_index.json`.
- **Risco Externo**: weekly per-participant risk from votes received + public/secret negative events + paredão status.
- **Animosidade**: historical directional score (no decay — events accumulate). Experimental.
- **Cartola BBB**: point system (Líder +80 to Desistente -30). Precomputed in `data/derived/cartola_data.json`.

Power events are **modifiers** (rare, one-to-one), not the base — queridômetro drives ongoing sentiment.

## Manual Events (quick reference)

Full schema, fill rules, and update procedures are in **`docs/MANUAL_EVENTS_GUIDE.md`**.

**Structure**: `participants` (exits), `weekly_events` (Big Fone, Sincerão, Ganha‑Ganha, Barrado no Baile), `special_events` (dinâmicas), `power_events` (contragolpe, veto, voto duplo, ganha‑ganha, barrado, etc.), `cartola_points_log` (manual overrides).

**API auto-detects**: Líder, Anjo, Monstro, Imune, VIP, Paredão. Manual events fill what the API does not expose.

**After any edit**: run `python scripts/build_derived_data.py` to update derived data.

## Repository Structure

```
BBB26/
├── index.qmd               # Main dashboard — overview, rankings, heatmap, profiles
├── mudancas.qmd            # Day-over-day changes (O Que Mudou)
├── trajetoria.qmd          # Trajectory — sentiment evolution, hostilities, clusters, graphs
├── paredao.qmd             # Current paredão status + vote analysis
├── paredoes.qmd            # Paredão archive — historical analysis per paredão
├── cartola.qmd             # Cartola BBB points leaderboard
├── planta.qmd              # Planta Index breakdown per participant
├── datas.qmd               # Date View — explore queridômetro by date
├── clusters.qmd            # Affinity clusters analysis
├── relacoes_debug.qmd      # Relations scoring debug page
├── _quarto.yml             # Quarto configuration (website with navbar)
├── data/
│   ├── snapshots/           # Canonical JSON snapshots (one per unique data state)
│   ├── derived/             # Precomputed JSON (built by scripts)
│   ├── votalhada/           # Poll aggregation data
│   ├── latest.json          # Most recent snapshot
│   ├── paredoes.json        # Paredão data (formation, house votes, results)
│   └── manual_events.json   # Manual game events (Big Fone, exits, special events)
├── scripts/
│   ├── data_utils.py        # Single source of truth — constants, functions, theme
│   ├── fetch_data.py        # Fetch API, save if changed (hash comparison)
│   ├── build_derived_data.py # Build all derived JSON files
│   ├── build_index_data.py  # Precompute index page tables
│   ├── audit_manual_events.py # Audit manual events for consistency
│   ├── audit_snapshots.py   # Audit tool for deduplication
│   └── update_programa_doc.py # Update program guide timeline
├── docs/
│   ├── SCORING_AND_INDEXES.md    # Full scoring formulas and index specs
│   ├── HANDOFF_PAREDAO.md        # Paredão workflow, schemas, display logic
│   ├── MANUAL_EVENTS_GUIDE.md    # Manual events schema and fill rules
│   ├── HANDOFF_VOTALHADA.md      # Votalhada poll collection workflow
│   └── PROGRAMA_BBB26.md         # TV show rules, format, dynamics
├── requirements.txt         # Python dependencies
└── IMPLEMENTATION_PLAN.md   # GitHub Actions + Quarto + Pages plan
```

## Page Architecture

**Main navbar pages:**

| Page | File | Purpose |
|------|------|---------|
| **Painel** | `index.qmd` | Main dashboard: overview, ranking, heatmap, profiles |
| **O Que Mudou** | `mudancas.qmd` | Day-over-day changes: winners/losers, volatility, Sankey |
| **Trajetória** | `trajetoria.qmd` | Evolution: sentiment, alliances, hostilities, clusters, graphs |
| **Paredão** | `paredao.qmd` | Current paredão: formation, votes, vote-reaction analysis |
| **Arquivo** | `paredoes.qmd` | Paredão archive: historical analysis per elimination |

**Additional pages:** `cartola.qmd` (Cartola points), `planta.qmd` (Planta Index), `datas.qmd` (Date View), `clusters.qmd` (affinity clusters), `relacoes_debug.qmd` (relations debug).

**Design decisions**: Each `.qmd` renders independently (no shared Python state). Dark theme (`darkly`) with custom `bbb_dark` Plotly template. Full-width layout with TOC sidebar.

**Data source tags**: 📸 Dado do dia (latest snapshot) | 📅 Comparação dia-a-dia | 📈 Dado acumulado | 🗳️ Paredão-anchored

## Data Freshness and Paredão Archival

**Principle**: Live pages use `latest`/`snapshots[-1]`. Finalized paredão analysis uses **paredão-date snapshot ONLY** (historical archive must be frozen).

**Why**: When analyzing "did reactions predict votes?", we MUST use data from before/during voting, not after. Using Wednesday's data to analyze Tuesday's votes is **invalid**.

**Common mistake**: Using `latest` or `snapshots[-1]` in paredão analysis. Always use `get_snapshot_for_date(paredao_date)` for finalized paredões.

For implementation details (code patterns, archival process, snapshot timing): see **`docs/HANDOFF_PAREDAO.md`**.

## Paredão Workflow (quick reference)

Full step-by-step workflow, data schemas, and display logic are in **`docs/HANDOFF_PAREDAO.md`**.

**Status system**: `em_andamento` (Sunday night → Tuesday night) | `finalizado` (after result).

**Update timing**:
- **Mid-week**: Dinâmica nominates someone → create partial entry in `data/paredoes.json`
- **Sunday ~22h45**: Full formation → update entry with all nominees + `votos_casa`
- **Tuesday ~23h**: Result announced → set `finalizado`, add vote percentages

**Voting system (BBB 26)**: Voto Único (CPF, 70%) + Voto da Torcida (unlimited, 30%) = Média Final.

## Critical: Name Matching Between Manual Data and API

The `votos_casa` dict and all manual data use participant names as keys. These **MUST match exactly** with the names in the API snapshots.

**Official API Names (as of Jan 2026):**

| API Name | Group | Notes |
|----------|-------|-------|
| `Alberto Cowboy` | Veterano | Full name used |
| `Ana Paula Renault` | Veterano | Full name used |
| `Babu Santana` | Veterano | Full name used |
| `Breno` | Pipoca | First name only |
| `Brigido` | Pipoca | First name only (not "Brígido") |
| `Chaiany` | Pipoca | First name only (entered Jan 18) |
| `Edilson` | Camarote | **NOT** "Edilson Capetinha" |
| `Gabriela` | Pipoca | First name only (entered Jan 18) |
| `Jonas Sulzbach` | Veterano | Full name used |
| `Jordana` | Pipoca | First name only |
| `Juliano Floss` | Camarote | Full name used |
| `Leandro` | Pipoca | First name only (entered Jan 18) |
| `Marcelo` | Pipoca | First name only |
| `Marciele` | Pipoca | First name only |
| `Matheus` | Pipoca | First name only (entered Jan 18) |
| `Maxiane` | Pipoca | First name only |
| `Milena` | Pipoca | First name only |
| `Paulo Augusto` | Pipoca | Full name used |
| `Samira` | Pipoca | First name only |
| `Sarah Andrade` | Veterano | Full name used |
| `Sol Vega` | Veterano | Full name used |
| `Solange Couto` | Camarote | Full name used |

**Eliminated/Exited (no longer in API):**
- `Aline Campos` — Eliminada (1º Paredão, Jan 21)
- `Henri Castelli` — Desistente (Jan 15)
- `Pedro` — Desistente (Jan 19)

**Before adding manual data**, always verify names against the snapshot:
```python
python3 -c "
import json
with open('data/latest.json') as f:
    data = json.load(f)
participants = data['participants'] if 'participants' in data else data
for p in participants:
    print(p['name'])
"
```

## Votalhada Poll Data (summary)

Votalhada aggregates poll results from multiple platforms during paredões.
Full schema, workflow, and dashboard integration: see **`docs/HANDOFF_VOTALHADA.md`** and **`data/votalhada/README.md`**.

**Quick workflow**: Screenshot Consolidados → save to `data/` → tell Claude to process it → updates `data/votalhada/polls.json`.

**Loader functions**: `load_votalhada_polls()`, `get_poll_for_paredao()`, `calculate_poll_accuracy()` from `data_utils`.

## Future Plans

See `IMPLEMENTATION_PLAN.md` for GitHub Actions + Quarto + GitHub Pages automation setup.
