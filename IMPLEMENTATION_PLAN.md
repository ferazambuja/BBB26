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
| | **Commit all reorganization changes** (116 deletions + 18 new files) | ⏳ Pending |
| | Create `_quarto.yml` | ⏳ Pending |
| | Create `requirements.txt` | ⏳ Pending |
| | Create/update `index.qmd` or adapt notebook | ⏳ Pending |
| | Test Quarto locally | ⏳ Pending |
| | Create GitHub Actions workflow | ⏳ Pending |
| | Enable GitHub Pages | ⏳ Pending |

### Git Status (Uncommitted)

The repository reorganization is complete on disk but **not yet committed**. Current git state:

| Change Type | Count | Description |
|-------------|-------|-------------|
| Deleted (from git tracking) | 116 | Old root-level JSONs, CSVs, PNGs, `backup/`, `archive_duplicates/`, `BBB_old.ipynb`, `organize_and_backup.py` — all moved to `_legacy/` (gitignored) |
| Modified | 2 | `CLAUDE.md`, `IMPLEMENTATION_PLAN.md` |
| New (untracked) | 18 | `.gitignore`, `data/` (CHANGELOG.md, latest.json, 13 snapshots), `scripts/` (fetch_data.py, audit_snapshots.py) |

**Note**: The 116 "deleted" files are safe — they all exist physically in `_legacy/` which is gitignored. The deletions just remove them from git tracking.

### Current Repository Structure

```
BBB26/
├── .git/
├── .gitignore              ✅ NEW (ignores _legacy/, *.png, *.csv, etc.)
├── .vscode/
├── BBB.ipynb               (original notebook — tracked, unmodified)
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
│   │   ├── 2026-01-13_17-18-02.json   # Full timestamp format
│   │   ├── ...                        # (one per unique data state)
│   │   └── 2026-01-24_18-46-05.json
│   ├── latest.json                # Copy of most recent snapshot
│   └── CHANGELOG.md               # Data timeline + audit findings
│
├── scripts/
│   ├── fetch_data.py              # Fetch API, save if hash changed
│   └── audit_snapshots.py         # Deduplication audit tool
│
├── _quarto.yml                    # Quarto configuration (Phase 1)
├── index.qmd                      # Main dashboard (Phase 1)
│
├── BBB.ipynb                      # Original notebook (kept for development)
├── CLAUDE.md                      # Project guidance
├── requirements.txt               # Python dependencies (Phase 1)
├── IMPLEMENTATION_PLAN.md         # This file
├── .gitignore                     # Ignores _legacy/, *.png, *.csv, etc.
│
└── _legacy/                       # (gitignored) Backup of all old files
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

### 1.3 Convert Notebook to Quarto Document

Option A: Use notebook directly (Quarto can render `.ipynb`):
```yaml
# In _quarto.yml, just reference the notebook
website:
  navbar:
    left:
      - href: BBB.ipynb
        text: Dashboard
```

Option B: Convert to `.qmd` for more control:
```bash
quarto convert BBB.ipynb --output index.qmd
```

### 1.4 Data Fetching Script ✅ DONE

See `scripts/fetch_data.py` — already created and tested. Key features:
- Only saves when data hash changes (no duplicates)
- Wraps data in `{ "_metadata": {...}, "participants": [...] }`
- Updates `data/latest.json` on each new save
- Handles both old format (raw array) and new format (with metadata)

### 1.5 Update Notebook to Read from `data/` Directory

When adapting `BBB.ipynb` (or creating `index.qmd`), the data loading functions need to handle both old format (raw array) and new format (with `_metadata`):

```python
from pathlib import Path

DATA_DIR = Path("data/snapshots")
LATEST_FILE = Path("data/latest.json")

def load_snapshot(filepath):
    """Load a snapshot file, handling both old and new formats."""
    with open(filepath) as f:
        data = json.load(f)
    if isinstance(data, dict) and "participants" in data:
        return data["participants"], data.get("_metadata")
    return data, None  # Old format: raw array

def load_latest_data():
    """Load most recent snapshot."""
    if LATEST_FILE.exists():
        return load_snapshot(LATEST_FILE)
    snapshots = sorted(DATA_DIR.glob("*.json"))
    if snapshots:
        return load_snapshot(snapshots[-1])
    return None, None

def load_all_snapshots():
    """Load all historical snapshots for timeline analysis."""
    snapshots = []
    for filepath in sorted(DATA_DIR.glob("*.json")):
        participants, metadata = load_snapshot(filepath)
        snapshots.append({
            "file": filepath.name,
            "timestamp": filepath.stem,  # YYYY-MM-DD_HH-MM-SS
            "participants": participants,
            "metadata": metadata
        })
    return snapshots
```

### 1.6 Test Locally

```bash
# Render the site locally
quarto preview

# Or render once
quarto render
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

#### Phase 0.5: Git Cleanup ⏳ PENDING
- [ ] **0.5a. Commit the full reorganization** — 116 git deletions + 18 new files + 2 modified files
- [ ] **0.5b. Verify clean `git status`** after commit

#### Phase 1: Local Quarto Setup
- [x] **1.1. Install Quarto locally** ✅ (v1.8.27 via Homebrew)
- [x] **1.2. Create `data/snapshots/` directory structure** ✅
- [x] **1.3. Create `scripts/fetch_data.py`** ✅ (hash comparison, metadata wrapper, latest.json update)
- [ ] **1.4. Create `_quarto.yml` configuration**
- [ ] **1.5. Create `requirements.txt`**
- [ ] **1.6. Update notebook or create `index.qmd`**
- [ ] **1.7. Test `quarto render` locally**
- [ ] **1.8. Test `quarto preview` locally**

#### Phase 2: GitHub Actions
- [ ] **2.1. Create `.github/workflows/daily-update.yml`** (4x daily cron)

#### Phase 3: GitHub Pages
- [ ] **3.1. Push to GitHub**
- [ ] **3.2. Enable GitHub Pages in repo settings**
- [ ] **3.3. Manually trigger workflow to test**
- [ ] **3.4. Verify site is live at `<username>.github.io/BBB26`**

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

1. ~~**Data Audit** (Phase 0)~~: ✅ COMPLETE — 13 canonical snapshots established
2. **Git Cleanup** (Phase 0.5): Commit the reorganization (116 deletions + 18 new files)
3. **Local Setup** (Phase 1): Create `_quarto.yml`, `requirements.txt`, test rendering
4. **Workflow Creation** (Phase 2): Set up GitHub Actions (4x daily cron)
5. **Pages Setup** (Phase 3): Enable GitHub Pages, test deployment
6. **Go Live**: Enable scheduled runs

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
