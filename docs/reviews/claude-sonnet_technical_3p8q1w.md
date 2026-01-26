# BBB26 Dashboard Technical Review: Interactivity, Deployment, Data Architecture

**Reviewer**: Claude Sonnet 4.5
**Date**: 2026-01-25
**Focus Areas**: Sections 7-11 (Interactivity, Deployment, Cartola BBB, Data Storage, Mobile/Accessibility)
**Review Type**: Technical Implementation

---

## Executive Summary

**Key findings:**

1. **Interactivity is currently unnecessary** — Pre-rendered static pages serve the use case well; pursue only if user demand emerges
2. **GitHub Pages + Actions is sufficient** with minor hardening needed for production readiness
3. **Current JSON-per-snapshot architecture scales well to 90 days** (~32MB, manageable); pre-computation would optimize render times
4. **Cartola BBB page should be manual-heavy** with semi-automated point calculations from existing API data
5. **Mobile experience needs work** — 22×22 heatmaps are unreadable on phones; recommend responsive alternatives

**Risk level**: Low. The current technical stack is sound. Main concerns are render time growth (addressable via pre-computation) and mobile UX (solvable with CSS/alternative views).

---

## 8. Interactivity Assessment

### Current State

The dashboard is **fully pre-rendered static HTML** with:
- No user-controlled date selection
- "O Que Mudou" always compares yesterday → today (hardcoded)
- All analysis baked at render time
- Plotly charts provide built-in zoom/pan/hover (sufficient interactivity for exploration)

### Is Interactivity Essential?

**No.** Here's why:

| Use Case | Current Solution | Interactive Alternative | Verdict |
|----------|------------------|------------------------|----------|
| "What changed today?" | Dedicated page (mudancas.qmd) | Date pickers to compare any two dates | Static is sufficient |
| "Show me Jan 18" | User scrolls to trajetoria.qmd timeline charts | Date selector that reloads page | Not worth the complexity |
| "Filter by group" | Separate group favoritism charts | Toggle Pipoca/Camarote/Veterano | Nice-to-have, not essential |
| "Focus on one participant" | Individual profile cards (accordion) | Click participant → deep dive modal | Static cards work well |
| "Compare two arbitrary dates" | Only yesterday vs today available | Full date range picker | **This is the only compelling case** |

**Conclusion**: Interactivity is **nice-to-have, not essential** at current scale (12 days of data, 22 participants).

### When Would Interactivity Become Essential?

After **~30+ days of data**:
- Timeline charts become cluttered with 30+ lines
- Users want to isolate specific participants or date ranges
- Comparing any two dates (not just yesterday→today) becomes valuable

**Recommendation**: **Don't implement interactivity now.** Wait until:
1. Users request it (gather feedback after launch)
2. You have 30+ days of data and can validate the need
3. You have capacity to maintain a more complex system

### If You Do Add Interactivity Later: Recommended Approach

**Option 1: Observable JS (Client-Side Only) — RECOMMENDED**

**Pros:**
- No server required (stays on GitHub Pages)
- Runs entirely in browser
- Data embedded in HTML or fetched from JSON files
- Quarto has built-in support: https://quarto.org/docs/interactive/ojs/

**Cons:**
- Data must be pre-loaded (all snapshots embedded = larger page size)
- Limited to what JavaScript can do (no heavy computation)
- Learning curve for Observable syntax

**Implementation sketch:**
```javascript
// In a .qmd file with {ojs} blocks
viewof selectedDate1 = Inputs.date({label: "Compare from:", value: "2026-01-13"})
viewof selectedDate2 = Inputs.date({label: "To:", value: "2026-01-25"})

// Filter Python-computed data
filteredChanges = changes.filter(d => d.date === selectedDate2)

// Render with Observable Plot or D3
Plot.plot({
  marks: [
    Plot.barY(filteredChanges, {x: "name", y: "sentiment_delta", fill: "group"})
  ]
})
```

**Cost:** ~3-4 hours to convert one page (mudancas.qmd) to Observable

---

**Option 2: Pre-Render Multiple Comparison Pages**

Create static pages for common comparisons:
- `mudancas.qmd` → yesterday vs today (current)
- `mudancas_weekly.qmd` → 7 days ago vs today
- `mudancas_full.qmd` → first snapshot vs today

Use tabsets in Quarto to organize:
```markdown
::: {.panel-tabset}
## Ontem → Hoje
[Current mudancas content]

## Última Semana
[7-day comparison]

## Desde o Início
[Full timeline comparison]
:::
```

**Pros:**
- Zero new dependencies
- Works on static hosting
- Fast page loads (pre-rendered)

**Cons:**
- Not flexible (fixed comparisons only)
- More pages to maintain

**Cost:** ~1-2 hours per additional comparison view

---

**Option 3: Shiny for Python (Server-Side) — NOT RECOMMENDED**

**Why not:**
- Requires hosting on shinyapps.io (free tier: 5 apps, 25 hours/month)
- Adds server maintenance burden
- Overkill for simple date selection
- Breaks the "free static hosting" constraint

**Only consider if:** You want advanced features like "simulate a paredão" or "predict next elimination" that require heavy computation.

---

### Specific Interactive Features Worth Implementing (If You Go This Route)

If you decide to add interactivity via Observable JS:

1. **Date range selector for timeline charts** (trajetoria.qmd)
   - Zoom into Jan 13-20 vs full timeline
   - Toggle participant visibility (show/hide lines)
   - **Impact:** High — makes evolution charts readable at scale

2. **Participant filter on heatmaps** (index.qmd)
   - Select 5-10 participants to focus on
   - Reduces 22×22 matrix to manageable size
   - **Impact:** High — solves mobile readability

3. **Group toggle on ranking** (index.qmd)
   - Show only Pipoca, only Camarote, only Veterano
   - **Impact:** Medium — nice but not essential

4. **Arbitrary date comparison** (mudancas.qmd)
   - Two date pickers → compare any snapshots
   - **Impact:** Medium — valuable after 30+ days

**Priority order:** (1) Timeline zoom/filter > (2) Heatmap participant filter > (4) Date comparison > (3) Group toggle

---

### Trade-offs Summary

