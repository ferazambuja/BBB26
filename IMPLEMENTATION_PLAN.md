# BBB26 Dashboard - GitHub Actions + Quarto + GitHub Pages

## Implementation Plan

This document outlines the plan to automate the BBB26 reaction analysis notebook and publish it as a daily-updated website using GitHub Actions and GitHub Pages.

---

## Progress Log

| Date | Task | Status |
|------|------|--------|
| 2026-01-24 | Created initial implementation plan | ✅ Done |
| 2026-01-24 | Analyzed API (no timestamps, event-driven updates) | ✅ Done |
| 2026-01-24 | Installed Quarto v1.8.27 | ✅ Done |
| 2026-01-24 | Created `.gitignore` | ✅ Done |
| 2026-01-24 | Created `_legacy/` folder (gitignored) for old assets | ✅ Done |
| 2026-01-24 | Moved old CSVs, PNGs, backups, `BBB_old.ipynb`, `organize_and_backup.py` to `_legacy/` | ✅ Done |
| 2026-01-24 | Created `data/snapshots/` directory structure | ✅ Done |
| 2026-01-24 | Migrated 11 JSON files to `data/snapshots/` (renamed from `bbb_participants_*` to timestamp-only) | ✅ Done |
| 2026-01-24 | Created `data/latest.json` | ✅ Done |
| 2026-01-24 | Created `scripts/fetch_data.py` (with hash comparison, metadata wrapper) | ✅ Done |
| 2026-01-24 | Created `CLAUDE.md` with project guidance | ✅ Done |
| 2026-01-24 | Added Phase 0: Historical Data Audit to plan | ✅ Done |
| 2026-01-24 | Recovered 15 JSON files from git history — all empty/corrupted (0 bytes) | ✅ Done |
| 2026-01-24 | Created `scripts/audit_snapshots.py` | ✅ Done |
| 2026-01-24 | Ran full audit: 41 files across 3 sources → 12 unique data states, 29 duplicates | ✅ Done |
| 2026-01-24 | Fixed canonical files: added Jan 23 first captures from `archive_duplicates/` | ✅ Done |
| 2026-01-24 | Created `data/CHANGELOG.md` documenting full data timeline and findings | ✅ Done |
| 2026-01-24 | Fetched new API data at 18:46 — new intraday state detected, saved as 13th snapshot | ✅ Done |
| 2026-01-24 | Confirmed: Jan 18 data was never captured, unrecoverable from any source | ✅ Done |
| 2026-01-24 | Discovered critical data model: reactions are NOT permanent — reassigned daily | ✅ Done |
| 2026-01-24 | Updated CLAUDE.md, CHANGELOG.md, IMPLEMENTATION_PLAN.md with corrected data model | ✅ Done |
| 2026-01-24 | Committed full reorganization: 124 files (116 deletions + 18 new), commit `28ef943` | ✅ Done |
| 2026-01-25 | Created `arquivo.qmd` — comprehensive paredão archive with per-paredão analysis | ✅ Done |
| 2026-01-25 | Added "O Que Mudou Hoje?" section — day-over-day change visualizations (diverging bar, heatmap, Sankey, volatility) | ✅ Done |
| 2026-01-25 | Added "Clusters de Afinidade" — hierarchical clustering based on mutual sentiment | ✅ Done |
| 2026-01-25 | Added affinity heatmap reordered by cluster with boundary lines | ✅ Done |
| 2026-01-25 | Verified Jan 13 snapshot matches GShow queridômetro article | ✅ Done |
| 2026-01-25 | Switched to dark theme (`darkly`) with custom `bbb_dark` Plotly template | ✅ Done |
| 2026-01-25 | Added data type tags to all sections (📸 daily, 📅 day-to-day, 📈 accumulated) | ✅ Done |
| 2026-01-25 | Removed TOC sidebar, enabled full-width page layout | ✅ Done |
| 2026-01-25 | Removed duplicate vote-reaction analysis (kept in arquivo.qmd) | ✅ Done |
| 2026-01-24 | Created `_quarto.yml` — renders BBB.ipynb only, cosmo theme, code-fold | ✅ Done |
| 2026-01-24 | Created `requirements.txt` (7 packages + jupyter/nbformat/nbclient) | ✅ Done |
| 2026-01-24 | Tested `quarto render` — `_site/BBB.html` (291KB) + 4 figures generated | ✅ Done |
| 2026-01-24 | Fixed timeline x-axis ordering bug (string dates → pd.to_datetime) | ✅ Done |
| 2026-01-24 | Updated notebook data loading to use `data/snapshots/` instead of root-level files | ✅ Done |
| 2026-01-24 | Cleared stale cached outputs from `.ipynb` | ✅ Done |
| 2026-01-24 | **Decision**: Abandon `.ipynb` editing — create fresh `index.qmd` from scratch | ✅ Decided |
| 2026-01-24 | Deep analysis of all 13 snapshots (8 sections, 2500 lines) + web research | ✅ Done |
| 2026-01-24 | Created `index.qmd` — 17-section Quarto dashboard in pt-BR | ✅ Done |
| 2026-01-24 | Updated `_quarto.yml` to render `index.qmd` | ✅ Done |
| 2026-01-24 | Added `tabulate` to `requirements.txt` | ✅ Done |
| 2026-01-24 | Tested `quarto render` — all 19 cells pass, 454KB HTML output | ✅ Done |
| 2026-01-24 | Moved `BBB.ipynb` to `_legacy/` | ✅ Done |
| 2026-01-25 | Added participant avatars to paredão cards (with B&W filter for eliminated) | ✅ Done |
| 2026-01-25 | Added avatars to individual profiles section | ✅ Done |
| 2026-01-25 | Implemented paredão status system (`em_andamento` / `finalizado`) | ✅ Done |
| 2026-01-25 | Renamed `arquivo.qmd` → `paredoes.qmd` ("Histórico de Paredões") | ✅ Done |
| 2026-01-25 | Added link box to paredões page from main dashboard | ✅ Done |
| 2026-01-25 | Moved historical summary table to paredoes.qmd | ✅ Done |
| 2026-01-25 | Fixed user-facing language (removed developer jargon, "reações públicas" → "queridômetro") | ✅ Done |
| 2026-01-25 | Created GitHub Actions workflow with 4x daily cron (multi-capture strategy) | ✅ Done |
| 2026-01-25 | Enhanced fetch_data.py with change type detection (reactions/balance/roles) | ✅ Done |
| | Enable GitHub Pages | ⏳ Pending |

