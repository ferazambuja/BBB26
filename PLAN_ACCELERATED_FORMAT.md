# Platform Icons + Votalhada Branding — Pass 1

> **Scope**: Single pass — centralize constants, add SVG platform icons, add Votalhada logo branding, update comparison card, fix mobile poll tables with proper scroll/sticky behavior.

**Goal:** Replace generic poll platform emojis with centralized branded SVG icons and add Votalhada logo attribution across the live/archive poll surfaces. Centralize all platform label variants in `data_utils.py` to eliminate 10+ scattered local dictionaries.

**Architecture:** Keep platform-label variants and Votalhada source/logo helpers in `scripts/data_utils.py`, then reuse them from `paredao.qmd`, `paredoes.qmd`, and `scripts/paredao_viz.py`. Shared CSS goes in `assets/cards.css` (globally loaded). `assets/votacao.css` is NOT globally loaded — only `votacao.qmd` imports it.

**SVG source:** Simple Icons (CC0 public domain, https://github.com/simple-icons/simple-icons). Paths confirmed available for YouTube, Instagram, X/Twitter. No licensing concerns.

**Key constraint:** The VOTALHADA.png logo contains the text "VOTALHADA" — never write "Votalhada" adjacent to the logo image.

---

## Scope Corrections (from challenge review)

- `assets/votacao.css` is NOT globally loaded — shared styles go in `assets/cards.css`.
- Comparison-card entry points: `build_poll_comparison_payload()` + `render_poll_comparison_card()` in `scripts/paredao_viz.py`.
- `index.qmd` is out of scope — the comparison card branding change flows through `paredao_viz.py`.
- `polls.json` `fontes` are **flat URL strings** (NOT objects like `paredoes.json`). Paredão 7 has `fontes: null`. Helper must handle both.
- `paredao.qmd` has **5** platform dict locations (not 3): lines 534, 840, 942, 1823, 1944.
- `paredoes.qmd` has **6** platform dict/label locations: lines 199, 340 (reuse), 662 (inline `.get()`), 1396, 1461, 1489.
- `paredoes.qmd` line 662 is `_pl_name = {...}.get(_pl, _pl)` — inline expression, not a standalone dict.
- Mobile table fix included: apply `poll-precision-table--compact` to `paredao.qmd` tables + resolve `pruneWideTables` interaction + mobile layout audit.
- Plotly charts currently use emoji-prefixed labels (`'🌐 Sites'`). Switching to plain text is acceptable — emoji in Plotly is cosmetic and inconsistent with SVG icons.
- `_quarto.yml` `resources:` must include `assets/votalhada-logo.png` — Quarto does NOT auto-discover images from Python `print()` output. **Deployment blocker if missed.**
- "Nosso Modelo" icon: replace `🧮` with `📊` site-wide.

## Search Anchors To Use Instead Of Fragile Line Numbers

- `paredao.qmd`
  - `platform_names =`
  - `_plat_labels_err =`
  - `_plat_labels_d =`
  - `Dados agregados de <a href="https://votalhada.blogspot.com/"`
  - `print('<table class=\"table table-striped`
- `paredoes.qmd`
  - `## Precisão das Enquetes (Votalhada)`
  - `platform_names =`
  - `plat_names =`
  - `_plat_names_h =`
  - `_plat_label_a =`
- `scripts/paredao_viz.py`
  - `def build_poll_comparison_payload`
  - `def _votalhada_blurb`
  - `def render_poll_comparison_card`
- `scripts/data_utils.py`
  - `def build_precision_methodology_text`

## Task 1: Centralize Platform + Votalhada Helpers

**Files:**
- Modify: `scripts/data_utils.py`
- Test: `tests/test_data_utils_extended.py`

- [ ] **Step 1: Add shared constants for all platform-label variants**

Add shared constants near the other shared labels/constants:

```python
VOTALHADA_HOME = "https://votalhada.blogspot.com/"

PLATFORM_LABELS = {
    "sites": "Sites",
    "youtube": "YouTube",
    "twitter": "Twitter",
    "instagram": "Instagram",
}

PLATFORM_SHORT_LABELS = {
    "sites": "Sites",
    "youtube": "YT",
    "twitter": "TW",
    "instagram": "IG",
}

_YT_SVG = '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>'
_IG_SVG = '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M7.0301.084c-1.2768.0602-2.1487.264-2.911.5634-.7888.3075-1.4575.72-2.1228 1.3877-.6652.6677-1.075 1.3368-1.3802 2.127-.2954.7638-.4956 1.6365-.552 2.914-.0564 1.2775-.0689 1.6882-.0626 4.947.0062 3.2586.0206 3.6671.0825 4.9473.061 1.2765.264 2.1482.5635 2.9107.308.7889.72 1.4573 1.388 2.1228.6679.6655 1.3365 1.0743 2.1285 1.38.7632.295 1.6361.4961 2.9134.552 1.2773.056 1.6884.069 4.9462.0627 3.2578-.0062 3.668-.0207 4.9478-.0814 1.28-.0607 2.147-.2652 2.9098-.5633.7889-.3086 1.4578-.72 2.1228-1.3881.665-.6682 1.0745-1.3378 1.3795-2.1284.2957-.7632.4966-1.636.552-2.9124.056-1.2809.0692-1.6898.063-4.948-.0063-3.2583-.021-3.6668-.0817-4.9465-.0607-1.2797-.264-2.1487-.5633-2.9117-.3084-.7889-.72-1.4568-1.3876-2.1228C21.2982 1.33 20.628.9208 19.8378.6165 19.074.321 18.2017.1197 16.9244.0645 15.6471.0093 15.236-.005 11.977.0014 8.718.0076 8.31.0215 7.0301.0839m.1402 21.6932c-1.17-.0509-1.8053-.2453-2.2287-.408-.5606-.216-.96-.4771-1.3819-.895-.422-.4178-.6811-.8186-.9-1.378-.1644-.4234-.3624-1.058-.4171-2.228-.0595-1.2645-.072-1.6442-.079-4.848-.007-3.2037.0053-3.583.0607-4.848.05-1.169.2456-1.805.408-2.2282.216-.5613.4762-.96.895-1.3816.4188-.4217.8184-.6814 1.3783-.9003.423-.1651 1.0575-.3614 2.227-.4171 1.2655-.06 1.6447-.072 4.848-.079 3.2033-.007 3.5835.005 4.8495.0608 1.169.0508 1.8053.2445 2.228.408.5608.216.96.4754 1.3816.895.4217.4194.6816.8176.9005 1.3787.1653.4217.3617 1.056.4169 2.2263.0602 1.2655.0739 1.645.0796 4.848.0058 3.203-.0055 3.5834-.061 4.848-.051 1.17-.245 1.8055-.408 2.2294-.216.5604-.4763.96-.8954 1.3814-.419.4215-.8181.6811-1.3783.9-.4224.1649-1.0577.3617-2.2262.4174-1.2656.0595-1.6448.072-4.8493.079-3.2045.007-3.5825-.006-4.848-.0608M16.953 5.5864A1.44 1.44 0 1 0 18.39 4.144a1.44 1.44 0 0 0-1.437 1.4424M5.8385 12.012c.0067 3.4032 2.7706 6.1557 6.173 6.1493 3.4026-.0065 6.157-2.7701 6.1506-6.1733-.0065-3.4032-2.771-6.1565-6.174-6.1498-3.403.0067-6.156 2.771-6.1496 6.1738M8 12.0077a4 4 0 1 1 4.008 3.9921A3.9996 3.9996 0 0 1 8 12.0077"/></svg>'
_TW_SVG = '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M14.234 10.162 22.977 0h-2.072l-7.591 8.824L7.251 0H.258l9.168 13.343L.258 24H2.33l8.016-9.318L16.749 24h6.993zm-2.837 3.299-.929-1.329L3.076 1.56h3.182l5.965 8.532.929 1.329 7.754 11.09h-3.182z"/></svg>'

PLATFORM_ICON_LABELS = {
    "sites": '<span class="plat-icon" title="Sites">🌐</span> Sites',
    "youtube": f'<span class="plat-icon plat-icon--youtube" title="YouTube">{_YT_SVG}</span> YouTube',
    "twitter": f'<span class="plat-icon plat-icon--twitter" title="Twitter/X">{_TW_SVG}</span> Twitter',
    "instagram": f'<span class="plat-icon plat-icon--instagram" title="Instagram">{_IG_SVG}</span> Instagram',
}

# Source: Simple Icons (CC0 public domain) — https://github.com/simple-icons/simple-icons
```

- [ ] **Step 2: Add tiny helpers so QMD pages stop reimplementing fallback logic**

Use helpers instead of scattering direct dict access:

```python
def platform_label(platform: str, *, variant: str = "text") -> str: ...
def get_votalhada_source_url(poll: dict | None) -> str: ...
def render_votalhada_logo(*, href: str | None = None, size: str = "sm", extra_classes: str = "") -> str: ...
```

Implementation rules:
- `platform_label(..., variant="html")` returns SVG icon + text for HTML tables.
- `variant="text"` returns plain text for Plotly axes, prose, and hover text. No emoji (Plotly currently has emoji but switching to plain text is acceptable).
- `variant="short"` returns `YT` / `TW` / `IG` for compact vote-share strings.
- Unknown platform keys fall through: `platform_label("tiktok") == "tiktok"`.
- `get_votalhada_source_url()` scans `poll.get("fontes") or []` (handles `None` from paredão 7 paredao_falso). Fontes in `polls.json` are **flat URL strings**, not objects. Returns first URL containing `"votalhada"` or `"blogspot"`, otherwise `VOTALHADA_HOME`.
- `render_votalhada_logo()` returns `<a href="..."><img src="assets/votalhada-logo.png" alt="Votalhada" class="votalhada-logo" /></a>`. Alt text is **always** "Votalhada" (tests depend on this). Never write "Votalhada" text next to the logo — the image already contains the word.

- [ ] **Step 3: Move existing methodology text to the new helpers**

Update `build_precision_methodology_text()` to use `PLATFORM_LABELS` / `platform_label()`, and wrap prose mentions of Votalhada in a homepage link without placing text next to the logo.

- [ ] **Step 4: Add helper tests before page changes**

Add targeted tests for:
- `platform_label("youtube", variant="html")` includes `plat-icon--youtube` class.
- `platform_label("instagram", variant="short") == "IG"`.
- `platform_label("tiktok", variant="text") == "tiktok"` (unknown key fallthrough).
- `get_votalhada_source_url({"fontes": ["https://votalhada.blogspot.com/2026/03/pesquisa10.html"]})` returns that URL.
- `get_votalhada_source_url({"fontes": None})` returns `VOTALHADA_HOME` (paredao_falso edge case).
- `get_votalhada_source_url({})` returns `VOTALHADA_HOME` (missing key).
- `get_votalhada_source_url({"fontes": ["https://gshow.globo.com/..."]})` returns `VOTALHADA_HOME` (no votalhada URL).
- `render_votalhada_logo(size="lg")` emits `votalhada-logo--lg` class and `assets/votalhada-logo.png`.
- `render_votalhada_logo()` alt text is "Votalhada".

Run:

```bash
python -m pytest tests/test_data_utils_extended.py -q
```

Expected: PASS with new helper coverage.

## Task 2: Add Shared Asset + Shared CSS In The Right Place

**Files:**
- Create: `assets/votalhada-logo.png`
- Modify: `.gitignore`
- Modify: `assets/cards.css`
- Optional follow-up: `data/votalhada/VOTALHADA.png` if the source image should be tracked for reproducibility

- [ ] **Step 1: Add the web-sized Votalhada logo asset**

Create the tracked web asset from the local source image:

```bash
sips -Z 120 data/votalhada/VOTALHADA.png --out assets/votalhada-logo.png
```

`data/votalhada/VOTALHADA.png` is **untracked** (confirmed: `git ls-files` returns empty despite `!data/votalhada/**/*.png` gitignore exception — it was never `git add`-ed). The derived `assets/votalhada-logo.png` is what gets tracked and deployed. The source PNG is a local prerequisite only (already present on disk). If it ever needs to be regenerated, the source file must exist locally — document this in the `sips` command comment.

- [ ] **Step 2: Allow the derived asset through `.gitignore` + ensure deployment**

Add to `.gitignore`:
```gitignore
!assets/votalhada-logo.png
```

Add to `_quarto.yml` `resources:` (DEPLOYMENT BLOCKER — Quarto does not auto-discover images from Python `print()` output):
```yaml
resources:
  - data/derived/*.json
  - assets/votalhada-logo.png
```

- [ ] **Step 3: Put new shared styling in `assets/cards.css`, not `assets/votacao.css`**

Extend the already-global shared stylesheet with:

```css
.plat-icon { display:inline-flex; align-items:center; gap:0; margin-right:2px; }
.plat-icon svg { width:16px; height:16px; vertical-align:-2px; }
.plat-icon--youtube svg { fill:#ff0000; }
.plat-icon--instagram svg { fill:#e1306c; }
.plat-icon--twitter svg { fill:#ffffff; }

.votalhada-logo { height:22px; width:auto; vertical-align:middle; }
.votalhada-logo--lg { height:28px; width:auto; vertical-align:middle; }
.votalhada-attr { margin:6px 0; display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
.votalhada-attr a { text-decoration:none; }

.poll-compare-brand img { display:block; }
```

Reuse and, if needed, lightly extend the existing `.poll-precision-table-wrap` / `.poll-precision-table` block instead of adding a second parallel table system. The existing block already provides: `overflow-x: auto`, `white-space: nowrap`, sticky first column, and themed Votalhada/Model row backgrounds.

Potential CSS tweaks to evaluate during implementation:
- `min-width: 720px` on `.poll-precision-table` may force unnecessary horizontal scrolling for small tables (3 nominees = 5 columns). Consider reducing or removing this `min-width` when the table has fewer columns, or add a modifier class (e.g., `.poll-precision-table--compact`) that omits it.
- mobile icon/logo size reductions at `max-width: 520px`
- optional tighter header font/avatar sizing if overflow still remains after icon/logo compression
- no new dependency on `assets/votacao.css`

- [ ] **Step 4: Keep avatar-size reduction as a fallback, not the first move**

Do not hardcode a 32px avatar change into the first pass. First verify whether:
- icon labels,
- logo labels, and
- existing horizontal scroll + sticky first column

already fix the mobile breakage. Only add a smaller avatar size/CSS tweak if the 390px/520px audit still shows header overflow.

## Task 3: Replace Page-Local Mappings And Fix Table Markup

**Files:**
- Modify: `paredao.qmd`
- Modify: `paredoes.qmd`

- [ ] **Step 1: Import the new helpers from `data_utils.py`**

Update both QMD import lists to include the new helper/constant surface instead of keeping page-local platform dictionaries.

- [ ] **Step 2: Replace all local platform label dictionaries with helper calls**

In `paredao.qmd`, replace **all 5** locations:
- Line 534: `platform_names = {...}` (live current-poll table) → `platform_label(plat, variant="html")`
- Line 840: `_plat_labels_err = {...}` (curiosity bullets) → `platform_label(plat, variant="text")`
- Line 942: `_plat_labels_d = {...}` (weight breakdown) → `platform_label(plat, variant="text")`
- Line 1823: `platform_names = {...}` (finalized poll table) → `platform_label(plat, variant="html")`
- Line 1944: `platform_names = {...}` (finalized ranking table) → `platform_label(plat, variant="html")`

In `paredoes.qmd`, replace **all 6** locations:
- Line 199: `platform_names = {...}` (summary card) → `platform_label(plat, variant="html")`
- Line 662: `_pl_name = {...}.get(_pl, _pl)` (inline, trend curiosities) → `platform_label(_pl, variant="text")`
- Line 1396: `plat_names = {...}` (per-paredão archive table) → `platform_label(plat, variant="html")`
- Line 1461: `_plat_names_h = {...}` (per-paredão curiosities) → `platform_label(plat, variant="text")`
- Line 1489: `_plat_label_a = {...}` (compact vote-share) → `platform_label(plat, variant="short")`
- Lines 393, 429, 432, 482: Plotly `name=`/`x=`/`hovertemplate=` → `platform_label(plat, variant="text")`

Also replace "🧮 Nosso Modelo" with "📊 Nosso Modelo" site-wide (grep for `🧮` in QMD and Python files).

Use:
- `platform_label(plat, variant="html")` for HTML tables/cards
- `platform_label(plat, variant="text")` for Plotly labels, hover text, and prose
- `platform_label(plat, variant="short")` for compact vote-share strings

- [ ] **Step 3: Apply poll-precision-table classes to paredao.qmd tables**

The `paredao.qmd` poll tables currently use `class="table table-striped"` without sticky columns or mobile scroll. Apply the shared table system:

```html
<div class="poll-precision-table-wrap">
  <table class="table table-striped table-sm poll-precision-table poll-precision-table--compact" data-mobile-no-prune="1">
```

Apply to:
- the live current-poll platform table (~line 524)
- the finalized `Enquetes vs Resultado` platform table (~line 1813)

CSS additions needed in `assets/cards.css`:
```css
.poll-precision-table--compact { min-width: 0; }  /* override 720px for per-paredão tables */
```

Also add `data-mobile-no-prune="1"` to prevent the `pruneWideTables()` script from conflicting with the horizontal scroll behavior.

Fix the sticky-column background for themed rows:
```css
.poll-precision-row-votalhada td:first-child { background: #21202e; }
.poll-precision-row-model td:first-child { background: #1a2420; }
```

- [ ] **Step 4: Replace raw text attribution with helper-based logo attribution**

For the live and finalized sections in `paredao.qmd`, replace the raw text line:

```html
Dados agregados de <a ...>Votalhada</a>
```

with helper-driven markup:

```python
_poll_url = get_votalhada_source_url(poll)
print(
    f'<div class="votalhada-attr">'
    f'{render_votalhada_logo(href=_poll_url)}'
    f'<span class="text-muted small">Dados agregados — coleta em ...</span>'
    f'</div>'
)
```

Do not append the word `Votalhada` beside the logo.

- [ ] **Step 5: Update the archive section heading without converting it to Python-generated markdown**

Keep the `##` heading in `paredoes.qmd` as static markdown/HTML so the anchor stays stable:

```markdown
## <span class="poll-accuracy-heading"><a ...><img ... class="votalhada-logo votalhada-logo--lg" ...></a> Precisão das Enquetes</span> {#precisão-das-enquetes-votalhada}
```

Do not replace the heading with a `print()` block unless the anchor contract is deliberately re-tested.

- [ ] **Step 6: Keep Plotly text-only**

Update Plotly `name=`, `x=`, and `hovertemplate=` inputs in `paredoes.qmd` to use the text variant only. Plotly should not receive inline HTML/SVG labels.

## Task 4: Brand The Shared Comparison Card Without Expanding Scope

**Files:**
- Modify: `scripts/paredao_viz.py`
- Test: `tests/test_paredao_active_card.py`

- [ ] **Step 1: Update the live comparison card brand row in the actual renderer**

Modify `render_poll_comparison_card()` so the Votalhada side uses the logo instead of `📊 VOTALHADA`, while the model side keeps text:

```python
f'<div class="poll-compare-brand">{render_votalhada_logo(href=get_votalhada_source_url(poll_like_payload), extra_classes="...")}</div>'
```

Implementation: `build_poll_comparison_payload()` should import `get_votalhada_source_url` from `data_utils` and add `"source_url": get_votalhada_source_url(poll)` to the returned dict. This avoids changing the function's public signature. The renderer reads `payload["source_url"]` and passes it to `render_votalhada_logo(href=...)`.

- [ ] **Step 2: Keep prose text textual, not logo-only**

`_votalhada_blurb()` and any comparison prose should stay text-based for readability, but linked where appropriate. Only source-badge/brand placements should swap to the logo.

- [ ] **Step 3: Do not touch `index.qmd` unless a real Votalhada badge is discovered there during implementation**

Current repo search shows the comparison-card branding change is scoped to `paredao.qmd` through `render_poll_comparison_card()`. Treat `index.qmd` as out of scope for this plan revision.

- [ ] **Step 4: Update renderer tests**

Adjust `tests/test_paredao_active_card.py` so it verifies:
- the compare card still renders,
- the Votalhada panel includes the logo asset/class,
- the card still links to `paredoes.html#precisão-das-enquetes-votalhada`,
- text expectations that must remain textual still do so.

Run:

```bash
python -m pytest tests/test_paredao_active_card.py -q
```

Expected: PASS with updated branding assertions.

## Task 5: Add Contract Coverage For Page Hooks And Finish Verification

**Files:**
- Modify: `tests/test_paredoes_ui_contract.py`
- Optional: `docs/ARCHITECTURE.md`
- Optional: `docs/OPERATIONS_GUIDE.md`
- Optional local-only follow-up: `CLAUDE.md`

- [ ] **Step 1: Add/adjust contract tests for the new shared hooks**

Update `tests/test_paredoes_ui_contract.py` to assert:
- `paredao.qmd` and `paredoes.qmd` import the shared platform/Votalhada helpers
- the live/archive tables use `.poll-precision-table-wrap` / `.poll-precision-table`
- the archive heading keeps the `#precisão-das-enquetes-votalhada` anchor
- `render_poll_comparison_card()` still owns the compare-card branding

- [ ] **Step 2: Keep tracked docs aligned, but keep them secondary**

Only after the implementation is stable:
- update `docs/ARCHITECTURE.md` to mention the shared platform/Votalhada helpers in `data_utils.py`
- update `docs/OPERATIONS_GUIDE.md` with the note that logo attribution comes automatically from poll metadata

Do not make `CLAUDE.md` a required tracked change.

- [ ] **Step 3: Run the targeted automated checks**

Run:

```bash
python -m pytest tests/test_data_utils_extended.py tests/test_paredao_active_card.py tests/test_paredoes_ui_contract.py -q
```

Expected: PASS.

- [ ] **Step 4: Render only the affected pages**

Run:

```bash
quarto render paredao.qmd
quarto render paredoes.qmd
```

Expected: both pages render cleanly with no missing asset errors for `assets/votalhada-logo.png`.

- [ ] **Step 5: Perform focused visual verification**

Desktop checks:
- `_site/paredao.html`
  - current-poll table uses branded platform labels
  - finalized `Enquetes vs Resultado` attribution uses the logo only
  - compare card shows logo on the Votalhada side and no duplicate adjacent brand text
- `_site/paredoes.html`
  - archive section heading shows the linked logo with the existing anchor
  - per-paredao archive sections use the logo and correct poll/homepage fallback links
  - Plotly labels stay text-only, not raw HTML

Mobile checks:
- SVG icons render at 16px on mobile (no overflow or clipping)
- Votalhada logo image scales properly (height-constrained via CSS)
- "VOTALHADA" text no longer wraps because it's now an image
- `paredao.qmd` poll tables scroll horizontally with sticky first column
- `Mobile compacto` note does NOT appear on poll tables (they have `data-mobile-no-prune="1"`)
- No `VOTALHA/DA`, `NOSSO/MODELO`, or `RESULTA/DO` line breaks in first column
- Themed row backgrounds (Votalhada purple, Model green) bleed correctly into sticky first column
- If avatar headers still overflow after all fixes, reduce `avatar_img` to 32px as fallback

## Commit Checkpoints

- Checkpoint A: shared helpers + tests in `scripts/data_utils.py`
- Checkpoint B: shared CSS + asset + `_quarto.yml` resource + `.gitignore` exception
- Checkpoint C: QMD + renderer integration + mobile table fix + contract tests

## Out Of Scope

- Touching `index.qmd` (comparison card flows through `paredao_viz.py`, not direct index rendering)
- Rebranding unrelated Votalhada prose across the whole repo
- Rebuilding derived JSON data unless some unrelated local change requires it