| Aspect | Static (Current) | Observable JS | Shiny Server |
|--------|------------------|---------------|--------------|
| **Hosting** | GitHub Pages (free) | GitHub Pages (free) | shinyapps.io (25h/mo free) |
| **Complexity** | Low | Medium | High |
| **Page Load** | Fast (~500KB HTML) | Medium (~2MB with data) | Fast (server-rendered) |
| **Flexibility** | Pre-defined views only | High (client-side filters) | Unlimited (server compute) |
| **Maintenance** | Low | Medium | High |
| **User Experience** | Click → instant display | Click → instant re-render | Click → server round-trip |
| **Offline Use** | Works offline once loaded | Works offline once loaded | Requires internet |

**Verdict:** Static is best for now. Observable JS is the right next step if user demand emerges.

---

## 9. Deployment & Robustness Review

### Current Architecture

```
GitHub Actions (cron: 4x daily)
  ↓
fetch_data.py → Only saves if hash changed
  ↓
quarto render → 5 pages × ~500KB each
  ↓
GitHub Pages Deploy
```

**Is This Sufficient?** **Yes**, with minor improvements.

---

### Strengths

✅ **Hash-based deduplication** — Won't spam repo with duplicate snapshots
✅ **Multiple daily captures** — Catches reactions (12h BRT), balance changes (any time), roles (post-episode)
✅ **Metadata tracking** — Records `change_types` (reactions, balance, roles, elimination)
✅ **Atomic commits** — Data changes committed separately from renders
✅ **Idempotent fetching** — Safe to re-run anytime

---

### Weaknesses & Recommended Fixes

#### 1. **No Error Notification**

**Problem:** If GitHub Actions fails (API down, render error), nobody knows until users report stale data.

**Fix:** Add failure notifications to workflow.

