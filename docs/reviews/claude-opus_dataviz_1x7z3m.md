# Data Visualization Review: BBB26 Dashboard

**Reviewer**: Claude Opus 4.5 (Data Visualization Expert)
**Date**: 2026-01-25
**Focus**: Chart types, visual design, effectiveness, and improvements

---

## Executive Summary

The BBB26 dashboard employs a solid foundation of Plotly visualizations with a coherent dark theme. The visualizations effectively communicate social dynamics, but there are opportunities for improvement in chart selection, mobile accessibility, and visual hierarchy. Key recommendations:

1. **Replace the pie chart** with a more effective alternative (donut or waffle)
2. **Simplify the 22x22 heatmap** with progressive disclosure or filtering
3. **Add trend indicators** to static charts for quick comprehension
4. **Improve color accessibility** for colorblind users
5. **Add three new visualizations**: Bump chart, radar profiles, and small multiples

---

## Chart-by-Chart Analysis

### 1. Horizontal Bar Chart (Sentiment Ranking)

**Location**: `index.qmd` - `make_sentiment_ranking()`

**Current Implementation**:
- Horizontal bars sorted by sentiment score
- Color-coded by participant group (Camarote/Pipoca/Veterano)
- Score displayed outside bar with +/- prefix
- Red dashed line at zero

**Assessment**: **Good choice**

Horizontal bar charts are ideal for ranking data with categorical labels. The implementation is solid.

**What I Would Change**:

1. **Add trend arrows**: Show if sentiment is rising/falling compared to yesterday
   ```
   Alberto Cowboy  ████████████ +8.5  ↑
   Jordana         ██████████   +6.0  ↓
   ```

2. **Add micro-sparklines**: Small 7-day trend line next to each bar (Plotly supports this with `add_trace`)

3. **Consider lollipop chart variant**: For cleaner look with many participants
   ```
   Participant ●────────────── +8.5
   ```

4. **Diverging layout**: Since scores can be negative, consider centering bars at zero:
   ```
   Negative ◄────────────────────────► Positive
                    │
   Name A    ██████│
   Name B          │████████
   Name C     █████│
   ```

**Code Improvement**:
```python
# Add trend indicator
yesterday_scores = {...}  # from previous snapshot
for name, score in current_scores.items():
    delta = score - yesterday_scores.get(name, score)
    trend = "↑" if delta > 0.5 else "↓" if delta < -0.5 else "→"
    # Add as annotation or text
```

---

### 2. 22x22 Heatmap (Reaction Matrix)

**Location**: `index.qmd` - `make_cross_table_heatmap()`

**Current Implementation**:
- Full 22x22 matrix with emoji in each cell
- Diverging color scale (red-yellow-green)
- Text template shows emoji
- Hover shows giver -> receiver

**Assessment**: **Problematic at scale**

This is the most information-dense visualization but has significant issues:

**Problems**:
1. **22x22 = 484 cells** is overwhelming
2. **Emoji are tiny** (14px) and hard to distinguish
3. **Mobile unusable** - requires horizontal scroll
4. **No hierarchy** - all relationships shown equally

**Recommended Alternatives**:

**Option A: Filtered View with Tabs**
```
[All] [Show Conflicts Only] [Show Alliances Only] [Participant Focus: ▼]
```
Pre-filter to show only interesting cells (non-heart reactions).

**Option B: Chord Diagram** (for showing flows)
Plotly doesn't have native chord diagrams, but you could use a radial layout with arcs. However, this may be too complex.

**Option C: Adjacency Matrix with Clustering**
Already implemented in `trajetoria.qmd` - consider making this the primary view.

**Option D: Aggregated Summary + Drill-down**
Show summary stats first, then detailed matrix on click.

**Specific Improvements**:

1. **Increase emoji size** to 18px minimum for readability
2. **Add row/column highlighting** on hover
3. **Collapse to first names** (already done, but could truncate further)
4. **Provide a "zoom" interaction** that expands a 5x5 region

**Mobile Alternative**:
```
┌─────────────────────────────┐
│ Select Participant: [▼]     │
├─────────────────────────────┤
│ JORDANA                     │
│ ───────────                 │
│ Gave:  ❤️×12  🐍×5  🌱×3   │
│ Got:   ❤️×15  🐍×2  💼×1   │
│                             │
│ Key Relationships:          │
│ ❤️ Alberto, Ana Paula...    │
│ 🐍 Brigido, Edilson...     │
└─────────────────────────────┘
```

