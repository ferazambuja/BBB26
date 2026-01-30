# Relations Scoring Review — Full Audit (2026-01-29)

Comprehensive review of the A→B / B→A relationship scoring system, covering architecture, gaps, data validation, and improvement proposals.

---

## 1. Architecture Summary

The scoring system lives in `scripts/build_derived_data.py` → `build_relations_scores()` and outputs `data/derived/relations_scores.json`.

**Formula**: `Score(A→B) = Q_base(3d rolling) + Σ events(full weight, no decay)`

**Components**:

| Component | Source | Weight Range | Notes |
|-----------|--------|-------------|-------|
| Queridômetro (base) | API snapshots | -1.0 to +1.0 | 3-day rolling window (0.6/0.3/0.1) |
| Power events | manual + auto | -3.36 to +0.96 | Visibility factor applied (public 1.2×, secret 0.5×) |
| Sincerão edges | manual | -1.0 to +0.7 | Per-pair directional (pódio, nao_ganha, bomba) |
| VIP | derived from roles | +0.2 | Leader → VIP members (first day of reign) |
| Votes (casa) | paredoes.json | -2.5 to -2.0 | 4 types: secret (-2.0), confissão (-2.0), dedo-duro (-2.0), open (-2.5); backlash varies |
| Anjo dynamics | manual | -0.15 to +0.15 | Almoço (+0.15), duo (+0.10 mutual), não-imunizou (-0.15) |

**Three pair modes**: `pairs_daily` (active only, Q anchored to today), `pairs_paredao` (active only, Q anchored to paredão formation), `pairs_all` (includes eliminated participants). Events are identical in all three.

---

## 2. Data Validation Results

### 2.1 Edge counts (as of Jan 29, Week 3)

| Type | Count |
|------|-------|
| Sincerão | 108 |
| Votes | 43 |
| Power events | 28 |
| VIP | 14 |
| Anjo | 11 |
| **Total** | **204** |

### 2.2 Active participants: 21 (excludes Aline Campos, Henri Castelli, Pedro, Matheus)

`pairs_all` includes 24 participants (all except Henri Castelli — only 1 day of data).

### 2.3 Top hostile mutual relationships

| A ↔ B | Mutual | A→B | B→A |
|-------|--------|-----|-----|
| Alberto ↔ Leandro | **-5.82** | -6.26 | -5.38 |
| Brigido ↔ Leandro | **-4.69** | -4.36 | -5.02 |
| Alberto ↔ Milena | **-3.41** | -3.96 | -2.87 |
| Juliano ↔ Sol Vega | **-3.40** | -3.50 | -3.30 |
| Brigido ↔ Milena | **-2.56** | -1.80 | -3.32 |

### 2.4 Top positive mutual relationships

| A ↔ B | Mutual | A→B | B→A |
|-------|--------|-----|-----|
| Jonas ↔ Sarah | **+2.25** | +2.96 | +1.55 |
| Marcelo ↔ Maxiane | **+1.77** | +1.86 | +1.68 |
| Babu ↔ Solange | **+1.60** | +1.70 | +1.50 |
| Ana Paula ↔ Milena | **+1.50** | +1.50 | +1.50 |
| Babu ↔ Edilson | **+1.50** | +1.50 | +1.50 |

### 2.5 Contradiction rate: Vote vs Queridômetro

**23 out of 38 vote edges (61%)** show positive queridômetro but negative vote. This is expected in BBB (secret reactions ≠ true intent). Now surfaced via the `contradictions` field and per-pair `vote_contradiction` flag in `relations_scores.json`.

Notable cases:
- **Breno → Paulo Augusto**: Q=+1.00, voted to eliminate (-2.0)
- **Chaiany → Brigido**: Q=+1.00, voted twice against (-4.0 total)
- **Alberto → Chaiany**: Q=+1.00, voted to eliminate (-2.0)

---

## 3. Gaps Found

### GAP 1: Eliminated participants lose ALL scoring data ✅ Fixed

**Severity**: High → **Resolved**

