# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BBB26 is a data analysis project that tracks **participant reaction data** from Big Brother Brasil 26 using the GloboPlay API. The main analysis is in `BBB.ipynb`, which fetches daily snapshots, processes reactions, and generates visualizations.

## Key Commands

```bash
# Fetch new data (saves only if data changed)
python scripts/fetch_data.py

# Audit all snapshots (find duplicates, unique states)
python scripts/audit_snapshots.py

# Run the notebook (requires Jupyter)
jupyter notebook BBB.ipynb
```

## Data Architecture

### API Source
- **Endpoint**: `https://apis-globoplay.globo.com/mve-api/globo-play/realities/bbb/participants/`
- **Returns**: Complete state snapshot — NOT cumulative, NOT additive
- **No timestamp**: API provides no `Last-Modified` header or update timestamp
- **Update frequency**: Data changes daily at unpredictable times, with intraday changes possible

### Critical: Reactions Are Reassigned Daily

The API returns the **current state** of all reactions, not a history. Participants **change** their reactions to others daily:
- Someone who gave ❤️ yesterday can switch to 🐍 today
- Reaction amounts can go up OR down
- The giver lists (who gave which reaction) change between snapshots

This means **every snapshot is a unique complete game state** and must be kept.

### Data Files
- `data/snapshots/YYYY-MM-DD_HH-MM-SS.json` — Full API snapshots (~200-270KB each)
- `data/latest.json` — Copy of most recent snapshot
- `data/CHANGELOG.md` — Documents data timeline and findings
- New format wraps data: `{ "_metadata": {...}, "participants": [...] }`
- Old format is just the raw array: `[...]`
- `scripts/fetch_data.py` handles both formats and saves only when data hash changes

### Reaction Categories
```python
POSITIVE = ['Coração']  # ❤️
MILD_NEGATIVE = ['Planta', 'Mala', 'Biscoito']  # 🌱💼🍪
STRONG_NEGATIVE = ['Cobra', 'Alvo', 'Vômito', 'Mentiroso', 'Coração partido']  # 🐍🎯🤮🤥💔
```

Sentiment weights: positive = +1, mild_negative = -0.5, strong_negative = -1

### Volatile Fields (change daily)
- `balance` — decreases over time
- `roles` — rotates (Líder, Paredão, etc.)
- `group` — can change (Vip ↔ Xepa)
- `receivedReactions` — amounts AND givers change daily
- `eliminated` — permanent once true

## Repository Structure

```
BBB26/
├── data/
│   ├── snapshots/          # Canonical JSON snapshots (one per unique data state)
│   ├── latest.json         # Most recent snapshot
│   └── CHANGELOG.md        # Data timeline documentation
├── scripts/
│   ├── fetch_data.py       # Fetch API, save if changed (hash comparison)
│   └── audit_snapshots.py  # Audit tool for deduplication
├── BBB.ipynb               # Main analysis notebook
├── _legacy/                # Old assets (gitignored)
└── IMPLEMENTATION_PLAN.md  # GitHub Actions + Quarto + Pages plan
```

## Notebook Structure (BBB.ipynb)

The notebook follows a linear pipeline:
1. **Setup** — imports (pandas, matplotlib, plotly, networkx)
2. **Reaction categorization** — emoji mapping and sentiment weights
3. **Data collection** — API fetch with local JSON backup/fallback
4. **Data processing** — cross tables (cumulative and daily), sentiment matrices
5. **Analysis** — sentiment scores, controversy scores, alliance detection
6. **Visualizations** — heatmaps, correlation plots, network graphs, timelines

## Future Plans

See `IMPLEMENTATION_PLAN.md` for GitHub Actions + Quarto + GitHub Pages automation setup.
