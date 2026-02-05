# BBB26 Dashboard — Automation & Deployment Plan

> **Status**: Local development complete. GitHub Actions workflow ready. GitHub Pages deployment pending.
>
> **Last updated**: 2026-02-04

---

## Overview

BBB26 is a Quarto-based dashboard that tracks participant reaction data from Big Brother Brasil 26 using the GloboPlay API. The dashboard auto-fetches snapshots, builds derived analytics, and renders interactive Plotly visualizations.

**Stack**: Python 3.10+ · Quarto · Plotly · GitHub Actions · GitHub Pages

---

## Current Architecture

### Pages (11 QMD files)

| Page | File | Purpose |
|------|------|---------|
| Painel | `index.qmd` | Main dashboard: overview, ranking, heatmap, profiles |
| Evolução | `evolucao.qmd` | Temporal: rankings, sentiment evolution, impact, balance |
| Relações | `relacoes.qmd` | Social fabric: alliances, rivalries, contradictions, network |
| Paredão | `paredao.qmd` | Current paredão: formation, votes, analysis |
| Paredões | `paredoes.qmd` | Paredão archive: historical analysis per elimination |
| Cartola | `cartola.qmd` | Cartola BBB points leaderboard |
| Provas | `provas.qmd` | Competition performance rankings |
| Datas | `datas.qmd` | Date View: explore queridômetro by date |
| Clusters | `clusters.qmd` | Affinity clusters analysis |
| Planta (debug) | `planta_debug.qmd` | Planta Index debug breakdown |
| Relações (debug) | `relacoes_debug.qmd` | Relations scoring debug page |

### Data Pipeline

```
GloboPlay API
    ↓  scripts/fetch_data.py (saves only if data changed)
data/snapshots/*.json + data/latest.json
    ↓  scripts/build_derived_data.py
data/derived/*.json (20 files: metrics, scores, indexes, timeline, etc.)
    ↓  quarto render
_site/ (11 HTML pages)
```

### Data Sources

| Type | Files | Update Method |
|------|-------|---------------|
| **Auto (API)** | `data/snapshots/*.json`, `data/latest.json` | `fetch_data.py` (4×/day via CI) |
| **Manual** | `manual_events.json`, `paredoes.json`, `provas.json`, `votalhada/polls.json` | Human-maintained after events |
| **Derived** | `data/derived/*.json` (20 files) | `build_derived_data.py` after any change |

### Data Coverage

- **32 snapshots** from Jan 13 to Feb 4, 2026
- **19 active participants** (5 exited: Henri, Pedro, Aline Campos, Matheus, Brigido)
- **3 paredões** completed with full analysis
- **1 synthetic snapshot** (Jan 18 — built from GShow article)

---

## Syncs & Scripts

### Automatic (CI / GitHub Actions)

- **API snapshots**: `python scripts/fetch_data.py` — runs on cron (4×/day), saves only if changed, rebuilds `data/derived/*`
- **Render site**: `quarto render` — runs after data update in CI

### Manual (editor-driven)

- **Paredão data**: update `data/paredoes.json` after formation/results
- **Manual events**: update `data/manual_events.json` after Big Fone, veto, Sincerão, etc.
- **Votalhada polls**: update `data/votalhada/polls.json` Tuesday ~21:00 BRT
- **Provas**: update `data/provas.json` after competitions
- **Rebuild derived**: `python scripts/build_derived_data.py` after any manual edit
- **Update program guide**: `python scripts/update_programa_doc.py` after manual events

### Script Reference

| Script | When | Output |
|--------|------|--------|
| `scripts/fetch_data.py` | Daily or before events | `data/snapshots/*`, `data/latest.json`, `data/derived/*` |
| `scripts/build_derived_data.py` | After manual edits | `data/derived/*` |
| `scripts/update_programa_doc.py` | After updating events | `docs/PROGRAMA_BBB26.md` |
| `scripts/audit_snapshots.py` | One-off audit | Console report |
| `scripts/analyze_snapshots.py` | Integrity check | Console report |
| `scripts/compare_sameday.py` | Intraday diff | Console report |
| `scripts/build_jan18_snapshot.py` | Rebuild synthetic Jan 18 | Snapshot file |

---

## GitHub Actions Workflow

File: `.github/workflows/daily-update.yml`

**Schedule**: 4× daily (06:00, 12:00, 18:00, 00:00 BRT)

```yaml
name: BBB26 Update

on:
  schedule:
    - cron: '0 6 * * *'   # 03:00 BRT
    - cron: '0 15 * * *'  # 12:00 BRT
    - cron: '0 21 * * *'  # 18:00 BRT
    - cron: '0 3 * * *'   # 00:00 BRT
  workflow_dispatch:

permissions:
  contents: write
  pages: write
  id-token: write

jobs:
  update-and-publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - run: pip install -r requirements.txt

      - run: python scripts/fetch_data.py

      - uses: quarto-dev/quarto-actions/setup@v2

      - run: quarto render

      - name: Commit data changes
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          git add data/
          git diff --staged --quiet || git commit -m "chore: update data snapshot $(date +%Y-%m-%d)"
          git push

      - uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./_site
```

---

## GitHub Pages Deployment (Pending)

### Steps to Deploy

1. **Push to GitHub**
   ```bash
   git push origin main
   ```

2. **Enable GitHub Pages**
   - Repository **Settings** → **Pages**
   - Source: **GitHub Actions**