## Weekly Paredão Update Workflow

### Sunday Night (~22h45 BRT) — Paredão Formation

1. **Watch the formation live** — Paredão typically starts around 22h45 BRT on Sundays
2. **Fetch fresh API data** after the formation:
   ```bash
   python scripts/fetch_data.py
   ```
3. **Check who has the Paredão role**:
   ```bash
   python3 -c "
   import json
   with open('data/latest.json') as f:
       data = json.load(f)
   participants = data['participants'] if 'participants' in data else data
   for p in participants:
       roles = p.get('characteristics', {}).get('roles', [])
       role_labels = [r.get('label') if isinstance(r, dict) else r for r in roles]
       if 'Paredão' in role_labels:
           print(f\"{p['name']} ({p['characteristics'].get('memberOf', '?')})\")
   "
   ```
4. **Create `em_andamento` entry** in both `index.qmd` and `paredoes.qmd` with:
   - Formation story
   - House votes (who voted for whom)
   - Leader nomination
   - Bate e Volta results (if applicable)

### Monday-Tuesday — Update as Needed

- Add any missing details as they become available from news sources
- Verify participant names match API exactly

### Tuesday Night (~23h BRT) — Result

1. **Watch the elimination live**
2. **Update both files** to change `status: 'finalizado'` and add:
   - Vote percentages (Voto Único, Voto Torcida, Média Final)
   - Result (ELIMINADO/SALVO for each participant)
3. **Fetch fresh API data** to capture the post-elimination state:
   ```bash
   python scripts/fetch_data.py
   ```
4. **Render and commit**:
   ```bash
   quarto render && git add -A && git commit -m "Nº Paredão: [nome] eliminado(a)"
   ```

### Git Status

Reorganization committed as `28ef943`. Pending uncommitted work:
- Modified `BBB.ipynb` (data loading rewrite, timeline fix, cleared outputs)
- Modified `_quarto.yml`, `IMPLEMENTATION_PLAN.md`
- Will be superseded by `index.qmd` rewrite (see Phase 1.5 below)

### Current Repository Structure

```
BBB26/
├── .git/
├── .gitignore              ✅ NEW (ignores _legacy/, *.png, *.csv, etc.)
├── .vscode/
├── BBB.ipynb               (original notebook — kept for reference, replaced by index.qmd)
├── CLAUDE.md               ✅ NEW (project guidance for Claude Code)
├── IMPLEMENTATION_PLAN.md  ✅ MODIFIED (this file)
├── data/                   ✅ NEW
│   ├── CHANGELOG.md        ✅ NEW (data timeline, audit results, key findings)
│   ├── latest.json         ✅ NEW (copy of most recent snapshot)
│   └── snapshots/          ✅ NEW (13 canonical JSON files)
│       ├── 2026-01-13_17-18-02.json  (21p, 420r — initial state)
│       ├── 2026-01-14_15-44-42.json  (21p, 420r)
│       ├── 2026-01-15_21-12-50.json  (20p, 380r — 1st elimination)
│       ├── 2026-01-16_14-42-50.json  (20p, 380r)
│       ├── 2026-01-17_17-46-39.json  (20p, 380r)
│       ├── 2026-01-19_22-34-41.json  (23p, 506r — +3 new entrants)
│       ├── 2026-01-20_18-57-19.json  (23p, 506r)
│       ├── 2026-01-21_14-08-12.json  (22p, 462r — 2nd elimination)
│       ├── 2026-01-22_23-19-10.json  (22p, 462r)
│       ├── 2026-01-23_15-48-49.json  (22p, 462r)
│       ├── 2026-01-23_16-55-52.json  (22p, 462r — intraday change)
│       ├── 2026-01-24_15-52-39.json  (22p, 462r)
│       └── 2026-01-24_18-46-05.json  (22p, 462r — intraday change)
├── scripts/                ✅ NEW
│   ├── audit_snapshots.py  ✅ NEW (deduplication audit tool)
│   └── fetch_data.py       ✅ NEW (API fetch with hash comparison)
└── _legacy/                ✅ NEW (gitignored — safe backup of all old files)
    ├── archive_duplicates/ (15 duplicate Jan 23 JSON files)
    ├── backup/2026-01-24_16-59-39/ (66 files: JSONs, CSVs, PNGs, BBB.ipynb copy)
    ├── BBB_old.ipynb       (empty file)
    ├── organize_and_backup.py
    ├── *.csv               (18 reaction cross table files)
    └── *.png               (4 visualization files)
```

