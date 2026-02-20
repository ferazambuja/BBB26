# Refactor-Clean: Core QMD Files — Pass 2 Report

**Files processed:** `index.qmd`, `evolucao.qmd`, `relacoes.qmd`, `paredao.qmd`

**Date:** 2026-02-20

---

## index.qmd

### Issues Fixed

**Unused variables removed:**
- `current_week = index_data.get("current_week")` — never referenced after assignment
- `active_names = index_data.get("active_names", [])` — never referenced after assignment

**Remaining dead import removed:**
- `from collections import defaultdict` (was `defaultdict, OrderedDict` in Pass 1, `defaultdict` not used; `OrderedDict` is used)

---

## evolucao.qmd

### Issues Fixed

**Unused variables removed:**
- `n_snapshots = len(snapshots)` — never referenced after assignment
- `latest = snapshots[-1]` — never referenced after assignment (evolucao.qmd uses `daily_snapshots` for charts)

**Remaining dead import removed:**
- `from datetime import datetime` — never used anywhere in the file

---

## relacoes.qmd

### Issues Fixed

All Pass 1 issues were fully addressed. Pass 2 found no additional issues — the file is clean.

---

## paredao.qmd

### Issues Fixed

**Unused import removed:**
- `from collections import defaultdict` — `defaultdict` never instantiated in the file; only `Counter` is used

**Unused data_utils imports removed:**
- `MONTH_MAP_PT` — imported but never referenced in the file body
- `parse_votalhada_hora` — imported but never called in the file body

---

## Summary

| File | Pass 2 Issues | Description |
|------|--------------|-------------|
| `index.qmd` | 3 | 2 unused vars + 1 dead import (`defaultdict`) |
| `evolucao.qmd` | 3 | 2 unused vars + 1 dead import (`datetime`) |
| `relacoes.qmd` | 0 | Clean after Pass 1 |
| `paredao.qmd` | 3 | 1 dead import (`defaultdict`) + 2 dead data_utils imports (`MONTH_MAP_PT`, `parse_votalhada_hora`) |

All files passed AST syntax check after edits. No business logic was changed in either pass.