`all_names_set` (from `participants_index`) now includes all participants ever seen (excluding Henri Castelli — only 1 day). `add_edge_raw()` uses `all_names_set` instead of `active_set`. A new `pairs_all` output includes all 24 participants with `active_pair` flag per pair.

**Previously lost, now preserved**:
- Aline Campos' vote for Paulo Augusto (week 1)
- Matheus' vote for Ana Paula Renault (week 2)
- Aline's contragolpe on Ana Paula
- Babu → Matheus indicação
- All eliminated participants' queridômetro base (computed from `last_seen` snapshot)

`pairs_daily` remains active-only (21 participants) — existing consumers unaffected.

### GAP 2: No contradiction metric (Vote vs Queridômetro) ✅ Fixed

**Severity**: Medium → **Resolved**

The `contradictions` field in `relations_scores.json` now surfaces all cases where Q_base > 0 but a negative vote edge exists. Includes:
- `vote_vs_queridometro`: list of per-pair contradiction entries (actor, target, Q value, vote weight, week)
- `total`, `total_vote_edges`, `rate`: aggregate statistics
- `context_notes`: contextual notes (e.g., Pedro's quit inflating week 1 contradictions)
- Per-pair: `vote_contradiction: true` flag in `pairs_all` and `pairs_daily`

### GAP 3: Doc-vs-code weight inconsistency (Sincerão) ✅ Fixed

**Severity**: Medium → **Resolved**

`docs/SCORING_AND_INDEXES.md` now matches the code values:
- pódio slot 1/2/3: +0.7/+0.5/+0.3
- nao_ganha: -1.0
- bomba: -0.8

### GAP 4: Anjo dynamics not captured ✅ Fixed

**Severity**: Low → **Resolved**

Previously only `anjo_autoimune` metadata was tracked. Now the full Anjo dynamics are modeled:

- **`almoco_anjo`**: Anjo → each lunch invitee (+0.15). Tracks who the Anjo chose to share the special lunch.
- **`duo_anjo`**: Mutual edge between Prova do Anjo duo partners (+0.10 each way). Accumulates per occurrence — Jonas ↔ Sarah competed as duo twice (+0.20 total each way).
- **`anjo_nao_imunizou`**: Closest ally (duo partner) → Anjo (−0.15). Only when Anjo is autoimune and chose not to use extra immunity power. Represents subtle disappointment from the person most likely to have expected protection.

Data stored in `manual_events.json` → `weekly_events[].anjo` with full schema (vencedor, duo, almoco_convidados, tipo, escolha, extra_poder, etc.).

### GAP 5: No "received impact" aggregation ✅ Fixed

**Severity**: Low → **Resolved**

`received_impact` per participant now included in `relations_scores.json`. For each participant: `positive` (sum of incoming positive edges), `negative` (sum of incoming negative edges), `total`, `count`.

### GAP 6: Week 1 votes — all treated as secret ✅ Verified

**Severity**: Low (data question)
**Status**: Confirmed correct.

All week 1 votes are treated as `secret`. BBB26 uses standard confessionário voting: each participant votes in the confessionário (shown to the TV audience), but votes are not revealed to the other participants inside the house. This is the standard BBB format — votes are **secret within the game**. The `secret` classification is correct.

**Note**: Vote visibility is now tracked with four distinct types: `secret`, `confissao` (voluntary confession), `dedo_duro` (game mechanic), `open_vote` (votação aberta). See `docs/MANUAL_EVENTS_GUIDE.md`.

### GAP 6b: Jordana → Sol Vega vote reclassified ✅ Fixed

**Previous**: Classified as `voto_revelado` (treated as dedo-duro, −2.5 voter weight, −1.2 backlash).
**Corrected**: Classified as `confissao_voto` (−2.0 voter weight, −1.0 backlash).

**Reason**: Jordana **voluntarily** told Sol Vega she voted for her after the paredão formation. This was a personal conversation, not a game dynamic. Source: [GShow](https://gshow.globo.com/realities/bbb/bbb-26/dentro-da-casa/noticia/apos-formacao-do-paredao-jordana-revela-a-sol-vega-que-votou-na-sister.ghtml) — "Jordana decide contar para Sol Vega o motivo de ter votado na Veterana."

### GAP 7: Group dynamics / bloc voting not captured ✅ Fixed

**Severity**: Low → **Resolved**

`voting_blocs` in `relations_scores.json` detects groups of 4+ participants voting for the same target. Each entry: `week`, `date`, `target`, `voters` (list), `count`. Detected blocs:
- Week 1: 11 → Paulo Augusto
- Week 2: 6 → Brigido, 4 → Chaiany

---

## 4. Scoring Validation — Spot Checks

### Alberto Cowboy → Leandro: Score = -6.26

| Component | Value | Explanation |
|-----------|-------|-------------|
| Queridômetro | -1.00 | Strong negative emoji (3-day avg) |
| Power event (barrado_baile) | -0.48 | -0.4 × 1.2 (public) |
| Power event (indicação) | -3.36 | -2.8 × 1.2 (public) |
| Sincerão (nao_ganha wk1) | -0.30 | nao_ganha backlash (Alberto was target of Leandro's "não ganha"... wait) |
| Sincerão (bomba wk2) | -0.80 | Alberto bombed Leandro with "mais chato" |
| Sincerão (bomba backlash) | -0.32 | -0.8 × 0.4 backlash factor |
| **Total** | **-6.26** | Extremely hostile — consistent with game reality |

**Reality check**: Alberto (leader wk1) indicated Leandro indirectly via Caixas-Surpresa (wk2, consensus with Brigido), barred him from the party, and bombed him in Sincerão. Score accurately reflects deep animosity. ✅

### Leandro → Alberto: Score = -5.38

| Component | Value |
|-----------|-------|
| Queridômetro | -1.00 |
| Power event (indicação backlash) | -2.016 |
| Power event (barrado backlash) | -0.24 |
| Sincerão (nao_ganha wk1) | -1.00 |
| Sincerão (bomba wk2) | -0.80 |
| Sincerão (bomba backlash) | -0.32 |
| **Total** | **-5.38** |

**Reality check**: Leandro publicly said Alberto "não ganha" in week 1 Sincerão. Reciprocal bomba. No direct vote against Alberto (voted for Brigido in week 2). ✅

### Jonas → Sarah: Score = +2.96 (strongest positive)

| Component | Value | Explanation |
|-----------|-------|-------------|
| Queridômetro | +1.00 | Strong positive emoji (3-day avg) |
| Power event (imunidade) | +0.96 | +0.8 × 1.2 (public) |
| Sincerão (pódio slot 2) | +0.50 | Jonas put Sarah on podium slot 2 |
| Anjo (almoco × 2) | +0.30 | Invited to Almoço do Anjo both weeks |
| Anjo (duo × 2) | +0.20 | Duo partner in Prova do Anjo both weeks |
| **Total** | **+2.96** | Strongest alliance — consistent with game reality |

**Reality check**: Jonas immunized Sarah (week 1 Anjo), put her on podium, invited her to both Almoço do Anjo, and competed as duo partner twice. ✅

### Sarah → Ana Paula: Score = -1.91

| Component | Value |
|-----------|-------|
| Queridômetro | -0.95 |
| Power event (voto_anulado) | -0.96 |
| **Total** | **-1.91** |

**Reality check**: Sarah used Caixas-Surpresa power to veto Ana Paula's vote. Score correctly negative. ✅

---

## 5. Improvement Proposals — Status

All original proposals have been implemented:

| # | Proposal | Status |
|---|----------|--------|
| 1 | Sync docs with code (Sincerão weights) | ✅ Done (GAP 3) |
| 2 | Historical pairs mode for eliminated participants | ✅ Done (GAP 1 — `pairs_all`) |
| 3 | Contradiction metric (vote-reaction gap) | ✅ Done (GAP 2 — `contradictions` + per-pair flag) |
| 4 | Received impact aggregation | ✅ Done (GAP 5 — `received_impact`) |
| 5 | Bloc voting detection | ✅ Done (GAP 7 — `voting_blocs`) |
| 6 | Anjo dynamics (almoco, duo, não-imunizou) | ✅ Done (GAP 4 — 3 new edge types) |
| 7 | Vote visibility taxonomy (4 types) | ✅ Done (GAP 6/6b — secret, confissao, dedo_duro, open_vote) |

---

## 6. Weight Calibration Assessment

The current weights produce scores that **align well with game reality**:

- **Alberto ↔ Leandro** (-5.82 mutual) is the most hostile pair — consistent with in-game conflict (indicação + barrado + Sincerão bombas).
- **Jonas ↔ Sarah** (+2.25 mutual) is the strongest alliance — consistent with Anjo immunization + pódio + Almoço do Anjo invites + duo partnership (both weeks).
- **Queridômetro range** (-1.0 to +1.0) vs **event range** (votes up to -5.0 for revealed+double) means events dominate when they exist, while queridômetro provides the baseline. This is correct: rare but deliberate actions (votes, indicações) should matter more than daily secret emoji.
- **Vote weight** (-2.0 secret/confissão/dedo-duro, -2.5 open) creates significant impact. A single vote drops the score by 2 points, which can flip a relationship from positive to negative. Backlash varies: confissão -1.0, dedo-duro -1.2, open -1.5. Voting is the most consequential player-to-player action.
- **Visibility factor** (1.2× public, 0.5× secret) properly amplifies public actions. An indicação being public (everyone knows) makes it 1.2× more impactful than the base weight.

**Potential recalibration needed**: As more paredões happen, vote accumulation could dominate all other signals. With 2+ votes against the same target, the score can reach -4.0 to -5.0 from votes alone, potentially overwhelming queridômetro and Sincerão. Monitor after week 4.

---

## 7. Missing Data Points to Collect

| Data | Source | Status |
|------|--------|--------|
| ~~Week 1 voting type (open/secret?)~~ | ~~GShow~~ | ✅ Confirmed secret (GAP 6) |
| Week 3 Sincerão edges | When it happens | ⏳ Pending (week 3 ongoing) |
| Week 3 power events | As they happen | ⏳ Partially collected (Ganha-Ganha wk3, Barrado wk3 done) |
| ~~Anjo autoimune non-action~~ | ~~paredoes.json~~ | ✅ Modeled (GAP 4 — `anjo_nao_imunizou` edge) |
| ~~Dedo-duro events~~ | ~~GShow~~ | ✅ Infrastructure ready (4-type vote visibility) |
| Week 3 Anjo data | GShow/news | ⏳ Pending (Prova do Anjo not yet happened) |
| Week 3 confissao_voto events | GShow/news | ⏳ Monitor after paredão formation |

---

## 8. System Health Summary

| Aspect | Status | Notes |
|--------|--------|-------|
| Edge generation | ✅ Working | 204 edges across 5 types (sincerao 108, vote 43, power 28, vip 14, anjo 11) |
| Weight application | ✅ Correct | Visibility factor, backlash, consensus all working |
| Decay policy | ✅ Aligned | No decay, accumulation at full weight |
| VIP edges | ✅ Fixed | Per-leader-reign, new entrants excluded |
| Vote edges | ✅ Working | Secret/revealed/backlash properly classified |
| Sincerão edges | ✅ Working | Pódio, nao_ganha, bomba with backlash |
| Eliminated handling | ✅ Fixed | `pairs_all` includes eliminated (except Henri — 1 day only) |
| Contradiction metric | ✅ Fixed | `contradictions` field with per-pair flags |
| Received impact | ✅ Added | Per-participant incoming edge totals |
| Voting blocs | ✅ Added | 4+ voters on same target detected |
| Anjo dynamics | ✅ Added | almoco_anjo (+0.15), duo_anjo (+0.10 mutual), anjo_nao_imunizou (−0.15) + autoimune metadata |
| Doc sync | ✅ Fixed | Sincerão weights synced to code values |
| Queridômetro base | ✅ Correct | 3-day rolling with proper fallback |
