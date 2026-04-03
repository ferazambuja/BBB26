# Viradas card design

## Context

The current `index.qmd` dashboard exposes three separate pair-change cards:

- `Mudanças Dramáticas`
- `Novas Hostilidades`
- `Alianças Rompidas`

They all describe the same underlying type of thing: a relationship shift between two participants observed in the latest queridômetro comparison.

At the same time, the recently redesigned `Arquivo do Queridômetro` card established the current visual reference for a denser, dashboard-native card with:

- one main story area
- a compact stat block
- collapsed drill content
- clear mobile behavior

The approved direction is:

1. Keep `Arquivo do Queridômetro` as its own history-first card.
2. Replace the three pair-change cards above with one merged card called `Viradas`.
3. Make `Viradas` use the standard dashboard footprint instead of an oversized feature-panel layout.

## Problem

The current three-card split has three issues:

- It fragments one concept across three separate panels.
- It repeats the same pair-story visual logic with slightly different copy and ranking rules.
- It forces the user to scan three different places to understand “what changed in relationships from yesterday to today.”

The early `Viradas` mockups also exposed a second problem:

- they drifted away from the actual dashboard card footprint and started behaving like standalone feature sections rather than standard cards.

## Current dashboard constraints

The design must match the real local `index` layout, not a freehand mockup.

Measured on the locally rendered `_site/index.html`:

- `Arquivo do Queridômetro`: width `369.27px`
- `Mudanças Dramáticas`: width `369.27px`
- `Novas Hostilidades`: width `369.27px`

This measurement came from the actual DOM bounding boxes on the rendered page. `Viradas` should use the same card width envelope and similar internal density. Wider mockups were explicitly rejected.

## Chosen approach

Introduce a single `Viradas` card that merges the behavior of:

- `Mudanças Dramáticas`
- `Novas Hostilidades`
- `Alianças Rompidas`

The card keeps a hybrid structure:

1. `hero`: the strongest relationship shift in the latest comparison
2. `summary`: one compact strip with category counts
3. `drill`: collapsed grouped sections with all items from the three categories

This preserves the speed of a dashboard card while centralizing the full story behind one drill.

## Published payload contract

`Viradas` replaces the published `dramatic`, `hostilities`, and `breaks` card payloads in `index_data.json`.

There is no dual-publish compatibility period on the index payload surface: once `Viradas` lands, the old three card types should stop being emitted in `highlights.cards`.

Required top-level shape:

```json
{
  "type": "viradas",
  "icon": "🔄",
  "title": "Viradas",
  "color": "#e74c3c",
  "link": "evolucao.html#pulso",
  "source_tag": "📅 dd/mm → dd/mm",
  "subtitle": "As principais viradas de um dia para o outro no queridômetro.",
  "from_date": "YYYY-MM-DD",
  "to_date": "YYYY-MM-DD",
  "reference_date": "YYYY-MM-DD",
  "state": "today" | "partial",
  "total": 0,
  "counts": {
    "dramatic": 0,
    "hostilities": 0,
    "breaks": 0
  },
  "hero": {
    "kind": "dramatic" | "hostilities" | "breaks",
    "kicker": "string",
    "title": "string",
    "body": "string",
    "date": "YYYY-MM-DD",
    "giver": "string",
    "receiver": "string",
    "old_emoji": "string",
    "new_emoji": "string",
    "prior_same_emoji_days": 0,
    "prior_heart_days": 0,
    "other_side_current_emoji": "string|null",
    "other_side_kept_heart": "true|false|null",
    "meta_line": "string",
    "severity_score": "number|null",
    "severity_label": "string|null",
    "stat_value": "string",
    "stat_label": "string",
    "chips": [
      {
        "text": "string",
        "tone": "neutral|accent"
      }
    ]
  },
  "summary": [
    {
      "kind": "dramatic",
      "title": "Mudanças Dramáticas",
      "count": 0,
      "note": "string"
    },
    {
      "kind": "hostilities",
      "title": "Novas Hostilidades",
      "count": 0,
      "note": "string"
    },
    {
      "kind": "breaks",
      "title": "Alianças Rompidas",
      "count": 0,
      "note": "string"
    }
  ],
  "groups": [
    {
      "kind": "dramatic",
      "title": "Mudanças Dramáticas",
      "count": 0,
      "items": []
    },
    {
      "kind": "hostilities",
      "title": "Novas Hostilidades",
      "count": 0,
      "items": []
    },
    {
      "kind": "breaks",
      "title": "Alianças Rompidas",
      "count": 0,
      "items": []
    }
  ]
}
```

