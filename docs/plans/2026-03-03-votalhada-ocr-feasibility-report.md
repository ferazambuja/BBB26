# Votalhada OCR Feasibility Report (Pass 3)

> Date: 2026-03-03  
> Scope: Consolidado OCR feasibility only (no GitHub automation rollout)

## What changed in Pass 3

After Pass 2 and the 5 historical failures found in the full sweep, Pass 3 added targeted hardening:

- Added top-table OCR crop (psm6 + psm4) to recover cleaner platform rows.
- Improved percentage token normalization (handles trailing separators like `6,75,`).
- Added fuzzy `VARIAÇÃO DAS MÉDIAS` header detection (`VARIACGAO` OCR drift).
- Added time-progression coercion to TSV row parser (fixes `03:00`/`13:00` OCR slips).
- Added regression tests for the exact 5 failing samples.

## Files added/updated

- `scripts/votalhada_ocr_feasibility.py`
- `tests/test_votalhada_ocr_feasibility.py`
- `docs/plans/2026-03-03-votalhada-ocr-feasibility.md`
- `docs/plans/2026-03-03-votalhada-ocr-feasibility-report.md`

## Verification commands

```bash
pytest tests/test_votalhada_ocr_feasibility.py -q
python scripts/votalhada_ocr_feasibility.py --images-dir data/votalhada/2026_03_01 --paredao 7 --debug
python scripts/votalhada_ocr_feasibility.py --images-dir data/votalhada/2026_02_22 --paredao 6 --debug
```

## Benchmark setup (Pass 2)

- Classification benchmark dataset:
  - all `.png` files in `data/votalhada/2026_03_01/` and `data/votalhada/2026_02_22/`
  - expected labels by known pattern in these batches:
    - `consolidados_5*` -> `consolidado_data`
    - `consolidados_6*` -> `noise`
    - others -> `platform_breakdown`
- Extraction benchmark reference images:
  - P6: `data/votalhada/2026_02_22/consolidados_5_2026-02-25_01-35.png`
  - P7: `data/votalhada/2026_03_01/consolidados_5_2026-03-04_00-32.png`
- Ground truth:
  - `data/votalhada/polls.json`
- Vision verification:
  - manual visual checks on representative consolidated batches
  - confirmed content drift (e.g., `consolidados_6*` banner/noise, consolidated card often in `consolidados_5*`)
  - confirmed key values/time rows on selected images match expected reading

## Metrics (Pass 2)

| Metric | Result | Target | Status |
|---|---:|---:|---|
| Classification accuracy | 100.0% (66/66) | >= 95% | ✅ |
| Consolidado MAE (p.p.) | 0.0033 | <= 0.15 | ✅ |
| Platform vote exact-match rate | 100.0% (8/8) | >= 98% | ✅ |
| Series row recall | 100.0% (22/22) | >= 95% | ✅ |
| Validation failures on benchmark cases | 0/2 | 0 critical escapes | ✅ |

## Full sample sweep (all stored samples, after Pass 3)

Additional sweep over all local samples in `data/votalhada/*/*.png`:

- Total PNG samples scanned: `93`
- Classification distribution:
  - `consolidado_data`: `18`
  - `platform_breakdown`: `64`
  - `noise`: `11`
- Consolidado-like images parsed+validated: `18/18` pass
- Consolidado-like failures: `0/18`

Interpretation:

- OCR is strongly feasible on recent/current formatted samples (P6/P7 benchmark).
- Historical edge cases from the first sweep are now covered by parser hardening.

## Real-batch parsing status

| Batch | Selected image | Capture hora | Series rows | Validation |
|---|---|---|---:|---|
| `2026_03_01` (P7) | `consolidados_5_2026-03-04_00-32.png` | `03/mar 21:00` | 11 | ✅ |
| `2026_02_22` (P6) | `consolidados_5_2026-02-25_01-35.png` | `24/fev 21:00` | 11 | ✅ |

## Decision (Pass 3)

- **Go (feasibility proven on sampled P6/P7 data).**

This means OCR extraction quality is now good enough to proceed to the next phase (automation design/implementation), while keeping guardrails and debug artifacts.

## Remaining caveats

- Benchmark is currently based on P6/P7 plus available historical samples; new layout changes still require ongoing monitoring.
- The 1% vote-total tolerance is deliberate to absorb source-side inconsistencies; this threshold should remain configurable.
