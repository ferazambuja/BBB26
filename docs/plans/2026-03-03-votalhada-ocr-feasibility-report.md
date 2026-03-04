# Votalhada OCR Feasibility Report (Pass 4)

> Date: 2026-03-04  
> Scope: Consolidado OCR feasibility only (no GitHub automation rollout)

## What changed in Pass 4

After Pass 3, an additional hardening pass targeted BBB25 layout drift:

- Added dynamic platform-schema parsing:
  - 3-platform (`Sites`, `YouTube`, `Twitter`)
  - `Outras Redes`
  - split `Média Threads` + `Média Instagram`
- Switched totals/weighting to dynamic platform keys (no fixed 4-platform assumption).
- Tightened OCR-noise handling:
  - recompute consolidado from weighted rows when sum drift exceeds `0.25`
  - stricter series-row sanity filtering (`0.75` sum tolerance)
- Added dedicated regression tests for sum-drift and noisy series outliers.

## Files added/updated

- `scripts/votalhada_ocr_feasibility.py`
- `tests/test_votalhada_ocr_feasibility.py`
- `docs/plans/2026-03-03-votalhada-ocr-feasibility.md`
- `docs/plans/2026-03-03-votalhada-ocr-feasibility-report.md`

## Verification commands (Pass 4)

```bash
pytest tests/test_votalhada_ocr_feasibility.py -q
python scripts/votalhada_ocr_feasibility.py --images-dir data/votalhada/2026_03_01 --paredao 7 --debug
python scripts/votalhada_ocr_feasibility.py --images-dir data/votalhada/2026_02_22 --paredao 6 --debug
```

Pass 4 verification results:
- Test suite: `26 passed`
- P6 parser run: no validation errors
- P7 parser run: no validation errors

## Benchmark setup (core)

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

## Full sample sweep (all stored samples)

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
- Historical edge cases from the first sweep are covered by parser hardening.

## BBB25 batch rerun (same 18 URLs)

Using the same discovered BBB25 URL batch:

- Previous baseline (before dynamic schemas): `3/18` ok, `15/18` error
- After dynamic-schema + tolerance patch: `18/18` ok, `0/18` error
- Report artifact: `tmp/bbb25_batch/report.json`

Residual-failure root causes were vision-checked before final patch:
- one consolidado row sum drift (`99.51`) despite readable image values
- two noisy mid-series OCR rows (`101.24` and `98.79` sums)

These are now handled by weighted fallback + stricter series filtering.

## Real-batch parsing status (latest run)

| Batch | Selected image | Capture hora | Series rows | Validation |
|---|---|---|---:|---|
| `2026_03_01` (P7) | `consolidados_5_2026-03-04_00-32.png` | `03/mar 21:00` | 9 | ✅ |
| `2026_02_22` (P6) | `consolidados_5_2026-02-25_01-35.png` | `24/fev 21:00` | 11 | ✅ |

## Decision (Pass 4)

- **Go (feasibility confirmed and hardened for BBB25/BBB26 drift).**

This means OCR extraction quality is suitable to proceed to automation with guardrails.

## Next-week readiness checklist

- Run OCR at expected update windows (Mon/Tue schedule) and keep timestamped captures.
- For each run, require empty `validation_errors` before updating `polls.json`.
- Treat `serie_temporal` as append-only historical data:
  - add only unseen `hora` rows
  - never remove prior rows
- Keep `consolidado` and `plataformas` as latest snapshot overwrite.
- If validation fails, inspect selected consolidado image via vision and re-run parser.

## Remaining caveats

- New visual layouts can still appear mid-season; keep monitoring and add regression fixtures when detected.
- Vote-total tolerance (`1%`) remains intentional to absorb source-side inconsistencies.