---

### 3. Diverging Bar Chart (Winners/Losers)

**Location**: `mudancas.qmd` - Winners/Losers section

**Current Implementation**:
- Horizontal bars diverging from zero
- Green for positive delta, red for negative
- Score displayed outside

**Assessment**: **Excellent choice**

This is the correct chart type for showing change (delta). The implementation is clean.

**Minor Improvements**:

1. **Add waterfall markers**: Show what contributed to the change
   ```
   Jordana  [+2 from Ana] [+1 from Babu] [-1 from Edilson] = +2.0
   ```

2. **Threshold lines**: Add subtle lines at +/-1.0 to indicate "significant" changes

3. **Sort by absolute value option**: Currently sorted by value, could add option to sort by magnitude of change

---

### 4. Difference Heatmap (Changes Between Days)

**Location**: `mudancas.qmd` - Difference Heatmap section

**Current Implementation**:
- NaN for unchanged cells (shown as blank)
- Transition emoji in cells (e.g., "❤️→🐍")
- Star annotations for dramatic changes
- Color scale for delta magnitude

**Assessment**: **Good, but busy**

The star annotations are clever but add visual noise.

**Improvements**:

1. **Sparse matrix display**: Only show cells that changed (currently done via NaN, but could go further with filtering)

2. **Replace stars with glow effect**: Use marker border color intensity instead of emoji overlay

3. **Add summary row/column**: Totals for each participant
   ```
              A  B  C  D  | Total
         A    -  ❤️ -  - |  +1
         B    -  -  🐍 - |  -1
         C    -  -  -  - |   0
   ```

4. **Animation potential**: If implementing client-side interactivity, animate the transition between states

---

### 5. Sankey Diagram (Reaction Flow)

**Location**: `mudancas.qmd` - Sankey section

**Current Implementation**:
- Left nodes: "Before" reactions
- Right nodes: "After" reactions
- Link colors indicate improvement (green) or deterioration (red)
- Width proportional to count

**Assessment**: **Appropriate but underutilized**

Sankey diagrams excel at showing flow/transition. This implementation is correct but could be enhanced.

**Improvements**:

1. **Consolidate reaction types**: Group into 3 categories instead of 9
   ```
   Positive (❤️) → Mild Negative → Strong Negative
   ```
   This reduces visual complexity.

2. **Add participant filtering**: "Show flows for: [Participant Name ▼]"

3. **Vertical layout option**: May work better on mobile
   ```
   BEFORE
     ↓
   AFTER
   ```

4. **Add counts on links**: Show "42 people changed" on hover (already in hover, but could add as text)

**Alternative: Transition Matrix**
A simpler alternative might be a 3x3 or 4x4 transition matrix:
```
           TO →
        ❤️   Mild  Strong
FROM  ❤️   --   12    5
↓     Mild  8    --    3
      Strong 2    4    --
```

---

### 6. Scatter Plots (Various Correlations)

**Locations**:
- `mudancas.qmd` - "Centro do Drama" (drama involvement)
- `trajetoria.qmd` - "Saldo vs Sentimento" (balance vs sentiment)

**Current Implementation**:
- Bubble chart with participant names as text
- Color by group
- Trend line for correlation

**Assessment**: **Good for correlation analysis**

Scatter plots are appropriate for showing relationships between two continuous variables.

**Improvements**:

1. **Quadrant labels**: Add text annotations for each quadrant
   ```
   HIGH BALANCE          HIGH BALANCE
   LOW SENTIMENT         HIGH SENTIMENT
   (Unpopular Rich)      (Popular Rich)
   ─────────────────┼─────────────────
   LOW BALANCE           LOW BALANCE
   LOW SENTIMENT         HIGH SENTIMENT
   (Struggling)          (Popular Poor)
   ```

2. **Marginal distributions**: Add histograms on axes showing distribution
   ```
   ┌──────────────────────────┐
   │ ▃▅▇▅▂                    │ ← histogram
   ├──────────────────────────┤
   │    ●                     │
   │  ●    ●                  │
   │      ●   ●               │
   │                          │
   ├──┴──┴──┴──┴──┴──┴──┴──┤
   │histogram                 │
   └──────────────────────────┘
   ```

