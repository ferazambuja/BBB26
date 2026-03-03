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
- `scripts/analyze_capture_timing.py` — **weekly** (checks whether probes are catching Raio-X updates and if the 15:00 BRT primary slot can be adjusted).
- `scripts/audit_snapshots.py` / `scripts/analyze_snapshots.py` / `scripts/compare_sameday.py` — **one-off audits**.

**Scheduled events (upcoming week dynamics):**
- Add future events to `data/manual_events.json` → `scheduled_events` array with `date`, `week`, `category`, `emoji`, `title`, `detail`, `time` (e.g., "Ao Vivo", "7h", "A definir").
- `build_game_timeline()` includes them in `game_timeline.json` with `"status": "scheduled"` and `"source": "scheduled"`.
- Auto-dedup by `(date, category)`: if a real event already exists with the same date and category, the scheduled entry is automatically skipped (regardless of title differences).
- Rendered in Cronologia do Jogo (via `render_cronologia_html()` from `data_utils`) with dashed borders, outlined badges, yellow time badge, and 🔮 prefix.
- **After an event happens**: record the real data normally, rebuild. The scheduled entry is auto-dropped if a matching real event exists. Clean up past entries periodically.
- **Weekly pattern**: See `docs/OPERATIONS_GUIDE.md` → "Standard Week Pattern" for the full recurring cycle. Key: **Sincerão is every Monday** (~22h live show, format varies weekly), separate from the Friday "Week Dynamic" (Bloco, Exilado, Big Fone, etc.). Checklist includes: Sincerão (Mon), Ganha-Ganha (Tue), Barrado (Wed), Líder (Thu), Dynamic (Fri), Anjo/Monstro (Sat), Paredão (Sun), Eliminação (Tue).

**Votalhada polls (manual):**
- Update `data/votalhada/polls.json` **Tuesday ~21:00 BRT** (before elimination).
- After elimination, fill `resultado_real`.
- See `data/votalhada/README.md` for screenshot workflow.

## Code Architecture Rules

### Single Source of Truth: `scripts/data_utils.py`

All shared constants, functions, and the Plotly theme live in **`scripts/data_utils.py`**. QMD pages and scripts import from it.

**What lives in `data_utils.py`:**
- Reaction constants: `REACTION_EMOJI`, `REACTION_SLUG_TO_LABEL`, `SENTIMENT_WEIGHTS`, `POSITIVE`, `MILD_NEGATIVE`, `STRONG_NEGATIVE`
- Visual constants: `GROUP_COLORS`, `POWER_EVENT_EMOJI`, `POWER_EVENT_LABELS`
- Cartola constants: `CARTOLA_POINTS`, `POINTS_LABELS`, `POINTS_EMOJI`
- Analysis descriptions: `ANALYSIS_DESCRIPTIONS` — centralized explanation text for QMD pages (composite score, profiles intro/footer, vulnerability explanation). Single source of truth for scoring descriptions shown to users.
- Theme colors: `PLOT_BG`, `PAPER_BG`, `GRID_COLOR`, `TEXT_COLOR`, `BBB_COLORWAY`
- Theme setup: `setup_bbb_dark_theme()` — registers and activates the Plotly dark theme
- Week boundaries: `WEEK_END_DATES` — Líder-transition-based dates that define game week boundaries
- Premiere constant: `BBB26_PREMIERE` — start date of the season (`"2026-01-13"`)
- Shared functions: `calc_sentiment()`, `load_snapshot()`, `get_all_snapshots()`, `utc_to_game_date()`, `parse_roles()`, `build_reaction_matrix()`, `get_week_number()`, `get_week_start_date()`
- Data loaders: `load_votalhada_polls()`, `load_sincerao_edges()`, `get_poll_for_paredao()`, `calculate_poll_accuracy()`
- Timeline rendering: `render_cronologia_html()`, `TIMELINE_CAT_COLORS`, `TIMELINE_CAT_LABELS`
- Votalhada helpers: `MONTH_MAP_PT`, `parse_votalhada_hora()`, `make_poll_timeseries()`
- Avatar HTML helpers: `avatar_html()`, `avatar_img()`
- Gender helpers: `genero()`, `artigo()`
- Nominee helpers: `get_nominee_badge()`
- Audit: `require_clean_manual_events()`