### Data Coverage Summary

| Date | Snapshots | Status |
|------|-----------|--------|
| Jan 13 | 1 | ✅ Captured |
| Jan 14 | 1 | ✅ Captured |
| Jan 15 | 1 | ✅ Captured (elimination day) |
| Jan 16 | 1 | ✅ Captured |
| Jan 17 | 1 | ✅ Captured |
| Jan 18 | 0 | ❌ **Never captured** — unrecoverable |
| Jan 19 | 1 | ✅ Captured (+3 new entrants) |
| Jan 20 | 1 | ✅ Captured |
| Jan 21 | 1 | ✅ Captured (elimination day) |
| Jan 22 | 1 | ✅ Captured |
| Jan 23 | 2 | ✅ Captured (intraday change at 16:55) |
| Jan 24 | 2 | ✅ Captured (intraday change at 18:46) |
| **Total** | **13** | **Missing only Jan 18** |

### Files Audited and Accounted For

| Source | Files Found | Unique States | Duplicates | Empty/Corrupted |
|--------|-------------|---------------|------------|-----------------|
| Root-level `bbb_participants_*.json` | 11 | 11 | 0 | 0 |
| `archive_duplicates/` | 15 | 2 | 13 | 0 |
| Git-recovered (commit `6ea9807`) | 15 | 0 | 0 | 15 (all 0 bytes) |
| `backup/2026-01-24_16-59-39/` | ~26 JSONs | 0 new | all duplicates | 0 |
| API fetch (Jan 24 18:46) | 1 | 1 | 0 | 0 |
| **Total** | **~68** | **13** | ~40 | 15 |

---

## Overview

**Goal**: Transform the current Jupyter notebook into an automated, publicly accessible dashboard that:
- Fetches fresh data daily from the GloboPlay API
- Stores dated JSON snapshots for historical analysis
- Renders a static site with analysis and visualizations
- Deploys automatically to GitHub Pages

**Stack**:
- **Automation**: GitHub Actions (scheduled cron job)
- **Rendering**: Quarto (preferred) or Jupyter Book
- **Hosting**: GitHub Pages
- **Data Storage**: JSON files committed to repo (or Parquet if data grows)

---

## API Analysis (Important Findings)

### No Timestamp Available

The GloboPlay API **does not provide any timestamp** indicating when data was last updated:

- **Response format**: Plain JSON array of participants (no metadata wrapper)
- **HTTP headers**: Only `cache-control: max-age=180` (3 min cache), no `Last-Modified` header
- **No internal timestamps**: Participant objects have no `updatedAt` or similar fields

### Data Changes are Event-Driven, Not Time-Driven

Analysis of historical snapshots reveals data changes correlate with **show events**, not a fixed daily schedule:

| Date Range | Participants | Total Reactions | Event |
|------------|--------------|-----------------|-------|
| Jan 13-14 | 21 | 420 | Initial state |
| Jan 15-17 | 20 | 380 | Elimination (1 out) |
| Jan 19-20 | 23 | 506 | New entrants (+3 veteranos/camarotes) |
| Jan 21-24 | 22 | 462 | Elimination (1 out) |

**Key observations:**
- Data changes daily even without eliminations (reactions are reassigned)
- Intraday changes happen (Jan 23 and Jan 24 each had 2 different states)
- Changes happen around eliminations, new entrants, voting rounds, AND daily reaction reshuffles
- There is no predictable update time

### Current Data Storage (Already Good!)

Full API response (~200-270KB per file):
- 13 canonical snapshots = ~3MB
- Projected season total (~90 days, ~1-2 per day): ~25-50MB — easily manageable in git

### Critical: Reactions Are Reassigned Daily

Diff analysis (Jan 22 vs Jan 23) revealed that the API is **NOT cumulative**. It returns the **current state**. Participants actively **reassign** their reactions daily:

- Solange Couto changed Alberto Cowboy from ❤️ to 💼
- Jordana changed Babu Santana from ❤️ to 💔
- Gabriela's ❤️ dropped from 16→11, 🍪 Biscoito rose from 2→6

All fields are volatile: balances, roles, groups, AND reactions (amounts + givers).

**Every unique snapshot must be kept.** There are no "duplicates" unless the hash matches exactly.

### Recommended Strategy

1. **Save full API response** (already doing this - keep it!)
2. **Save only when data hash changes** (identical hash = truly the same state)
3. **Keep timestamp in filename** (intraday changes happen, need to distinguish)
4. **Run multiple times per day** to catch changes when they happen

---

## Why Quarto?

| Feature | Quarto | Jupyter Book |
|---------|--------|--------------|
| Native Jupyter support | Yes | Yes |
| Interactive widgets | Yes (Plotly, etc.) | Limited |
| Output formats | HTML, PDF, EPUB, slides | Primarily HTML |
| GitHub Actions integration | Excellent | Good |
| Learning curve | Low | Low |
| Single-file config | Yes (`_quarto.yml`) | Yes (`_config.yml`) |

**Recommendation**: Quarto - better Plotly support, cleaner output, actively developed by Posit.

---

## Repository Structure (Target)