3. **Confidence ellipses**: Add 95% confidence ellipse for each group

4. **Interactive regression**: Allow toggling trend line and showing R-squared prominently

---

### 7. Line Charts (Sentiment Over Time)

**Location**: `trajetoria.qmd` - Sentiment Evolution

**Current Implementation**:
- Multi-series line chart with one line per participant
- Top 3 and bottom 3 visible by default
- Click legend to show/hide
- Zero line reference

**Assessment**: **Correct chart type, but cluttered**

With 22 participants, even with selective visibility, this becomes hard to read.

**Major Improvements**:

1. **Bump Chart (Rank Over Time)**: Instead of absolute values, show rank position
   ```
   Rank
   1  ─────●───────●────●─── Alberto
   2  ───●─────●───────●──── Jordana
   3  ────────●────●──────── Babu
   ...
   22 ●─────────────────────── Brigido
       Day1  Day2  Day3  Day4
   ```
   This is much cleaner for comparing trajectories.

2. **Small Multiples**: One small chart per participant (or per group)
   ```
   ┌────┐ ┌────┐ ┌────┐
   │╱╲  │ │ ╱  │ │╲╱  │
   │  ╲╱│ │╱   │ │    │
   │Alb │ │Jord│ │Babu│
   └────┘ └────┘ └────┘
   ```

3. **Highlight on hover**: Dim all other lines when hovering one

4. **Annotations for events**: Add vertical lines for paredoes, entries, exits
   ```
   │ Aline     │ Pedro
   │ Eliminated│ Quit
   ▼           ▼
   ─────────────────────────
   ```

---

### 8. Network Graph (Relationship Visualization)

**Location**: `trajetoria.qmd` - Grafo de Relacoes

**Current Implementation**:
- Spring layout via NetworkX
- Node size = sentiment score
- Node color = group
- Green edges = alliances (mutual hearts)
- Red dashed edges = rivalries (mutual negative)
- First name labels

**Assessment**: **Computationally expensive, visually cluttered**

Network graphs look impressive but are often hard to interpret with >15 nodes.

**Problems**:
1. **Spring layout is non-deterministic** (seed helps but layout varies)
2. **Edge crossing** makes it hard to trace relationships
3. **Node overlap** at this density
4. **CPU intensive** for rendering

**Improvements**:

1. **Force-directed with collision detection**: Ensure nodes don't overlap

2. **Edge bundling**: Group edges going similar directions

3. **Radial layout by group**: Place Camarote, Pipoca, Veterano in separate arcs
   ```
        Camarote
        ●  ●  ●
      ●        ●
   Pipoca    Veterano
   ●    ●    ●    ●
   ●    ●    ●    ●
   ```

4. **Filter by relationship type**: Toggle between alliance-only, rivalry-only, or both

5. **Consider Chord Diagram alternative**: Shows flows between groups more clearly

**Mobile Alternative**: Replace with a simple adjacency list
```
ALLIANCES:
• Alberto <-> Jordana, Ana Paula, Babu
• Jordana <-> Alberto, Sol Vega

RIVALRIES:
• Ana Paula <-> Brigido (since Day 1)
```

---

### 9. Stacked Bar Charts (Various Breakdowns)

**Locations**:
- `mudancas.qmd` - Volatility chart (melhora/piora/lateral)
- `trajetoria.qmd` - Reaction changes between days
- `trajetoria.qmd` - Negative givers profile

**Current Implementation**:
- Horizontal stacked bars
- Green for positive, red for negative, gray for neutral
- Sorted by total or by specific metric

**Assessment**: **Good, but consider alternatives for some uses**

Stacked bars are appropriate for showing composition. However:

**Improvement for Volatility**:
- Consider **diverging stacked bar** to emphasize direction:
  ```
  Pioras ←───────────┼───────────→ Melhoras
  Name A       ████████│████████████
  Name B           ████│██████████████████
  ```

**Improvement for Negative Givers**:
- Add **percentage labels** instead of just counts
- Consider **100% stacked bar** to normalize by total reactions given

---

### 10. Pie Charts (Vote Coherence)

