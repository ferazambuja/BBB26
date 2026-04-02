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
  "source_tag": "📅 Ontem → Hoje",
  "subtitle": "As principais viradas de um dia para o outro no queridômetro.",
  "reference_date": "YYYY-MM-DD",
  "state": "today" | "partial",
  "total": 0,
  "display_limit": 4,
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
    "other_side_kept_heart": true,
    "meta_line": "string",
    "stat_value": "string",
    "stat_label": "string",
    "chips": []
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
  "other_side_kept_heart": true,
  "meta_line": "string",
  "severity": "number|string|null"
}
```

Contract rules:

- `summary` is always emitted in fixed order: `dramatic`, `hostilities`, `breaks`.
- `groups` is always emitted in the same fixed order.
- `hero` is one of the emitted group items, enriched with hero-only copy fields.
- `meta_line` is prebuilt by the builder so the renderer does not need card-type-specific sentence logic.
- `link` is fixed to `evolucao.html#pulso` for this change; no new destination page is introduced as part of this spec.

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

## Hero selection

The hero should be chosen from the latest comparison only.

Use importance-based priority, not raw category counts:

1. A one-sided rupture or hostility that follows a meaningful prior streak of support
2. Otherwise, the longest streak break
3. Otherwise, the strongest dramatic emoji jump
4. Tie-break by recency and by whether the opposite side still keeps `❤️`

The hero should answer “what is the most meaningful virada today?”, not “which bucket has the most rows?”

## Empty-state and partial-data rules

`Viradas` is strictly a latest-comparison card. It does not fall back to older historical pair events the way `Arquivo do Queridômetro` falls back to archive facts.

Deterministic emission rules:

- If `counts.dramatic == 0`, `counts.hostilities == 0`, and `counts.breaks == 0`, do not emit a `viradas` card in `highlights.cards`.
- If at least one category has items, emit exactly one `viradas` card.
- `state = "today"` when all three groups have at least one item.
- `state = "partial"` when the card renders but one or two groups are empty.

Deterministic render rules:

- The summary strip always shows all three categories, including zero counts.
- The drill only renders non-empty groups; empty groups stay represented in payload counts but do not create empty open sections in the HTML.
- The hero is selected from the union of all emitted items across the non-empty groups.
- If the union is non-empty but the priority ranking ties completely, fall back to the first ranked item in this order: `hostilities`, `breaks`, `dramatic`, preserving that group's item order.

Scope rules:

- Only pair changes that belong to the latest queridômetro comparison may feed `Viradas`.
- Historical break rows that are not part of the latest comparison do not belong in this card.
- `Arquivo do Queridômetro` remains the place for historical curiosities and archive-first storytelling.

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
- Verify the old three-card render path is removed from `index.qmd`.
- Test hero selection priority with controlled fixtures.
- Test the explicit top-level payload shape for `hero`, `summary`, `counts`, and `groups`.
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
