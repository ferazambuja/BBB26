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
data/derived/*.json
        ↓
Quarto render (*.qmd)
        ↓
_site/ (GitHub Pages)
```

## Main Layers

- `scripts/`:
  - data ingestion, transformations, validations, and derived builders
- `data/`:
  - `snapshots/` raw captures
  - manual sources (`manual_events.json`, `paredoes.json`, `provas.json`, `votalhada/polls.json`)
  - `derived/` precomputed artifacts consumed by pages
- `*.qmd`:
  - page rendering and visualization composition
- `_quarto.yml`:
  - site navigation, page render list, theme and global includes

## Single Source Principles

- Shared logic/constants should live in Python modules (not duplicated in QMD pages).
- Heavy computation should be precomputed into `data/derived/`.
- QMD pages should load data and render, not own business logic.

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

## Related Public Docs

- `docs/OPERATIONS_GUIDE.md` — operational runbooks
- `docs/MANUAL_EVENTS_GUIDE.md` — manual schema and fill rules
- `docs/SCORING_AND_INDEXES.md` — scoring definitions
- `docs/PROGRAMA_BBB26.md` — non-analytical program context

---

## Derived Data Files

All files in `data/derived/`, built by `scripts/build_derived_data.py`:

| File | Description |
|------|-------------|
| `roles_daily.json` | Roles + VIP per day |
| `auto_events.json` | Auto power events (Líder/Anjo/Monstro/Imune) |
| `daily_metrics.json` | Sentiment + reaction totals per day |
| `participants_index.json` | Canonical participant list (name, avatar, active, first/last seen) |
| `index_data.json` | Precomputed tables for `index.qmd` |
| `plant_index.json` | Planta Index per week + rolling averages |
| `cartola_data.json` | Cartola BBB points (leaderboard, weekly breakdown, stats) |
| `relations_scores.json` | Pairwise sentiment scores (A→B) with **daily** and **paredão** versions, plus `streak_breaks` (detected alliance ruptures) |
| `sincerao_edges.json` | Sincerão aggregates + optional edges |
| `prova_rankings.json` | Competition performance rankings (leaderboard, per-prova detail) |
| `snapshots_index.json` | Manifest of available dates for the Date View |
| `game_timeline.json` | Unified chronological timeline (past + scheduled events). Displayed in `index.qmd` and `evolucao.qmd` |
| `clusters_data.json` | Affinity cluster analysis data |
| `cluster_evolution.json` | Cluster membership changes over time |
| `paredao_analysis.json` | Per-paredão analysis data |
| `paredao_badges.json` | Paredão performance badges |
| `vote_prediction.json` | Vote prediction model data |
| `reaction_matrices.json` | Precomputed daily reaction matrices (loaded via `load_reaction_matrices()`) |
| `validation.json` | Sanity checks |
| `manual_events_audit.json` | Manual events audit report |
| `eliminations_detected.json` | Auto-detected participant exits |

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

BBB game weeks are Líder-cycle-based (not calendar). See `WEEK_END_DATES` in `data_utils.py`.

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

### Main Navbar Pages

| Page | File | Purpose |
|------|------|---------|
| **Painel** | `index.qmd` | Main dashboard: overview, ranking, heatmap, profiles |
| **Evolução** | `evolucao.qmd` | Temporal: rankings, sentiment evolution, impact, daily pulse, balance, powers |
| **Relações** | `relacoes.qmd` | Social fabric: alliances, rivalries, streak breaks, contradictions, hostility map, network graph |
| **Paredão** | `paredao.qmd` | Current paredão: formation, votes, vote-reaction analysis, Líder nomination prediction |
| **Arquivo** | `paredoes.qmd` | Paredão archive: historical analysis per elimination |
| **Provas** | `provas.qmd` | Competition performance rankings and bracket results |
| **Votação** | `votacao.qmd` | Voting system analysis: 70/30 Voto Único / Torcida split |

### Additional Pages

- `cartola.qmd` — Cartola BBB points leaderboard
- `planta_debug.qmd` — Planta Index debug breakdown
- `datas.qmd` — Date View (explore queridômetro by date)
- `clusters.qmd` — Affinity clusters analysis
- `relacoes_debug.qmd` — Relations scoring debug + Líder nomination prediction

### Design Decisions

- Each `.qmd` renders independently (no shared Python state)
- Dark theme (`darkly`) with custom `bbb_dark` Plotly template
- Full-width layout with TOC sidebar

### Data Source Tags

- 📸 Dado do dia (latest snapshot)
- 📅 Comparação dia-a-dia
- 📈 Dado acumulado
- 🗳️ Paredão-anchored