**QMD setup pattern** (every `.qmd` file follows this):
```python
import sys
sys.path.append(str(Path("scripts").resolve()))
from data_utils import (
    require_clean_manual_events, calc_sentiment, setup_bbb_dark_theme,
    REACTION_EMOJI, SENTIMENT_WEIGHTS, POSITIVE, MILD_NEGATIVE, STRONG_NEGATIVE,
    GROUP_COLORS, ANALYSIS_DESCRIPTIONS, # ... other imports as needed
)

require_clean_manual_events()
setup_bbb_dark_theme()
```

### Calculations in Scripts, Not QMD Pages

**Rule**: Heavy computation should happen in Python scripts (`scripts/`) that output to `data/derived/`. QMD pages should load precomputed data and render visualizations.

| Location | Purpose | Examples |
|----------|---------|---------|
| `scripts/data_utils.py` | Shared constants, functions, theme | `calc_sentiment()`, `REACTION_EMOJI`, `CARTOLA_POINTS` |
| `scripts/builders/*.py` | Heavy computation → JSON | relations, cartola, clusters, plant_index, etc. (11 domain modules) |
| `scripts/build_derived_data.py` | Pipeline orchestrator | Imports from builders/, writes to data/derived/ |
| `scripts/build_index_data.py` | Precompute index page data → JSON | profiles, rankings, highlights, cross-table |
| `*.qmd` pages | Load JSON + render visualizations | Charts, tables, HTML output |

**Anti-patterns to avoid:**
- Defining `calc_sentiment()` locally in a QMD file (import from `data_utils`)
- Copy-pasting `REACTION_EMOJI`, `GROUP_COLORS`, `POSITIVE/MILD_NEGATIVE/STRONG_NEGATIVE` (import from `data_utils`)
- Defining the Plotly `bbb_dark` template inline (call `setup_bbb_dark_theme()`)
- Computing in QMD what could be precomputed in a script (use `data/derived/`)
- Hardcoding scoring explanation text in QMD files (use `ANALYSIS_DESCRIPTIONS` from `data_utils`)

**Documented exception (temporary):**
- `planta_debug.qmd` ainda monta algumas listas por participante (ex.: eventos por pessoa e edges do Sincerão) **para facilitar a leitura**.
  Se essas listas começarem a ser reutilizadas em outras páginas, migrar para `build_derived_data.py` e salvar em `data/derived/`.

## Tool Preferences

- **Code navigation**: Prefer LSP operations (`goToDefinition`, `findReferences`, `hover`, `documentSymbol`) over Grep/Glob when navigating Python code. Use LSP for finding references, understanding types, and tracing call chains.
- **When to use LSP**: After locating a symbol (via Grep/Glob), use LSP for follow-up navigation — finding all callers, checking type signatures, listing definitions, and understanding scope.
- **When Grep/Glob is still appropriate**: Initial broad text searches, searching across non-Python files (JSON, QMD, Markdown), and pattern matching where semantic analysis isn't needed.

## Known Issues

*(No known issues at this time.)*

## Data Architecture

### API Source
- **Endpoint**: `https://apis-globoplay.globo.com/mve-api/globo-play/realities/bbb/participants/`
- **Returns**: Complete state snapshot — NOT cumulative, NOT additive
- **No timestamp**: API provides no `Last-Modified` header or update timestamp
- **Update frequency**: Data changes daily at unpredictable times, with intraday changes possible
- **Eliminação**: o participante **some da lista**; o campo `eliminated` na API não é confiável (geralmente sempre `false`). Exit detection is automatic via `data/derived/eliminations_detected.json`.

### Critical: Reactions Are Reassigned Daily

The API returns the **current state** of all reactions, not a history. Participants **change** their reactions to others daily. **Every snapshot is a unique complete game state** and must be kept.

### Missing Raio-X Safeguard

When a participant misses the morning Raio-X, the API returns them with 0 outgoing reactions. The scoring pipeline (`build_derived_data.py`) automatically detects this (0 outgoing reactions for an active participant) and carries forward their previous day's reactions via `patch_missing_raio_x()` from `data_utils.py`. Detection is data-driven (no hardcoded names). Metadata logged in `relations_scores.json` → `missing_raio_x`. QMD display pages are NOT patched — they show raw API data. See `docs/SCORING_AND_INDEXES.md` for full details.

### Snapshot Format
- New format wraps data: `{ "_metadata": {...}, "participants": [...] }`; old format is just the raw array.
- `scripts/fetch_data.py` handles both formats and saves only when data hash changes.
- **Synthetic snapshots** have `_metadata.synthetic = true`.

