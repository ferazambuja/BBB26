# Votalhada Poll Data

## What is Votalhada?

[Votalhada](https://votalhada.blogspot.com/) is a Brazilian blog that aggregates poll results from multiple platforms (websites, Twitter/X, YouTube, Instagram) during BBB paredões. They collect data from dozens of sources and compute weighted averages to predict elimination results.

## Temporary Policy — 2026-03-10

As of **March 10, 2026** (`10/mar 21:00` BRT), Votalhada changed the final poll card:
- removed the historical timed series from the final summary card
- replaced the old vote-weighted consolidado with `MÉDIA FINAL PONDERADA (0,3 x 0,7)`

For this week, OCR feasibility is **paused for operational updates**. Use **vision/manual extraction** from the visible card values and recompute the consolidado with the **previous Votalhada formula**: weighted average by platform vote count. If needed, append a **synthetic series row** for the visible capture time.

## Quick Workflow

**Option A — Manual fetch + latest-capture OCR gate (recommended)**

```bash
# 1. Download all poll images for the current paredão
python scripts/fetch_votalhada_images.py --paredao N

# 2. Validate only the latest timestamped capture set
python scripts/votalhada_auto_update.py \
  --paredao N \
  --images-dir data/votalhada/YYYY_MM_DD \
  --dry-run \
  --output tmp/votalhada_ocr/paredao_N_latest.json

# 3. Apply only after the dry-run gate is clean
python scripts/votalhada_auto_update.py \
  --paredao N \
  --images-dir data/votalhada/YYYY_MM_DD \
  --apply \
  --build \
  --output tmp/votalhada_ocr/paredao_N_apply.json
```

Images are saved to `data/votalhada/YYYY_MM_DD/` with a datetime suffix by default (e.g. `consolidados_2026-03-02_21-05.png`), preserving a history of captures for OCR training. Prefer keeping that history. Use `--no-timestamp` only if you explicitly want overwrite mode.

The dry-run gate is the production path:
- validates the latest timestamped capture set only
- keeps older images available for OCR training/regression work
- blocks apply if validation fails or the parsed capture is not newer than `polls.json`

**Option B — Raw parser / debugging**

If downloading fails or you need OCR debugging detail, run the raw parser directly:

```bash
python scripts/votalhada_ocr_feasibility.py \
  --images-dir data/votalhada/YYYY_MM_DD \
  --paredao N \
  --debug \
  --output tmp/votalhada_ocr/paredao_N_latest.json
```

**Option C — Historical OCR audit (research / training)**

```bash
python scripts/votalhada_ocr_batch_validate.py \
  --images-root data/votalhada \
  --folders YYYY_MM_DD \
  --paredao N \
  --scope full-history \
  --fail-on-errors
```

This mode intentionally audits older noisy/conflicted captures too. Use it to improve OCR quality, not as the release gate.

**Current ops policy**: do manual fetches for now. The default production flow is:

1. `fetch_votalhada_images.py`
2. `votalhada_auto_update.py --dry-run`
3. `votalhada_auto_update.py --apply --build`

The local scheduler is disabled by default. For the current week, prefer **vision/manual extraction** over OCR for the final card.

If a local scheduler is running, stop it:

```bash
pkill -f schedule_votalhada_fetch.py
pkill -f "tail -f logs/votalhada_scheduler.log"
```

**Important**: extraction is consolidado-card based. The parser selects the best consolidado image by content signature (it does not assume fixed filename index).

## When to Collect

| Timing | Purpose |
|--------|---------|
| **Anytime during voting** | Track poll evolution (preliminary) |
| **Tuesday ~21:00 BRT** | Final snapshot before elimination |
| **After elimination** | Add `resultado_real` with actual percentages |

Votalhada typically updates images at **Monday** 1:00, 8:00, 12:00, 15:00, 18:00, 21:00 and **Tuesday** 8:00, 12:00, 15:00, 18:00, 21:00 BRT (a few minutes after the hour). Run after those times to capture updates. By default the fetch script keeps timestamped history; keep that history unless you explicitly need overwrite mode.

## Collection Steps

### Step 1: Fetch images

```bash
python scripts/fetch_votalhada_images.py --paredao N
```

### Step 2: OCR gate or temporary manual fallback

```bash
python scripts/votalhada_auto_update.py \
  --paredao N \
  --images-dir data/votalhada/YYYY_MM_DD \
  --dry-run \
  --output tmp/votalhada_ocr/paredao_N_latest.json
```

Latest-capture gate behavior:
1. Restricts validation to the latest timestamped capture set in the folder
2. Selects the best consolidado card by content signature
3. Extracts top-table platform aggregates + bottom-table historical series
4. Validates sums/totals/monotonic series before output

Fallback parser behavior (`votalhada_ocr_feasibility.py`) remains available for debugging.

Temporary fallback for the current formula/layout change:
- inspect the latest final card visually
- capture the platform rows (`Sites`, `YouTube`, `Twitter`, `Instagram`)
- ignore the displayed `0,3 x 0,7` formula for now
- recompute the consolidado with the previous vote-weighted method
- add a synthetic `serie_temporal` row when the final card no longer includes the timed table

Dry-run acceptance criteria:

Require:
- `validation_errors` empty
- `gate_errors` empty
- `parsed.capture_hora` present
- `parsed.serie_temporal` non-empty

If validation fails, inspect selected image with vision and rerun.

### Step 3: Apply update and rebuild

Preferred apply path:

```bash
python scripts/votalhada_auto_update.py \
  --paredao N \
  --images-dir data/votalhada/YYYY_MM_DD \
  --apply \
  --build \
  --output tmp/votalhada_ocr/paredao_N_apply.json
```

Recommended regression checks:

```bash
pytest -q \
  tests/test_votalhada_ocr_batch_validate.py \
  tests/test_votalhada_ocr_feasibility.py \
  tests/test_votalhada_platform_consistency_audit.py \
  tests/test_fetch_votalhada_images.py
```

When applying OCR output:
- `consolidado` and `plataformas`: overwrite latest snapshot
- `serie_temporal`: append only unseen `hora` rows (historical series is cumulative)
- `imagens`: keep all prior image paths and append only the new capture set

Optional render check:

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

**Historical captures are intentional:** keep older image sets in the folder. They are useful for OCR training, regression tests, and debugging source-side layout drift.

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

1. Temporary override for week 8 final capture: prefer vision/manual extraction over OCR when the final Votalhada card uses `0,3 x 0,7` and omits the timed series.
2. Use only the selected consolidado image for extraction (same file for top and bottom crops).
3. Accept dynamic schema variants:
   - 3-platform rows
   - `Outras Redes`
   - `Threads + Instagram` split
4. Keep `serie_temporal` append-only by `hora`.
5. Block updates when `validation_errors` is non-empty.
6. Use latest-capture validation for operational updates; use `--scope full-history` only for OCR research.
