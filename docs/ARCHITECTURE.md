# BBB26 Architecture (Public)

Public technical reference for repository architecture, data flow, and file responsibilities.

## System Overview

```text
GloboPlay API + Manual JSON
        ↓
scripts/fetch_data.py
        ↓
data/snapshots/*.json + data/latest.json
        ↓
scripts/build_derived_data.py
        ↓
scripts/derived_pipeline.py
        ↓
data/derived/*.json
        ↓
scripts/*_viz.py helpers + thin Quarto pages (*.qmd)
        ↓
Quarto render
        ↓
_site/ (GitHub Pages)
```

## Main Layers

- `scripts/`:
  - data ingestion, transformations, validations, derived builders, and render helpers
- `data/`:
  - `snapshots/` raw captures
  - manual sources (`manual_events.json`, `paredoes.json`, `provas.json`, `votalhada/polls.json`)
  - `derived/` precomputed artifacts consumed by pages
- `scripts/*_viz.py`:
  - reusable render helpers, HTML fragment builders, and Plotly figure helpers
- `*.qmd`:
  - page rendering, section ordering, and final visualization composition
- `_quarto.yml`:
  - site navigation, page render list, theme and global includes

## Single Source Principles

- `scripts/data_utils.py` is the shared source of truth for constants, date logic, loaders, helper utilities, and the Plotly theme.
- Shared logic/constants should live in Python modules (not duplicated in QMD pages).
- Heavy computation should be precomputed into `data/derived/`.
- QMD pages should load data and render, not own business logic.
- `scripts/build_derived_data.py` is a compatibility entrypoint; `scripts/derived_pipeline.py` is the real derived-data orchestrator.

## Render-Layer Ownership

- `scripts/builders/*`:
  domain computation, reusable analysis state, and derived artifact generation.
- `scripts/*_viz.py`:
  render helpers with explicit parameters, reusable HTML fragments, and Plotly builders.
- `*.qmd`:
  headings, prose, state-driven section ordering, and final ordered rendering.

## QMD Code Categories

- Category A:
  unit-testable render/formatting helpers.
  Prefer moving to `scripts/*_viz.py`.
- Category B:
  expensive or reusable computation.
  Prefer moving to builders and `data/derived/*`.
- Category C:
  ordered page orchestration and print chains tied to layout.
  Keep in `.qmd` unless a clearly reusable fragment emerges.

## Critical Data Contracts

- Snapshot timestamps are UTC in filenames and metadata.
- Game-date conversion applies BRT logic with morning cutoff.
- Manual-event schema conventions are documented in `docs/MANUAL_EVENTS_GUIDE.md`.
- Scoring and weighting models are documented in `docs/SCORING_AND_INDEXES.md`.

## Build / Render Contracts

- After editing manual data, run:
  - `python scripts/build_derived_data.py`
- Site render:
  - `quarto render`
- CI pipeline validates and rebuilds derived data before deploy.
- Normal release order is:
  - `python scripts/build_derived_data.py`
  - `quarto render`
  - publish `_site/`

## New-Agent Read Order

For a new engineer or agent, the fastest route into the repo is:

1. `README.md` — product overview + quick repo map
2. `docs/ARCHITECTURE.md` — this file
3. `docs/OPERATIONS_GUIDE.md` — operational recipes
4. `docs/MANUAL_EVENTS_GUIDE.md` — manual data contract
5. `docs/SCORING_AND_INDEXES.md` — scoring formulas and model behavior
6. `docs/TESTING.md` — verification map by change type

## Change Routing

Use this table before editing anything:

| If you need to change... | Primary owner | Avoid |
|--------------------------|---------------|-------|
| Shared constants, sentiment weights, date/week logic, loaders, theme | `scripts/data_utils.py` | Re-defining constants or date logic inside QMD pages |
| Reusable analytical computation | `scripts/builders/*` + `scripts/derived_pipeline.py` | Ad hoc recalculation in `*.qmd` |
| Reusable card fragments / Plotly helper rendering | `scripts/*_viz.py` | Copy-pasting HTML builders across pages |
| Page ordering, prose, section composition | `*.qmd` | Moving business logic into layout cells |
| Manual game records | `data/manual_events.json`, `data/paredoes.json`, `data/provas.json`, `data/votalhada/polls.json` | Inventing schema fields without checking docs + live data |
| Verification strategy | `docs/TESTING.md` | Running the entire suite blindly for every tiny edit |

