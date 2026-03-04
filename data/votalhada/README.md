# Votalhada Poll Data

## What is Votalhada?

[Votalhada](https://votalhada.blogspot.com/) is a Brazilian blog that aggregates poll results from multiple platforms (websites, Twitter/X, YouTube, Instagram) during BBB paredões. They collect data from dozens of sources and compute weighted averages to predict elimination results.

## Quick Workflow

**Option A — Automated download (recommended)**

```bash
# Download all poll images for the current paredão (e.g. 6º)
python scripts/fetch_votalhada_images.py --paredao 6
```

Images are saved to `data/votalhada/YYYY_MM_DD/` with a datetime suffix by default (e.g. `consolidados_2026-03-02_21-05.png`), preserving a history of captures. Use `--no-timestamp` to overwrite instead.

Then run OCR on the downloaded folder:

```bash
python scripts/votalhada_ocr_feasibility.py \
  --images-dir data/votalhada/YYYY_MM_DD \
  --paredao N \
  --debug \
  --output tmp/votalhada_ocr/paredao_N_latest.json
```

**Option B — Manual screenshot**

If downloading fails, save a single consolidado screenshot and run the same OCR parser against that directory.

**Important**: extraction is consolidado-card based. The parser selects the best consolidado image by content signature (it does not assume fixed filename index).

## When to Collect

| Timing | Purpose |
|--------|---------|
| **Anytime during voting** | Track poll evolution (preliminary) |
| **Tuesday ~21:00 BRT** | Final snapshot before elimination |
| **After elimination** | Add `resultado_real` with actual percentages |

Votalhada typically updates images at **Monday** 1:00, 8:00, 12:00, 15:00, 18:00, 21:00 and **Tuesday** 8:00, 12:00, 15:00, 18:00, 21:00 BRT (a few minutes after the hour). Run after those times to capture updates. By default the fetch script keeps timestamped history; use `--no-timestamp` to overwrite.

## Collection Steps

### Step 1: Fetch images

```bash
python scripts/fetch_votalhada_images.py --paredao N
```

### Step 2: Run OCR parser

```bash
python scripts/votalhada_ocr_feasibility.py \
  --images-dir data/votalhada/YYYY_MM_DD \
  --paredao N \
  --debug \
  --output tmp/votalhada_ocr/paredao_N_latest.json
```

Parser behavior:
1. Classifies all images as `consolidado_data`, `platform_breakdown`, or `noise`
2. Selects the best consolidado card by content signature
3. Extracts top-table platform aggregates + bottom-table historical series
4. Validates sums/totals/monotonic series before output

### Step 3: Validate OCR output

Require:
- `validation_errors` empty
- `parsed.capture_hora` present
- `parsed.serie_temporal` non-empty

If validation fails, inspect selected image with vision and rerun.

### Step 4: Update `polls.json` and verify

When applying OCR output:
- `consolidado` and `plataformas`: overwrite latest snapshot
- `serie_temporal`: append only unseen `hora` rows (historical series is cumulative)

Then verify render:

```bash
quarto render paredao.qmd
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

**Scheduled runs (optional):** To capture at Votalhada’s usual update times, run the script via cron or Task Scheduler (e.g. Mon/Tue at 1:00, 8:00, 12:00, 15:00, 18:00, 21:00 BRT). Use `--paredao N` and set `N` to the current paredão, or use `--url` with the current post URL. Default behavior keeps timestamped history per run; use `--no-timestamp` only if you intentionally want overwrite mode.

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

When handling Votalhada OCR:

1. Prefer `scripts/votalhada_ocr_feasibility.py` output over manual transcription.
2. Use only the selected consolidado image for extraction (same file for top and bottom crops).
3. Accept dynamic schema variants:
   - 3-platform rows
   - `Outras Redes`
   - `Threads + Instagram` split
4. Keep `serie_temporal` append-only by `hora`.
5. Block updates when `validation_errors` is non-empty.
