# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BBB26 is a data analysis project that tracks **participant reaction data** from Big Brother Brasil 26 using the GloboPlay API. The main analysis is in `BBB.ipynb`, which fetches daily snapshots, processes reactions, and generates visualizations.

## Key Commands

```bash
# Run the notebook (requires Jupyter)
jupyter notebook BBB.ipynb

# Organize data files (backup + deduplicate by effective date)
python organize_and_backup.py
```

## Data Architecture

### API Source
- **Endpoint**: `https://apis-globoplay.globo.com/mve-api/globo-play/realities/bbb/participants/`
- **Returns**: Array of participant objects with cumulative reaction totals (not daily increments)
- **No timestamp**: API provides no `Last-Modified` header or update timestamp
- **Event-driven updates**: Data changes with eliminations/new entrants, not on a fixed schedule

### Data Files
- `bbb_participants_YYYY-MM-DD_HH-MM-SS.json` — Full API snapshots (~200-270KB each)
- Effective date rule: captures before noon are treated as previous calendar day's data
- One canonical file kept per effective date; duplicates moved to `archive_duplicates/`

### Reaction Categories
```python
POSITIVE = ['Coração']  # ❤️
MILD_NEGATIVE = ['Planta', 'Mala', 'Biscoito']  # 🌱💼🍪
STRONG_NEGATIVE = ['Cobra', 'Alvo', 'Vômito', 'Mentiroso', 'Coração partido']  # 🐍🎯🤮🤥💔
```

Sentiment weights: positive = +1, mild_negative = -0.5, strong_negative = -1

## Notebook Structure (BBB.ipynb)

The notebook follows a linear pipeline:
1. **Setup** — imports (pandas, matplotlib, plotly, networkx)
2. **Reaction categorization** — emoji mapping and sentiment weights
3. **Data collection** — API fetch with local JSON backup/fallback
4. **Data processing** — cross tables (cumulative and daily), sentiment matrices
5. **Analysis** — sentiment scores, controversy scores, alliance detection
6. **Visualizations** — heatmaps, correlation plots, network graphs, timelines

Key functions to understand:
- `save_api_response()` — fetches API, saves only if effective date has no canonical file
- `catalog_bbb_files()` — returns DataFrame of all snapshots with effective dates
- `calculate_daily_changes()` — diffs current vs previous day for daily analysis
- `create_emoji_cross_table()` — giver×receiver matrix with emoji indicators

## Future Plans

See `IMPLEMENTATION_PLAN.md` for GitHub Actions + Quarto + GitHub Pages automation setup.