### Snapshot Timestamps (UTC)
- **Filenames are always UTC**: `YYYY-MM-DD_HH-MM-SS.json` in UTC.
- **`_metadata.captured_at`**: ISO 8601 with `+00:00` UTC timezone suffix.
- **Game-date extraction**: `utc_to_game_date()` converts UTC→BRT and applies a 06:00 BRT cutoff. Captures before 06:00 BRT belong to the **previous** game day (no Raio-X happens overnight). This is used by `get_all_snapshots()` and `get_daily_snapshots()` in all scripts.
- **`fetch_data.py`** uses `datetime.now(timezone.utc)` for both filenames and metadata.

### Data Sources (auto vs manual vs derived)

**Auto (from API snapshots)** — produced by `scripts/fetch_data.py`:
- `data/snapshots/*.json` — daily state of reactions + roles + groups (source of truth)
- `data/latest.json` — copy of most recent snapshot

**Manual (human-maintained):**
- `data/manual_events.json` — power events + weekly events not in API. See `docs/MANUAL_EVENTS_GUIDE.md`.
- `data/paredoes.json` — paredão formation + votos da casa + resultado + % público.
- `data/provas.json` — competition results and placements for all BBB26 provas (Líder, Anjo, Bate e Volta).
- `data/votalhada/polls.json` — poll aggregation from Votalhada.

**Derived** (`data/derived/`, built by `scripts/build_derived_data.py`):
- `roles_daily.json` — roles + VIP per day
- `auto_events.json` — auto power events (Líder/Anjo/Monstro/Imune)
- `daily_metrics.json` — sentiment + reaction totals per day
- `participants_index.json` — canonical participant list (name, avatar, active, first/last seen)
- `index_data.json` — precomputed tables for `index.qmd`
- `plant_index.json` — Planta Index per week + rolling averages
- `cartola_data.json` — Cartola BBB points (leaderboard, weekly breakdown, stats)
- `relations_scores.json` — pairwise sentiment scores (A→B) with **daily** and **paredão** versions, plus `streak_breaks` (detected alliance ruptures)
- `sincerao_edges.json` — Sincerão aggregates + optional edges
- `prova_rankings.json` — competition performance rankings (leaderboard, per-prova detail)
- `snapshots_index.json` — manifest of available dates for the Date View
- `game_timeline.json` — unified chronological timeline (past + scheduled events). Displayed in `index.qmd` and `evolucao.qmd`.
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

### Game Week Boundaries

BBB game weeks are **not** calendar 7-day periods. Each week is defined by a **Líder cycle**: it starts when a new Líder is defined (typically Thursday night Prova do Líder) and ends the day before the next Líder is defined. The paredão result AND the barrado no baile both belong to the week of the Líder who presided over them. Week lengths vary (6–9 days).

`get_week_number(date_str)` uses `WEEK_END_DATES` (a sorted list of week-end dates) with `bisect_left`. The boundary date is **inclusive** — it belongs to the week it ends.

| Week | End Date | Líder | Paredão | Next Líder |
|------|----------|-------|---------|------------|
| 1 | 2026-01-21 | Alberto Cowboy | 1º (Jan 21) | Babu (Jan 22) |
| 2 | 2026-01-28 | Babu Santana | 2º (Jan 27) | Maxiane (Jan 29) |
| 3 | 2026-02-04 | Maxiane | 3º (Feb 3) | Jonas (Feb 5) |
| 4 | 2026-02-12 | Jonas Sulzbach | 4º (Feb 10) | Jonas (Feb 13) |
| 5 | 2026-02-18 | Jonas Sulzbach | 5º (Feb 17) | Jonas (?) |
| 6 | 2026-02-25 | Jonas Sulzbach | 6º (Feb 25) | Samira (Feb 26) |
| 7 | TBD | Samira | 7º (Mar 3, Falso) | ??? |

**When a new Líder is crowned**: follow the **Líder Transition Checklist** in `docs/OPERATIONS_GUIDE.md` — create paredão skeleton (critical for `leader_periods`), update provas, scrape articles, add scheduled events. **When a Líder cycle completes**: update `WEEK_END_DATES` in `data_utils.py` with the last day of that week (day before next Prova do Líder).

**Consecutive Líder**: When the same person wins multiple Prova do Líder, each term is a separate week with its own `WEEK_END_DATES` entry. The `leader_periods` in `index_data.json` are derived from `WEEK_END_DATES` + `paredoes.json` (not from API role changes), so consecutive same-person terms are correctly separated.

### Source Citations (fontes)

`paredoes.json` stores source references as objects in the `fontes` array:

```json
"fontes": [
  {"url": "https://gshow.globo.com/.../slug.ghtml", "arquivo": "docs/scraped/slug.md", "titulo": "Article Title"},
  {"url": "https://gshow.globo.com/.../outro.ghtml", "arquivo": null, "titulo": null}
]
```

- `url` — required, the web source URL
- `arquivo` — relative path to local scraped `.md` copy (in `docs/scraped/`), or `null`
- `titulo` — optional article title, or `null`

**When adding new sources**: add the entry with both `url` and `arquivo` filled. Older entries may have `arquivo: null` — fill retroactively when convenient.

### Data Update Timing

| Data Type | Update Time (BRT) | Stability |
|-----------|-------------------|-----------|
| **Reactions (Queridômetro)** | ~10h–12h daily | Raio-X in the morning; API publishes shortly after (~10:30 BRT observed Mar 3). Timing probes active to confirm window. |
| **Balance (Estalecas)** | Any time | Changes with purchases, rewards, punishments |
| **Roles** | During/after episodes | Líder, Anjo, Monstro, Paredão ceremonies |

### Multi-Capture Strategy

GitHub Actions runs permanent slots at **00:00, 06:00, 15:00, 18:00 BRT** plus Saturday extras at **17:00** and **20:00 BRT** (6 runs/day, 8 on Saturdays).
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
| Jan 28 | 21 | Matheus **eliminado** (2º Paredão) |
| Jan 30 | 20 | Paulo Augusto **desclassificado** (agressão durante Big Fone) |
| Feb 3 | 19 | Brigido **eliminado** (3º Paredão) |
| Feb 10 | 18 | Sarah Andrade **eliminada** (4º Paredão) |
| Feb 11 | 17 | Sol Vega **desclassificada** (confronto com Ana Paula Renault) |
| Feb 14 | 16 | Edilson **desclassificado** (discussão com Leandro Boneco) |
| Feb 17 | 15 | Marcelo **eliminado** (5º Paredão) |
| Feb 25 | 14 | Maxiane **eliminada** (6º Paredão) |

## Scoring & Indexes (summary)

All scoring formulas, weights, and detailed specifications are in **`docs/SCORING_AND_INDEXES.md`**. Key concepts:

