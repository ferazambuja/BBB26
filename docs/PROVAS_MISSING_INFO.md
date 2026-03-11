# Provas Needing More Information

Updated: 2026-03-09

This list is for provas where the current `data/provas.json` entry is still missing source detail that would improve ranking quality, participant coverage, or reproducibility.

## Not Missing

- Prova 23 (`bate_volta`, 2026-03-08): Jordana is already registered as the winner.
- The recent build warnings were not caused by missing Bate e Volta winners.

## Priority List

### Prova 2 — Prova do Anjo — Dupla Velocidade

- Date: `2026-01-18`
- Current state:
  - pairs are recorded
  - finalists are recorded
  - Pedro + Paulo Augusto are marked as `dq`
- Missing:
  - confirm why `Chaiany`, `Gabriela`, `Leandro`, and `Matheus` do not appear in the recorded duplas
  - decide whether they should be added to `excluidos` or whether the prova happened before they were eligible on that date
- Why it matters:
  - the entry is mostly complete, but those four names still make the participation boundary ambiguous

### Prova 4 — Prova do Líder — Equilíbrio

- Date: `2026-01-25`
- Current state:
  - only the top 5 from phase 1 are recorded
  - the top 4 duel/final stage is recorded
  - `nota_ranking` already says positions `6-22` are unknown
- Missing:
  - placements below the top 5, or at least a stronger cutoff description from the source
  - phase-1 elimination detail for the non-classified participants
- Why it matters:
  - this is a true partial-ranking prova, not just a warning artifact

### Prova 9 — Prova do Líder — Cadeados e Cubos (Agilidade)

- Date: `2026-02-05`
- Current state:
  - only the 4 classified from phase 1 are recorded
  - semifinals/finalists are recorded
  - `nota_ranking` already says the rest of the field is unknown
- Missing:
  - names or placements for the non-classified participants from phase 1
  - any cutoff or elimination ordering from the source coverage
- Why it matters:
  - current ranking only captures the finalists path, not the full field

### Prova 10 — Prova do Anjo — Vegetais Sazón (Dupla Velocidade)

- Date: `2026-02-07`
- Current state:
  - the top 6 duplas are recorded
  - the final `Alberto Cowboy x Ana Paula Renault` is recorded
  - six players are marked as `dq`, but the exact pairings are unknown
- Missing:
  - exact duo pairings for `Chaiany`, `Juliano Floss`, `Leandro`, `Samira`, `Sarah Andrade`, and `Sol Vega`
- Why it matters:
  - we can account for the DQs, but we still do not know the actual pair structure of the full first phase

### Prova 12 — Prova do Líder — Resistência (pontuação)

- Date: `2026-02-13`
- Current state:
  - only the top 3 from round 1 are recorded
  - only the top 2 from round 2 are recorded
  - `nota_ranking` already says the rest of the field is unknown
- Missing:
  - scores or at least elimination order for the other participants in round 1
- Why it matters:
  - this is currently a podium-only record for a prova that affected a large field

### Prova 13 — Prova do Anjo — Tabuleiro de Celulares

- Date: `2026-02-14`
- Current state:
  - only Gabriela is ranked as winner
  - `nota_ranking` already says the rest of the classification is unknown
- Missing:
  - list of the 9 participants selected into the tabuleiro
  - any intermediate advancement/elimination structure after the sorteio
- Why it matters:
  - this is the sparsest ranking entry in the file today

## Probably Good Enough For Now

These had recent warnings before the builder fix, but they do not look like true missing-info problems:

- Prova 6 — team elimination + finalist phase are already modeled; warning was inflated by `dq` handling
- Prova 7 — quarterfinal/semifinal/final path is recorded; warning was inflated by `dq` handling

## Suggested Next Pass

1. Fill missing participant coverage for Provas 2 and 10.
2. Find deeper source detail for partial rankings in Provas 4, 9, 12, and 13.
3. When source detail cannot be recovered, keep `nota_ranking` explicit instead of pretending the ranking is complete.