Required per-item shape inside each `groups[*].items` array:

```json
{
  "kind": "dramatic" | "hostilities" | "breaks",
  "date": "YYYY-MM-DD",
  "giver": "string",
  "receiver": "string",
  "old_emoji": "string",
  "new_emoji": "string",
  "prior_same_emoji_days": 0,
  "prior_heart_days": 0,
  "other_side_current_emoji": "string|null",
  "other_side_kept_heart": "true|false|null",
  "meta_line": "string",
  "severity_score": "number|null",
  "severity_label": "string|null"
}
```

Severity derivation rules:

- `dramatic.severity_score` uses the existing dramatic jump magnitude already computed by the builder.
- `dramatic.severity_label` is derived from `severity_score`:
  - `alta` for `severity_score >= 1.5`
  - `média` for `1.0 <= severity_score < 1.5`
  - `leve` for `severity_score < 1.0`
- `hostilities.severity_score` is `2.0` when `old_emoji = ❤️`; otherwise `1.0`.
- `hostilities.severity_label` is always `hostilidade`.
- `breaks.severity_score` is `2.0` when the existing break severity is `strong`; otherwise `1.0`.
- `breaks.severity_label` is `grave` for `2.0` and `leve` for `1.0`.

Contract rules:

- `summary` is always emitted in fixed order: `dramatic`, `hostilities`, `breaks`.
- `groups` is always emitted in the same fixed order and always contains exactly three entries, even when one or more groups are empty.
- `hero` is one of the emitted group items, copied with all item fields preserved and enriched with hero-only copy fields.
- `meta_line` is prebuilt by the builder so the renderer does not need card-type-specific sentence logic.
- `from_date` and `to_date` identify the two snapshots being compared.
- `reference_date` must equal `to_date`.
- `link` is fixed to `evolucao.html#pulso` for this change; no new destination page is introduced as part of this spec.
- `source_tag` is derived from `from_date` and `to_date`:
  - use `📅 Ontem → Hoje` only when the two available snapshots are consecutive calendar days and `to_date` is the latest snapshot in the dataset
  - otherwise use `📅 dd/mm → dd/mm`
- `total` must equal `counts.dramatic + counts.hostilities + counts.breaks`.
- each `summary[*].count` must equal the matching value in `counts`.
- each `groups[*].count` must equal `len(groups[*].items)`.
- an event may appear in more than one category when it satisfies multiple category rules; counts are not deduplicated across groups.
- `hero.chips` is always emitted; use `[]` when there are no chips.
- the builder owns all narrative payload strings and the renderer prints them verbatim after escaping:
  - `subtitle`
  - `source_tag`
  - `summary[*].note`
  - `hero.kicker`
  - `hero.title`
  - `hero.body`
  - `hero.meta_line`
  - `hero.stat_value`
  - `hero.stat_label`
  - `hero.chips[*].text`
- the builder only emits participant names (`giver`, `receiver`); the renderer resolves avatars from the existing participant metadata/avatar helpers already used by the index.

## Card structure

### 1. Hero

The hero is a single pair-story surface with:

- date + short kicker
- left and right participant avatars
- the main emoji transition in the center
- a short context line directly under the transition
- a short headline
- one short explanatory sentence
- a compact stat block aligned beside the headline/copy, not floating high on its own
- compact chips only when they add real information

The hero must not read like a mini-article. It should read like a dashboard story.

### 2. Summary strip

Under the hero, show a compact three-part strip:

- `Mudanças Dramáticas`
- `Novas Hostilidades`
- `Alianças Rompidas`

Each segment shows:

- count
- short label
- one tiny supporting note

These are not mini-cards. They are summary indicators and must stay visually secondary to the hero.

### 3. Drill

The drill stays collapsed by default and opens grouped sections in this order:

1. `Mudanças Dramáticas`
2. `Novas Hostilidades`
3. `Alianças Rompidas`

Each group reuses the pair-story row model with avatars on both sides and a center transition.

This retains the current “show me everything” behavior, but consolidates it behind one entry point.

### Group ordering

The renderer should preserve payload order for every `groups[*].items` list. The builder is responsible for pre-sorting those items.

Required sort for `hostilities` and `breaks` groups:

1. `prior_heart_days` descending
2. `other_side_kept_heart` with `true` before `false` before `null`
3. `severity_score` descending, with `null` after any numeric value
4. `giver` alphabetical
5. `receiver` alphabetical

Required sort for `dramatic` groups:

1. `severity_score` descending, with `null` after any numeric value
2. `prior_same_emoji_days` descending
3. `prior_heart_days` descending
4. `giver` alphabetical
5. `receiver` alphabetical

