# BBB26 Dashboard - GitHub Actions + Quarto + GitHub Pages

## Implementation Plan

This document outlines the plan to automate the BBB26 reaction analysis notebook and publish it as a daily-updated website using GitHub Actions and GitHub Pages.

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
- Multiple consecutive days can have **identical data**
- Changes happen around eliminations, new entrants, or voting rounds
- The "noon cutoff" assumption may not be accurate

### Current Data Storage (Already Good!)

The notebook **already saves the full API response** (~200-270KB per file):
- ~11 files = ~2.4MB
- Projected season total (~90 days): ~25MB - easily manageable in git

### Recommended Strategy

1. **Save full API response** (already doing this - keep it!)
2. **Save only when data changes** (compare hash/content with previous)
3. **Record capture timestamp** in filename (for audit trail)
4. **Run multiple times per day** if you want to catch exact change times (optional)

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

## Repository Structure

```
BBB26/
├── .github/
│   └── workflows/
│       └── daily-update.yml       # GitHub Actions workflow
│
├── data/
│   ├── snapshots/                 # Historical JSON files
│   │   ├── 2026-01-13.json
│   │   ├── 2026-01-14.json
│   │   └── ...
│   └── latest.json                # Symlink or copy of most recent
│
├── scripts/
│   └── fetch_data.py              # Standalone data fetching script
│
├── _quarto.yml                    # Quarto configuration
├── index.qmd                      # Main dashboard (converted from notebook)
├── analysis.qmd                   # Detailed analysis page (optional)
├── about.qmd                      # About page (optional)
│
├── assets/                        # Static assets (CSS, images)
│
├── BBB.ipynb                      # Original notebook (kept for development)
├── requirements.txt               # Python dependencies
├── IMPLEMENTATION_PLAN.md         # This file
└── README.md                      # Project documentation
```

---

## Phase 1: Local Setup (Do First)

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

### 1.4 Extract Data Fetching Script

Create `scripts/fetch_data.py` with smarter save-only-if-changed logic:

```python
#!/usr/bin/env python3
"""
Fetch BBB26 participant data and save as dated snapshot.
Designed to run via GitHub Actions.

Key behaviors:
- Saves full API response (for rich historical data)
- Only creates new file if data actually changed
- Uses content hash to detect changes
- Records capture timestamp in filename
"""

import requests
import json
import hashlib
from datetime import datetime
from pathlib import Path

API_URL = "https://apis-globoplay.globo.com/mve-api/globo-play/realities/bbb/participants/"
DATA_DIR = Path("data/snapshots")

def get_data_hash(data):
    """Generate hash of data for comparison (ignores formatting)."""
    # Sort keys for consistent hashing
    normalized = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(normalized.encode()).hexdigest()

def get_latest_snapshot():
    """Get the most recent snapshot file and its data."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    snapshots = sorted(DATA_DIR.glob("*.json"))
    if not snapshots:
        return None, None
    latest = snapshots[-1]
    with open(latest) as f:
        return latest, json.load(f)

def fetch_and_save():
    """Fetch data from API and save snapshot only if data changed."""

    # Fetch from API
    print(f"Fetching from API...")
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    new_data = response.json()
    new_hash = get_data_hash(new_data)

    # Compare with latest snapshot
    latest_file, latest_data = get_latest_snapshot()

    if latest_data:
        latest_hash = get_data_hash(latest_data)
        if new_hash == latest_hash:
            print(f"No changes detected (hash: {new_hash[:8]}...)")
            print(f"Latest snapshot: {latest_file}")
            return str(latest_file)
        else:
            print(f"Data changed! Old hash: {latest_hash[:8]}..., New hash: {new_hash[:8]}...")
    else:
        print("No previous snapshots found - this will be the first one")

    # Save new snapshot with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    snapshot_path = DATA_DIR / f"{timestamp}.json"

    # Include metadata in saved file
    save_data = {
        "_metadata": {
            "captured_at": datetime.now().isoformat(),
            "api_url": API_URL,
            "data_hash": new_hash,
            "participant_count": len(new_data),
            "total_reactions": sum(
                sum(r.get("amount", 0) for r in p.get("characteristics", {}).get("receivedReactions", []))
                for p in new_data
            )
        },
        "participants": new_data
    }

    with open(snapshot_path, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)

    # Update latest.json (for easy access)
    latest_path = DATA_DIR.parent / "latest.json"
    with open(latest_path, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)

    print(f"Saved new snapshot: {snapshot_path}")
    print(f"  Participants: {len(new_data)}")
    print(f"  Total reactions: {save_data['_metadata']['total_reactions']}")

    return str(snapshot_path)

if __name__ == "__main__":
    fetch_and_save()
```

**Key improvements:**
- Only saves when data actually changes (saves disk space, cleaner git history)
- Adds `_metadata` block with capture timestamp, hash, and summary stats
- Maintains `latest.json` for easy notebook access

### 1.5 Update Notebook to Read from `data/` Directory

Modify the data loading functions to handle the new format with metadata:

```python
from pathlib import Path

DATA_DIR = Path("data/snapshots")
LATEST_FILE = Path("data/latest.json")

def load_snapshot(filepath):
    """Load a snapshot file, handling both old and new formats."""
    with open(filepath) as f:
        data = json.load(f)

    # New format has _metadata and participants keys
    if "_metadata" in data and "participants" in data:
        return data["participants"], data["_metadata"]

    # Old format is just the array of participants
    return data, None

def load_latest_data():
    """Load most recent snapshot."""
    if LATEST_FILE.exists():
        return load_snapshot(LATEST_FILE)

    # Fallback to most recent in snapshots/
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

The existing `catalog_bbb_files()` logic handles deduplication by effective date. We'll simplify this in the new structure by using `YYYY-MM-DD.json` filenames (one file per effective date).

---

## Phase 5: Migration Checklist

### Step-by-Step Migration

- [ ] **1. Install Quarto locally**
- [ ] **2. Create `_quarto.yml` configuration**
- [ ] **3. Create `data/snapshots/` directory structure**
- [ ] **4. Migrate existing JSON files to new structure**
  ```bash
  mkdir -p data/snapshots
  # Rename files to YYYY-MM-DD.json format
  ```
- [ ] **5. Create `scripts/fetch_data.py`**
- [ ] **6. Update notebook data loading paths**
- [ ] **7. Test `quarto render` locally**
- [ ] **8. Test `quarto preview` locally**
- [ ] **9. Create `.github/workflows/daily-update.yml`**
- [ ] **10. Create/update `requirements.txt`**
- [ ] **11. Push to GitHub**
- [ ] **12. Enable GitHub Pages in repo settings**
- [ ] **13. Manually trigger workflow to test**
- [ ] **14. Verify site is live at `<username>.github.io/BBB26`**

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

1. **Local Setup** (Phase 1): Test Quarto rendering locally
2. **Workflow Creation** (Phase 2): Set up GitHub Actions
3. **Pages Setup** (Phase 3): Enable and test deployment
4. **Data Migration** (Phase 4): Move existing snapshots to new structure
5. **Go Live** (Phase 5): Enable scheduled runs

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
