# Mobile Layout Audit — 2026-03-04

## Scope

Audit run based on full-page screenshots generated on 2026-03-04:

- `tmp/page_screenshots/mobile-review-2026-03-04/desktop/*.png`
- `tmp/page_screenshots/mobile-review-2026-03-04/mobile/*.png`
- `tmp/page_screenshots/mobile-review-2026-03-04/manifest.json`

Viewport target for mobile captures: `390x844`.

---

## Quantitative Baseline (Before Fixes)

| Page | Mobile Size | Overflow vs 390px | Longest near-empty run |
|---|---:|---:|---:|
| cartola | `390x30077` | `0px (0.0%)` | `147px` |
| clusters | `390x13924` | `0px (0.0%)` | `223px` |
| datas | `390x1642` | `0px (0.0%)` | `211px` |
| evolucao | `390x26822` | `0px (0.0%)` | `10181px` |
| index | `390x43410` | `0px (0.0%)` | `26769px` |
| paredao | `525x15902` | `135px (34.6%)` | `97px` |
| paredoes | `564x21098` | `174px (44.6%)` | `93px` |
| planta_debug | `975x15215` | `585px (150.0%)` | `87px` |
| provas | `390x11080` | `0px (0.0%)` | `224px` |
| relacoes | `390x8744` | `0px (0.0%)` | `220px` |
| relacoes_debug | `941x125300` | `551px (141.3%)` | `108791px` |
| votacao | `399x13298` | `9px (2.3%)` | `224px` |

---

## Findings by Severity

### Critical

1. Severe horizontal overflow on debug pages.
   - Pages: `planta_debug`, `relacoes_debug`
   - Symptoms:
     - Mobile width explodes to `975px` and `941px`.
     - Large right-side empty gutter in screenshots.
   - Root cause:
     - Wide code blocks (`pre/sourceCode`) and debug tables expanding document width.
     - No mobile-safe wrapping/containment on code/table content.

2. Severe horizontal overflow on historical page.
   - Page: `paredoes`
   - Symptoms:
     - Width grows to `564px` (44.6% overflow).
     - Right-side columns/avatars clipped from mobile viewport.
   - Root cause:
     - Fixed-width / nowrap tables not constrained in mobile.

### High

3. Significant overflow on current paredão page.
   - Page: `paredao`
   - Symptoms:
     - Width grows to `525px` (34.6% overflow).
   - Root cause:
     - Wide tables (`table-full`/striped) rendered without responsive constraints.

4. Very long blank tails in some full-page screenshots.
   - Pages: `index`, `evolucao`, `relacoes_debug`
   - Symptoms:
     - Large near-empty regions before footer in full-page image output.
   - Root cause:
     - Capture-tool limitation for extremely tall full-page screenshots.
     - Verified not a true page-empty DOM state: at `scrollY=20000` on `index`, visible content is still present (`IMG` at viewport center).

### Medium

5. Minor horizontal overflow in voting page.
   - Page: `votacao`
   - Symptoms:
     - Width `399px` (+9px).
   - Root cause:
     - Slight navbar title overflow + some dense table rows.

6. Dense visualizations/tables with low readability on phone.
   - Pages: `relacoes`, `clusters`, `votacao`, `paredoes`
   - Symptoms:
     - Plot labels and dense tabular sections are difficult to scan.
   - Root cause:
     - Content density and small labels on mobile-width viewport.

### Low

7. Stable pages with acceptable mobile behavior.
   - Pages: `datas`, `cartola`, `provas`
   - Notes:
     - No width overflow detected.
     - Layout remains visually consistent.

---

## DOM Diagnostics (Root-Cause Evidence)

Using browser-side evaluation at `390x844`:

- `paredao`: top offender `table.table-full.fs-base` (`~669px` intrinsic width).
- `paredoes`: top offender `table.table.table-striped.fs-base` (`~540px` intrinsic width).
- `planta_debug`: top offenders are source code spans/blocks (`sourceCode`, `pre`, `code`) exceeding `1400–1900px`.
- `relacoes_debug`: top offenders are both `sourceCode` blocks and wide debug data tables (`#edgesTable` ~`916px`).
- `votacao`: table overflow plus slight navbar title overflow.

---

## Fix Strategy

