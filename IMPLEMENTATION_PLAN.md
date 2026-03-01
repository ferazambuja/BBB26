# BBB26 Dashboard — Deployment Guide

> **Status**: Ready to deploy. All features complete. GitHub Actions workflow on disk.
>
> **Last updated**: 2026-02-11

---

## Overview

BBB26 is a Quarto-based dashboard tracking participant reaction data from Big Brother Brasil 26 via the GloboPlay API. It auto-fetches snapshots, builds derived analytics, and renders interactive Plotly visualizations.

**Stack**: Python 3.10+ · Quarto · Plotly · GitHub Actions · GitHub Pages

---

## Data Pipeline

```
GloboPlay API
    ↓  scripts/fetch_data.py (saves only if data hash changed)
data/snapshots/*.json + data/latest.json
    ↓  scripts/build_derived_data.py (called automatically by fetch)
data/derived/*.json (20+ files: metrics, scores, indexes, timeline, clusters, etc.)
    ↓  quarto render
_site/ (11 HTML pages)
```

**Data sources:**

| Type | Files | Update Method |
|------|-------|---------------|
| **Auto (API)** | `data/snapshots/*.json`, `data/latest.json` | `fetch_data.py` (scheduled CI multi-capture: permanent slots + probes) |
| **Manual** | `manual_events.json`, `paredoes.json`, `provas.json`, `votalhada/polls.json` | Human-maintained after events |
| **Derived** | `data/derived/*.json` (20+ files) | `build_derived_data.py` (auto or after manual edits) |

---

## GitHub Actions Workflow

**File**: `.github/workflows/daily-update.yml`

**Schedule** (current, all UTC → BRT):

Permanent slots (daily):

| UTC | BRT | Purpose |
|-----|-----|---------|
| 03:00 | 00:00 | Night — post-episode changes |
| 09:00 | 06:00 | Pre-Raio-X baseline |
| 18:00 | 15:00 | Post-Raio-X — primary capture (data updates ~14:00 BRT) |
| 21:00 | 18:00 | Evening — balance/role changes |

Observation probes (currently enabled):

| UTC | BRT | Purpose |
|-----|-----|---------|
| 13:00 | 10:00 | Probe — early Raio-X window |
| 14:00 | 11:00 | Probe |
| 15:00 | 12:00 | Probe |
| 16:00 | 13:00 | Probe |
| 17:00 | 14:00 | Probe — expected update window |
| 19:00 | 16:00 | Probe — late safety net |

Saturday extras:

| UTC | BRT | Purpose |
|-----|-----|---------|
| 20:00 | 17:00 | Post-Anjo challenge |
| 23:00 | 20:00 | Post-Monstro pick |

**What the workflow does:**
1. Checkout repo (full history)
2. Setup Python 3.11 + install `requirements.txt`
3. Run `fetch_data.py` (fetches API, saves if changed, rebuilds derived data)
4. Validate all JSON snapshots
5. Setup Quarto + render all 11 pages
6. Commit new data to `main` (if changed)
7. Deploy `_site/` to GitHub Pages via `actions/deploy-pages@v4`

Also supports `workflow_dispatch` for manual triggers.

---

## Deployment Checklist

### First-time setup

- [ ] Push code to GitHub (`git push origin main`)
- [ ] Go to repository **Settings → Pages → Source** → select **GitHub Actions**
- [ ] Go to **Actions** tab → "BBB26 Daily Update" → **Run workflow** (manual trigger)
- [ ] Verify site is live at `https://<username>.github.io/BBB26/`
- [ ] Wait for next scheduled run to confirm automation works

### After manual data edits

See **`docs/OPERATIONS_GUIDE.md`** → [Git Workflow](docs/OPERATIONS_GUIDE.md#git-workflow) for the full procedure (pull → edit → build → push → deploy).

---

## Storage & Limits

- ~300KB per snapshot × multi-capture/day = manageable in git
- 55 snapshots so far = ~14MB (projected ~25-60MB for full season)
- GitHub Pages limit: 1GB site size (dashboard is ~50MB rendered — well within limits)
- GitHub Actions: 2,000 min/month free tier (workflow runs ~3-5 min each, current cadence can reach ~1,100-1,800 min/month)

---

## Error Handling

- **Dedup**: Fetch script saves only when data hash changes (no duplicate snapshots)
- **Validation**: Workflow validates all JSON snapshots before rendering
- **Audit**: `build_derived_data.py` hard-fails on manual events audit issues
- **Raio-X**: Missing morning reactions auto-detected and patched for scoring
- **Concurrency**: Workflow uses concurrency group `"pages"` to prevent parallel deploys