**Location**: `paredao.qmd` - "Votaram no que mais detestam?"

**Current Implementation**:
- Standard pie chart showing coherence categories
- Likely segments: "Voted for enemy", "Voted for friend", "Mixed"

**Assessment**: **Avoid pie charts**

Pie charts are famously hard to read accurately. Humans struggle to compare angles.

**Recommended Alternatives**:

**Option A: Waffle Chart (Plotly approximation)**
```
■ ■ ■ ■ ■ ■ ■ ■ ■ ■  = 10 votes
■ ■ ■ ■ ■ ■ ■ □ □ □
■ = Coherent (voted for enemy)
□ = Incoherent (voted for friend)

Coherence: 70%
```

**Option B: Donut Chart with Center Stat**
If you must use a circular chart, make it a donut with the key number in the center:
```
    ╭───────╮
   ╱  70%   ╲
  │ coherent │
   ╲         ╱
    ╰───────╯
```

**Option C: Horizontal Bar**
```
Coherent   ████████████████████ 70%
Incoherent ██████               30%
```

This is cleaner and easier to compare.

---

## Three New Visualizations to Add

### New Viz 1: Bump Chart (Rank Evolution)

**Purpose**: Show how participant rankings change over time without the clutter of 22 intersecting lines.

**ASCII Mockup**:
```
SENTIMENT RANK OVER TIME

Rank │
  1  │ ──●────●──────●───●─── Alberto (currently #1)
  2  │ ●───────●──●──────────  Jordana (currently #4)
  3  │ ────────────●────●──── Sol Vega (currently #2)
  4  │ ───●──●───────────●─── Babu (currently #3)
  .  │
  .  │ (show all 22 with highlight on hover)
  .  │
 22  │ ●────●────●────●────●─ Brigido (currently #22)
     └──────────────────────────
       Day1  Day5  Day10  Today
```

**Why This Works**:
- No lines cross unless ranks change
- Immediately shows trajectory (rising/falling)
- Compact representation of 22 participants

**Plotly Implementation**:
```python
# Pseudo-code
fig = go.Figure()
for participant in ranked_data:
    fig.add_trace(go.Scatter(
        x=dates,
        y=participant['ranks'],  # 1, 2, 3... instead of scores
        mode='lines+markers',
        name=participant['name'],
        line=dict(width=2),
        marker=dict(size=8)
    ))
fig.update_yaxes(autorange='reversed')  # Rank 1 at top
```

---

### New Viz 2: Radar Chart (Participant Profiles)

**Purpose**: Show multi-dimensional profile of a single participant at a glance.

**ASCII Mockup**:
```
        JORDANA - Profile

        Sentiment Score
              ▲
             ╱ ╲
            ╱   ╲
   Allies  ●─────● Enemies
          ╱       ╲
         ╱         ╲
        ●───────────●
    Balance      Volatility

    Compared to house average (dashed)
```

**Metrics to Include**:
1. Sentiment Score (normalized 0-100)
2. Number of Allies (mutual hearts)
3. Number of Enemies (mutual negative)
4. Volatility (opinion changes)
5. Balance (Estalecas)
6. Vulnerability (hearts to enemies)

**Plotly Implementation**:
```python
fig = go.Figure()
fig.add_trace(go.Scatterpolar(
    r=[sentiment, allies, enemies, volatility, balance, vulnerability],
    theta=['Sentiment', 'Allies', 'Enemies', 'Volatility', 'Balance', 'Vulnerability'],
    fill='toself',
    name='Jordana'
))
fig.add_trace(go.Scatterpolar(
    r=[avg_sentiment, avg_allies, ...],
    theta=same_categories,
    line=dict(dash='dash'),
    name='House Average'
))
```

**Use Case**: Add to each participant's profile card in the "Perfis Individuais" section.

---

### New Viz 3: Small Multiples Heatmap (Per-Participant View)

**Purpose**: Replace the overwhelming 22x22 heatmap with digestible individual views.

