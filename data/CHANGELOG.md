# BBB26 Data Changelog

This document tracks when the API data actually changed, based on audit of all historical snapshots.

## Audit Summary (2026-01-24)

- **Total files analyzed**: 41
- **Unique data states**: 13 (12 from audit + 1 new intraday capture)
- **Duplicates discarded**: 29
- **Git-recovered files**: 15 (all empty/corrupted, discarded)
- **Missing dates**: Jan 18 (never captured, unrecoverable)

## Key Findings

### 1. Reactions Are NOT Permanent

The API returns a **complete state snapshot**, not a cumulative log. Participants **reassign** their reactions to other people daily. For example, between Jan 22 and Jan 23:

- Solange Couto changed Alberto Cowboy from ❤️ Coração to 💼 Mala
- Jordana changed Babu Santana from ❤️ Coração to 💔 Coração Partido
- Edilson lost 4 ❤️ and gained 🎯 Alvo, 🌱 Planta, 💼 Mala
- Gabriela's ❤️ dropped from 16→11, 🍪 Biscoito rose from 2→6

This means every snapshot captures a genuinely different game state.

### 2. All Fields Are Volatile

| Field | Behavior |
|-------|----------|
| `balance` | Changes daily (decreases over time) |
| `roles` | Rotates (Líder, Paredão, etc.) |
| `group` | Can change (Vip ↔ Xepa) |
| `eliminated` | Permanent once true |
| `receivedReactions.amount` | **Changes daily** (not just accumulates) |
| `receivedReactions.participants` | **Givers reassign daily** |

### 3. Every Snapshot Should Be Kept

Since all data (including reactions) changes between captures, each snapshot is the complete truth at that moment. There are no true "duplicates" unless the hash matches exactly.

## Data Timeline

| First Captured | Participants | Reactions | Event | Hash (first 16) |
|----------------|--------------|-----------|-------|-----------------|
| 2026-01-13 17:18 | 21 | 420 | Initial state | `bf31ebb9b8992f32` |
| 2026-01-14 15:44 | 21 | 420 | Data updated (same counts) | `45479df71b6fa4eb` |
| 2026-01-15 21:12 | 20 | 380 | **Elimination** (-1 participant) | `d9edce86cd21ca46` |
| 2026-01-16 14:42 | 20 | 380 | Data updated | `3c3ac8964764f516` |
| 2026-01-17 17:46 | 20 | 380 | Data updated | `aacff0a82e759f88` |
| 2026-01-19 22:34 | 23 | 506 | **New entrants** (+3 participants) | `d0abb56ecb282c1f` |
| 2026-01-20 18:57 | 23 | 506 | Data updated | `493ff51dfe8344f0` |
| 2026-01-21 14:08 | 22 | 462 | **Elimination** (-1 participant) | `1cd2ab263a24e1ec` |
| 2026-01-22 23:19 | 22 | 462 | Data updated | `c7d03d856d9e1ab5` |
| 2026-01-23 15:48 | 22 | 462 | Data updated | `d9ae8caaef4d119c` |
| 2026-01-23 16:55 | 22 | 462 | **Intraday change** | `a2f6805c0cb857fc` |
| 2026-01-24 15:52 | 22 | 462 | Data updated | `2d574f35967e2367` |
| 2026-01-24 18:46 | 22 | 462 | **Intraday change** | `0341fe147a1b` |

## Major Events

1. **2026-01-15**: First elimination (21 → 20 participants)
2. **2026-01-19**: Three new entrants (20 → 23 participants) - likely Veteranos/Camarotes
3. **2026-01-21**: Second elimination (23 → 22 participants)

## Observations

- Data changes **more frequently** than daily eliminations
- **Intraday changes** occur (see Jan 23 with 2 different states)
- Changes likely include: balance updates, role changes, group reassignments
- Participant counts only change with eliminations/new entrants, but other data evolves daily

## Canonical Snapshots

The `snapshots/` directory contains only the first capture of each unique data state. Files are named with full timestamps (`YYYY-MM-DD_HH-MM-SS.json`) to preserve the exact capture time, especially important when multiple states occur on the same day.