```yaml
# Add to .github/workflows/daily-update.yml
jobs:
  update-and-publish:
    steps:
      # ... existing steps ...

      - name: Notify on failure
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: `[AUTO] Dashboard update failed - ${new Date().toISOString().split('T')[0]}`,
              body: `Workflow run failed: ${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`,
              labels: ['automated', 'bug']
            })
```

**Alternative:** Use a monitoring service like UptimeRobot (free tier) to ping the site and alert via email if down.

---

#### 2. **No Graceful Degradation for API Failures**

**Problem:** If the GloboPlay API returns 500 or malformed JSON, `fetch_data.py` will crash and the workflow fails.

**Fix:** Add retry logic and fallback behavior.

```python
# In scripts/fetch_data.py
import time

def fetch_with_retry(url, max_retries=3, backoff=5):
    """Fetch with exponential backoff."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Validate basic structure
            if not isinstance(data, list) or len(data) == 0:
                raise ValueError(f"Invalid data structure: {type(data)}")

            return data
        except (requests.RequestException, ValueError) as e:
            if attempt == max_retries - 1:
                print(f"ERROR: Failed after {max_retries} attempts: {e}")
                return None
            print(f"Attempt {attempt+1} failed: {e}. Retrying in {backoff}s...")
            time.sleep(backoff * (2 ** attempt))
    return None
```

Then in `fetch_and_save()`:
```python
new_data = fetch_with_retry(API_URL)
if new_data is None:
    print("CRITICAL: Could not fetch data. Using latest snapshot for render.")
    return str(latest_file), False  # Don't fail, just skip this update
```

**Impact:** Prevents one API hiccup from breaking the entire workflow.

---

#### 3. **Render Time Will Grow**

**Current:** 2-3 minutes for 5 pages with 15 snapshots
**Projected (Day 90):** ~8-12 minutes for 5 pages with 120 snapshots

**Problem:** GitHub Actions free tier has 2000 minutes/month. At 12 min/render × 4 runs/day × 30 days = **1440 minutes/month** (within limit but tight).

**Fix Options:**

**A. Incremental Rendering (Quarto built-in)**

Only re-render pages that changed.

```yaml
# In .github/workflows/daily-update.yml
- name: Render Quarto site
  run: quarto render --execute-daemon --execute-daemon-restart
```

Quarto's freeze feature caches unchanged computations: https://quarto.org/docs/projects/code-execution.html#freeze

**Impact:** Reduces render time by ~50% when only data changed (not code).

**B. Optimize Data Loading**

Currently each `.qmd` loads all snapshots from scratch. Pre-compute daily metrics.

```python
# scripts/precompute_metrics.py (run before quarto render)
import json
from pathlib import Path

# Load all snapshots once
snapshots = load_all_snapshots()

# Compute daily metrics
daily_metrics = {
    "dates": [s['date'] for s in snapshots],
    "sentiment_scores": {p['name']: [calc_sentiment(p) for s in snapshots for p in s['participants']] for ...},
    "reaction_counts": {...},
    # etc.
}

# Save to data/daily_metrics.json
Path("data/daily_metrics.json").write_text(json.dumps(daily_metrics, indent=2))
```

Then in `.qmd` files:
```python
# Fast: load pre-computed metrics (5KB) instead of 15 snapshots (3.4MB)
metrics = json.loads(Path("data/daily_metrics.json").read_text())
```

**Impact:** Cuts render time by ~70% (data loading is the bottleneck).

**Recommendation:** Implement option B first (easy win), then A if still needed.

---

#### 4. **No Stale Data Warning for Users**

**Problem:** If GitHub Actions fails silently, users see yesterday's data but think it's current.

**Fix:** Add "Last updated" timestamp to each page.

```python
# In index.qmd setup cell
last_fetch = snapshots[-1]['metadata'].get('captured_at', 'Unknown')
last_fetch_formatted = pd.to_datetime(last_fetch).strftime('%d/%m/%Y %H:%M BRT') if last_fetch != 'Unknown' else 'Unknown'
```

```markdown
::: {.callout-note}
**Última atualização:** {python} last_fetch_formatted
:::
```

Show a warning if data is >24h old:
```python
from datetime import datetime, timedelta

last_update = pd.to_datetime(snapshots[-1]['metadata'].get('captured_at'))
if datetime.now() - last_update > timedelta(hours=24):
    # Show alert callout
```

**Impact:** Users know when data is stale.

---

#### 5. **Git Repository Size Management**

**Current:** 3.4MB for 15 snapshots
**Projected (Day 90):** ~32MB for 120 snapshots

**Is this a problem?** No. 32MB is well within GitHub's limits (repositories can be GBs). Git compresses JSON well.

**Optional optimization:** Use Git LFS for snapshots.

```bash
# .gitattributes
data/snapshots/*.json filter=lfs diff=lfs merge=lfs -text
```

**When to do this:** Only if repo exceeds 100MB or clone times become slow. Not needed now.

---

### Alternative Hosting Options (Not Recommended)

| Platform | Pros | Cons | Verdict |
|----------|------|------|---------|
| **Vercel** | Fast CDN, auto-deploys | Free tier: 100GB bandwidth/mo | Overkill for static site |
| **Netlify** | Generous free tier | Same as Vercel | No advantage over GitHub Pages |
| **Cloudflare Pages** | Unlimited bandwidth | More complex setup | Unnecessary |
| **Shinyapps.io** | Interactive dashboards | 25h/month limit, server needed | Wait for user demand |

**Verdict:** Stay on GitHub Pages. It's free, simple, and sufficient.

---

### Recommended Safeguards Summary

| Priority | Safeguard | Effort | Impact |
|----------|-----------|--------|--------|
| **HIGH** | Add retry logic to API fetcher | 30 min | Prevents failures |
| **HIGH** | Add "Last updated" timestamp to pages | 15 min | User trust |
| **MEDIUM** | Add failure notifications (GitHub Issues) | 20 min | Faster debugging |
| **MEDIUM** | Pre-compute daily metrics | 2 hours | 70% faster renders |
| **LOW** | Enable Quarto freeze/incremental | 10 min | 50% faster renders |
| **LOW** | Add stale data warning | 30 min | User awareness |

**Total effort for HIGH priority:** ~45 minutes. Do these first.

---

### Performance Concerns at 90+ Days

**Render time projection:**

| Days | Snapshots | Current Approach | With Pre-Computation |
|------|-----------|------------------|---------------------|
| 12 | 15 | 2-3 min | 1 min |
| 30 | 40 | 5-7 min | 2 min |
| 60 | 80 | 10-14 min | 4 min |
| 90 | 120 | 15-20 min | 6 min |

GitHub Actions timeout: 6 hours (default). No risk of hitting it.

**Page load time for users:**

Currently each page is ~500KB HTML. With 120 snapshots embedded in charts:
- Worst case: 2-3MB per page (still acceptable on 4G)
- Plotly charts lazy-load (only render visible charts)

**Recommendation:** Monitor render times. If they exceed 10 minutes, implement pre-computation.

---

## 10. Cartola BBB Page Design

### Context

Cartola BBB is a fantasy game where viewers pick participants and earn points based on game events. The official point system is fixed (Líder = +80, Eliminado = -20, etc.).

### Target Audience

| Audience Type | What They Want | Page Requirements |
|---------------|----------------|-------------------|
| **Casual players** | "Who's scoring well?" | Weekly leaderboard, top performers |
| **Serious players** | "Who to pick next week?" | Trend analysis, VIP probability, point projections |
| **Post-mortem** | "How did my team do?" | Historical weekly scores, event breakdown |

Most users are **casual players** checking weekly standings.

---

### What Can Be Auto-Calculated vs Manual

| Data Point | Source | Auto/Manual | Notes |
|------------|--------|-------------|-------|
| **Líder** | API (`roles`) | ✅ Auto | Check for "Líder" role |
| **Anjo** | API (`roles`) | ✅ Auto | Check for "Anjo" role |
| **Monstro** | API (`roles`) | ✅ Auto | Check for "Monstro" role |
| **Paredão** | API (`roles`) | ✅ Auto | Check for "Paredão" role |
| **VIP** | API (`memberOf`) | ✅ Auto | Check if memberOf == "VIP" |
| **Eliminated** | API (participant disappears) | ✅ Semi-auto | Track participant count changes |
| **Não eliminado no paredão** | API + manual | ⚠️ Semi | API says Paredão role, manual says who was eliminated |
| **Salvo do paredão** | Manual (`paredoes` data) | ❌ Manual | Bate e Volta info |
| **Não recebeu votos da casa** | Manual (`votos_casa`) | ✅ Auto | Count votes in paredoes data |
| **Big Fone** | Manual events | ❌ Manual | Not in API |
| **Quarto Secreto** | Manual events | ❌ Manual | Not in API |
| **Imunizado** | Manual events | ❌ Manual | Not in API |
| **Desistente** | Manual events | ❌ Manual | Track manually |

**Auto coverage:** ~60% of points can be auto-calculated from existing data
**Manual effort:** Track ~5-8 events per week (Big Fone, immunity, Bate e Volta results)

---

### Proposed Page Structure

**File:** `cartola.qmd` (add to `_quarto.yml`)

**Section Order:**

```markdown
---
title: "📊 Cartola BBB 26"
---

## 🏆 Ranking Semanal (current week)
- Top 10 scorers this week
- Bar chart: points by participant
- Grouped by event type (Líder, Anjo, VIP, Paredão avoided, etc.)

## 📈 Pontuação Acumulada (season total)
- Cumulative line chart over time
- Filter: Top 10 / All participants / Custom selection
- Shows who's leading overall

## 📅 Pontos por Semana (weekly breakdown)
- Heatmap: participants (rows) × weeks (cols) → point value
- Color scale: red (negative) → green (positive)
- Click a cell → see event details

## 🎯 Melhores Apostas (strategic insights)
- Who consistently scores high?
- Who's in VIP most often? (VIP = +5/week)
- Líder/Anjo probability (based on history)

## 📋 Tabela Completa (full data)
- Sortable table with all participants
- Columns: Name, Week 1, Week 2, ..., Total
- Expandable rows → event details

## 🔍 Eventos da Semana (event log)
- List of all point-generating events this week
- Format: "Day X: [Event] → [Participant] → +Y points"

## ℹ️ Como Funciona (rules reference)
- Table of point values (collapsible)
- Link to official Cartola BBB rules
```

---

### Proposed Visualizations

#### 1. Weekly Leaderboard (Bar Chart)

```python
# Horizontal bar chart, sorted by points
fig = px.bar(
    weekly_scores,
    x='points', y='name', color='group',
    orientation='h',
    title=f'Pontuação - Semana {current_week}',
    color_discrete_map=GROUP_COLORS
)
```

**Why:** Quick scan of who's winning this week.

---

#### 2. Cumulative Points Timeline (Line Chart)

```python
# Line chart with cumulative points over time
fig = px.line(
    cumulative_df,
    x='week', y='cumulative_points', color='name',
    title='Pontuação Acumulada'
)
```

**Why:** Shows momentum (who's rising/falling).

---

#### 3. Weekly Heatmap (Participant × Week)

```python
# Heatmap showing points per participant per week
pivot = points_df.pivot(index='name', columns='week', values='points')
fig = px.imshow(
    pivot,
    color_continuous_scale='RdYlGn',
    color_continuous_midpoint=0,
    title='Pontos por Semana'
)
```

**Why:** Easy to spot consistent performers vs volatile players.

---

#### 4. Event Breakdown (Stacked Bar)

```python
# Stacked bar showing point sources
fig = px.bar(
    event_breakdown,
    x='name', y='points', color='event_type',
    title='Origem dos Pontos',
    barmode='stack'
)
```

**Why:** Shows why someone scored high (lots of VIP weeks vs one Líder).

---

#### 5. "Best Picks" Cards (Value Boxes)

```python
# Quarto value boxes
::: {.panel-tabset}
## Mais Pontos
- **{python} top_scorer** ({python} top_scorer_points pts)

## Mais Consistente
- **{python} most_consistent** (média {python} avg_points pts/semana)

## Melhor Custo-Benefício
- **{python} best_value** (pontos/cartoleta)
:::
```

**Why:** Helps casual players make quick picks.

---

### Data Structure in `manual_events.json`

Extend the existing structure:

```json
{
  "cartola_weekly": [
    {
      "week": 1,
      "start_date": "2026-01-13",
      "end_date": "2026-01-19",
      "events": [
        {"participant": "Alberto Cowboy", "event": "Líder", "points": 80},
        {"participant": "Leandro", "event": "Paredão", "points": -15},
        {"participant": "Leandro", "event": "Não eliminado no paredão", "points": 20},
        {"participant": "Aline Campos", "event": "Eliminada", "points": -20},
        {"participant": "Henri Castelli", "event": "Desistente", "points": -30}
      ],
      "auto_calculated": ["Líder", "Anjo", "Monstro", "VIP", "Paredão"],
      "manual_added": ["Big Fone", "Quarto Secreto", "Salvo do paredão"]
    },
    {
      "week": 2,
      "start_date": "2026-01-20",
      "end_date": "2026-01-26",
      "events": [...]
    }
  ]
}
```

---

### Semi-Automated Point Calculation Script

```python
# scripts/calculate_cartola_points.py

def calculate_week_points(week_number):
    """Auto-calculate points from API + manual data."""

    # Get snapshots for the week
    week_snapshots = get_snapshots_for_week(week_number)

    points = defaultdict(int)
    events = []

    for snapshot in week_snapshots:
        for participant in snapshot['participants']:
            name = participant['name']
            roles = get_roles(participant)

            # Auto: Líder
            if 'Líder' in roles:
                points[name] += 80
                events.append({"participant": name, "event": "Líder", "points": 80})

            # Auto: Anjo
            if 'Anjo' in roles:
                points[name] += 45
                events.append({"participant": name, "event": "Anjo", "points": 45})

            # Auto: Monstro
            if 'Monstro' in roles:
                points[name] -= 10
                events.append({"participant": name, "event": "Monstro", "points": -10})

            # Auto: VIP (daily, so count once per week)
            if participant['characteristics'].get('memberOf') == 'VIP':
                points[name] += 5
                events.append({"participant": name, "event": "VIP", "points": 5})

            # Auto: Paredão
            if 'Paredão' in roles:
                points[name] -= 15
                events.append({"participant": name, "event": "Paredão", "points": -15})

    # Manual: Load from manual_events.json
    manual_events = load_manual_events_for_week(week_number)
    for event in manual_events:
        points[event['participant']] += event['points']
        events.append(event)

    return points, events
```

**Usage:** Run weekly after Tuesday elimination, outputs events to `manual_events.json` for review.

---

### Integration with Existing Pages

**Link from index.qmd:**
```markdown
::: {.callout-tip}
## 📊 Cartola BBB
Veja os pontos dos participantes no [Cartola BBB](cartola.qmd).
:::
```

**Link from paredao.qmd:**
```markdown
Após o resultado, confira como isso afeta os [pontos do Cartola](cartola.qmd).
```

---

### Manual Effort Assessment

**Weekly workload:**
- Collect Big Fone events: ~5 min (search GShow)
- Check Quarto Secreto: ~2 min (rare event)
- Verify Bate e Volta results: ~3 min (already tracked for paredão)
- Update `manual_events.json`: ~10 min

**Total:** ~20 min/week

**Can be reduced by:** Scripting point calculation (run after paredão update, outputs JSON template for manual review).

---

### Recommendation

**Implement Cartola page as:**
1. **Semi-automated** — Script calculates 60% of points from API, outputs JSON
2. **Weekly update** — Manual review adds missing events (Big Fone, etc.)
3. **Simple visualizations** — Bar charts, line charts, heatmap (no complex interactivity)
4. **Target casual players first** — Weekly leaderboard + cumulative chart as MVP

**Phase 1 (MVP):** Leaderboard + cumulative chart (~3 hours)
**Phase 2:** Heatmap + event breakdown (~2 hours)
**Phase 3:** Best picks analysis (~2 hours)

---

## 11. Data Storage Architecture Assessment

### Current Approach

**Storage:**
- One JSON file per API fetch (`YYYY-MM-DD_HH-MM-SS.json`)
- Each file: ~220KB (one participant = ~10KB × 22 participants)
- Metadata wrapper: `{_metadata: {...}, participants: [...]}`
- Saved only if data hash changed (deduplication)

**Loading:**
- Each `.qmd` loads ALL snapshots at render time
- Sorted by filename (chronological order)
- Handles both old format (array) and new format (with metadata)

**Scaling:**
- 15 snapshots → 3.4MB (current)
- 120 snapshots → ~32MB (projected Day 90)

---

### Is JSON-per-Snapshot Optimal for 90+ Days?

**Yes**, with caveats.

#### Pros

✅ **Fine-grained history** — Every unique game state captured
✅ **Human-readable** — Easy to inspect, debug, diff in git
✅ **Flexible schema** — Can add fields without breaking old files
✅ **Git-friendly** — Text-based, compresses well (3.4MB → ~800KB in git)
✅ **Simple loading** — `json.load(f)` works, no database setup
✅ **Auditable** — Each file has metadata (capture time, change types)

#### Cons

❌ **Slow at scale** — Loading 120 files × 220KB = ~26MB into memory
❌ **Redundant data** — Participant structure repeated across files (~90% unchanged day-to-day)
❌ **No indexing** — Must scan all files to find "Jan 18 snapshot"
❌ **Render time grows linearly** — More files = longer load time

---

### Alternatives Evaluated

| Format | Pros | Cons | Verdict |
|--------|------|------|---------|
| **SQLite** | Indexed queries, fast joins | Binary (not git-friendly), migration effort | Overkill |
| **Parquet** | Columnar storage, very fast | Binary, requires Pandas/PyArrow | Overkill |
| **DuckDB** | SQL on JSON files, no server | Extra dependency, learning curve | Interesting but unnecessary |
| **One JSON per day** | Fewer files (90 vs 120+) | Loses intraday granularity | Bad trade-off |
| **Single consolidated JSON** | One file to load | File grows to 32MB, git diffs useless | Bad for git |
| **Pre-computed metrics JSON** | Fast rendering | Requires separate compute step | **Best optimization** |

**Recommendation:** Keep current JSON-per-snapshot. Add pre-computed metrics file.

---

### Recommended: Pre-Computation Strategy

**Create:** `data/daily_metrics.json` (auto-generated before render)

**Script:** `scripts/precompute_metrics.py`

```python
#!/usr/bin/env python3
"""
Pre-compute metrics from all snapshots to speed up rendering.
Run this before `quarto render`.
"""

import json
from pathlib import Path
from collections import defaultdict

def load_all_snapshots():
    """Load all snapshots."""
    # ... (same as in .qmd files)
    pass

def compute_daily_metrics():
    """Compute daily metrics for fast access."""
    snapshots = load_all_snapshots()

    # One snapshot per day (last capture of the day)
    daily_snapshots = {}
    for snap in snapshots:
        date = snap['date']
        if date not in daily_snapshots or snap['timestamp'] > daily_snapshots[date]['timestamp']:
            daily_snapshots[date] = snap

    # Compute metrics
    metrics = {
        "dates": sorted(daily_snapshots.keys()),
        "participants": {},
        "global": {}
    }

    # Per-participant metrics
    all_participants = set()
    for snap in daily_snapshots.values():
        all_participants.update(p['name'] for p in snap['participants'])

    for name in all_participants:
        metrics["participants"][name] = {
            "sentiment_by_date": {},
            "reactions_received_by_date": {},
            "group": None,
            "avatar": None
        }

        for date, snap in daily_snapshots.items():
            participant = next((p for p in snap['participants'] if p['name'] == name), None)
            if participant:
                # Sentiment score
                sentiment = calc_sentiment(participant)
                metrics["participants"][name]["sentiment_by_date"][date] = sentiment

                # Reaction breakdown
                rxn_breakdown = {}
                for rxn in participant.get('characteristics', {}).get('receivedReactions', []):
                    rxn_breakdown[rxn['label']] = rxn['amount']
                metrics["participants"][name]["reactions_received_by_date"][date] = rxn_breakdown

                # Static fields
                if not metrics["participants"][name]["group"]:
                    metrics["participants"][name]["group"] = participant.get('characteristics', {}).get('memberOf')
                if not metrics["participants"][name]["avatar"]:
                    metrics["participants"][name]["avatar"] = participant.get('avatar')

    # Global metrics
    for date, snap in daily_snapshots.items():
        metrics["global"][date] = {
            "participant_count": len(snap['participants']),
            "total_reactions": sum(
                sum(r.get('amount', 0) for r in p.get('characteristics', {}).get('receivedReactions', []))
                for p in snap['participants']
            )
        }

    return metrics

if __name__ == "__main__":
    metrics = compute_daily_metrics()
    output_path = Path(__file__).parent.parent / "data" / "daily_metrics.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    print(f"✅ Wrote metrics to {output_path} ({output_path.stat().st_size / 1024:.1f}KB)")
```

**Update workflow:**
```yaml
# .github/workflows/daily-update.yml
- name: Pre-compute metrics
  run: python scripts/precompute_metrics.py

- name: Render Quarto site
  run: quarto render
```

**Update .qmd files:**
```python
# Fast loading (5KB instead of 3.4MB)
metrics = json.loads(Path("data/daily_metrics.json").read_text())

# Access pre-computed data
dates = metrics["dates"]
sentiment_scores = {name: list(data["sentiment_by_date"].values()) for name, data in metrics["participants"].items()}
```

**Impact:**
- Render time: ~70% faster (2-3 min → <1 min)
- Memory usage: 90% lower (26MB → 2MB)
- Page load time: Unchanged (metrics not embedded, still use full snapshots for details)

---

### Support for Interactive Date Selection

If you later add Observable JS date pickers:

**Option 1: Embed daily metrics in HTML**

```python
# In .qmd, create OJS reactive data
ojs_define(daily_metrics=metrics)
```

```javascript
// In OJS block
viewof selectedDate = Inputs.date({...})
filteredData = daily_metrics.participants.filter(d => d.date === selectedDate)
```

**Size impact:** Embedding 90 days of metrics = ~500KB (acceptable).

---

**Option 2: Fetch snapshots on-demand**

Copy `data/snapshots/*.json` to `_site/data/snapshots/` (published):

```yaml
# _quarto.yml
project:
  resources:
    - data/snapshots/*.json
```

Then fetch from JavaScript:
```javascript
snapshot = await fetch(`data/snapshots/${selectedDate}.json`).then(r => r.json())
```

**Size impact:** No embedding, but user downloads ~220KB per date selected.

**Recommendation:** Use Option 1 (embed metrics) for common queries. Full snapshots remain server-side.

---

### Git Repository Size Management

**Current:** 3.4MB snapshots → ~800KB compressed in git
**Projected:** 32MB snapshots → ~8MB compressed in git

**Is this a problem?** No. GitHub's soft limit is 1GB, warning at 5GB.

**When to worry:** If repo exceeds 100MB (clone times slow). Not an issue here.

**Optional optimization (not needed now):**

```bash
# Use Git LFS for large files
git lfs track "data/snapshots/*.json"
git add .gitattributes
git commit -m "Enable LFS for snapshots"
```

**Cost:** Free tier: 1GB storage, 1GB bandwidth/month (sufficient).

---

### Migration Path (If Recommending Changes)

**Not needed.** Current architecture is sound. If you implement pre-computation:

**Migration steps:**
1. Create `scripts/precompute_metrics.py` (1 hour)
2. Add workflow step (5 min)
3. Update one `.qmd` file to use metrics (30 min)
4. Test render time improvement
5. Migrate remaining pages (2 hours)

**Total effort:** ~4 hours. **ROI:** 70% faster renders, scales to 90+ days.

---

## 12. Mobile & Accessibility Review

### Mobile Usability Issues

#### 1. **22×22 Heatmap is Unreadable on Phones**

**Problem:** Each cell is ~15px on a 375px phone screen. Emoji (14px) + participant names are illegible.

**Current behavior:**
- User must pinch-zoom to read
- Scrolling is awkward (horizontal + vertical)
- Plotly's responsive mode doesn't help (layout issue, not size)

**Fixes:**

**A. Responsive Breakpoint — Show Top 10 Only on Mobile**

```python
# In index.qmd
import plotly.graph_objects as go

# Desktop: Full 22×22 matrix
fig_full = create_heatmap(all_participants)

# Mobile: Top 10 sentiment participants only
top10 = sorted(participants, key=calc_sentiment, reverse=True)[:10]
fig_mobile = create_heatmap(top10)

# Conditional rendering (CSS media query via HTML)
display(HTML(f"""
<div class="d-none d-lg-block">
    {fig_full.to_html(include_plotlyjs=False, div_id='heatmap-desktop')}
</div>
<div class="d-lg-none">
    {fig_mobile.to_html(include_plotlyjs=False, div_id='heatmap-mobile')}
    <p class="text-muted small">Mostrando top 10 participantes. <a href="#heatmap-desktop">Ver todos (desktop)</a>.</p>
</div>
"""))
```

**Impact:** Mobile users see 10×10 matrix (readable), desktop users see full 22×22.

---

**B. Alternative View — List Instead of Matrix**

On mobile, replace heatmap with expandable cards:

```markdown
::: {.d-lg-none}
## Reações (visualização mobile)

::: {.accordion}
### Alberto Cowboy
**Recebeu:** ❤️ 15, 🐍 3, 🌱 2
**Deu:** [list of who he gave to]
:::
:::
```

**Impact:** Vertical scrolling (natural on mobile) instead of 2D navigation.

---

**Recommendation:** Implement option A first (10×10 mobile matrix). Add option B if users request it.

---

#### 2. **Navbar Collapses Poorly**

**Current:** Bootstrap navbar with 5 links. On mobile:
- Hamburger menu works
- But long page titles ("📈 Trajetória") wrap awkwardly

**Fix:** Shorter mobile-only labels.

```yaml
# _quarto.yml
navbar:
  left:
    - href: index.qmd
      text: "📊 Painel"
      # Add custom class for responsive text
```

Then in CSS:
```css
/* assets/mobile.css */
@media (max-width: 768px) {
  .navbar-nav .nav-link {
    font-size: 14px;
  }
}
```

**Impact:** Minor improvement. Not critical.

---

#### 3. **TOC Offcanvas Button Hard to Tap**

**Current:** "📋 Índice" button in navbar is 44px tall (Apple's minimum touch target).

**Issue:** On iOS Safari, button sometimes requires double-tap due to hover states.

**Fix:** Remove hover-only interactions on mobile.

```css
/* assets/toc-offcanvas.css */
@media (max-width: 768px) {
  .toc-toggle-btn:hover {
    /* Disable hover effects on mobile */
    background-color: inherit;
  }
}
```

---

#### 4. **Plotly Charts Load Slowly on 3G**

**Current:** Each page has 5-8 Plotly charts. On slow connections, user sees blank page for 5-10 seconds.

**Fix:** Lazy-load below-the-fold charts.

```javascript
// assets/lazy-plotly.js
document.addEventListener('DOMContentLoaded', function() {
  const charts = document.querySelectorAll('.plotly-chart-lazy');

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const chartDiv = entry.target;
        const dataScript = chartDiv.querySelector('script[type="application/json"]');
        const plotData = JSON.parse(dataScript.textContent);
        Plotly.newPlot(chartDiv, plotData.data, plotData.layout, plotData.config);
        observer.unobserve(chartDiv);
      }
    });
  });

  charts.forEach(chart => observer.observe(chart));
});
```

**Impact:** First chart loads immediately, rest load as user scrolls. Perceived performance improves.

---

### Accessibility Issues

#### 1. **Charts Have No Alt Text**

**Problem:** Screen readers announce "Plotly chart" with no description.

**Fix:** Add `aria-label` to chart divs.

```python
fig.update_layout(
    title="Ranking de Sentimento",
    # Add accessible description
    **{"aria-label": "Gráfico de barras horizontais mostrando o ranking de sentimento dos participantes. Alberto Cowboy lidera com 12.5 pontos, seguido por..."}
)
```

Or add summary text after chart:
```markdown
[Chart]

::: {.sr-only}
Descrição acessível: Alberto Cowboy lidera o ranking com 12.5 pontos, seguido por Ana Paula Renault com 10.2 pontos...
:::
```

---

#### 2. **Color is the Only Way to Convey Group Info**

**Problem:** Color-blind users can't distinguish Pipoca (blue), Camarote (red), Veterano (green).

**Fix:** Add patterns or shapes.

```python
# Use both color AND marker shape
fig = px.scatter(
    df,
    x='sentiment', y='name',
    color='group',
    symbol='group',  # Different shapes per group
    color_discrete_map=GROUP_COLORS,
    symbol_map={'Pipoca': 'circle', 'Camarote': 'square', 'Veterano': 'diamond'}
)
```

Or add text labels:
```python
fig.update_traces(
    text=[f"{name} ({group})" for name, group in zip(df['name'], df['group'])],
    textposition='auto'
)
```

---

#### 3. **Emoji Accessibility**

**Problem:** Screen readers announce "snake emoji" instead of "Cobra reaction".

**Fix:** Use `aria-label` on emoji spans.

```python
# When rendering emoji in HTML
def emoji_with_label(reaction_name):
    emoji = REACTION_EMOJI[reaction_name]
    return f'<span aria-label="{reaction_name}">{emoji}</span>'
```

Or add text labels alongside emoji:
```markdown
❤️ Coração (15) → "15 Coração ❤️"
```

---

#### 4. **Dark Theme Contrast Issues**

**Current:** Dark theme (#222 background, #fff text) has good contrast (18.3:1).

**Potential issue:** Link color (#00bc8c) on dark background = 5.8:1 (WCAG AA compliant, but not AAA).

**Fix:** Increase link brightness for AAA compliance.

```css
/* assets/accessibility.css */
a {
  color: #00d9a3; /* Brighter green, 7.2:1 contrast */
}

a:hover {
  color: #00ffbb;
}
```

---

#### 5. **Keyboard Navigation**

**Problem:** Plotly modals (fullscreen charts) may trap focus.

**Fix:** Ensure ESC key works (already implemented in `plotly-fullscreen.js`). Add focus management:

```javascript
// In plotly-fullscreen.js openModal()
function openModal(plotDiv) {
    createModal();
    modal.classList.add('active');

    // Trap focus in modal
    const closeBtn = modal.querySelector('.plotly-modal-close');
    closeBtn.focus();

    // ... rest of implementation
}
```

---

### Performance on Low-End Devices

**Test device:** iPhone SE 2016 (A9 chip, 2GB RAM)

**Expected issues:**
1. **Heatmap rendering:** 22×22 matrix with emoji = 484 cells → ~2-3 seconds to render
2. **Network graph:** Force-directed layout with 22 nodes, 462 edges → CPU-intensive
3. **Multiple charts per page:** 8 charts × 200KB each = 1.6MB → slow on 3G

**Fixes:**

**A. Lazy-load charts** (see above)

**B. Reduce heatmap complexity on mobile**
```python
# Detect low-end device via user agent (optional)
# Or just use responsive breakpoint (simpler)
```

**C. Simplify network graph**
```python
# For mobile, use static layout instead of force-directed
fig.update_layout(
    xaxis=dict(visible=False),
    yaxis=dict(visible=False),
    hovermode='closest',
    # Disable animations on mobile
    transition={'duration': 0} if is_mobile else {'duration': 500}
)
```

---

### Recommended Improvements Summary

| Priority | Fix | Effort | Impact |
|----------|-----|--------|--------|
| **HIGH** | Mobile heatmap: Show top 10 only | 1 hour | Readable on phones |
| **HIGH** | Add alt text to charts | 2 hours | Screen reader access |
| **MEDIUM** | Lazy-load below-fold charts | 1 hour | Faster perceived load |
| **MEDIUM** | Use shapes + color for groups | 30 min | Color-blind friendly |
| **LOW** | Emoji accessibility labels | 1 hour | Screen reader quality |
| **LOW** | Increase link contrast | 10 min | AAA compliance |

**Total effort for HIGH priority:** ~3 hours. Do these before launch.

---

## Summary of Open Questions Answered

### 1. Is interactivity essential, nice-to-have, or unnecessary?

**Answer:** **Nice-to-have, not essential** at current scale (12 days, 22 participants).

Wait until:
- You have 30+ days of data
- Users request date comparison features
- Timeline charts become cluttered

Then implement via **Observable JS** (client-side, stays on GitHub Pages).

---

### 2. Should we use Shiny, Observable, pure JS, or none?

**Answer:** **None for now.** If you add interactivity later: **Observable JS** (client-side only).

**Not recommended:** Shiny (requires server, breaks free hosting constraint).

---

### 3. Is GitHub Pages + Actions sufficient for production?

**Answer:** **Yes**, with minor hardening:

**Add:**
- Retry logic in API fetcher (prevent one-off failures)
- "Last updated" timestamp on pages (user trust)
- Failure notifications via GitHub Issues (faster debugging)

**Optional:**
- Pre-compute metrics (70% faster renders)
- Incremental rendering (50% faster rebuilds)

---

### 4. What safeguards should we add?

**Answer:** See [Deployment section](#recommended-safeguards-summary).

**Priority 1:** API retry logic + last updated timestamp (~45 min effort).

---

### 5. Performance concerns at 90+ days?

**Answer:** Manageable, but **pre-computation recommended** at Day 30.

**Projected render time (Day 90):**
- Without optimization: 15-20 minutes (within GitHub Actions limits)
- With pre-computation: 6 minutes (acceptable)

**Git repo size:** 32MB (well within GitHub's 1GB limit).

---

### 6. Is JSON-per-snapshot optimal for 90+ days?

**Answer:** **Yes.** It's human-readable, git-friendly, and flexible.

**Optimization:** Add pre-computed `daily_metrics.json` to speed up renders (70% faster).

**Don't switch to:** SQLite, Parquet, or single consolidated JSON (unnecessary complexity).

---

### 7. How to support interactive date selection?

**Answer:** **Embed pre-computed metrics in HTML** (Observable JS).

```javascript
// User selects date
viewof selectedDate = Inputs.date({...})

// Filter embedded metrics
filteredData = daily_metrics.filter(d => d.date === selectedDate)
```

**Size impact:** ~500KB embedded data (acceptable).

---

### 8. What visualizations for Cartola BBB page?

**Answer:**
1. Weekly leaderboard (bar chart)
2. Cumulative points timeline (line chart)
3. Weekly heatmap (participant × week)
4. Event breakdown (stacked bar)
5. "Best picks" value boxes

**Data:** 60% auto-calculated, 40% manual (~20 min/week effort).

---

### 9. Mobile accessibility issues?

**Answer:** **Main issue: 22×22 heatmap unreadable on phones.**

**Fix:** Show top 10 participants only on mobile (10×10 matrix).

**Other fixes:**
- Add alt text to charts (screen readers)
- Lazy-load below-fold charts (performance)
- Use shapes + color for groups (color-blind users)

---

## Final Recommendations

### Immediate Actions (Before Launch)

| Action | Effort | Why |
|--------|--------|-----|
| Add API retry logic | 30 min | Prevent one-off failures |
| Add "Last updated" timestamp | 15 min | User trust |
| Mobile heatmap: top 10 only | 1 hour | Readability on phones |
| Add chart alt text | 2 hours | Accessibility |

**Total:** ~4 hours

---

### Phase 2 (After 30 Days of Data)

| Action | Effort | Why |
|--------|--------|-----|
| Pre-compute daily metrics | 4 hours | 70% faster renders |
| Implement Cartola BBB page | 7 hours | New feature, user value |
| Add failure notifications | 20 min | Monitoring |

**Total:** ~11 hours

---

### Phase 3 (If User Demand Emerges)

| Action | Effort | Why |
|--------|--------|-----|
| Add Observable JS date picker | 4 hours | Interactive date comparison |
| Timeline zoom/filter | 3 hours | Readable at scale |
| Participant filter on heatmap | 2 hours | Mobile UX |

**Total:** ~9 hours

---

## Code Snippets

### 1. API Retry Logic

```python
# scripts/fetch_data.py
import time

def fetch_with_retry(url, max_retries=3, backoff=5):
    """Fetch with exponential backoff."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            if not isinstance(data, list) or len(data) == 0:
                raise ValueError(f"Invalid data: {type(data)}")

            return data
        except (requests.RequestException, ValueError) as e:
            if attempt == max_retries - 1:
                print(f"ERROR after {max_retries} attempts: {e}")
                return None
            print(f"Attempt {attempt+1} failed: {e}. Retrying in {backoff}s...")
            time.sleep(backoff * (2 ** attempt))
    return None

# In fetch_and_save()
new_data = fetch_with_retry(API_URL)
if new_data is None:
    print("CRITICAL: Using latest snapshot for render.")
    return str(latest_file), False
```

---

### 2. Last Updated Timestamp

```python
# In index.qmd setup cell
last_fetch = snapshots[-1]['metadata'].get('captured_at', 'Unknown')
last_fetch_dt = pd.to_datetime(last_fetch) if last_fetch != 'Unknown' else None
last_fetch_brt = (last_fetch_dt - pd.Timedelta(hours=3)).strftime('%d/%m/%Y %H:%M BRT') if last_fetch_dt else 'Unknown'

# Check if stale
is_stale = (datetime.now() - last_fetch_dt) > timedelta(hours=24) if last_fetch_dt else False
```

```markdown
::: {.callout-note}
**Última atualização:** {python} last_fetch_brt
:::

{python}
if is_stale:
    display(HTML('''
    <div class="alert alert-warning">
    ⚠️ Dados desatualizados (>24h). Pode haver problemas na atualização automática.
    </div>
    '''))
```

---

### 3. Mobile-Responsive Heatmap

```python
# In index.qmd
# Create two versions
top10_names = sorted_by_sentiment[:10]

# Full matrix for desktop
fig_full = create_heatmap(all_participants)

# Reduced matrix for mobile
fig_mobile = create_heatmap([p for p in all_participants if p['name'] in top10_names])

# Conditional display
display(HTML(f"""
<div class="d-none d-lg-block">
    {plotly_to_html(fig_full)}
</div>
<div class="d-lg-none">
    {plotly_to_html(fig_mobile)}
    <p class="text-muted small mt-2">
        <i class="bi bi-phone"></i> Visualização mobile: mostrando top 10 participantes.
        Para ver a tabela completa, acesse em um desktop.
    </p>
</div>
"""))
```

---

### 4. Pre-Computation Script

```python
# scripts/precompute_metrics.py
#!/usr/bin/env python3
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "snapshots"

def load_all_snapshots():
    files = sorted(DATA_DIR.glob("*.json"))
    snapshots = []
    for f in files:
        with open(f) as fp:
            data = json.load(fp)
            participants = data.get('participants', data)
            date = f.stem.split('_')[0]
            snapshots.append({'date': date, 'participants': participants})
    return snapshots

def compute_metrics():
    snapshots = load_all_snapshots()

    # One per day (last capture)
    daily = {}
    for s in snapshots:
        if s['date'] not in daily or s['timestamp'] > daily[s['date']]['timestamp']:
            daily[s['date']] = s

    metrics = {
        "dates": sorted(daily.keys()),
        "participants": {}
    }

    # Per-participant sentiment over time
    for snap in daily.values():
        for p in snap['participants']:
            name = p['name']
            if name not in metrics["participants"]:
                metrics["participants"][name] = {
                    "sentiment": {},
                    "group": p.get('characteristics', {}).get('memberOf')
                }

            sentiment = sum(
                rxn.get('amount', 0) * SENTIMENT_WEIGHTS.get(rxn.get('label'), 0)
                for rxn in p.get('characteristics', {}).get('receivedReactions', [])
            )
            metrics["participants"][name]["sentiment"][snap['date']] = sentiment

    return metrics

if __name__ == "__main__":
    metrics = compute_metrics()
    out = Path(__file__).parent.parent / "data" / "daily_metrics.json"
    out.write_text(json.dumps(metrics, indent=2, ensure_ascii=False))
    print(f"✅ Wrote {out} ({out.stat().st_size / 1024:.1f}KB)")
```

---

### 5. GitHub Actions Failure Notification

```yaml
# .github/workflows/daily-update.yml
jobs:
  update-and-publish:
    steps:
      # ... existing steps ...

      - name: Create issue on failure
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            const date = new Date().toISOString().split('T')[0];
            await github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: `Dashboard update failed - ${date}`,
              body: `Workflow failed: ${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}\n\nCheck logs for details.`,
              labels: ['automated', 'bug', 'ci-failure']
            });
```

---

## Conclusion

The BBB26 dashboard has a **solid technical foundation**. The current stack (GitHub Pages, Quarto, JSON snapshots) scales well to 90 days with minor optimizations.

**No major architectural changes needed.** Focus on:
1. Hardening deployment (retry logic, monitoring)
2. Mobile UX improvements (responsive heatmap, alt text)
3. Optional: Pre-computation for faster renders (after Day 30)

**Interactivity can wait.** Static pre-rendered pages serve the current use case well. Revisit after 30 days if user demand emerges.

The recommended approach is **incremental improvement** rather than re-architecture. Total effort for Phase 1 (production-ready): **~4 hours**.