**ASCII Mockup**:
```
REACTIONS AT A GLANCE (sorted by sentiment)

┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   ALBERTO    │ │   JORDANA    │ │   SOL VEGA   │
│ ❤️: 17  🐍: 2│ │ ❤️: 15  🐍: 4│ │ ❤️: 14  🐍: 3│
│ Got/Gave Bar │ │ Got/Gave Bar │ │ Got/Gave Bar │
│ ████████░░░░ │ │ ██████░░░░░░ │ │ ████████░░░░ │
│ Trend: ↑     │ │ Trend: ↓     │ │ Trend: →     │
└──────────────┘ └──────────────┘ └──────────────┘

┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│     BABU     │ │   EDILSON    │ │   BRIGIDO    │
│ ❤️: 13  🐍: 5│ │ ❤️: 10  🐍: 8│ │ ❤️: 8  🐍: 12│
│ ██████░░░░░░ │ │ ████░░░░░░░░ │ │ ██░░░░░░░░░░ │
│ Trend: ↑     │ │ Trend: ↓     │ │ Trend: ↓     │
└──────────────┘ └──────────────┘ └──────────────┘
```

**Benefits**:
- Each card is self-contained and readable
- Works on mobile (cards stack vertically)
- Quick visual scanning
- Click to expand for full details

**Plotly Implementation**:
```python
from plotly.subplots import make_subplots

fig = make_subplots(
    rows=4, cols=6,  # 24 slots for 22 participants
    subplot_titles=[p['name'] for p in participants],
    specs=[[{'type': 'indicator'}] * 6] * 4
)

for i, p in enumerate(participants):
    row = i // 6 + 1
    col = i % 6 + 1
    fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=p['sentiment'],
        delta={'reference': p['yesterday_sentiment']},
        gauge={'axis': {'range': [-21, 21]}},
    ), row=row, col=col)
```

---

## Chart Types: Overuse and Misuse

### Overused: Horizontal Bar Charts

The dashboard uses horizontal bar charts for:
- Sentiment ranking
- Volatility
- Hostility counts
- Negative givers
- Alliance/rivalry persistence

While appropriate in most cases, the visual monotony reduces engagement.

**Mitigation**: Vary the visual style:
- Use lollipop charts for some
- Use diverging bars where applicable
- Add icons/avatars to differentiate

### Misused: Pie Chart

As noted above, the pie chart for vote coherence should be replaced.

### Underused: Area Charts

For cumulative metrics over time (total reactions, total hostilities), area charts would show accumulation better than line charts.

### Missing: Bullet Charts

For showing a metric against a target/benchmark:
```
SENTIMENT
Target ├───────────────┤
Actual ├════════│      │
       0       10     15
```

---

## Color Scheme Recommendations

### Current Scheme

- Background: #303030 (dark gray)
- Paper: #303030
- Grid: #444444
- Text: #fff (white)
- Group colors:
  - Camarote: #E6194B (red)
  - Veterano: #3CB44B (green)
  - Pipoca: #4363D8 (blue)
- Sentiment scale: Red-Yellow-Green diverging

### Issues

1. **Red-Green colorblind problem**: The sentiment scale and group colors use red/green extensively. ~8% of males are red-green colorblind.