3. **Trigger first deployment**
   - **Actions** tab → "BBB26 Update" → **Run workflow**

4. **Verify** at `https://<username>.github.io/BBB26/`

### Checklist

- [ ] Push code to GitHub
- [ ] Enable GitHub Pages with "GitHub Actions" source
- [ ] Manually trigger workflow to test
- [ ] Verify site is live
- [ ] Verify automated runs work (check next scheduled run)

---

## Considerations

### API Behavior

- **No timestamp**: API provides no `Last-Modified` header
- **Event-driven changes**: Data changes correlate with show events, not a schedule
- **Complete state**: Each response is the full current state, not cumulative
- **Daily reassignment**: Participants change their reactions every morning (Raio-X)

### Storage

- ~300KB per snapshot × ~1-2/day = manageable in git
- 32 snapshots so far = ~8MB (projected ~25-50MB for full season)

### Error Handling

- Fetch script only saves when hash changes (dedup built-in)
- Build script hard-fails on manual events audit issues
- Missing Raio-X auto-detected and patched for scoring

---

## Feature Ideas (reviewed 2026-02-04)

Ideas extracted from planning docs and AI reviews, evaluated against the current system.

### Worth Implementing

| # | Idea | Page | Description | Status |
|---|------|------|-------------|--------|
| 1 | **Votalhada Accuracy Leaderboard** | `paredoes.qmd` | Which platform predicts best across paredões? | **Exists** — "Precisão por Plataforma" table with per-paredão error + rank. Enhance: add trend chart showing per-platform error evolution as more paredões accumulate |
| 2 | **Votalhada Time Series** | `paredao.qmd` | Visualize how poll percentages evolve in the 24-48h before elimination | **Not implemented** — data exists in `serie_temporal` field of `polls.json` but is not visualized. Add a line chart showing poll evolution with final result as reference line |
| 3 | **Platform Trends** | `paredoes.qmd` | Cross-paredão per-platform accuracy — is Twitter consistently closer than YouTube? | **Exists** — basic table in "Precisão das Enquetes" section. Enhance: add grouped bar chart or line chart for visual trend comparison |
| 4 | **Participant Line Selector** | `evolucao.qmd` | Toggle specific participants on/off in sentiment evolution chart (19+ lines is cluttered) | **Not implemented** — requires Plotly `updatemenus` or `buttons` for interactive filtering. Could use dropdown/checkboxes to show/hide lines |
| 5 | **Dynamic Cluster k** | `clusters.qmd` | Auto-select optimal cluster count via silhouette score instead of hardcoded k | **Not implemented** — currently uses fixed k. Add silhouette analysis to `build_derived_data.py`, store optimal k in `clusters_data.json` |
| 6 | **Temporal Cluster Tracking** | `clusters.qmd` | How cluster membership evolves over snapshots — who switches allegiances? | **Not implemented** — only current-day clustering exists. Would need to run clustering per snapshot and track membership changes. High value for detecting shifting alliances |

### Maybe Later (lower priority or high effort)

| Idea | Why Deferred |
|------|-------------|
| Date picker for queridômetro comparison | `datas.qmd` already serves this need with date navigation |
| Compare paredões side-by-side | Useful but niche; archive tabs already allow manual comparison |
| Participant focus mode | High effort; profiles section in `index.qmd` partially covers this |
| Auto-name clusters | Naming heuristics are fragile; generic names are fine |
| Vote-based clustering | Requires more paredão data for meaningful vote patterns |
| Narrative arcs detection | Algorithm complexity not justified for current data volume |

### Already Implemented (since plans were written)

These ideas appeared in old planning docs and have since been implemented:
- Bump chart with individual participant colors → `evolucao.qmd`
- Accessibility toggle (colorblind mode) → `assets/accessibility.js`
- KPI boxes and daily highlights → `index.qmd`
- Streak breaks detection → `relacoes.qmd` + `evolucao.qmd`
- Paredão prediction analysis → `paredao.qmd` vote prediction section
- Sincerão contradictions analysis → `relacoes.qmd`
- VIP/Xepa tracking → `evolucao.qmd`
- Power events timeline → `evolucao.qmd`
- Voting blocs analysis → `relacoes.qmd` + `clusters.qmd`
- Cross-paredão accuracy summary → `paredoes.qmd` poll accuracy section
- Votalhada accuracy leaderboard (basic) → `paredoes.qmd` "Precisão por Plataforma"
- Enquetes vs vote type comparison → `paredoes.qmd` "Enquetes vs Tipos de Voto"

---

## Completed Milestones

| Date | Milestone |
|------|-----------|
| Jan 13 | First API snapshot captured |
| Jan 24 | Data audit complete (13 unique states from ~68 files) |
| Jan 24 | Quarto dashboard created (`index.qmd`) |
| Jan 25 | Dark theme, paredão archive, GitHub Actions workflow |
| Jan 26 | Dashboard reorganization (5→11 pages), derived data pipeline |
| Jan 28 | Date View, elimination detection, index precomputation |
| Jan 29 | Relations scoring system, Planta Index, Cartola BBB |
| Jan 30 | Provas page, manual events guide, code centralization |
| Feb 1 | AI reviews (14 reviews from 4 models), accessibility features |
| Feb 3 | 3rd paredão (Brigido eliminated), Sincerão week 3, Votalhada integration |
| Feb 4 | Documentation cleanup, GitHub-readiness preparation |