## Related Public Docs

- `docs/OPERATIONS_GUIDE.md` — operational runbooks
- `docs/MANUAL_EVENTS_GUIDE.md` — manual schema and fill rules
- `docs/SCORING_AND_INDEXES.md` — scoring definitions
- `docs/PROGRAMA_BBB26.md` — non-analytical program context
- `docs/TESTING.md` — verification matrix and test ownership

---

## Derived Data Files

All files in `data/derived/`, built by `scripts/build_derived_data.py`:

| File | Built by | Primary consumers | Description |
|------|----------|-------------------|-------------|
| `roles_daily.json` | `build_daily_roles()` | `paredao.qmd`, `evolucao.qmd`, `index_data.json` | Roles + VIP per day |
| `auto_events.json` | `build_auto_events()` + `apply_big_fone_context()` | timeline, Cartola, derived relations | Auto power events (Líder/Anjo/Monstro/Imune) |
| `daily_metrics.json` | `build_daily_metrics()` + change/history helpers | `evolucao.qmd`, `relacoes.qmd`, `index.qmd` | Sentiment + reaction totals per day |
| `participants_index.json` | `build_participants_index()` | `paredao.qmd`, `paredoes.qmd`, `provas.qmd`, economy pages | Canonical participant list (name, avatar, active, first/last seen) |
| `index_data.json` | `build_index_data()` | `index.qmd`, economy pages | Precomputed tables for `index.qmd`, profiles, highlights, strategic timeline, leader periods |
| `plant_index.json` | `build_plant_index()` | `index_data.json`, visibility cards | Planta Index per week + rolling averages |
| `cartola_data.json` | `build_cartola_data()` | `cartola.qmd` | Cartola BBB points (leaderboard, weekly breakdown, stats) |
| `relations_scores.json` | `build_relations_scores()` | `relacoes.qmd`, `paredao.qmd`, `evolucao.qmd` | Pairwise sentiment scores (A→B) with **daily** and **paredão** versions, plus `streak_breaks` |
| `sincerao_edges.json` | `build_sincerao_edges()` | relations pipeline, `index_data.json` | Sincerão aggregates + optional edges |
| `prova_rankings.json` | `build_prova_rankings()` | `provas.qmd` | Competition performance rankings (leaderboard, per-prova detail) |
| `snapshots_index.json` | `build_snapshots_manifest()` | Date-oriented debug/review flows | Manifest of available dates |
| `game_timeline.json` | `build_game_timeline()` | `index.qmd`, `evolucao.qmd`, `cronologia_mobile_review.qmd` | Unified chronological timeline (past + scheduled events) |
| `clusters_data.json` | `build_clusters_data()` | `relacoes.qmd` | Affinity cluster analysis data |
| `cluster_evolution.json` | `build_cluster_evolution()` | historical/debug analysis | Cluster membership changes over time |
| `paredao_analysis.json` | `build_paredao_analysis()` | `paredoes.qmd` | Per-paredão analysis data |
| `paredao_badges.json` | `build_paredao_badges()` | paredão/archive presentation layers | Paredão performance badges |
| `paredao_exposure_stats.json` | `compute_paredao_exposure_stats()` | `docs/SCORING_AND_INDEXES.md`, exposure cards | Paredão exposure analytics (route metrics, BV stats, facts). Hash-gated |
| `vote_prediction.json` | `build_vote_prediction()` | `paredao.qmd`, `paredoes.qmd`, `index.qmd` | Líder nomination / vote prediction data |
| `reaction_matrices.json` | `build_reaction_matrices()` | `relacoes.qmd` | Precomputed daily reaction matrices |
| `balance_events.json` | `build_balance_events()` | `economia.qmd`, `_dev/drafts/economia_v2.qmd` | Balance deltas, compras/punições, fairness metrics |
| `integrity_audit.json` | `audit_data_integrity.py` | CI, operators | Cross-source data integrity audit report |
| `validation.json` | `validate_manual_events()` | debugging and sanity review | Sanity checks |
| `manual_events_audit.json` | `audit_manual_events.run_audit()` | `docs/MANUAL_EVENTS_AUDIT.md`, operators | Manual events audit report |
| `eliminations_detected.json` | `detect_eliminations()` | timeline + validation | Auto-detected participant exits |

