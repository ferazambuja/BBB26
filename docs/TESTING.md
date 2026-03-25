# BBB26 Testing Guide

Verification map for local changes in BBB26.

Use this document to answer two questions quickly:

1. What is the **minimum safe verification** for the change I just made?
2. Which test files own the subsystem I touched?

## CI Reference

The main GitHub Actions pipeline (`.github/workflows/daily-update.yml`) runs the full public gate:

1. `python -m pytest tests/ -v --tb=short --cov=scripts --cov-report=term-missing`
2. `python scripts/build_derived_data.py`
3. `python scripts/quarto_render_safe.py`

When your change is broad, shared, or hard to reason about locally, use that same order.

## Minimum Verification by Change Type

| Change type | Minimum local verification |
|-------------|----------------------------|
| Docs only (`README.md`, `docs/*.md`) | Proofread links, section references, and command examples. No rebuild required unless the docs describe changed behavior. |
| Manual data (`data/manual_events.json`, `data/paredoes.json`, `data/provas.json`, `data/votalhada/polls.json`) | `python scripts/build_derived_data.py` and inspect `docs/MANUAL_EVENTS_AUDIT.md`; render the affected page if the data is user-facing. |
| Shared loaders, constants, weights, date/week logic (`scripts/data_utils.py`) | `pytest -q tests/test_data_utils.py tests/test_data_utils_extended.py tests/test_loaders.py tests/test_build_pipeline.py` |
| Derived builders / pipeline (`scripts/builders/*`, `scripts/derived_pipeline.py`, `scripts/build_derived_data.py`) | `pytest -q tests/test_build_pipeline.py tests/test_integration_analysis.py tests/test_integration_scoring.py` plus any subsystem-specific tests below; then `python scripts/build_derived_data.py` |
| Main dashboard (`index.qmd`, `scripts/index_viz.py`) | `pytest -q tests/test_index_qmd_contract.py tests/test_index_viz.py tests/test_index_render_contract.py tests/test_index_highlights.py` and `python scripts/quarto_render_safe.py index.qmd` |
| Relations / social graph (`relacoes.qmd`) | `pytest -q tests/test_integration_analysis.py tests/test_integration_scoring.py` and `python scripts/quarto_render_safe.py relacoes.qmd` |
| Current paredão / archive / voting (`paredao.qmd`, `paredoes.qmd`, `votacao.qmd`, `scripts/paredao_viz.py`, `scripts/votacao_viz.py`) | `pytest -q tests/test_paredao_active_card.py tests/test_paredao_viz_contract.py tests/test_paredoes_ui_contract.py tests/test_votacao_ui_contract.py` and render the affected page(s) |
| Cartola (`cartola.qmd`, Cartola scoring code/data) | `pytest -q tests/test_cartola_official_safeguards.py tests/test_cartola_lider_fallback.py tests/test_cartola_points_language.py tests/test_cartola_ui_contract.py` and `python scripts/quarto_render_safe.py cartola.qmd` |
| Provas (`provas.qmd`, prova rankings) | `pytest -q tests/test_provas_ui_contract.py tests/test_prova_rankings_warnings.py` and `python scripts/quarto_render_safe.py provas.qmd` |
| Economia / balance (`economia.qmd`, `_dev/drafts/economia_v2.qmd`, `scripts/builders/balance.py`) | `pytest -q tests/test_balance_events.py` and render the affected economy page(s) |
| Votalhada fetch / poll model | `pytest -q tests/test_fetch_votalhada_images.py tests/test_votalhada_manual_formula_policy.py tests/test_get_final_nominees.py` |
| Git/public safety tooling (`.githooks/pre-push`, `.github/workflows/public-policy-report.yml`, workflow docs) | Proofread docs and command examples; run `bash -n .githooks/pre-push` if the hook changed. |
| Legacy sync / publish helper (`scripts/sync_public.sh`) | `pytest -q tests/test_sync_public_script.py` and run `scripts/sync_public.sh` in report mode if behavior changed |
| Layout, shell, typography, mobile review | `pytest -q tests/test_quarto_ui_config.py tests/test_ui_shell_cleanup.py tests/test_typography_contract.py tests/test_ranking_mobile_layout.py` and, when needed, `./scripts/capture_layout_screenshots.sh --output-dir tmp/page_screenshots/<label>` |

## Test Ownership by Subsystem

| Subsystem | Core tests |
|-----------|------------|
| Snapshot loaders, names, week/date handling | `tests/test_data_utils.py`, `tests/test_data_utils_extended.py`, `tests/test_loaders.py` |
| Derived pipeline orchestration and scoring edges | `tests/test_build_pipeline.py`, `tests/test_integration_analysis.py`, `tests/test_integration_scoring.py` |
| Index / Painel surface | `tests/test_index_qmd_contract.py`, `tests/test_index_viz.py`, `tests/test_index_render_contract.py`, `tests/test_index_highlights.py`, `tests/test_blindados.py`, `tests/test_sincerao_migration.py` |
| Paredão / Paredões | `tests/test_paredao_active_card.py`, `tests/test_paredao_viz_contract.py`, `tests/test_paredoes_ui_contract.py` |
| Votação page | `tests/test_votacao_ui_contract.py` |
| Cartola | `tests/test_cartola_official_safeguards.py`, `tests/test_cartola_lider_fallback.py`, `tests/test_cartola_points_language.py`, `tests/test_cartola_ui_contract.py` |
| Provas | `tests/test_provas_ui_contract.py`, `tests/test_prova_rankings_warnings.py` |
| Balance / economia | `tests/test_balance_events.py` |
| Votalhada fetch/poll model | `tests/test_fetch_votalhada_images.py`, `tests/test_votalhada_manual_formula_policy.py`, `tests/test_get_final_nominees.py` |
| Capture scripts / mobile review | `tests/test_capture_quarto_screenshots.py`, `tests/test_capture_mobile_slices.py`, `tests/test_cronologia_mobile_review_contract.py` |
| Site shell / config / typography | `tests/test_quarto_ui_config.py`, `tests/test_ui_shell_cleanup.py`, `tests/test_typography_contract.py`, `tests/test_ranking_mobile_layout.py` |
| Legacy sync/public helper | `tests/test_sync_public_script.py` |

## Common Commands

### Full suite

```bash
python -m pytest tests/ -v --tb=short --cov=scripts --cov-report=term-missing
python scripts/build_derived_data.py
python scripts/quarto_render_safe.py
```

### Fast dashboard loop

```bash
pytest -q tests/test_index_qmd_contract.py tests/test_index_viz.py tests/test_index_render_contract.py
python scripts/quarto_render_safe.py index.qmd
```

### Fast manual-data loop

```bash
python scripts/build_derived_data.py
python scripts/quarto_render_safe.py paredao.qmd
```

### Layout / screenshot review

```bash
./scripts/capture_layout_screenshots.sh --output-dir tmp/page_screenshots/<label>
```

## Notes

- Some tests intentionally `skip` when specific derived files or regression images are unavailable. A skip is not automatically a failure, but you should understand why it skipped.
- `python scripts/build_derived_data.py` is the fastest sanity gate for any manual-data or scoring change because it rebuilds all derived artifacts and fails on manual-event audit issues.
- For doc-only changes like this one, consistency review is usually enough; no site rebuild is required unless you changed instructions, commands, or architecture claims tied to code behavior.
