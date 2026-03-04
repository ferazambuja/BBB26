# BBB26 Architecture (Public)

Public technical reference for repository architecture, data flow, and file responsibilities.

## System Overview

```text
GloboPlay API + Manual JSON
        ↓
scripts/fetch_data.py
        ↓
data/snapshots/*.json + data/latest.json
        ↓
scripts/build_derived_data.py
        ↓
data/derived/*.json
        ↓
Quarto render (*.qmd)
        ↓
_site/ (GitHub Pages)
```

## Main Layers

- `scripts/`:
  - data ingestion, transformations, validations, and derived builders
- `data/`:
  - `snapshots/` raw captures
  - manual sources (`manual_events.json`, `paredoes.json`, `provas.json`, `votalhada/polls.json`)
  - `derived/` precomputed artifacts consumed by pages
- `*.qmd`:
  - page rendering and visualization composition
- `_quarto.yml`:
  - site navigation, page render list, theme and global includes

## Single Source Principles

- Shared logic/constants should live in Python modules (not duplicated in QMD pages).
- Heavy computation should be precomputed into `data/derived/`.
- QMD pages should load data and render, not own business logic.

## Critical Data Contracts

- Snapshot timestamps are UTC in filenames and metadata.
- Game-date conversion applies BRT logic with morning cutoff.
- Manual-event schema conventions are documented in `docs/MANUAL_EVENTS_GUIDE.md`.
- Scoring and weighting models are documented in `docs/SCORING_AND_INDEXES.md`.

## Build / Render Contracts

- After editing manual data, run:
  - `python scripts/build_derived_data.py`
- Site render:
  - `quarto render`
- CI pipeline validates and rebuilds derived data before deploy.

## Related Public Docs

- `docs/OPERATIONS_GUIDE.md` — operational runbooks
- `docs/MANUAL_EVENTS_GUIDE.md` — manual schema and fill rules
- `docs/SCORING_AND_INDEXES.md` — scoring definitions
- `docs/PROGRAMA_BBB26.md` — non-analytical program context