---

## Participant Timeline

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
| Mar 3 | 14 | Breno → **Quarto Secreto** (7º Paredão Falso; returns Mar 4) |

---

## Game Week History

BBB game weeks are Líder-cycle-based (not calendar). The **Prova do Líder is the first event of the new week** — events earlier on the same day belong to the previous week. `WEEK_END_DATES` in `data_utils.py` stores the last day of each week (= day before the next Prova do Líder).

| Week | End Date | Líder | Paredão | Next Líder |
|------|----------|-------|---------|------------|
| 1 | 2026-01-21 | Alberto Cowboy | 1º (Jan 21) | Babu (Jan 22) |
| 2 | 2026-01-28 | Babu Santana | 2º (Jan 27) | Maxiane (Jan 29) |
| 3 | 2026-02-04 | Maxiane | 3º (Feb 3) | Jonas (Feb 5) |
| 4 | 2026-02-12 | Jonas Sulzbach | 4º (Feb 10) | Jonas (Feb 13) |
| 5 | 2026-02-18 | Jonas Sulzbach | 5º (Feb 17) | Jonas (?) |
| 6 | 2026-02-25 | Jonas Sulzbach | 6º (Feb 25) | Samira (Feb 26) |
| 7 | TBD | Samira | 7º (Mar 3, Falso) | ??? |

---

## Participant Reference

### Active Participants (14)

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
| `Milena` | Pipoca | First name only |
| `Samira` | Pipoca | First name only |
| `Solange Couto` | Camarote | Full name used |

### Eliminated/Exited (11)

| Name | Exit Type | Date | Details |
|------|-----------|------|---------|
| `Henri Castelli` | Desistente | Jan 15 | Quit |
| `Pedro` | Desistente | Jan 19 | Quit |
| `Aline Campos` | Eliminada | Jan 21 | 1º Paredão |
| `Matheus` | Eliminado | Jan 28 | 2º Paredão |
| `Paulo Augusto` | Desclassificado | Jan 30 | Agressão durante Big Fone |
| `Brigido` | Eliminado | Feb 3 | 3º Paredão |
| `Sarah Andrade` | Eliminada | Feb 10 | 4º Paredão |
| `Sol Vega` | Desclassificada | Feb 11 | Confronto com Ana Paula Renault |
| `Edilson` | Desclassificado | Feb 14 | Discussão com Leandro Boneco |
| `Marcelo` | Eliminado | Feb 17 | 5º Paredão |
| `Maxiane` | Eliminada | Feb 25 | 6º Paredão |

---

## Hostility Analysis

**Two-sided (mutual) hostility**: Both A and B give each other negative reactions — both secretly dislike each other.

**One-sided (unilateral) hostility**: A gives B negative, but B gives A ❤️ — creates **blind spots** where B may be surprised when A votes against them.

**Vulnerability ratio**: `(hearts given to enemies) / (attacks on friends + 1)` — high ratio = major blind spots.

---

## Snapshot Details

### Volatile Fields (change daily)
- `balance`, `roles`, `group` (Vip ↔ Xepa), `receivedReactions` (amounts AND givers)
- `eliminated` — **always false in practice**; participants who leave simply disappear

### Data Update Timing

| Data Type | Update Time (BRT) | Stability |
|-----------|-------------------|-----------|
| **Reactions (Queridômetro)** | ~10h–12h daily | Raio-X in the morning; API publishes shortly after. Timing confirmed: primary update ~15:00 BRT (probes removed Feb 26). |
| **Balance (Estalecas)** | Any time | Changes with purchases, rewards, punishments |
| **Roles** | During/after episodes | Líder, Anjo, Monstro, Paredão ceremonies |

### Synthetic Snapshots

When a date is missed, build a synthetic snapshot from GShow's queridômetro article using `scripts/build_jan18_snapshot.py` as template. Hearts are inferred (complete directed graph). Mark with `_metadata.synthetic = true`.

---

## Page Architecture

`_quarto.yml` is the authoritative source for the current render list and navbar. Keep this section in sync with it.

