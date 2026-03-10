# Index / Paredão Ativo Merge Notes

## Scope

This branch prepares the homepage and live `Paredão Ativo` surfaces for merge while preserving the site's existing visual language.

The final direction is:

- keep the new `Paredão Ativo` functionality and shared payload
- keep the restored homepage visual grammar from `main`
- avoid bespoke card systems on `index`
- keep the newer split metadata where it adds value

## What Changed

### 1. `Paredão Ativo` on `index`

- `Paredão Ativo` now appears first in the homepage highlight order.
- The homepage card is driven by the shared `Nosso Modelo` payload used by the live page.
- The homepage version keeps the site's existing `info-panel` / header language instead of introducing a separate dashboard shell.
- The trust line links to the retrospective model explanation section on `paredoes.html`.

### 2. `Ranking` visual restore

- `Ranking` uses the simpler 3-column `main` structure again.
- The layout is explicit:
  - desktop: 3 columns
  - medium width: 2 columns
  - mobile: 1 column
- `Mais queridos` now shows only participants with positive score.
- `Menos queridos` still shows only negative scores.
- The third column keeps the newer behavior:
  - `📅 Variação vs ontem` by default
  - fallback to `📅 Variação na semana` when daily deltas are flat

### 3. `Mais Blindados` visual restore

- The old inline badge style from `main` is back.
- The newer split functionality stays:
  - `Escapou Bate-Volta`
  - `Autoimune`
  - `Líder`
  - `Imune`
- Split badges still preserve counts and `paredão` numbers.

### 4. Pair highlight cards

- `Mudanças Dramáticas`, `Hostilidades Recentes`, and related pair cards keep the restored centered layout rather than the temporary cramped/chip treatment.

## Main Files

- `index.qmd`
- `assets/cards.css`
- `scripts/paredao_viz.py`
- `tests/test_paredao_active_card.py`
- `tests/test_paredoes_ui_contract.py`

Derived data was also rebuilt, including `data/derived/index_data.json`.

## Verification

Latest verification run on this branch:

```bash
pytest tests/test_paredoes_ui_contract.py::test_index_keeps_restored_highlight_layout_hooks \
       tests/test_index_highlights.py \
       tests/test_blindados.py \
       tests/test_paredao_active_card.py -q

quarto render index.qmd
```

Observed result:

- targeted tests passed
- `index.qmd` rendered successfully
- browser review on `http://localhost:8123/index.html` confirmed:
  - `Paredão Ativo` first
  - `Ranking` back to the intended 3-column structure
  - `Mais queridos` limited to positive scores
  - `Mais Blindados` using inline badges instead of chips

## Merge Readiness Notes

- This branch is intended to merge back into `main`.
- The important part to preserve during merge is the combination of:
  - shared `Paredão Ativo` functionality
  - restored homepage visual language
  - split blindados metadata
- Avoid broad file restores when resolving conflicts, especially in:
  - `index.qmd`
  - `assets/cards.css`

