# Votalhada Consolidado OCR — Feasibility Plan

> Date: 2026-03-03  
> Status: Ready for execution  
> Scope: OCR feasibility only (no GitHub automation yet)

## Goal

Verify if we can reliably extract Votalhada **Consolidados** data (including time series) from images with enough quality to replace manual reading.

The outcome of this phase is a **go/no-go decision** for automation.

## In Scope

- Identify the correct image containing `CONSOLIDADOS` + `VARIAÇÃO DAS MÉDIAS`.
- Extract and normalize:
  - `consolidado` (participant %, `total_votos`, optional `nota`)
  - `plataformas` aggregates (sites/youtube/twitter/instagram: participant %, `votos`, `fontes_count`)
  - `serie_temporal` rows (`hora`, participant %, `votos`)
- Validate extracted values against strict consistency checks.
- Benchmark accuracy on existing historical images already in the repo.

## Out of Scope (for this phase)

- GitHub Actions workflow changes
- Auto-commit to `main`
- Updating `data/votalhada/polls.json` in production flow
- Scheduling/cadence orchestration

## Ground Truth Observations (from current dataset)

Based on direct inspection of recent files in `data/votalhada/`:

- Filename index is not reliable for content meaning.
  - In the latest batches, the actual consolidated card is `consolidados_5_*`.
  - `consolidados_6_*` is often just a `Pesquisa de Popularidade` banner (non-data).
- The relevant consolidated card includes both:
  - Top table (`CONSOLIDADOS`)
  - Bottom table (`VARIAÇÃO DAS MÉDIAS`)
- During a single paredão, `fontes_count` can go up or down between captures.
- `serie_temporal` is append-only in `polls.json`.

These observations must be encoded in feasibility checks.

## Feasibility Questions

1. Can we consistently detect the correct consolidated image in mixed 6-image batches?
2. Can OCR recover numeric values with low enough error for percentages and vote totals?
3. Can we parse time-series rows (`dia/hora`) robustly, including uncommon times like `17:30`?
4. Can we validate extracted data strongly enough to block bad writes later?

## Target Output Contract (Feasibility Parser)

The parser should return a normalized object:

```json
{
  "image_selected": "path/to/consolidados_5_....png",
  "capture_hora": "03/mar 18:00",
  "consolidado": {
    "Alberto Cowboy": 48.68,
    "Breno": 47.30,
    "Jordana": 4.01,
    "total_votos": 6760035,
    "nota": "EMPATE TÉCNICO"
  },
  "plataformas": {
    "sites": {"Alberto Cowboy": 52.21, "Breno": 45.02, "Jordana": 2.77, "votos": 3042768, "fontes_count": 14},
    "youtube": {"Alberto Cowboy": 53.14, "Breno": 43.55, "Jordana": 3.25, "votos": 1351500, "fontes_count": 22},
    "twitter": {"Alberto Cowboy": 42.68, "Breno": 49.02, "Jordana": 8.30, "votos": 623394, "fontes_count": 21},
    "instagram": {"Alberto Cowboy": 41.21, "Breno": 53.57, "Jordana": 5.21, "votos": 1742373, "fontes_count": 15}
  },
  "serie_temporal": [
    {"hora": "02/mar 01:00", "Alberto Cowboy": 46.60, "Breno": 46.92, "Jordana": 6.70, "votos": 1141249}
  ]
}
```

## Technical Approach (Feasibility Stage)

### 1) Image classification (content-based)

Evaluate each downloaded image and classify as:

- `consolidado_data` (contains both key headers)
- `platform_breakdown` (Sites/YouTube/Twitter/Instagram tables)
- `noise` (banner/non-data)

Selection rule:
- Use the image with strongest consolidated signature.
- Never rely on filename index (`_2`, `_5`, `_6`) alone.

### 2) OCR extraction strategy

Primary:
- Local OCR (Tesseract) + deterministic text normalization.

Optional fallback for feasibility comparison:
- Vision model parse path to compare extraction quality on hard images.