The drill rows must render in that payload order without additional client-side sorting.

## Hero selection

The hero should be chosen from the latest comparison only.

Use deterministic importance-based priority, not raw category counts.

Definitions:

- A `meaningful prior streak of support` means `prior_heart_days >= 3`.
- A dramatic item's `strength` is `severity_score`, sorted descending.

Selection order:

1. Tier A: any `hostilities` or `breaks` item with `other_side_kept_heart = true` and `prior_heart_days >= 3`
2. Tier B: otherwise, any `breaks` item
3. Tier C: otherwise, any `dramatic` item
4. Tier D: otherwise, any remaining `hostilities` item

Duplicate identity:

- Two emitted rows describe the same underlying event when all of these fields match:
  - `date`
  - `giver`
  - `receiver`
  - `old_emoji`
  - `new_emoji`

Hero selection algorithm:

1. Build the union of all emitted row instances from the three groups.
2. Partition those row instances by the duplicate identity key above.
3. For each partition, determine the highest-ranked tier reached by any row in that partition.
4. Inside that selected tier, if multiple row instances from the same partition remain, apply the within-tier duplicate category precedence defined below.
5. The surviving row instance becomes that partition's canonical hero candidate.
6. Rank the canonical hero candidates using the sort keys below.
7. Copy the first ranked canonical hero candidate into `hero`, preserving all item fields from that chosen row instance and adding the hero-only fields.

Sort within each tier:

1. `prior_heart_days` descending
2. `severity_score` descending, with `null` after any numeric value
3. `prior_same_emoji_days` descending
4. `giver` alphabetical
5. `receiver` alphabetical

If the same underlying event is present in multiple groups, duplicate resolution must respect tier order first:

- select the highest-ranked tier reached by any duplicate instance of that event
- if multiple duplicate instances of the same event survive inside that selected tier, use category precedence only inside that tier

Within-tier duplicate category precedence:

- Tier A: `hostilities` before `breaks`
- Tier B: `breaks` only
- Tier C: `dramatic` only
- Tier D: `hostilities` only

This rule only decides the canonical hero candidate for overlapping duplicates. The event may still remain present in multiple groups for counts and drill rendering.

The hero should answer “what is the most meaningful virada today?”, not “which bucket has the most rows?”

## Empty-state and partial-data rules

`Viradas` is strictly a latest-comparison card. It does not fall back to older historical pair events the way `Arquivo do Queridômetro` falls back to archive facts.

`Latest comparison` means the two latest available comparable queridômetro snapshots in the derived dataset, not necessarily the previous calendar day.

A snapshot is `comparable` when:

- it has a valid queridômetro date
- it produces a usable daily matrix for pair comparison
- it can be compared against the same participant-pair universe as the later snapshot after the existing derived-data normalization step

If the immediately previous day is missing, the card still compares the latest snapshot against the nearest earlier available snapshot and exposes that gap through `from_date`, `to_date`, and `source_tag`.

Deterministic emission rules:

- If fewer than two comparable snapshots exist, do not emit a `viradas` card in `highlights.cards`.
- If `counts.dramatic == 0`, `counts.hostilities == 0`, and `counts.breaks == 0`, do not emit a `viradas` card in `highlights.cards`.
- If at least one category has items, emit exactly one `viradas` card.
- `state = "today"` when all three groups have at least one item.
- `state = "partial"` when the card renders but one or two groups are empty.

Deterministic render rules:

- The summary strip always shows all three categories, including zero counts.
- The payload always keeps all three `groups` entries; empty groups use `count = 0` and `items = []`.
- The drill only renders non-empty groups; empty groups stay represented in payload counts but do not create empty open sections in the HTML.
- The hero is selected from the union of all emitted items across the non-empty groups.

Scope rules:

- Only pair changes that belong to the latest queridômetro comparison may feed `Viradas`.
- Historical break rows that are not part of the latest comparison do not belong in this card.
- `Arquivo do Queridômetro` remains the place for historical curiosities and archive-first storytelling.
- Category membership is not exclusive: the same latest-comparison event may be present in multiple groups if it qualifies for each group's rules.

## Context enrichment contract

To make all three categories feel coherent, every item should carry the same contextual fields when available:

- `date`
- `old_emoji`
- `new_emoji`
- `prior_same_emoji_days`
- `prior_heart_days`
- `other_side_current_emoji`
- `other_side_kept_heart`

### Display rule

For all row types, show durability context when available.

Preferred order in row meta:

1. duration
2. opposite-side retention, if meaningful
3. date

Examples:

- `Depois de 6 dias de ❤️ · 02/04`
- `Depois de 13 dias de ❤️ · Chaiany manteve ❤️ · 02/04`
- `Leandro manteve ❤️ · 02/04`

If the previous emoji was not `❤️`, the copy may fall back to:

- `Depois de 4 dias de 🌱 · 02/04`

This should be generated from the actual queridômetro history, not hard-coded per card type.

Nullability rules:

- `prior_same_emoji_days` and `prior_heart_days` are numeric and default to `0`.
- `other_side_current_emoji` may be `null` when the reciprocal snapshot is unavailable.
- `other_side_kept_heart` may be `null` only when `other_side_current_emoji` is `null`; otherwise it must be `true` or `false`.

## Copy rules

### Vocabulary

Prefer user-facing BBB / queridômetro terms:

- `queridômetro`
- `emoji`
- `❤️`
- `manteve`
- `mudou`
- `sequência`
- `virada`

Avoid analyst-like phrasing such as:

- `sinais fortes`
- `retrato seguinte`
- `descompasso`
- `editorial weight`

### Hero style

The hero should use:

- a short headline
- one short context sentence near the transition
- one short explanatory sentence below the headline

Good shape:

- headline: `Ruptura com ❤️ ainda do outro lado`
- transition context: `Gabriela vinha de 9 dias seguidos dando ❤️ para Leandro; no queridômetro seguinte, ele manteve o ❤️ para ela.`
- body: `Entre as viradas do dia, esta pesa mais porque quebra uma sequência longa de ❤️ e vira só de um lado.`

### Row style

Rows should keep the same order and phrasing pattern regardless of category:

1. who changed
2. which emoji changed
3. how long it had been stable before the change
4. whether the other side kept `❤️`, when relevant
5. date last

## Avatar rules

Use participant avatars more aggressively than the current separate cards do.

- Hero: both avatars always visible
- Drill rows: both avatars always visible
- Summary strip: no avatars

Avatars should carry identity load so the text can stay shorter.

## Visual rules

- Match the rendered card width envelope from the real `index`
- Follow `Arquivo do Queridômetro` density, not a feature-section layout
- Keep the right-side stat block aligned with the hero title/copy zone
- Avoid large empty gutters inside the hero
- Keep the drill collapsed by default
- Mobile must stack cleanly without turning the card into a full-page section

## Data migration

The merged card should replace the separate index cards for:

- `dramatic`
- `hostilities`
- `breaks`

Internally, the current builders may continue to compute those source lists, but they must be normalized to the latest comparison before they are merged into the published `type = "viradas"` card.

The old separate cards should stop rendering on `index.qmd` once `Viradas` is in place, and the old separate card payloads should stop being emitted to `index_data.json`.

## Non-goals

- Do not redesign `Arquivo do Queridômetro` as part of this change.
- Do not merge historical Pulso facts into `Viradas`.
- Do not change the underlying queridômetro scoring model.
- Do not redesign unrelated highlight cards.

Follow-up after this feature lands:

- review Pulso avatar use and alignment against the new pair-story lessons from `Viradas`

## Testing

- Add focused regression tests for the new `type = "viradas"` payload before changing production rendering.
- Test that the card is omitted when all three category counts are zero.
- Test that the card renders with `state = "partial"` when only one or two groups are present.
- Test missing-day comparisons, including the explicit `from_date`, `to_date`, and `source_tag` fallback.
- Test the published count invariants: `total`, `counts`, `summary[*].count`, and `groups[*].count`.
- Verify the old three-card render path is removed from `index.qmd`.
- Test hero selection priority with controlled fixtures.
- Test the deterministic tier ordering for `hostilities`, `breaks`, and `dramatic`.
- Test the explicit top-level payload shape for `hero`, `summary`, `counts`, `groups`, and `hero.chips`.
- Test durability context generation for all three categories.
- Test that row meta prefers:
  - duration first
  - opposite-side `❤️` retention second
  - date last
- Test the HTML contract for:
  - compact hero
  - three-part summary strip
  - grouped drill sections
  - avatar presence in hero and rows
- Re-render local `index.qmd` and compare against the actual dashboard footprint, not only standalone mockups.

## Expected implementation surfaces

- `scripts/builders/index_data_builder.py`
- `scripts/index_viz.py`
- `index.qmd`
- `assets/cards.css`
- `tests/test_index_highlights.py`
- `tests/test_index_viz.py`
- `tests/test_index_qmd_contract.py`
- `tests/test_index_render_contract.py`
