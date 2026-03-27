# Phase 3 Cycle Migration — Classification & Rename Map

## Classification

### Gameplay-cycle contract (MUST migrate to `cycle`)

**Constants:**
- `WEEK_END_DATES` → `CYCLE_END_DATES`

**Functions (bridge inversion — move impl to cycle name, delete week name):**
- `get_week_number()` → `get_cycle_number()`
- `get_week_start_date()` → `get_cycle_start_date()`
- `get_effective_week_end_dates()` → `get_effective_cycle_end_dates()`
- `_compute_effective_week_end_dates()` → `_compute_effective_cycle_end_dates()`
- `_effective_week_end_dates_cached()` → `_effective_cycle_end_dates_cached()`

**Raw data keys:**
- `manual_events["weekly_events"]` → `["cycles"]`
- `power_events[*].week` → `.cycle`
- `scheduled_events[*].week` → `.cycle`
- `special_events[*].week` → `.cycle`
- `cartola_points_log[*].week` → `.cycle`
- `paredoes[*].semana` → `.cycle`
- `provas[*].week` → `.cycle`

**Derived JSON output keys:**
- `weekly_points` → `cycle_points` (cartola_data.json)
- `_metadata.n_weeks` → `_metadata.n_cycles` (cartola_data.json)
- `"week": N` in events → `"cycle": N` (balance_events, prova_rankings, game_timeline, cartola_data)
- `current_cycle_week` → delete (index_data.json)
- gameplay-facing `current_week` → `current_cycle` (index_data.json)

**Builder locals/parameters (gameplay identity):**
- `current_week` → `current_cycle` (relations.py, index_data_builder.py)
- `weekly_points` → `cycle_points` (cartola.py)
- `n_weeks` → `n_cycles` (cartola.py)
- `week_end_dates` (parameter) → `cycle_end_dates`
- Various `week` locals meaning cycle identity

### Genuine weekly analytics (KEEP as `week`)
- `weekly_summary` key name in balance.py:899-909 (rolling weekly aggregation)
- `weekday` in timeline.py (Python date.weekday(), 27 occurrences)
- `weekly_summary[*].week` field INSIDE the analytics — this IS gameplay-cycle, rename to `cycle`

### Quoted/source/archive prose (IGNORE)
- Prose in paredoes.json `titulo` and `fontes` string values
- Quoted text in MANUAL_EVENTS_GUIDE.md examples (e.g., "semana 1")
- Search terms in docs (e.g., "BBB 26 líder semana [N]")
- `docs/PROGRAMA_BBB26.md` prose
- `_legacy/` files
