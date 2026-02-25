# Votalhada Poll Data

## What is Votalhada?

[Votalhada](https://votalhada.blogspot.com/) is a Brazilian blog that aggregates poll results from multiple platforms (websites, Twitter/X, YouTube, Instagram) during BBB paredões. They collect data from dozens of sources and compute weighted averages to predict elimination results.

## Quick Workflow

**Option A — Automated download (recommended)**

```bash
# Download all poll images for the current paredão (e.g. 6º)
python scripts/fetch_votalhada_images.py --paredao 6
```

Images are saved to `data/votalhada/YYYY_MM_DD/` (e.g. `2026_02_22/`). By default the script **overwrites** the previous capture (consolidados.png, consolidados_2.png, …), so you always keep the latest. Use `--timestamp` to keep a history of captures instead.

**Option B — Manual screenshot**

```
1. Save Consolidados screenshot → data/votalhada/YYYY_MM_DD/consolidados.png
2. Ask Claude to read the image and extract data
3. Claude updates polls.json automatically
```

**Only the Consolidados image is required** for data extraction — it contains all platform aggregates and time series.

## When to Collect

| Timing | Purpose |
|--------|---------|
| **Anytime during voting** | Track poll evolution (preliminary) |
| **Tuesday ~21:00 BRT** | Final snapshot before elimination |
| **After elimination** | Add `resultado_real` with actual percentages |

Votalhada typically updates images at **Monday** 1:00, 8:00, 12:00, 15:00, 18:00, 21:00 and **Tuesday** 8:00, 12:00, 15:00, 18:00, 21:00 BRT (a few minutes after the hour). Run the script after those times to capture the latest; by default only the last run is kept (overwrite). Use `--timestamp` to keep multiple captures per day.

## Collection Steps

### Step 1: Screenshot Consolidados

1. Go to [votalhada.blogspot.com](https://votalhada.blogspot.com/)
2. Find the current paredão post (e.g., "2º Paredão - Consolidados")
3. Screenshot the **Consolidados** table (includes platform summary + time series)
4. Save to `data/` folder (any name is fine)

### Step 2: Ask Claude to Process

Tell Claude:
```
I saved a Votalhada screenshot to data/[filename].png
Please extract the poll data for paredão N and update polls.json
```

Claude will:
1. Read the image
2. Move it to `data/votalhada/YYYY_MM_DD/consolidados.png`
3. Extract all data (percentages, votes, time series)
4. Update `polls.json`

### Step 3: Verify

```bash
quarto render paredao.qmd
# Check the "Enquetes" section appears
```

## Updating Preliminary Data

Poll numbers change throughout voting. When you have new data:

| Field | What Happens |
|-------|--------------|
| `consolidado` | **Overwritten** with latest values |
| `plataformas` | **Overwritten** with latest values |
| `data_coleta` | **Overwritten** with new timestamp |
| `serie_temporal` | **Appended** — new time points added |

This keeps current prediction fresh while preserving history.

## After Elimination

Add the `resultado_real` field:

```json
"resultado_real": {
  "Name1": XX.XX,
  "Name2": XX.XX,
  "Name3": XX.XX,
  "eliminado": "NameX",
  "predicao_correta": true
}
```

## What Data We Store

### We Store (Aggregates Only)

| Field | Description |
|-------|-------------|
| `consolidado` | Weighted average across all platforms |
| `plataformas.sites` | "Média Proporcional" from Sites |
| `plataformas.youtube` | "Média" from YouTube |
| `plataformas.twitter` | "Média" from Twitter |
| `plataformas.instagram` | "Média Geral" from Instagram |
| `serie_temporal` | Hourly evolution of consolidado |

### We Don't Store

- Individual poll sources (@GilDoVigor, Splash UOL, etc.)
- Per-source vote counts
- Individual source accuracy

The platform aggregates are what matter for prediction.

## Image Organization

```
data/votalhada/
├── polls.json              # All poll data
├── README.md               # This file
├── 2026_01_20/            # 1º Paredão (timestamp filenames)
│   └── 2026-01-20_*.png    # Original screenshots
├── 2026_02_22/            # 6º Paredão (from fetch_votalhada_images.py)
│   ├── consolidados.png    # Key image (latest capture)
│   ├── consolidados_2.png  # Second image from post
│   └── ...                 # Optional: use --timestamp to keep history
└── ...
```

**Naming convention**: The script saves the first image as `consolidados.png` (overwrites each run so you “keep the last one”). Additional images from the post are `consolidados_2.png`, etc. Use `--timestamp` to keep dated copies (e.g. `consolidados_2026-02-24_21-05.png`).

Only `consolidados.png` (or `_final.png`) is needed for data extraction.

**Scheduled runs (optional):** To capture at Votalhada’s usual update times, run the script via cron or Task Scheduler (e.g. Mon/Tue at 1:00, 8:00, 12:00, 15:00, 18:00, 21:00 BRT). Use `--paredao N` and set `N` to the current paredão, or use `--url` with the current post URL. With default behavior, each run overwrites the previous capture in that folder.

## Name Matching

Votalhada typically uses first names. Verify against `data/paredoes.json`:

```bash
python -c "
import json
p = json.load(open('data/paredoes.json'))
par = next(x for x in p['paredoes'] if x['numero'] == N)
print([i['nome'] for i in par['indicados_finais']])
"
```

## Data Quality Notes

| Platform | Characteristics |
|----------|----------------|
| **Sites** | Most stable, larger sample |
| **YouTube** | Community polls, moderate sample |
| **Twitter** | Most volatile, vocal fanbases, smaller sample |
| **Instagram** | Large sample, can shift late |
| **Consolidado** | Weighted average — best overall predictor |

## AI Agent Instructions

When reading a Consolidados image:

1. **Identify participants** from photos at top (left to right)

2. **Extract platform table** (top section):
   - Sites / YouTube / Twitter / Instagram rows
   - Percentages for each participant
   - Vote counts in last column

3. **Extract Média Proporcional** (consolidado row):
   - Final weighted percentages
   - Total vote count

4. **Extract time series** (VARIAÇÃO DAS MÉDIAS section):
   - Date/time in first column
   - Percentages for each participant
   - Total votes in last column

5. **Preserve precision**: Keep 2 decimal places

6. **Determine prediction**: Highest % = predicted eliminated
