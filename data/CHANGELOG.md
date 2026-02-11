# BBB26 Data Changelog

This document tracks the initial data audit and key findings about the API data model.

## Current Status (2026-02-10)

- **Total snapshots**: 55 (Jan 13 – Feb 10, 2026)
- **Active participants**: 19
- **Exited participants**: 6 (Henri, Pedro, Aline Campos, Matheus, Brigido, Paulo Augusto)
- **Paredões completed**: 3

## Initial Audit Summary (2026-01-24)

- **Total files analyzed**: 41
- **Unique data states**: 14 (12 from audit + 1 intraday capture + 1 synthetic)
- **Duplicates discarded**: 29
- **Git-recovered files**: 15 (all empty/corrupted, discarded)
- **Recovered dates**: Jan 18 (synthetic — built from GShow queridômetro article)

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
| 2026-01-15 21:12 | 20 | 380 | **Henri Castelli desistiu** (-1 participant) | `d9edce86cd21ca46` |
| 2026-01-16 14:42 | 20 | 380 | Data updated | `3c3ac8964764f516` |
| 2026-01-17 17:46 | 20 | 380 | Data updated | `aacff0a82e759f88` |
| 2026-01-18 12:00 ⚠️ | 24 | 552 | **SYNTHETIC** — hearts inferred, negatives from GShow (see below) | `320eb69ba9fc94ff` |
| 2026-01-19 22:34 | 23 | 506 | Pedro desistiu; Chaiany already counted in Jan 18 | `d0abb56ecb282c1f` |
| 2026-01-20 18:57 | 23 | 506 | Data updated | `493ff51dfe8344f0` |
| 2026-01-21 14:08 | 22 | 462 | **Aline Campos eliminada** (-1 participant) | `1cd2ab263a24e1ec` |
| 2026-01-22 23:19 | 22 | 462 | Data updated | `c7d03d856d9e1ab5` |
| 2026-01-23 15:48 | 22 | 462 | Data updated | `d9ae8caaef4d119c` |
| 2026-01-23 16:55 | 22 | 462 | **Intraday change** | `a2f6805c0cb857fc` |
| 2026-01-24 15:52 | 22 | 462 | Data updated | `2d574f35967e2367` |
| 2026-01-24 18:46 | 22 | 462 | **Intraday change** | `0341fe147a1b` |

## Major Events

1. **2026-01-15**: Henri Castelli **desistiu** (21 → 20 participants)
2. **2026-01-18**: 4 new entrants — Chaiany, Gabriela, Leandro, Matheus (20 → 24 participants)
3. **2026-01-18**: Milena punished (500 estalecas) for late Raio-X, but reactions were recorded
4. **2026-01-19**: Pedro **desistiu** (24 → 23 participants)
5. **2026-01-21**: Aline Campos **eliminada** (1º Paredão) (23 → 22 participants)

## Observations

- Data changes **more frequently** than daily eliminations
- **Intraday changes** occur (see Jan 23 with 2 different states)
- Changes likely include: balance updates, role changes, group reassignments
- Participant counts only change with eliminations/new entrants, but other data evolves daily

## Synthetic Snapshots

### 2026-01-18_12-00-00.json (SYNTHETIC)

**Source**: [GShow queridômetro article](https://gshow.globo.com/realities/bbb/bbb-26/dentro-da-casa/noticia/queridometro-do-bbb-26-tem-pedro-tachado-de-mentiroso-e-novo-brother-disparando-biscoitos.ghtml)

**Why**: No API snapshot was captured on Jan 18. The GShow article published the complete queridômetro for that day, listing all negative/mild reactions (who gave what to whom).

**Methodology**:
- Structural fields (id, name, avatar, job, group, memberOf) cloned from Jan 17 snapshot for the original 20 participants, and from Jan 19 snapshot for 4 new entrants (Chaiany, Gabriela, Leandro, Matheus)
- `receivedReactions` negative/mild: exact data from GShow article
- `receivedReactions` hearts: **inferred** — each participant rates all 23 others; anyone not given a negative/mild reaction received a heart. This is logically certain because the queridômetro is a complete graph.
- Milena: participated late in Raio-X (punished with -500 estalecas, not reaction voiding). Her 7 negative/mild reactions are from the article; remaining 16 targets received hearts.
- Chaiany: entered the house the same day as the other 3 new entrants. Not mentioned in article → gave only hearts (100% positive).
- `balance` and `roles`: Carried from Jan 17 (exact values for Jan 18 are unknowable); 0/empty for new entrants
- `eliminated`: All false (Pedro still active on Jan 18)

**Limitations**:
- Heart reactions are **inferred**, not directly from article (but logically certain given complete graph)
- `balance` and `roles` are approximations from the previous day
- Timestamp `12:00:00` is a placeholder (actual article publication time unknown)

**Participants**: 24 (20 from Jan 17 + Chaiany, Gabriela, Leandro, Matheus)
**Total reactions**: 552 (453 hearts + 99 negative/mild) — matches 24 × 23 = 552

**How to identify**: `_metadata.synthetic == true` in the JSON file

### How to Build Future Synthetic Snapshots

If a date is missed, look for the GShow queridômetro article for that day. Search: `"queridômetro BBB 26" site:gshow.globo.com YYYY-MM-DD`. The article lists all negative/mild reactions. Use `scripts/build_jan18_snapshot.py` as a template.

## Canonical Snapshots

The `snapshots/` directory contains only the first capture of each unique data state. Files are named with full timestamps (`YYYY-MM-DD_HH-MM-SS.json`) to preserve the exact capture time, especially important when multiple states occur on the same day.