1. Add global mobile containment rules (`<=575px`) in shared CSS:
   - constrain root/container overflow on X axis
   - force tables to fit viewport width
   - wrap long code tokens (`pre/code/sourceCode`)
   - constrain Plotly/table/code blocks to `max-width: 100%`
   - clamp navbar title width to avoid small residual overflow

2. Re-run full screenshot pipeline and compare:
   - width overflow should be eliminated or reduced to <=1px rounding noise
   - visual clipping on `paredao`, `paredoes`, `planta_debug`, `relacoes_debug` should disappear

3. Keep blank-tail note separated as screenshot-tool limitation:
   - for extremely tall pages, prefer sectioned captures (`top/mid/bottom`) as mobile review alternative.

---

## Post-Fix Verification (After CSS Pass)

Validated with:

- `tmp/page_screenshots/mobile-review-2026-03-04-fixed2/mobile/*.png`
- `tmp/page_screenshots/mobile-review-2026-03-04-fixed2/manifest.json`

| Page | Size | Overflow vs 390px | Longest near-empty run |
|---|---:|---:|---:|
| cartola | `390x30087` | `0px (0.0%)` | `147px` |
| clusters | `390x13343` | `0px (0.0%)` | `224px` |
| datas | `390x1653` | `0px (0.0%)` | `211px` |
| evolucao | `390x14524` | `0px (0.0%)` | `219px` |
| index | `390x43349` | `0px (0.0%)` | `26698px` |
| paredao | `390x13693` | `0px (0.0%)` | `224px` |
| paredoes | `390x16432` | `0px (0.0%)` | `219px` |
| planta_debug | `390x9022` | `0px (0.0%)` | `213px` |
| provas | `390x11019` | `0px (0.0%)` | `224px` |
| relacoes | `390x7878` | `0px (0.0%)` | `219px` |
| relacoes_debug | `390x82399` | `0px (0.0%)` | `65748px` |
| votacao | `390x12431` | `0px (0.0%)` | `224px` |

### Status

- ✅ Horizontal overflow fixed on all pages (`390px` width across mobile outputs).
- ✅ `paredao`, `paredoes`, `planta_debug`, `votacao` no longer clip to the right.
- ✅ `evolucao` no longer shows the large blank tail from baseline capture.
- ⚠️ `index` and `relacoes_debug` can still show blank segments in **full-page** mobile captures due screenshot engine limits on very tall pages.

---

## Alternative Mobile Capture (Implemented)

For reliable review on very long pages, use viewport-slice captures:

```bash
python scripts/capture_mobile_slices.py
```

Output:

- `tmp/page_screenshots/mobile-review-2026-03-04-slices/*.png`
- `tmp/page_screenshots/mobile-review-2026-03-04-slices/manifest.json`

This mode captures `top`, `mid`, and `bottom` viewport slices per page and avoids the full-page blank-tail artifact.

---

## Latest Retake (After Latest Fixes)

Fresh retake completed on **2026-03-04**:

- Full-page capture (desktop + mobile):
  - `tmp/page_screenshots/mobile-review-2026-03-04-retake-full/desktop/*.png`
  - `tmp/page_screenshots/mobile-review-2026-03-04-retake-full/mobile/*.png`
  - `tmp/page_screenshots/mobile-review-2026-03-04-retake-full/manifest.json`
- Mobile slice capture (top/mid/bottom):
  - `tmp/page_screenshots/mobile-review-2026-03-04-retake-slices/*.png`
  - `tmp/page_screenshots/mobile-review-2026-03-04-retake-slices/manifest.json`
- Review summaries:
  - `tmp/page_screenshots/mobile-review-2026-03-04-retake-summaries/mobile_top_montage.png`
  - `tmp/page_screenshots/mobile-review-2026-03-04-retake-summaries/mobile_mid_montage.png`
  - `tmp/page_screenshots/mobile-review-2026-03-04-retake-summaries/mobile_bottom_montage.png`
  - `tmp/page_screenshots/mobile-review-2026-03-04-retake-summaries/mobile_dom_audit.jsonl`

### Capture Status

- Full-page run: `24/24` captures succeeded (`12 pages × 2 profiles`), `0` failures.
- Slice run: `36/36` captures succeeded (`12 pages × 3 slices`).

### Mobile Full-Page Dimensions (Retake)

| Page | Mobile Size |
|---|---:|
| cartola | `390x30087` |
| clusters | `390x13343` |
| datas | `390x1653` |
| evolucao | `390x14524` |
| index | `390x43349` |
| paredao | `390x13693` |
| paredoes | `390x16432` |
| planta_debug | `390x8829` |
| provas | `390x11019` |
| relacoes | `390x7878` |
| relacoes_debug | `390x82250` |
| votacao | `390x12431` |

