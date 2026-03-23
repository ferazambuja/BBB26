# Votalhada Poll Data

## What is Votalhada?

[Votalhada](https://votalhada.blogspot.com/) is a Brazilian blog that aggregates poll results from multiple platforms (websites, Twitter/X, YouTube, Instagram) during BBB paredões. They collect data from dozens of sources and compute weighted averages to predict elimination results.

## Card Layout (since March 2026)

Votalhada uses a card layout with three sections:
- **VOTO DA TORCIDA — SITES**: Sites polls (unlimited voting)
- **VOTO ÚNICO (CPF)**: YouTube + Twitter + Instagram (one vote per CPF)
- **ESTIMATIVA VOTALHADA**: Blended prediction (0.3 × Sites + 0.7 × Voto Único)

## Quick Workflow

**Primary path — LXC automated pipeline**

The LXC automatically captures images and updates `polls.json` via Claude Code headless vision. See `docs/OPERATIONS_GUIDE.md` → "Votalhada Collection Checklist" → "Automated Pipeline" for monitoring and troubleshooting.

**Manual fallback — fetch + Claude vision in conversation**

1. `fetch_votalhada_images.py`
2. Read the consolidado card with Claude vision
3. Update `polls.json` with extracted values

Images saved to `data/votalhada/YYYY_MM_DD/` with datetime suffix, preserving capture history.

## When to Collect

| Timing | Purpose |
|--------|---------|
| **Anytime during voting** | Track poll evolution (preliminary) |
| **Tuesday ~21:00 BRT** | Final snapshot before elimination |
| **After elimination** | Add `resultado_real` with actual percentages |

Votalhada typically updates images at **Monday** 1:00, 8:00, 12:00, 15:00, 18:00, 21:00 and **Tuesday** 8:00, 12:00, 15:00, 18:00, 21:00 BRT (a few minutes after the hour). Run after those times to capture updates. By default the fetch script keeps timestamped history; keep that history unless you explicitly need overwrite mode.

## Collection Steps (Manual Fallback)

### Step 1: Fetch images

```bash
python scripts/fetch_votalhada_images.py --paredao N
```

### Step 2: Extract values with Claude vision

Read the consolidado card image in a Claude Code conversation. Extract: date/time, platform Média rows, ESTIMATIVA VOTALHADA, total votes. Update `polls.json`.

### Step 3: Rebuild and deploy

```bash
python scripts/build_derived_data.py
git add data/ && git commit -m "public: votalhada P{N} update"
git push origin main && gh workflow run daily-update.yml
```

Data update rules:
- `consolidado` and `plataformas`: overwrite with latest values
- `serie_temporal`: append only new `hora` rows (cumulative, dedupe by hora)
- `imagens`: append new image paths

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
| `plataformas.instagram` | "Média" row when Instagram is present |
| `plataformas.outras_redes` | "Outras Redes" aggregate (BBB25/BBB26 variants) |
| `plataformas.threads` | "Média Threads" when split rows are present |
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
│   ├── consolidados_2026-02-25_01-35.png
│   ├── consolidados_2_2026-02-25_01-35.png
│   └── ...                 # one capture set per run
└── ...
```

**Naming convention**: The script saves images with a datetime suffix by default (e.g. `consolidados_2026-02-24_21-05.png`, `consolidados_2_2026-02-24_21-05.png`), preserving all captures. Use `--no-timestamp` to overwrite without suffix.

Only the selected consolidado image is needed for extraction. The parser auto-selects by content, since filename index can vary by post/layout.

**Historical captures are intentional:** keep older image sets in the folder for tracking poll evolution and debugging source-side layout changes.

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
| **Instagram / Outras Redes / Threads** | Extra social signal; row labels vary by season/layout |
| **Consolidado** | Weighted average — best overall predictor |

## AI Agent Instructions

When handling Votalhada data:

1. Use **vision** (Read tool on PNG) to extract values from consolidado cards. Do NOT use OCR tools (archived).
2. Read participants from `polls.json` entry (pre-populated by `get_final_nominees()` from `data_utils.py`).
3. Accept dynamic platform schemas: 3-platform, 4-platform, `Outras Redes`, `Threads + Instagram` split.
4. Keep `serie_temporal` **append-only by `hora`** — never delete existing rows.
5. Overwrite `consolidado` and `plataformas` with latest values.
6. Always verify extracted values: platform row sums should be ~100% (±0.5% rounding drift is normal).
