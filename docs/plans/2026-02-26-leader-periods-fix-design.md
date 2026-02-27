# Design: Leader Periods Fix + Source Citations

**Date:** 2026-02-26
**Status:** Approved

## Problem

### 1. leader_periods detection fails for consecutive same-person Líder

`build_index_data.py` detects Líder transitions by comparing `leader != prev_leader` in roles_daily. When Jonas won 3 consecutive Prova do Líder (weeks 4, 5, 6), the API never cleared his Líder role between weeks 5→6, so the code only detected 2 of his 3 terms. Week 5's detection was accidental (API had empty Líder on Feb 12).

Result: `leader_periods` has 5 entries instead of 6. Jonas's 2nd period spans Feb 13→Feb 26, merging weeks 5 and 6 with wrong VIP composition.

### 2. Source citations lack local file references

`paredoes.json` `fontes` is a string array of URLs. We scrape articles to `docs/scraped/*.md` but don't link them. No way to trace which local file corresponds to which source.

### 3. End-of-season weeks may lack a Líder

Final weeks (final 3/2) won't have a Prova do Líder. The week system must handle `lider=null`.

## Solution

### A. leader_periods: Derive from WEEK_END_DATES + paredoes.json

Replace the fragile API-based detection with a deterministic derivation:

- Week N start = `WEEK_END_DATES[N-2] + 1 day` (week 1 starts at premiere 2026-01-13)
- Week N Líder = `paredoes[N-1].formacao.lider` (or None for late-season)
- Week N VIP = `roles_daily` snapshot on start date (or nearest available)
- Current open week (after last WEEK_END_DATES entry) uses latest roles_daily

This eliminates the `leader != prev_leader` comparison entirely.

### B. Source citations: Migrate fontes to objects

Change `fontes` from `string[]` to `object[]`:

```json
"fontes": [
  {"url": "https://...", "arquivo": "docs/scraped/slug.md", "titulo": "Article Title"},
  {"url": "https://...", "arquivo": null, "titulo": null}
]
```

- `url` — required (same as today)
- `arquivo` — relative path to local .md copy, or null
- `titulo` — optional article title, or null
- Auto-migrate existing string entries to `{"url": "...", "arquivo": null, "titulo": null}`

### C. End-of-season: Continue WEEK_END_DATES with lider=null

Add end dates for every week, even without a Líder. leader_periods will have `leader: null` for those weeks. All downstream code must handle null leader gracefully.

## Files Changed

| File | Change |
|------|--------|
| `scripts/build_index_data.py` | Replace leader detection loop with WEEK_END_DATES-based derivation |
| `scripts/data_utils.py` | Add `get_leader_for_week()` helper |
| `scripts/schemas.py` | Update fontes schema validation |
| `data/paredoes.json` | Migrate fontes strings to objects |
| `data/derived/index_data.json` | Rebuilt with correct leader_periods |
| `tests/test_data_utils.py` | Tests for new helper |
| `CLAUDE.md` | Document source citation schema + week model notes |

## Not in Scope

- Scraping backlog of existing fontes URLs (arquivo=null is fine for now)
- Changes to manual_events.json or provas.json fontes (only paredoes.json for now)
- Tonight's new Líder data (will be added after results are known)