### 3) Parsing and normalization

- Normalize decimal comma/dot consistently.
- Parse PT-BR month abbreviations (`jan`, `fev`, `mar`, ...).
- Canonicalize participant names against current paredão participant list.
- Keep two decimals for percentages; integer for vote counts.

### 4) Validation gate

Each parsed capture must pass:

- Row percentage sum near 100 (`±0.25` p.p. tolerance).
- Consolidado `total_votos` equals (or near) sum of platform votes (`max(5 votes, 1%)` tolerance).
- `serie_temporal` vote totals are non-decreasing by `hora`.
- Participant set matches the paredão participant set after alias resolution.
- Duplicate `hora` rows are deduplicated deterministically.

## Validation Method (Vision + Polls Ground Truth)

Feasibility validation must use two independent checks:

- **Vision check** (manual spot-check):
  - inspect selected consolidated image directly
  - verify key rows and totals visually (`CONSOLIDADOS` + `VARIAÇÃO DAS MÉDIAS`)
  - confirm selected image is truly the consolidated card, not platform/noise card
- **Data check** (programmatic):
  - compare parsed output against `data/votalhada/polls.json`
  - compute MAE, vote exact-match rate, series recall
  - record validation errors by image/file

This avoids accepting OCR output based only on parser self-consistency.

## Benchmark Dataset

Use existing local images only:

- `data/votalhada/2026_03_01/*` (P7, multiple timestamps)
- `data/votalhada/2026_02_22/*` (P6, multiple timestamps)

Ground truth source:
- Values currently stored in `data/votalhada/polls.json`
- Manual spot-checks on images for disputed fields

## Success Criteria (Go)

Feasibility is considered **approved** if all are met:

- Image classification accuracy: `>= 95%` on sampled batches.
- Consolidado percentage MAE: `<= 0.15` p.p.
- Platform vote count exact-match rate: `>= 98%`.
- Time-series row recall: `>= 95%` (rows present in image are extracted).
- Zero critical validation escapes (no invalid parse marked as valid).

## Failure Criteria (No-Go / Rework)

- Frequent confusion between consolidated and non-data images.
- Numeric extraction instability on key totals/percentages.
- Inability to enforce validation confidently before write.

If failed, move to template-matching + region-specific OCR before any automation work.

## Implementation Tasks (Feasibility Only)

### Task 1 — Build parser skeleton

**Files**
- Create: `scripts/votalhada_ocr_feasibility.py`

**Deliverables**
- CLI to parse a directory of images and emit normalized JSON to stdout/file.
- Content-based image classification + selected-image debug log.

### Task 2 — Add validation module

**Files**
- Modify: `scripts/votalhada_ocr_feasibility.py`

**Deliverables**
- Validation report with pass/fail per rule.
- Explicit failure reasons (`sum_mismatch`, `participant_mismatch`, etc.).

### Task 3 — Build regression tests

**Files**
- Create: `tests/test_votalhada_ocr_feasibility.py`

**Deliverables**
- Fixture-driven tests for known image batches from P6 and P7.
- Tests for noise image rejection (`consolidados_6_*` banner case).

### Task 4 — Benchmark and decision report

**Files**
- Create: `docs/plans/2026-03-03-votalhada-ocr-feasibility-report.md`

**Deliverables**
- Metrics table vs success criteria.
- Go/No-Go recommendation.

## Risks and Mitigations

- OCR drift from layout/font changes:
  - Mitigation: content signatures + strict validation + fallback path comparison.
- Name alias mismatch (`A Cowboy` vs `Alberto Cowboy`):
  - Mitigation: explicit alias map + participant-set validation.
- Decimal parsing errors (`48,68` vs `48.68`):
  - Mitigation: locale normalization before numeric parse.

## Decision Rule for Next Phase

Only after this feasibility plan reaches **Go**:

- Start a second plan for automation (workflow, cron, commit policy, failure handling).
- Reuse the validated parser as the core OCR engine.