2. **Low contrast on some elements**: Gray (#888) on dark background is hard to read.

3. **Emoji rendering varies**: Some devices render emoji differently, affecting the heatmap.

### Recommendations

**1. Colorblind-safe palette for groups**:
```python
GROUP_COLORS_ACCESSIBLE = {
    'Camarote': '#E69F00',  # Orange (instead of red)
    'Veterano': '#56B4E9',  # Sky blue (instead of green)
    'Pipoca': '#009E73',    # Teal (instead of blue)
}
```

**2. Colorblind-safe diverging scale**:
```python
# Blue-White-Orange instead of Red-Yellow-Green
colorscale=[
    [0, '#d73027'],      # Keep red for strong negative
    [0.25, '#f46d43'],   # Orange
    [0.5, '#ffffbf'],    # Yellow/white
    [0.75, '#74add1'],   # Light blue
    [1.0, '#4575b4'],    # Blue for positive
]
```
This maintains intuition (warm = bad, cool = good) while being colorblind-safe.

**3. Add pattern/texture option**:
For critical distinctions, add hatching patterns:
```python
marker=dict(
    pattern=dict(shape="/") if is_negative else dict(shape="")
)
```

**4. Increase text contrast**:
Change gray text from #888 to #aaa or #bbb.

---

## Mobile-Friendly Alternatives

### Problem Areas

1. **22x22 Heatmap**: Requires scrolling in both directions
2. **Wide bar charts**: Labels get cut off
3. **Network graph**: Too dense to navigate
4. **Legend**: Often overlaps chart on small screens

### Solutions

**1. Responsive chart heights**:
```python
def responsive_height(base, n_items, min_height=300, max_height=800):
    height = base + n_items * 25
    return max(min_height, min(max_height, height))
```

**2. Collapsible sections**:
Use Quarto's `{.callout collapse="true"}` for detailed charts, showing summaries by default.

**3. Card-based layout on mobile**:
Replace complex charts with summary cards that expand on tap.

**4. Legend position**:
```python
fig.update_layout(
    legend=dict(
        orientation='h',
        yanchor='top',
        y=-0.1,  # Below chart on mobile
        xanchor='center',
        x=0.5
    )
)
```

**5. Swap chart types on mobile**:
- Replace heatmap with filterable list
- Replace network graph with adjacency list
- Replace stacked bars with simple percentage text

---

## Accessibility Improvements

### Current Gaps

1. **No alt text** for Plotly charts (Plotly generates SVG/canvas, not img tags)
2. **Color-only encoding** for sentiment (red/green)
3. **Small emoji** (14px) hard for low vision users
4. **No keyboard navigation** for interactive elements

### Recommendations

**1. Descriptive titles and subtitles**:
```python
fig.update_layout(
    title="Sentiment Ranking - Higher is Better<br><sub>22 participants, Jan 25 2026</sub>"
)
```

**2. Add ARIA descriptions via HTML wrapper**:
```html
<div role="img" aria-label="Bar chart showing Alberto Cowboy leading with +8.5 sentiment score, followed by Jordana at +6.0...">
  {{ fig | safe }}
</div>
```

**3. Provide text alternatives**:
Below each chart, add a collapsible text summary:
```markdown
::: {.callout-note collapse="true" title="Text Summary"}
Top 3: Alberto Cowboy (+8.5), Jordana (+6.0), Sol Vega (+5.5)
Bottom 3: Brigido (-8.0), Ana Paula (-5.5), Edilson (-4.0)
:::
```

**4. Increase minimum text size**:
- Axis labels: 12px minimum
- Tick labels: 11px minimum
- Emoji: 16px minimum (preferably 18px)

**5. Shape encoding for sentiment**:
Add shapes alongside colors:
- Positive: Circle marker
- Mild negative: Square marker
- Strong negative: Diamond marker

```python
marker=dict(
    symbol='circle' if sentiment > 0 else 'square' if sentiment > -0.5 else 'diamond'
)
```

**6. Screen reader considerations**:
Add a "Download data" option that exports the underlying data as CSV, which screen reader users can navigate.

---

## Implementation Priority

| Improvement | Impact | Effort | Priority |
|-------------|--------|--------|----------|
| Replace pie chart | High | Low | P0 |
| Add trend arrows to rankings | High | Low | P0 |
| Colorblind-safe palette | High | Medium | P1 |
| Mobile card layout | High | High | P1 |
| Bump chart for evolution | Medium | Medium | P1 |
| Text summaries for accessibility | Medium | Low | P1 |
| Radar chart profiles | Medium | Medium | P2 |
| Small multiples heatmap | Medium | High | P2 |
| Sankey simplification | Low | Low | P2 |
| Network graph radial layout | Low | High | P3 |

---

## Conclusion

The BBB26 dashboard demonstrates thoughtful visualization choices overall. The dark theme is well-executed, and the chart types are generally appropriate for the data. The main opportunities lie in:

1. **Reducing cognitive load**: The 22x22 heatmap and 22-line time series are overwhelming; progressive disclosure and filtering would help.

2. **Improving accessibility**: The current red-green color scheme and lack of text alternatives exclude significant user populations.

3. **Mobile optimization**: The data-dense visualizations need alternative representations for small screens.

4. **Adding context**: Trend indicators, benchmarks, and annotations would help users interpret the data faster.

The three proposed new visualizations (bump chart, radar profiles, small multiples) would add significant value while remaining implementable in Plotly without external dependencies.

---

*Review generated by Claude Opus 4.5 (claude-opus-4-5-20251101)*
*Focus area: Data Visualization and Chart Design*