```
BBB26/
├── .github/
│   └── workflows/
│       └── daily-update.yml       # GitHub Actions workflow (Phase 2)
│
├── data/
│   ├── snapshots/                 # Canonical JSON snapshots (13 files, growing)
│   │   ├── 2026-01-13_17-18-02.json
│   │   ├── ...
│   │   └── 2026-01-24_18-46-05.json
│   ├── latest.json                # Copy of most recent snapshot
│   └── CHANGELOG.md               # Data timeline + audit findings
│
├── scripts/
│   ├── fetch_data.py              # Fetch API, save if hash changed
│   └── audit_snapshots.py         # Deduplication audit tool
│
├── _quarto.yml                    # Quarto configuration
├── index.qmd                      # Main dashboard (pt-BR) ← NEW
│
├── CLAUDE.md                      # Project guidance
├── requirements.txt               # Python dependencies
├── IMPLEMENTATION_PLAN.md         # This file
├── .gitignore                     # Ignores _legacy/, *.png, *.csv, etc.
│
└── _legacy/                       # (gitignored)
    ├── BBB.ipynb                  # Original notebook (moved here after index.qmd is done)
    └── ...                        # Old assets
```

---

## Phase 0: Historical Data Audit ✅ COMPLETE

### What Was Done

Comprehensive audit of all data sources to establish a clean canonical dataset:

1. **Recovered 15 deleted files from git** (commit `6ea9807`) — all were empty/corrupted (0 bytes), discarded
2. **Audited ~68 files** across 5 sources (root, archive_duplicates, backup, git history, API)
3. **Found 13 unique data states** out of ~68 total files (~55 duplicates)
4. **Established canonical `data/snapshots/`** with exactly 13 files (first capture of each unique state)
5. **Documented everything** in `data/CHANGELOG.md`

### Key Discovery: Reactions Are Reassigned Daily

Diff analysis between snapshots proved the API returns **current state**, not cumulative data. Participants actively change their reactions to others daily — amounts go up AND down, givers swap around. This means every unique snapshot captures a genuinely different game state.

### Data Change Timeline (Final)

| First Captured | Participants | Reactions | Event | Hash (first 16) |
|----------------|--------------|-----------|-------|-----------------:|
| 2026-01-13 17:18 | 21 | 420 | Initial state | `bf31ebb9b8992f32` |
| 2026-01-14 15:44 | 21 | 420 | Data updated | `45479df71b6fa4eb` |
| 2026-01-15 21:12 | 20 | 380 | **1st elimination** (-1) | `d9edce86cd21ca46` |
| 2026-01-16 14:42 | 20 | 380 | Data updated | `3c3ac8964764f516` |
| 2026-01-17 17:46 | 20 | 380 | Data updated | `aacff0a82e759f88` |
| ~~2026-01-18~~ | — | — | **Never captured** | — |
| 2026-01-19 22:34 | 23 | 506 | **+3 new entrants** | `d0abb56ecb282c1f` |
| 2026-01-20 18:57 | 23 | 506 | Data updated | `493ff51dfe8344f0` |
| 2026-01-21 14:08 | 22 | 462 | **2nd elimination** (-1) | `1cd2ab263a24e1ec` |
| 2026-01-22 23:19 | 22 | 462 | Data updated | `c7d03d856d9e1ab5` |
| 2026-01-23 15:48 | 22 | 462 | Data updated | `d9ae8caaef4d119c` |
| 2026-01-23 16:55 | 22 | 462 | **Intraday change** | `a2f6805c0cb857fc` |
| 2026-01-24 15:52 | 22 | 462 | Data updated | `2d574f35967e2367` |
| 2026-01-24 18:46 | 22 | 462 | **Intraday change** | `0341fe147a1b` |

---

## Phase 1: Local Setup

### 1.1 Install Quarto

```bash
# macOS (Homebrew)
brew install quarto

# Or download from https://quarto.org/docs/get-started/
```

### 1.2 Create Quarto Configuration

Create `_quarto.yml`:

```yaml
project:
  type: website
  output-dir: _site

website:
  title: "BBB26 Reaction Dashboard"
  navbar:
    left:
      - href: index.qmd
        text: Dashboard
      - href: analysis.qmd
        text: Analysis
      - href: about.qmd
        text: About

format:
  html:
    theme: cosmo
    toc: true
    code-fold: true
    code-tools: true
```

### 1.3 Create `index.qmd` (Phase 1.5 — Fresh Start)

**Decision**: Instead of editing `BBB.ipynb` (fragile JSON manipulation, stale cached outputs), create a brand new `index.qmd` Quarto document from scratch.

**Key changes from the notebook**:
- **Language**: All text, titles, labels, legends in **pt-BR**
- **Data loading**: Use `data/snapshots/` with `load_snapshot()` (handles both formats)
- **Visualizations**: Fully reconsidered — analyze all 13 snapshots first, then decide what plots tell the best story
- **Format**: Native `.qmd` (plain text, clean git diffs, easy to edit)

The old `BBB.ipynb` will be moved to `_legacy/` after `index.qmd` is complete.

### 1.4 Data Fetching Script ✅ DONE

See `scripts/fetch_data.py` — already created and tested.

### 1.5 Test Locally

```bash
quarto render    # Build site
quarto preview   # Live preview with hot reload
```

---

## Phase 2: GitHub Actions Workflow

### 2.1 Create Workflow File

Create `.github/workflows/daily-update.yml`:

```yaml
name: BBB26 Update

on:
  schedule:
    # Run multiple times per day since we don't know exact update time
    # Data changes are event-driven (eliminations, new entrants) not time-driven
    # These times cover different parts of the day (BRT = UTC-3):
    - cron: '0 6 * * *'   # 03:00 BRT - early morning
    - cron: '0 15 * * *'  # 12:00 BRT - noon
    - cron: '0 21 * * *'  # 18:00 BRT - evening (after typical elimination shows)
    - cron: '0 3 * * *'   # 00:00 BRT - midnight
  workflow_dispatch:  # Allow manual trigger

permissions:
  contents: write
  pages: write
  id-token: write

jobs:
  update-and-publish:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for git operations

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install Python dependencies
        run: |
          pip install -r requirements.txt

      - name: Fetch latest data
        run: |
          python scripts/fetch_data.py

      - name: Set up Quarto
        uses: quarto-dev/quarto-actions/setup@v2

      - name: Render Quarto site
        run: |
          quarto render

      - name: Commit data changes
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          git add data/
          git diff --staged --quiet || git commit -m "chore: update data snapshot $(date +%Y-%m-%d)"
          git push

      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./_site
```

### 2.2 Create Requirements File

Create/update `requirements.txt`:

```
requests>=2.28.0
pandas>=2.0.0
numpy>=1.24.0
matplotlib>=3.7.0
seaborn>=0.12.0
plotly>=5.14.0
networkx>=3.1
jupyter
nbformat
nbclient
```

---

## Phase 3: GitHub Pages Setup

### 3.1 Enable GitHub Pages

1. Go to repository **Settings** > **Pages**
2. Source: **GitHub Actions** (recommended)
   - Or: Deploy from branch `gh-pages`
3. The site will be available at: `https://<username>.github.io/BBB26/`

### 3.2 Alternative: Branch-based Deployment

If using branch-based deployment, the workflow already handles it with `peaceiris/actions-gh-pages`.

---

## Phase 4: Data Management Strategy

### 4.1 Current Approach: JSON in Repo

**Pros**:
- Simple, no external dependencies
- Full version history via git
- Works well for small datasets

**Estimated size**: ~50KB per daily snapshot × 90 days = ~4.5MB per season

**Recommendation**: This is fine for BBB data size.

### 4.2 Future Option: Parquet (If Needed)

If data grows significantly:

```python
import pandas as pd

# Save as Parquet (more efficient)
df.to_parquet(f"data/snapshots/{date}.parquet")

# Load all history efficiently
all_files = Path("data/snapshots").glob("*.parquet")
history = pd.concat([pd.read_parquet(f) for f in all_files])
```

### 4.3 Data Deduplication

Handled automatically by `scripts/fetch_data.py` — it compares the MD5 hash of the new API response against the latest snapshot and only saves when data actually changes. Filenames use full timestamps (`YYYY-MM-DD_HH-MM-SS.json`) since intraday changes occur.

---

## Phase 5: Migration Checklist

### Step-by-Step Migration

#### Pre-work (Completed 2026-01-24)
- [x] **0.0a. Create `.gitignore`** — ignores `_legacy/`, `_site/`, `*.png`, `*.csv`, Python/OS/IDE files
- [x] **0.0b. Create `_legacy/` folder (gitignored)** — safe backup of all old assets
- [x] **0.0c. Move old files to `_legacy/`** — BBB_old.ipynb, organize_and_backup.py, 18 CSVs, 4 PNGs, archive_duplicates/ (15 files), backup/ (66 files)
- [x] **0.0d. Migrate JSON files to `data/snapshots/`** — renamed from `bbb_participants_YYYY-...` to `YYYY-MM-DD_HH-MM-SS.json`
- [x] **0.0e. Create `data/latest.json`** — copy of most recent snapshot
- [x] **0.0f. Create `CLAUDE.md`** — project guidance with corrected data model

#### Phase 0: Data Audit ✅ COMPLETE
- [x] **0.1. Recover deleted JSON files from git history** — 15 files from commit `6ea9807`, all empty (0 bytes)
- [x] **0.2. Create `scripts/audit_snapshots.py`** — audits 3 source dirs, groups by MD5 hash
- [x] **0.3. Run full audit** — ~68 files across 5 sources → 13 unique data states
- [x] **0.4. Establish canonical dataset** — first capture of each unique state in `data/snapshots/`
- [x] **0.5. Keep full timestamp format** — needed for intraday changes (Jan 23, Jan 24 each have 2 states)
- [x] **0.6. Create `data/CHANGELOG.md`** — full data timeline, key findings, audit results
- [x] **0.7. Discover and document corrected data model** — reactions are reassigned daily, not cumulative

#### Phase 0.5: Git Cleanup ✅ COMPLETE
- [x] **0.5a. Commit the full reorganization** — 124 files changed, commit `28ef943`
- [x] **0.5b. Verify clean `git status`** ✅ (no uncommitted changes)

#### Phase 1: Local Quarto Setup ✅ COMPLETE
- [x] **1.1. Install Quarto locally** ✅ (v1.8.27 via Homebrew)
- [x] **1.2. Create `data/snapshots/` directory structure** ✅
- [x] **1.3. Create `scripts/fetch_data.py`** ✅ (hash comparison, metadata wrapper, latest.json update)
- [x] **1.4. Create `_quarto.yml` configuration** ✅ — cosmo theme, code-fold
- [x] **1.5. Create `requirements.txt`** ✅
- [x] **1.6. Test `quarto render` with BBB.ipynb** ✅ — worked but editing `.ipynb` is fragile
- [x] **1.7. Fixed timeline x-axis ordering bug** ✅ — string dates → pd.to_datetime
- [x] **1.8. Updated notebook data loading for `data/snapshots/`** ✅ — but too many issues editing `.ipynb`