- **Sentiment Index (A → B)**: directional score combining streak-aware queridômetro (70% 3-day reactive window + 30% streak memory + break penalty) + all accumulated events (power, Sincerão, VIP, votos) at full weight (no decay). Two modes: `pairs_daily` (today's queridômetro) and `pairs_paredao` (formation-date queridômetro); events are identical in both. Streak breaks (long ❤️ streaks turning negative) are detected and stored in `streak_breaks`.
- **Planta Index**: weekly score (0–100) quantifying low visibility + low participation. Weights: 0.10 invisibility + 0.35 power activity + 0.25 Sincerão exposure + 0.15 🌱 emoji ratio + 0.15 heart uniformity (soft-gated by activity). Sincerão carry-forward with 0.7× decay. Computed in `data/derived/plant_index.json`.
- **Impacto Negativo**: per-participant negative impact received, from `received_impact` in `relations_scores.json`. Same calibrated weights as pairs system, no decay.
- **Hostilidade Gerada**: per-participant outgoing negative event edges, from `pairs_daily` components (non-queridômetro). Same calibrated weights, no decay.
- **Cartola BBB**: point system (Líder +80 to Desistente -30). Precomputed in `data/derived/cartola_data.json`.
- **Prova Rankings**: competition performance ranking with type multipliers (Líder 1.5×, Anjo 1.0×, Bate-Volta 0.75×) and placement points (1st=10 to 9th+=0.5). Precomputed in `data/derived/prova_rankings.json`.
- **VIP/Xepa Tracking**: VIP week = participant in VIP during a leader period. Counted at leader transitions only (from `roles_daily.json` Líder changes). `leader_periods` in `index_data.json` stores full composition per leader. See `docs/SCORING_AND_INDEXES.md` for details.

- **Líder Nomination Prediction**: ranks all participants by Líder → target score from `pairs_daily` (most negative = most likely nomination). Shows on `paredao.qmd` between paredões and during incomplete formation. Includes component breakdown, reciprocity analysis, expandable edge/queridômetro detail rows, VIP/immunity flags. Auto-hides when formation is complete. See `docs/SCORING_AND_INDEXES.md` for full spec.
- **Modelo Ponderado por Precisão**: re-weights Votalhada platform predictions using inverse-RMSE² (precision weighting). Votalhada weights by vote volume (Sites ~70%), but Sites are the least accurate. Model weights: Twitter 55% · Instagram 33% · YouTube 9% · Sites 4%. Validated with leave-one-out cross-validation (MAE 9.8→4.3 p.p., −56%). Functions: `calculate_precision_weights()`, `predict_precision_weighted()`, `backtest_precision_model()` in `data_utils.py`. See `docs/SCORING_AND_INDEXES.md` for full derivation.

Power events are **modifiers** (rare, one-to-one), not the base — queridômetro drives ongoing sentiment.

## Manual Events (quick reference)

Full schema, fill rules, and update procedures are in **`docs/MANUAL_EVENTS_GUIDE.md`**.

**Structure**: `participants` (exits), `weekly_events` (Big Fone, Sincerão, Ganha‑Ganha, Barrado no Baile, vote visibility events), `special_events` (dinâmicas), `power_events` (contragolpe, veto, voto duplo, ganha‑ganha, barrado, etc.), `cartola_points_log` (manual overrides).

**API auto-detects**: Líder, Anjo, Monstro, Imune, VIP, Paredão. Manual events fill what the API does not expose.

**Vote visibility** (in `weekly_events`): `confissao_voto` (voluntary confession to target), `dedo_duro` (game mechanic reveals vote). For full-week open voting, set `votacao_aberta: true` in the paredão entry in `data/paredoes.json`. See `docs/MANUAL_EVENTS_GUIDE.md` for full schema.

**Consensus events** (multiple actors on one target): Use a **single** `power_event` with `"actor": "A + B + C"` (display string) and `"actors": ["A", "B", "C"]` (array for edge creation). This produces 1 timeline row + N correct relationship edges. Never use separate entries per actor.

**After any edit**: run `python scripts/build_derived_data.py` to update derived data.

## Repository Structure

```
BBB26/
├── index.qmd               # Main dashboard — overview, rankings, heatmap, profiles
├── evolucao.qmd            # Temporal evolution — rankings, sentiment, impact, daily pulse, balance
├── relacoes.qmd            # Social fabric — alliances, rivalries, streak breaks, contradictions, network
├── paredao.qmd             # Current paredão status + vote analysis + Líder nomination prediction
├── paredoes.qmd            # Paredão archive — historical analysis per paredão
├── cartola.qmd             # Cartola BBB points leaderboard
├── planta_debug.qmd        # Planta Index debug breakdown
├── datas.qmd               # Date View — explore queridômetro by date
├── clusters.qmd            # Affinity clusters analysis
├── relacoes_debug.qmd      # Relations scoring debug page
├── _quarto.yml             # Quarto configuration (website with navbar)
├── data/
│   ├── snapshots/           # Canonical JSON snapshots (one per unique data state)
│   ├── derived/             # Precomputed JSON (built by scripts)
│   ├── votalhada/           # Poll aggregation data + README.md
│   ├── latest.json          # Most recent snapshot
│   ├── paredoes.json        # Paredão data (formation, house votes, results)
│   ├── provas.json          # Competition results (Líder, Anjo, Bate e Volta)
│   ├── manual_events.json   # Manual game events (Big Fone, exits, special events, scheduled)
│   └── CHANGELOG.md         # API data change audit + snapshot history
├── scripts/
│   ├── data_utils.py        # Single source of truth — constants, functions, theme
│   ├── fetch_data.py        # Fetch API, save if changed (hash comparison)
│   ├── build_derived_data.py # Pipeline orchestrator (imports from builders/)
│   ├── builders/            # Domain modules for derived data pipeline
│   │   ├── relations.py     # Pairwise scoring engine (~1,100 lines)
│   │   ├── daily_analysis.py # Daily metrics, hostility, vulnerability
│   │   ├── participants.py  # Participant index, roles, auto events
│   │   ├── plant_index.py   # Weekly visibility index
│   │   ├── sincerao.py      # Sincerão edges + validation
│   │   ├── cartola.py       # Cartola BBB points
│   │   ├── provas.py        # Competition rankings
│   │   ├── clusters.py      # Affinity cluster detection + evolution
│   │   ├── timeline.py      # Game timeline + power summary
│   │   ├── paredao_analysis.py # Paredão analysis + badges
│   │   └── vote_prediction.py  # Vote prediction model
│   ├── build_index_data.py  # Precompute index page tables
│   ├── audit_manual_events.py # Audit manual events for consistency
│   ├── audit_snapshots.py   # Audit tool for deduplication
│   └── update_programa_doc.py # Update program guide timeline
├── docs/
│   ├── SCORING_AND_INDEXES.md    # Full scoring formulas and index specs
│   ├── MANUAL_EVENTS_GUIDE.md    # Manual events schema and fill rules
│   ├── MANUAL_EVENTS_AUDIT.md    # Auto-generated audit of manual events
│   └── PROGRAMA_BBB26.md         # TV show rules, format, dynamics
└── requirements.txt         # Python dependencies
```

## Page Architecture

**Main navbar pages:**

| Page | File | Purpose |
|------|------|---------|
| **Painel** | `index.qmd` | Main dashboard: overview, ranking, heatmap, profiles |
| **Evolução** | `evolucao.qmd` | Temporal: rankings, sentiment evolution, impact, daily pulse, balance, powers |
| **Relações** | `relacoes.qmd` | Social fabric: alliances, rivalries, streak breaks, contradictions, hostility map, network graph |
| **Paredão** | `paredao.qmd` | Current paredão: formation, votes, vote-reaction analysis, Líder nomination prediction |
| **Arquivo** | `paredoes.qmd` | Paredão archive: historical analysis per elimination |
| **Provas** | `provas.qmd` | Competition performance rankings and bracket results |

**Additional pages:** `cartola.qmd` (Cartola points), `planta_debug.qmd` (Planta Index debug), `datas.qmd` (Date View), `clusters.qmd` (affinity clusters), `relacoes_debug.qmd` (relations debug + Líder nomination prediction).

**Design decisions**: Each `.qmd` renders independently (no shared Python state). Dark theme (`darkly`) with custom `bbb_dark` Plotly template. Full-width layout with TOC sidebar.

**Data source tags**: 📸 Dado do dia (latest snapshot) | 📅 Comparação dia-a-dia | 📈 Dado acumulado | 🗳️ Paredão-anchored

## Paredão Workflow

### Status System & Timing

**Status**: `em_andamento` (Sunday night → Tuesday night) | `finalizado` (after result).

**Voting system (BBB 26)**: Voto Único (CPF, 70%) + Voto da Torcida (unlimited, 30%) = Média Final.

**Update timing**: See `docs/OPERATIONS_GUIDE.md` for step-by-step checklists:
- **Thursday**: Líder Transition Checklist (paredão skeleton)
- **Sunday ~22h45**: Paredão Formation Checklist (full formation + votos_casa)
- **Tuesday ~21h**: Votalhada Collection Checklist (poll data)
- **Tuesday ~23h**: Elimination Result Checklist (resultado + ganha-ganha)

### Data Schema (data/paredoes.json)

Each entry in the `paredoes` array:
```python
{
    'numero': N,
    'status': 'em_andamento' | 'finalizado',
    'data': 'YYYY-MM-DD',                      # Elimination date (or expected)
    'data_formacao': 'YYYY-MM-DD',              # Formation date (for analysis anchoring)
    'titulo': 'Nº Paredão — DD de Mês de YYYY',
    'total_esperado': 3,                        # Expected nominees (for placeholder cards)
    'formacao': 'Description of formation...',
    'lider': 'Leader Name',
    'indicado_lider': 'Who the leader nominated',
    'imunizado': {'por': 'Who gave immunity', 'quem': 'Who received'},
    'indicados_finais': [                       # NOTE: use indicados_finais, NOT participantes
        {'nome': 'Name', 'grupo': 'Pipoca', 'como': 'Líder'},
    ],
    'votos_casa': {'Voter Name': 'Target Name'},
    'resultado': {
        'eliminado': 'Name',
        'votos': {
            'Name1': {'voto_unico': XX.XX, 'voto_torcida': XX.XX, 'voto_total': XX.XX},
            'Name2': {'voto_unico': XX.XX, 'voto_torcida': XX.XX, 'voto_total': XX.XX},
        }
    },
    'fontes': ['https://source1.com'],
}
```

The dashboard auto-adapts: partial formation shows placeholder cards, full formation shows "EM VOTAÇÃO", finalized shows results.

### Data Freshness & Archival

**Principle**: Live pages use `latest`/`snapshots[-1]`. Finalized paredão analysis uses **paredão-date snapshot ONLY** (historical archive must be frozen).

**Why**: When analyzing "did reactions predict votes?", we MUST use data from before/during voting, not after.

**Common mistake**: Using `latest` or `snapshots[-1]` in paredão analysis. Always use `get_snapshot_for_date(paredao_date)` for finalized paredões.

**Ideal snapshot timing**: Fetch data on the paredão date (afternoon, before the live show) and again the day after to capture post-elimination state.

### Where to Find Paredão Data

| Data | Search Terms |
|------|-------------|
| Vote percentages | `BBB 26 Nº paredão porcentagem resultado` |
| Voto Único / Torcida | `BBB 26 paredão voto único voto torcida` |
| House votes | `BBB 26 quem votou em quem Nº paredão` |
| Formation details | `BBB 26 como foi formado paredão` |

## Critical: Name Matching Between Manual Data and API

The `votos_casa` dict and all manual data use participant names as keys. These **MUST match exactly** with the names in the API snapshots.

**Official API Names (as of Feb 2026):**

| API Name | Group | Notes |
|----------|-------|-------|
| `Alberto Cowboy` | Veterano | Full name used |
| `Ana Paula Renault` | Veterano | Full name used |
| `Babu Santana` | Veterano | Full name used |
| `Breno` | Pipoca | First name only |
| `Chaiany` | Pipoca | First name only (entered Jan 18) |
| `Gabriela` | Pipoca | First name only (entered Jan 18) |
| `Jonas Sulzbach` | Veterano | Full name used |
| `Jordana` | Pipoca | First name only |
| `Juliano Floss` | Camarote | Full name used |
| `Leandro` | Pipoca | First name only (entered Jan 18) |
| `Marciele` | Pipoca | First name only |
| `Maxiane` | Pipoca | First name only |
| `Milena` | Pipoca | First name only |
| `Samira` | Pipoca | First name only |
| `Solange Couto` | Camarote | Full name used |

**Eliminated/Exited (no longer in API):**
- `Aline Campos` — Eliminada (1º Paredão, Jan 21)
- `Brigido` — Eliminado (3º Paredão, Feb 3)
- `Henri Castelli` — Desistente (Jan 15)
- `Matheus` — Eliminado (2º Paredão, Jan 28)
- `Paulo Augusto` — Desclassificado (agressão, Jan 30)
- `Pedro` — Desistente (Jan 19)
- `Sarah Andrade` — Eliminada (4º Paredão, Feb 10)
- `Sol Vega` — Desclassificada (confronto, Feb 11)
- `Edilson` — Desclassificado (discussão com Leandro, Feb 14)
- `Marcelo` — Eliminado (5º Paredão, Feb 17)
- `Maxiane` — Eliminada (6º Paredão, Feb 25)


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

## Votalhada Poll Data

[Votalhada](https://votalhada.blogspot.com/) aggregates polls from 70+ sources across 4 platforms (Sites, YouTube, Twitter, Instagram) before each elimination.

**Loader functions**: `load_votalhada_polls()`, `get_poll_for_paredao()`, `calculate_poll_accuracy()` from `data_utils`.

### Collection Workflow

1. **Tuesday ~21:00 BRT**: Screenshot Votalhada "Consolidados" → save to `data/` folder
2. Tell Claude: "Process Votalhada image for paredão N" → extracts data, updates `data/votalhada/polls.json`, organizes images into `data/votalhada/YYYY_MM_DD/`
3. **After elimination**: Add `resultado_real` to the poll entry

### Schema (data/votalhada/polls.json)

```json
{
  "paredoes": [{
    "numero": N,
    "data_paredao": "YYYY-MM-DD",
    "data_coleta": "YYYY-MM-DDT21:00:00-03:00",
    "participantes": ["Name1", "Name2", "Name3"],
    "consolidado": {"Name1": XX.XX, "Name2": XX.XX, "total_votos": N, "predicao_eliminado": "NameX"},
    "plataformas": {"sites": {...}, "youtube": {...}, "twitter": {...}, "instagram": {...}},
    "serie_temporal": [{"hora": "DD/mon HH:MM", "Name1": XX.XX, ...}],
    "resultado_real": {"Name1": XX.XX, "eliminado": "NameX", "predicao_correta": true}
  }]
}
```

**Updating preliminary data**: `consolidado`/`plataformas`/`data_coleta` → OVERWRITE with latest. `serie_temporal` → APPEND new time points.

### Name Matching

Votalhada often uses short names. Always match to API names:

| Votalhada Shows | Use in polls.json |
|-----------------|-------------------|
| "Aline" | "Aline Campos" |
| "Ana Paula" | "Ana Paula Renault" |
| "Cowboy" | "Alberto Cowboy" |
| "Sol" | "Sol Vega" |
| "Floss" | "Juliano Floss" |

### Dashboard Display

- **paredao.qmd** (`em_andamento`): "📊 Previsão das Enquetes" — predictions + platform table
- **paredao.qmd** (`finalizado`): "📊 Enquetes vs Resultado" — comparison chart + accuracy
- **paredoes.qmd**: Per-paredão "Enquetes vs Resultado" in archive tabs

See also `data/votalhada/README.md` for detailed screenshot-to-data workflow.

## Líder Nomination Prediction

### Overview

`paredao.qmd` includes a **forward-looking prediction section** ("🎯 Previsão — Indicação do Líder") that ranks all participants by how likely the current Líder is to nominate them. Also present on `relacoes_debug.qmd` for debugging.

### When It Shows (auto-gated)

| State | `ultimo.status` | Formation complete? | Prediction visible? |
|-------|-----------------|--------------------|--------------------|
| Between paredões | `finalizado` | N/A | **Yes** |
| Early formation | `em_andamento` | No (< expected nominees) | **Yes** |
| Full formation / voting | `em_andamento` | Yes (≥ expected nominees) | **No** — vote analysis takes over |

### Data Sources

| Data | Source | Purpose |
|------|--------|---------|
| `relations_scores.json` → `pairs_daily` | Precomputed | Líder → target scores + components |
| `relations_scores.json` → `edges` | Precomputed | Per-pair event history (power, Sincerão, votes) |
| `roles_daily.json` → latest entry | Precomputed | Current Líder, Anjo, VIP list |
| `participants_index.json` | Precomputed | Active participants + avatars |
| Queridômetro matrices (daily snapshots) | Loaded at runtime | Daily reaction history per pair |

### What It Renders

1. **Summary box**: Líder identity + avatar, top 3 most likely targets with score cards, Anjo/immunity status
2. **Full ranking table**: All eligible participants ranked by score ascending (most negative = most likely), with columns:
   - Score + colored bar (red < -2, orange < 0, green ≥ 0)
   - Component chips: queridômetro, power_event, sincerao, vote, vip, anjo
   - Reciprocity label: ⚔️ Mútua | 🔍 Alvo cego | ⚠️ Risco oculto | 💚 Aliados (+ reverse score)
   - Streak length + break indicator
   - VIP badge (Líder chose them → unlikely target)
3. **Expandable detail rows** (per participant): collapsible `<details>` with:
   - All edges between Líder ↔ target (both directions): date, type, direction, weight, event_type, backlash flag
   - Last 14 days of queridômetro reactions (emoji timeline, color-coded by sentiment)
4. **Methodology note**: explains this is score-based, not a dedicated prediction model

### Scoring Logic

Uses the existing **Sentiment Index** (`pairs_daily` from `relations_scores.json`):
- `score` = queridômetro (streak-aware) + power_events + Sincerão + votes + VIP + Anjo (all accumulated, no decay)
- Target ranked by score ascending: most negative = most likely nomination
- VIP members are flagged as unlikely (Líder chose them as allies)
- Immune participants are flagged with IMUNE badge

### Reciprocity Categories

| Líder → Target | Target → Líder | Label | Meaning |
|---------------|---------------|-------|---------|
| Negative | Negative | ⚔️ Mútua | Both secretly hostile |
| Negative | Positive | 🔍 Alvo cego | Target doesn't see it coming |
| Positive | Negative | ⚠️ Risco oculto | Líder unaware of target's hostility |
| Positive | Positive | 💚 Aliados | Mutual alliance |

## Documentation Index

All project documentation and their purposes:

| File | Type | Purpose |
|------|------|---------|
| **`CLAUDE.md`** | Reference | Master project guide — architecture, data flows, conventions (this file) |
| **`docs/OPERATIONS_GUIDE.md`** | **How-to** | **Single source for ALL operational procedures** — checklists for every event type, git workflow, troubleshooting. Start here for "how do I update X?" |
| **`docs/MANUAL_EVENTS_GUIDE.md`** | Schema | Field specs, fill rules, and examples for `manual_events.json` |
| **`docs/SCORING_AND_INDEXES.md`** | Specification | Scoring formulas, weights, and index computation specs |
| **`docs/PROGRAMA_BBB26.md`** | Reference | TV show reference — rules, format, dynamics (non-analytical) |
| **`docs/MANUAL_EVENTS_AUDIT.md`** | Auto-generated | Validation report (built by `build_derived_data.py`) |
| **`data/CHANGELOG.md`** | Archive | API data audit — snapshot dedup analysis and timeline |
| **`data/votalhada/README.md`** | How-to | Screenshot-to-data extraction workflow for Votalhada polls |
