# Design: Split build_derived_data.py into Domain Modules

> Date: 2026-03-01
> Status: Approved
> Addresses: Tech Debt H-4 (5,362-line God file)

## Problem

`scripts/build_derived_data.py` has grown to 5,362 lines with 80+ functions spanning 13 unrelated domains. This makes it hard to navigate, test, and maintain.

## Solution

Create a `scripts/builders/` package with 11 domain-focused modules. The orchestrator (`build_derived_data.py`) becomes a ~250-line pipeline that imports from `builders.*`.

## Package Structure

```
scripts/
  builders/                    # NEW package
    __init__.py                # re-exports all public build_* functions
    relations.py               # ~2,300 lines — pairwise scoring engine
    daily_analysis.py          # ~700 lines — metrics, hostility, vulnerability, impact
    participants.py            # ~250 lines — index, daily roles, auto events
    plant_index.py             # ~400 lines — weekly visibility index
    sincerao.py                # ~150 lines — edge aggregation + validation
    cartola.py                 # ~420 lines — point system
    provas.py                  # ~250 lines — competition rankings
    clusters.py                # ~800 lines — detection + evolution
    timeline.py                # ~300 lines — game timeline + power summary
    paredao_analysis.py        # ~600 lines — analysis + badges
    vote_prediction.py         # ~500 lines — cluster-boosted prediction model
  build_derived_data.py        # ~250 lines — orchestrator only
```

## Module Boundaries

Each module owns its domain-specific constants and functions. No cross-dependencies between builder modules — each imports only from `data_utils.py`.

### What stays in build_derived_data.py (orchestrator)
- Path constants: DATA_DIR, DERIVED_DIR, MANUAL_EVENTS_FILE, PAREDOES_FILE, PROVAS_FILE
- UTC/BRT timezone constants
- `write_json()` utility
- `build_snapshots_manifest()`, `detect_eliminations()`, `build_reaction_matrices()` (small utilities)
- `build_derived_data()` main pipeline function

### Module contents

| Module | Lines | Constants | Public API |
|--------|-------|-----------|------------|
| relations.py | ~2,300 | RELATION_*, STREAK_*, REACTIVE_WINDOW_WEIGHTS | build_relations_scores, compute_streak_data |
| daily_analysis.py | ~700 | — | build_daily_metrics, build_daily_changes_summary, build_hostility_daily_counts, build_vulnerability_history, build_impact_history |
| participants.py | ~250 | ROLES | build_participants_index, build_daily_roles, build_auto_events, apply_big_fone_context |
| plant_index.py | ~400 | PLANT_INDEX_*, PLANT_GANHA_GANHA_WEIGHT | build_plant_index |
| sincerao.py | ~150 | — | build_sincerao_edges, validate_manual_events, split_names |
| cartola.py | ~420 | — | build_cartola_data |
| provas.py | ~250 | PROVA_*, PROVA_DQ_POINTS | build_prova_rankings |
| clusters.py | ~800 | CLUSTER_COLORS | build_clusters_data, build_cluster_evolution |
| timeline.py | ~300 | — | build_game_timeline, build_power_summary |
| paredao_analysis.py | ~600 | — | build_paredao_analysis, build_paredao_badges |
| vote_prediction.py | ~500 | VOTE_PREDICTION_CONFIG | build_vote_prediction, extract_paredao_eligibility |

## Backwards Compatibility

`builders/__init__.py` re-exports all public functions. The orchestrator also imports and exposes them, so `from build_derived_data import build_relations_scores` continues to work.

Test files will be updated to import directly from `builders.*` modules for clarity.

## Implementation Plan

1. Create `scripts/builders/` package with `__init__.py`
2. Extract each module (can be parallelized — modules are independent)
3. Update `build_derived_data.py` to import from `builders.*`
4. Update test imports
5. Run full test suite + build pipeline
6. Update CLAUDE.md and docs references