### DOM Diagnostics (Retake at 390x844)

| Page | Overflow Px | Tables (Overflowing) | Visible Plots (Issues) |
|---|---:|---:|---:|
| cartola | `0` | `2 (0)` | `1 (0)` |
| clusters | `0` | `2 (0)` | `7 (0)` |
| datas | `0` | `1 (0)` | `0 (0)` |
| evolucao | `0` | `4 (0)` | `6 (0)` |
| index | `0` | `4 (0)` | `1 (0)` |
| paredao | `0` | `38 (13)` | `4 (0)` |
| paredoes | `0` | `32 (0)` | `7 (0)` |
| planta_debug | `0` | `9 (0)` | `0 (0)` |
| provas | `0` | `55 (0)` | `0 (0)` |
| relacoes | `0` | `2 (0)` | `4 (0)` |
| relacoes_debug | `0` | `66 (13)` | `0 (0)` |
| votacao | `0` | `5 (0)` | `0 (0)` |

Notes:
- Page-level horizontal overflow is now `0px` on every page.
- `overflowing tables` in `paredao` and `relacoes_debug` are contained inside horizontally scrollable table blocks; they do **not** cause document overflow.
- `Visible plot issues = 0` means no clipped/zero-size visible Plotly container was detected in this retake.

### Visual Review Summary

- ✅ Mobile alignment/spacing is stable across all pages in top/mid/bottom slices.
- ✅ Right-edge clipping/gutters from the pre-fix baseline are gone.
- ✅ Visible plots render and fit the viewport in this retake.
- ⚠️ Very long pages (`index`, `relacoes_debug`) can still show blank segments in **full-page** screenshots due capture limits; slice mode remains the reliable review mode.

### Remaining Improvement Opportunities (Quality, Not Breakages)

1. Dense tables on mobile (`paredao`, `relacoes_debug`, parts of `provas`) remain data-heavy and may require horizontal swipe.
2. Dense heatmap/line chart label readability on smaller phones could improve with mobile-specific figure variants.
3. Consider page-level “mobile compact” tabs that collapse debug tables behind toggles to reduce vertical noise.

---

## Index Ranking Mobile Redesign (Option 1) — 2026-03-04

To reduce dense Plotly visuals on phone width in `index`, the Rankings section now uses **mobile-first summary cards** and keeps full charts for desktop / dedicated pages.

### What changed

- On mobile (`<=575.98px`), hide dense ranking/evolution chart blocks inside `index` Rankings tabs.
- Add mobile summary cards with focused insights:
  - Queridômetro: `Radar rápido`, `Viradas da semana`, `Pressão de rejeição`
  - Estratégico: `Desalinhamento`, `Risco de voto surpresa`, `Influência subestimada`
  - Evolução tabs: `últimos 7 dias` up/down movers + CTA
- Add clear CTA links to `evolucao.html#sentimento` and `evolucao.html#estrategico`.

### Non-duplication check vs top cards

- Top “Destaques do Dia” ranking cards remain focused on **podium/top-bottom + variação vs ontem**.
- New mobile ranking cards focus on **risk concentration, weekly swings, strategic misalignment, and recent trend deltas**.
- This keeps complementary information rather than repeating the same leaderboard snapshots.

### Verification artifacts

- Render target: `_site/index.html`
- Single-page retake (desktop + mobile full-page):
  - `tmp/page_screenshots/mobile-review-2026-03-04-index-mobilecards-v5/mobile/index.png`
  - `tmp/page_screenshots/mobile-review-2026-03-04-index-mobilecards-v5/desktop/index.png`
  - `tmp/page_screenshots/mobile-review-2026-03-04-index-mobilecards-v5/manifest.json`
- Tab-state mobile checks (clicked tabs):
  - `tmp/page_screenshots/mobile-review-2026-03-04-index-mobilecards-v5/tab-checks/pw5-estrategico.png`
  - `tmp/page_screenshots/mobile-review-2026-03-04-index-mobilecards-v5/tab-checks/pw5-evolucao-queridometro.png`
  - `tmp/page_screenshots/mobile-review-2026-03-04-index-mobilecards-v5/tab-checks/pw5-evolucao-estrategico.png`