#### Phase 1.5: Create `index.qmd` from Scratch ✅ COMPLETE
> **Why**: Editing `.ipynb` programmatically is fragile (JSON cell manipulation, stale cached outputs,
> no clean diffing in git). A `.qmd` file is plain text, easy to edit, and Quarto-native.

- [x] **1.5a. Analyze all 13 snapshots** — deep 8-section analysis + web research for vote tallies
- [x] **1.5b. Create `index.qmd`** — brand new Quarto document in **pt-BR** with 17 sections
- [x] **1.5c. Implement data loading** — `load_snapshot()`, `get_all_snapshots()` from `data/snapshots/`
- [x] **1.5d. Reconsider all visualizations** — 17 visualization sections using Plotly + NetworkX:
  - Overview stats, timeline, paredão results, sentiment ranking, sentiment evolution
  - Cross-table heatmap, reaction summary, alliances, rivalries, network graph
  - Reaction dynamics, flip-floppers, balance timeline, balance vs sentiment scatter
  - Group favoritism, negative givers profile, individual participant profiles
  - All labels, titles, legends in pt-BR
- [x] **1.5e. Implement analysis** — sentiment scores, alliances/rivalries, vira-casacas, group favoritism
- [x] **1.5f. Update `_quarto.yml`** — renders `index.qmd`, title in pt-BR
- [x] **1.5g. Move `BBB.ipynb` to `_legacy/`**
- [x] **1.5h. Test `quarto render`** — all 19 cells executed, 454KB HTML output
- [x] **1.5i. Commit the new document** — commit `b98a3e3`

#### Phase 1.6: Manual Game Data ✅ COMPLETE

Some game data is **not available from the API** and must be added manually after each event.
The `index.qmd` includes a structured `paredoes` list that supports easy manual updates.

**Currently tracked (manual):**
- Paredão results: vote percentages (total + voto único/torcida breakdown), formation story, eliminated participant
- Leader nominations and immunity details
- House votes (who voted for whom)

**Completed:**
- [x] **1.6a. Voto Único vs Voto da Torcida breakdown** — `voto_unico` and `voto_torcida` fields in each paredão entry (70% + 30% weight system), with grouped bar chart
- [x] **1.6b. Indicações do Líder** — tracked in `lider`, `indicado_lider` fields; analyzed in vote-reaction-analysis (coerência com reações)
- [x] **1.6c. Votação da casa** — `votos_casa` dict in each paredão entry; cross-referenced with reaction cross-table (coerência analysis, scatter plots, pie charts)
- [x] **1.6e. Comparative visualizations** — vote vs reaction coherence analysis, scatter plot (neg received vs votes), pie chart of coherence types

**Deferred:**
- [ ] **1.6d. Create `data/manual/` directory** — currently all manual data lives in `index.qmd`; JSON extraction deferred until paredão count justifies it

#### Phase 1.7: Paredão Archive Page ✅ COMPLETE

Created `arquivo.qmd` — a separate page for comprehensive paredão analysis.

**What was done:**
- [x] **1.7a. Created `arquivo.qmd`** — separate page with per-paredão sections
- [x] **1.7b. Per-paredão analysis includes**: result chart, formation details, house votes table, vote vs reaction coherence (scatter + pie), "O caso [mais votado]", leader nomination analysis, sentiment ranking, reactions received table
- [x] **1.7c. Updated `_quarto.yml`** — two-page website with navbar (Painel + Arquivo)
- [x] **1.7d. Moved paredão archive from index.qmd to arquivo.qmd**

#### Phase 1.8: Day-Over-Day Changes Section ✅ COMPLETE

Added "O Que Mudou Hoje?" section with multiple visualizations:

- [x] **1.8a. Diverging bar chart** — winners and losers (who gained/lost most sentiment)
- [x] **1.8b. Difference heatmap** — cells showing which specific reactions changed
- [x] **1.8c. Volatility chart** — stacked bar showing who changed opinions most (positive/negative/lateral)
- [x] **1.8d. Sankey diagram** — flow of reaction changes (from → to)
- [x] **1.8e. Dramatic changes list** — narrative highlights of biggest changes

#### Phase 1.9: Cluster Analysis ✅ COMPLETE

Added affinity clustering and related visualizations:

- [x] **1.9a. Hierarchical clustering** — groups participants by mutual sentiment using Ward's method
- [x] **1.9b. Cluster summary** — shows members per cluster, group composition, inter-cluster dynamics
- [x] **1.9c. Affinity heatmap** — reordered by cluster with white boundary lines
- [x] **1.9d. Polarizing participants** — who gives/receives most negativity, most mutual enemies

#### Phase 1.10: Theme and Layout ✅ COMPLETE

Improved visual design:

- [x] **1.10a. Dark theme** — switched to Bootswatch `darkly` theme
- [x] **1.10b. Custom Plotly template** — `bbb_dark` template with matching colors (#303030 background)
- [x] **1.10c. Removed TOC sidebar** — `toc: false` in `_quarto.yml`
- [x] **1.10d. Full-width layout** — `page-layout: full` for wider content
- [x] **1.10e. Fixed legend overlaps** — adjusted margins and legend positions
- [x] **1.10f. Data type tags** — added 📸 (daily), 📅 (day-to-day), 📈 (accumulated) tags to all sections

#### Phase 1.11: Code Cleanup ✅ COMPLETE

- [x] **1.11a. Removed duplicate sections** — vote-reaction analysis now only in arquivo.qmd
- [x] **1.11b. Fixed label inconsistencies** — changed `/snap` to `/dia` in charts
- [x] **1.11c. Verified Jan 13 data** — matches GShow queridômetro article (51 negative + 369 hearts)

#### Phase 1.12: Hostility Analysis ✅ COMPLETE

Added comprehensive hostility tracking:
- [x] **1.12a. One-sided hostility** — A gives negative to B, B gives ❤️ to A ("blind spots")
- [x] **1.12b. Two-sided hostility** — Both A and B give negative to each other ("declared enemies")
- [x] **1.12c. Hostilidades do Dia section** — Daily snapshot analysis
- [x] **1.12d. Hostilidades Persistentes section** — Accumulated over time
- [x] **1.12e. Mudanças em Hostilidades** — Day-over-day hostility changes in "O Que Mudou Hoje?"
- [x] **1.12f. Insights do Jogo section** — Key findings connecting hostility to voting patterns
- [x] **1.12g. Updated CLAUDE.md** — Documented hostility analysis concepts

#### Phase 1.13: Flexible Paredão System ✅ COMPLETE

Improved paredão display to handle partial data:
- [x] **1.13a. `total_esperado` field** — Shows placeholder cards for missing nominees
- [x] **1.13b. `como` field** — Describes how each participant was nominated
- [x] **1.13c. Conditional section display** — Hide "Reações Preveem Votos?" until votos_casa available
- [x] **1.13d. Added 2º Paredão** — Leandro via Caixas-Surpresa dynamic (partial formation)

---

### Phase 2: Dashboard Reorganization ⏳ PENDING

> **Detailed plan**: See `REORGANIZATION_PLAN.md` for complete section audit and implementation details.

The dashboard has grown to 25+ sections and needs reorganization into focused pages.

#### Phase 2.0: Planning ✅ COMPLETE
- [x] **2.0a. Created REORGANIZATION_PLAN.md** — Complete section audit with 23 sections mapped
- [x] **2.0b. 5-page architecture** — Painel, O Que Mudou, Trajetória, Paredão, Arquivo
- [x] **2.0c. Improvements list** — 20+ improvements to existing sections
- [x] **2.0d. New ideas list** — 15+ new section ideas across all pages

#### Phase 2.1: Create Page Skeletons ✅ COMPLETE
- [x] **2.1.1. Create `mudancas.qmd`** — Copy setup cells, add header
- [x] **2.1.2. Create `trajetoria.qmd`** — Copy setup cells, add header
- [x] **2.1.3. Create `paredao.qmd`** — Copy setup cells, add header
- [x] **2.1.4. Update `_quarto.yml`** — Add 5 pages to navbar + render list

#### Phase 2.2: Move Sections (O Que Mudou) ✅ COMPLETE
- [x] **2.2.1. O Que Mudou Hoje?** — All subsections (winners/losers, heatmap, Sankey, volatility, dramatics, hostility changes)
- [x] **2.2.2. Mudanças Entre Dias** — Reaction changes over time
- [x] **2.2.3. Vira-Casacas** — Who changes opinions most

#### Phase 2.3: Move Sections (Trajetória) ✅ COMPLETE
- [x] **2.3.1. Cronologia do Jogo** — Entry/exit timeline (kept in index for overview)
- [x] **2.3.2. Evolução do Sentimento** — Line chart over time
- [x] **2.3.3. Alianças Mais Consistentes** — Accumulated mutual hearts
- [x] **2.3.4. Rivalidades Mais Persistentes** — Accumulated mutual negativity
- [x] **2.3.5. Hostilidades Persistentes** — One/two-sided over time
- [x] **2.3.6. Clusters de Afinidade** — Hierarchical clustering
- [x] **2.3.7. Evolução do Saldo** — Balance timeline
- [x] **2.3.8. Saldo vs Sentimento** — Scatter with correlation
- [x] **2.3.9. Favoritismo Intragrupo** — Vip vs Xepa analysis

#### Phase 2.4: Move Sections (Paredão) ✅ COMPLETE
- [x] **2.4.1. Resultado do Paredão** — Current paredão display (moved to paredao.qmd)
- [x] **2.4.2. Reações Preveem Votos?** — Vote vs reactions analysis (moved to paredao.qmd)
- [x] **2.4.3. Voto da Casa vs Queridômetro** — Coherence table (moved to paredao.qmd)
- [x] **2.4.4. Manual paredões data** — Now lives in paredao.qmd

#### Phase 2.5: Clean Up Painel ✅ COMPLETE
- [x] **2.5.1. Remove moved sections** — index.qmd reduced from 1485 to 889 lines
- [x] **2.5.2. Add paredão callout** — Callout linking to paredao.qmd
- [x] **2.5.3. Add navigation callouts** — Links to other pages via callouts
- [ ] **2.5.4. Add "Destaques do Dia"** — Auto-generated daily highlights (deferred)

#### Phase 2.6: Polish and Test ✅ COMPLETE
- [x] **2.6.1. Add page headers** — Each page has description
- [x] **2.6.2. Add cross-links** — Navigation callouts on each page
- [x] **2.6.3. Test all pages** — All 5 pages render without errors
- [x] **2.6.4. Update CLAUDE.md** — Document new architecture

#### Phase 2.7: Enhancements (Future)
- [ ] **2.7.1. Date picker** — Compare any two dates in queridômetro
- [ ] **2.7.2. Paredão predictions** — Based on hostility analysis
- [ ] **2.7.3. Participant focus mode** — Individual trajectory view
- [ ] **2.7.4. Compare paredões** — Side-by-side in arquivo
- [ ] **2.7.5. Mobile improvements** — Responsive design

---

### Phase 3: GitHub Actions ✅ COMPLETE
- [x] **3.1. Create `.github/workflows/daily-update.yml`** — 4x daily cron with multi-capture strategy
- [x] **3.2. Enhanced `fetch_data.py`** — Detects change types (reactions, balance, roles, elimination)

### Phase 4: GitHub Pages ⏳ READY TO DEPLOY

**When ready to publish, follow these steps:**

1. **Push to GitHub**
   ```bash
   git add -A
   git commit -m "feat: add GitHub Actions workflow for automated daily updates"
   git push origin main
   ```

2. **Enable GitHub Pages**
   - Go to repository **Settings** → **Pages**
   - Under "Build and deployment", set **Source**: `GitHub Actions`
   - (Do NOT select "Deploy from a branch" — use Actions)

3. **Trigger first deployment**
   - Go to **Actions** tab in GitHub
   - Select "BBB26 Daily Update" workflow
   - Click **Run workflow** → **Run workflow**
   - Wait for it to complete (~2-3 minutes)

4. **Verify site is live**
   - URL will be: `https://<username>.github.io/BBB26/`
   - Check all 5 pages render correctly
   - Verify data is current

**Checklist:**
- [ ] **4.1. Push code to GitHub**
- [ ] **4.2. Enable GitHub Pages with "GitHub Actions" source**
- [ ] **4.3. Manually trigger workflow to test**
- [ ] **4.4. Verify site is live at `<username>.github.io/BBB26`**
- [ ] **4.5. Verify automated runs work (check next scheduled run)**

---

## Considerations

### Timezone & Update Timing

- GitHub Actions runs in UTC
- **Data update time is UNKNOWN** - API has no timestamp
- Data changes are **event-driven** (eliminations, new entrants), not time-based
- Running 4x daily (every 6 hours) ensures we catch changes relatively quickly
- The fetch script only saves when data actually changes, so extra runs are cheap

### Error Handling

The workflow should handle:
- API failures (use cached data)
- No changes (skip commit)
- Render failures (fail workflow, notify)

### Caching

GitHub Actions caches:
- Python packages (`pip cache`)
- Quarto installation (handled by action)

### Notifications (Optional)

Add Slack/Discord notification on failure:

```yaml
- name: Notify on failure
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

---

## Timeline

### Completed Phases ✅

| # | Phase | Description | Status |
|---|-------|-------------|--------|
| 0 | Data Audit | 13 canonical snapshots established | ✅ Done |
| 0.5 | Git Cleanup | Commit `28ef943` | ✅ Done |
| 1 | Local Setup | `_quarto.yml`, `requirements.txt` | ✅ Done |
| 1.5 | Create `index.qmd` | Fresh Quarto doc, 17 sections | ✅ Done |
| 1.6 | Manual Game Data | Paredão results, house votes | ✅ Done |
| 1.7 | Paredão Archive | `paredoes.qmd` with per-paredão analysis | ✅ Done |
| 1.8 | Day-Over-Day Changes | Diverging bar, heatmap, Sankey, volatility | ✅ Done |
| 1.9 | Cluster Analysis | Hierarchical clustering, affinity heatmap | ✅ Done |
| 1.10 | Theme & Layout | Darkly theme, full-width, custom Plotly | ✅ Done |
| 1.11 | Code Cleanup | Removed duplicates, verified data | ✅ Done |
| 1.12 | Hostility Analysis | One/two-sided, blind spots, insights | ✅ Done |
| 1.13 | Flexible Paredão | Partial formation, `como` field, 2º Paredão | ✅ Done |
| 2.0 | Reorganization Plan | REORGANIZATION_PLAN.md with section audit | ✅ Done |

### Upcoming Phases ⏳

| # | Phase | Description | Priority |
|---|-------|-------------|----------|
| 2.1-2.6 | Dashboard Reorganization | Split into 5 focused pages | High |
| 2.7 | Enhancements | Date picker, predictions, focus mode | Medium |
| 3 | GitHub Actions | 4x daily cron workflow | High |
| 4 | GitHub Pages | Deploy to `username.github.io/BBB26` | High |

### Current Section Count

| Page | Sections | Charts |
|------|----------|--------|
| index.qmd (current) | 23 | ~20 |
| paredoes.qmd | 1 + N×8 | ~5×N |

### After Reorganization (Target)

| Page | File | Sections | Est. Charts |
|------|------|----------|-------------|
| Painel | `index.qmd` | 9 | 5-6 |
| O Que Mudou | `mudancas.qmd` | 11 | 6-8 |
| Trajetória | `trajetoria.qmd` | 12 | 8-10 |
| Paredão | `paredao.qmd` | 8 | 4-5 |
| Arquivo | `paredoes.qmd` | existing | 5×N |

---

## Resources

- [Quarto Documentation](https://quarto.org/docs/guide/)
- [Quarto with Jupyter](https://quarto.org/docs/tools/jupyter-lab.html)
- [GitHub Actions for Quarto](https://quarto.org/docs/publishing/github-pages.html)
- [GitHub Pages Documentation](https://docs.github.com/en/pages)

---

## Notes

- Keep the original `BBB.ipynb` for development/exploration
- The Quarto site can render the notebook directly or use converted `.qmd` files
- Consider adding interactive Plotly charts for better UX on the web
- The workflow runs daily but can be manually triggered for testing