### Main Navbar Pages

| Page | File | Purpose |
|------|------|---------|
| **Painel** | `index.qmd` | Main dashboard: overview, timeline, heatmap, profiles |
| **Evolução** | `evolucao.qmd` | Temporal: rankings, sentiment evolution, impact, daily pulse, balance, powers |
| **Estalecas VIP/Xepa** | `economia.qmd` | House economy, compras, punições, mesada, and VIP/Xepa fairness |
| **Relações** | `relacoes.qmd` | Social fabric: alliances, rivalries, streak breaks, contradictions, hostility map, network graph |
| **Paredão** | `paredao.qmd` | Current paredão: formation, votes, vote-reaction analysis, Líder nomination prediction |
| **Cartola** | `cartola.qmd` | Cartola BBB points leaderboard and event breakdown |
| **Provas** | `provas.qmd` | Competition performance rankings and bracket results |
| **Paredões** | `paredoes.qmd` | Paredão archive: historical analysis per elimination |
| **Votação** | `votacao.qmd` | Voting system analysis: 70/30 Voto Único / Torcida split |

### Rendered Utility Pages

- `_dev/drafts/economia_v2.qmd` — alternate narrative/mobile-focused economics page (draft)
- `cronologia_mobile_review.qmd` — mobile review surface for the timeline component

### Page Ownership Map

| Surface | Entry file | Primary helpers | Primary inputs |
|---------|------------|-----------------|----------------|
| Main dashboard | `index.qmd` | `scripts/index_viz.py`, `scripts/paredao_viz.py`, `data_utils.render_cronologia_html()` | `index_data.json`, `game_timeline.json`, `paredoes.json`, Votalhada loaders |
| Evolution | `evolucao.qmd` | shared chart helpers in `data_utils.py` | `daily_metrics.json`, `relations_scores.json`, `roles_daily.json`, `index_data.json`, snapshots |
| Economy | `economia.qmd` | page-local HTML helpers | `balance_events.json`, `index_data.json`, `participants_index.json`, snapshots, `manual_events.json` |
| Economy V2 | `_dev/drafts/economia_v2.qmd` | page-local narrative helpers | `balance_events.json`, `index_data.json`, `participants_index.json`, snapshots, `manual_events.json` |
| Relations | `relacoes.qmd` | page-local graph/table composition | `relations_scores.json`, `daily_metrics.json`, `clusters_data.json`, `reaction_matrices.json`, snapshots |
| Current paredão | `paredao.qmd` | `scripts/paredao_viz.py` | `paredoes.json`, `relations_scores.json`, `roles_daily.json`, `participants_index.json`, `vote_prediction.json`, Votalhada polls |
| Paredão archive | `paredoes.qmd` | `scripts/paredao_viz.py` | `paredao_analysis.json`, `vote_prediction.json`, `participants_index.json`, `paredoes.json` |
| Cartola | `cartola.qmd` | page-local HTML builders | `cartola_data.json`, `manual_events.json` |
| Provas | `provas.qmd` | page-local leaderboard/render helpers | `prova_rankings.json`, `provas.json`, `participants_index.json` |
| Voting analysis | `votacao.qmd` | `scripts/votacao_viz.py` | transformed `paredoes.json` data |
| Timeline review | `cronologia_mobile_review.qmd` | `data_utils.render_cronologia_html()` | `game_timeline.json` |

### Archived Debug Pages

The following pages are archived (not rendered in the active site navbar):
- `_legacy/archive_debug_pages/planta_debug.qmd` — Planta Index debug breakdown
- `_legacy/archive_debug_pages/datas.qmd` — Date View (explore queridômetro by date)
- `_legacy/archive_debug_pages/clusters.qmd` — Affinity clusters analysis
- `_legacy/archive_debug_pages/relacoes_debug.qmd` — Relations scoring debug + Líder nomination prediction

### Design Decisions

- Each `.qmd` renders independently (no shared Python state)
- Dark theme (`darkly`) with custom `bbb_dark` Plotly template
- Full-width layout with TOC sidebar

### Data Source Tags

- 📸 Dado do dia (latest snapshot)
- 📅 Comparação dia-a-dia
- 📈 Dado acumulado
- 🗳️ Paredão-anchored
