# BBB26 Dashboard — Holistic Review
**Reviewer**: Claude Sonnet 4.5
**Date**: 2026-01-25
**Review Type**: Holistic (Big Picture)

---

## The 8 Key Questions

### 1. What's the single biggest problem with the current approach?

**You buried the lede.**

The dashboard has a fundamental information architecture problem: it shows people **analysis tools** when they want **answers**. You're giving users a 22×22 heatmap when what they really want to know is: "Who's in trouble?" "Who's rising?" "What happened today?"

The landing page (Painel) starts with:
1. Generic stats (participant count, reaction count)
2. A timeline table
3. A ranking chart
4. A giant heatmap

But what users ACTUALLY want when they visit is:
- **"What's hot today?"** — Who had the biggest drama, who's vulnerable
- **"Who should I watch?"** — Risk alerts, trending participants
- **"What changed?"** — Quick summary of today's shifts

The current structure assumes users want to explore data. Most users want to consume insights. You're building a research tool when you should be building a news feed.

**Evidence**: "O Que Mudou" (daily changes) is buried on page 2. That should BE the landing page. Changes are the hook. Static rankings are reference material.

### 2. What's the single best thing about it?

**The data model is brilliant.**

Understanding that reactions are a **complete reassigned state** (not cumulative) and tracking one-sided vs two-sided hostilities is genuinely sophisticated game theory analysis. The vulnerability ratio, the blind spots concept, the "attacks friends who give hearts" metric — this is the kind of insight that makes BBB superfans say "holy shit, I never thought about it that way."

The technical foundation is also rock-solid: clean JSON snapshots, hash-based deduplication, synthetic snapshot methodology for missing days, multi-capture strategy to catch different game events. This is a system that will scale to 90 days without breaking.

### 3. If you could only make 3 changes, what would they be?

**Change 1: Flip the landing page from state → changes to changes → state**

Replace Painel with a **"Hoje no Queridômetro"** (Today in the Queridômetro) structure:

```
ABOVE THE FOLD (no scrolling):
┌─────────────────────────────────────────────────────┐
│ 🔥 DESTAQUES DO DIA — Jan 25, 2026                  │
│                                                     │
│ [Card] ⚠️ EM RISCO                                  │
│ Leandro está no paredão com 8 cobras recebidas     │
│                                                     │
│ [Card] 📈 SUBIU MAIS                                │
│ Jordana ganhou 4 corações (hoje: +6 sentiment)     │
│                                                     │
│ [Card] 📉 CAIU MAIS                                 │
│ Marcelo perdeu 5 corações, ganhou 3 cobras         │
│                                                     │
│ [Card] 💔 DRAMA DO DIA                              │
│ 11 mudanças dramáticas (❤️↔🐍)                      │
│ Marcelo virou 5 corações em cobras                 │
└─────────────────────────────────────────────────────┘

THEN (after scroll):
- Quick ranking (top 5 + bottom 5, not all 22)
- Current paredão status (if active)
- Link to full analysis pages
```

**Change 2: Add a "participant focus mode" with individual profile pages**

Each participant gets a dedicated page (e.g., `/jordana.html`) with:
- **Sentiment timeline** (just that person)
- **Who loves/hates them** (current state)
- **Relationship history** (how each relationship evolved)
- **Strategic position** (vulnerability, alliances, enemies)
- **Voting history** (in past paredões)

This makes the dashboard shareable ("Check out Jordana's profile!") and gives superfans a way to deep-dive on their favorites.

**Change 3: Consolidate from 5 pages to 3 focused pages**

Current 5-page structure is too fragmented:

```
PROPOSED 3-PAGE STRUCTURE:

📰 HOJE (index.qmd) — The news feed
   - Daily highlights (destaques)
   - What changed (winners/losers)
   - Current paredão status
   - Quick rankings

📊 ANÁLISE (analise.qmd) — The research tool
   - Full heatmap
   - All rankings
   - Clusters, graphs, hostilities
   - Historical trends
   (Merge: current Painel + Trajetória)

🗳️ PAREDÕES (paredoes.qmd) — The archive
   - Current paredão (detailed)
   - Historical paredões
   (Merge: current Paredão + Arquivo)

Plus: Individual profile pages for each participant
```

### 4. What's missing that seems obvious to an outsider?

**Predictions and risk scoring.**

You have 12 days of reaction data. You tracked voting coherence in the 1º Paredão. You KNOW reactions don't perfectly predict votes. But you're not synthesizing this into "Who's at risk this week?"

A simple **Risk Score** would be incredibly valuable:
```
Risk Score =
  (Strong negative received × 2) +
  (Mild negative received × 1) +
  (One-sided hostilities where they're the target × 1.5) +
  (Days since last received a heart from Líder × 0.5)
```

Display this as:
- 🟢 Safe (score < 10)
- 🟡 Watch (10-20)
- 🔴 High Risk (20+)
- ⚫ Paredão (currently nominated)

**Also missing**:
- **Week-over-week trends** (not just day-to-day) — "Jordana gained 8 hearts this week"
- **Relationship strength meter** — Which alliances are solid vs shaky?
- **"Participants like you might like..."** — Cluster similarity (if you like X, check Y's profile)
- **Embed codes** — Let fans embed charts in forums/blogs
- **Downloadable data** — CSV export for the data nerds

### 5. What would make a casual BBB viewer visit this daily?

**Push notifications energy.**

Casual viewers don't want to analyze 462 reactions. They want:

1. **A daily digest** (like a push notification):
   - "🔥 Marcelo had the biggest fall today (-9 sentiment)"
   - "⚠️ Leandro is in danger (8 people gave cobra)"
   - "💑 New alliance: Ana Paula ↔ Solange (mutual hearts 7 days)"

2. **Visual cards with faces** (not just names):
   - Show participant avatars prominently
   - "At risk this week" section with photos in a grid
   - Make it instantly recognizable who you're talking about

3. **Mobile-first design**:
   - Current heatmap is unreadable on mobile (22×22 matrix)
   - Landing page should be card-based, thumb-scrollable
   - Charts should be simplified or hidden behind "Ver detalhes"

4. **Shareable moments**:
   - Auto-generate quote cards: "Marcelo gave 5 cobras today 🐍"
   - Twitter-style shareable images
   - WhatsApp-friendly links that preview well

5. **Gamification hooks**:
   - "Your prediction: Will Leandro be eliminated?"
   - "Who do you think will give the most cobras tomorrow?"
   - Make it interactive without needing a backend (use localStorage)

**Bottom line**: Make it feel like Instagram Stories, not an Excel dashboard.

### 6. What would make a data enthusiast share this on Twitter/LinkedIn?

**The methodology section is BURIED.**

Data people share things that teach them something. Your work on:
- One-sided vs two-sided hostilities
- Vulnerability ratio (hearts to enemies ÷ attacks on friends)
- Synthetic snapshot methodology
- Complete directed graph analysis

...is genuinely clever. But it's hidden in CLAUDE.md and code comments.

**What would get shared**:

1. **A "Methodology" page** explaining:
   - How reactions are a complete state (not cumulative)
   - Why this matters for analysis
   - The graph theory approach
   - Sentiment weight rationale
   - Limitations and biases

2. **Reproducible analysis**:
   - Download raw data (CSV or JSON)
   - Jupyter notebook with full analysis
   - API documentation if you exposed one

3. **Novel visualizations**:
   - The Sankey diagram of reaction migrations is GREAT
   - Network graph needs better layout (current is messy)
   - Consider: Chord diagram for reactions
   - Consider: Alluvial diagram for sentiment over time
   - Consider: Heatmap calendar (GitHub contribution style)

4. **Statistical rigor**:
   - "Reactions predicted votes with 62% accuracy in Paredão 1"
   - "Correlation between sentiment and elimination: r = -0.43"
   - "Group favoritism: VIPs give 23% more hearts to VIPs"
   - Cite your sources, show the math

5. **Open source badge**:
   - Make the repo public (if not already)
   - Add proper README with setup instructions
   - Include LICENSE
   - Write a blog post: "Building a BBB analytics dashboard with Quarto + Plotly"

**Example shareable tweet**:
> "I built a BBB26 dashboard that tracks 462 daily reactions as a directed graph. Turns out 'blind spots' (A gives ❤️ to B, B gives 🐍 to A) are the #1 predictor of surprise eliminations. Thread 🧵👇"

### 7. Is the 5-page structure right, or should it be reorganized?

**5 pages is too many. But the problem isn't the count — it's the PURPOSE.**

Current structure is organized by **data type**:
- Painel = current state
- O Que Mudou = daily delta
- Trajetória = time series
- Paredão = current event
- Arquivo = historical events

This is a **database schema**, not a **user journey**.

**Better organization** (by user intent):

```
🏠 HOJE (Home/News)
   Purpose: Daily visitors checking "what's new"
   Content: Highlights, changes, paredão status
   Update: Daily
   Length: Short (2-3 scrolls max)

🔍 ANÁLISE (Research/Deep Dive)
   Purpose: Superfans exploring patterns
   Content: Full heatmap, rankings, clusters, graphs
   Update: Daily
   Length: Long (infinite scroll, tabbed sections)

🗳️ PAREDÕES (Archive/Reference)
   Purpose: Historical lookup, voting analysis
   Content: All paredões, voting coherence
   Update: Weekly (after eliminations)
   Length: Medium (one section per paredão)

👤 [PARTICIPANT] (Individual Profiles)
   Purpose: Deep dive on one person
   Content: Personal timeline, relationships, strategic position
   Update: Daily
   Length: Medium (focused on one person)

📖 SOBRE (About/Methodology)
   Purpose: Explain the system, share data
   Content: How it works, download data, contact
   Update: Rarely
   Length: Short
```

**Navigation flow**:
```
Casual viewer:
  Hoje → [Participant profile] → Done

Superfan:
  Hoje → Análise (explore) → Paredões (check history) → [Profiles]

Data nerd:
  Sobre → Download data → Build own analysis
```

**Kill the "O Que Mudou" page** — integrate it into "Hoje".
**Kill the "Trajetória" page** — integrate it into "Análise" as tabbed sections.
**Split "Painel"** — highlights go to "Hoje", deep charts go to "Análise".

### 8. Rate the current approach (1-10) and explain why.

**7/10 — Excellent foundation, poor presentation**

**What's working (🟢)**:
- Data model: 9/10 — Sophisticated, scalable, well-documented
- Technical stack: 8/10 — Quarto + Plotly + GitHub Actions is solid
- Analysis depth: 9/10 — Hostility analysis, clusters, coherence tracking
- Dark theme: 8/10 — Looks professional, easy on eyes
- Update frequency: 9/10 — 4x daily captures all events

**What's broken (🔴)**:
- Information hierarchy: 3/10 — Buried insights, bad first impression
- Mobile experience: 2/10 — Heatmaps unreadable, pages too long
- Shareability: 3/10 — No cards, no embeds, no quotes
- Storytelling: 4/10 — Feels like a database, not a narrative
- Accessibility: 4/10 — Color-only encoding, no alt text

**Why not higher**:
The current dashboard is built for YOU (the analyst) not for THEM (the audience). It's organized around "here's all the data I collected" rather than "here's what you need to know." The insights are brilliant but buried under mountains of charts.

**Why not lower**:
The technical execution is flawless. The data quality is excellent. The analysis is genuinely valuable. This is 80% of the way to great — it just needs a UX/storytelling layer.

**Analogy**: This is like writing an academic paper with all your findings in the appendix and no abstract. The research is solid, but nobody will read it.

---

## Top 5 Quick Wins (Can Be Done in a Day)

### 1. Add "Destaques do Dia" section to landing page
**Effort**: 2 hours
**Impact**: High

Auto-generate 3-4 highlight cards:
- Biggest sentiment gainer/loser
- Most dramatic change (❤️→🐍 or vice versa)
- Participant at risk (most cobras)
- New alliance/rivalry (if detected)

Code this in the existing `index.qmd` setup cell. Use simple logic:
```python
# Find biggest gainer
sentiment_changes = [(name, today[name] - yesterday[name]) for name in names]
biggest_gainer = max(sentiment_changes, key=lambda x: x[1])

# Display as Bootstrap card with avatar
```

### 2. Mobile-friendly quick rankings (top 5 + bottom 5 only)
**Effort**: 1 hour
**Impact**: Medium

Replace the full 22-person ranking chart with:
- Top 5 (green background)
- "..." (middle 12 collapsed by default)
- Bottom 5 (red background)

Add "Ver ranking completo" button that expands.

### 3. Add participant avatars to all charts
**Effort**: 3 hours
**Impact**: High

The API provides avatar URLs. Use them:
- In ranking charts (small circular avatars next to names)
- In cards (large avatars)
- In heatmap hover (show avatar in tooltip)

This makes participants instantly recognizable without reading names.

### 4. Create shareable Open Graph meta tags
**Effort**: 1 hour
**Impact**: Medium

Add to each page's YAML:
```yaml
metadata:
  pagetitle: "BBB26 Queridômetro — Análise de Reações"
  description: "Acompanhe as reações diárias entre participantes do BBB26"
  og:image: "/assets/og-image.png"
  twitter:card: "summary_large_image"
```

Generate a single good OG image (design in Canva, 5 minutes) showing a sample heatmap or ranking.

### 5. Add "última atualização" timestamp to all pages
**Effort**: 30 minutes
**Impact**: Low (but important)

Show in navbar or footer:
```
Última atualização: 25/01/2026 às 16:47 BRT
Próxima atualização: hoje às 21:00 BRT
```

Builds trust that data is fresh.

---

## Top 3 Big Bets (Worth Significant Investment)

### 1. Individual Participant Profile Pages (~/jordana.html)
**Effort**: 2-3 days
**Impact**: MASSIVE

Create a template `.qmd` that generates a page per participant:

**URL structure**: `/participantes/jordana.html`

**Content**:
```
┌─────────────────────────────────────────┐
│ [Avatar] Jordana                        │
│ Pipoca | VIP | Sentimento: +8.5        │
│ 🟡 Risco médio (12 pontos)              │
└─────────────────────────────────────────┘

📊 Trajetória de Sentimento
[Line chart: Jordana's sentiment over time]

❤️ Quem Jordana Dá Coração (11)
[Grid of avatars with names]

🐍 Quem Jordana Ataca (5)
[Grid of avatars]

💚 Quem Dá Coração para Jordana (12)
[Grid of avatars]

🚨 Quem Ataca Jordana (8)
[Grid of avatars]

⚠️ Pontos Cegos
- Jordana dá ❤️ para Marcelo, mas Marcelo dá 🐍
- Jordana dá ❤️ para Leandro, mas Leandro dá 💔

🤝 Alianças Mais Fortes
1. Jordana ↔ Ana Paula (7 dias de ❤️ mútuo)
2. Jordana ↔ Babu (5 dias)

🗳️ Histórico de Paredões
- 1º Paredão: Não foi ao paredão

📈 Evolução das Reações
[Table showing day-by-day who gave what]
```

**Why it's worth it**:
- Makes content shareable ("Look at MY participant!")
- Increases page views (22 participants × daily visitors)
- Creates SEO opportunities (long-tail: "jordana bbb26 reações")
- Enables deep analysis without cluttering main pages

**Implementation**:
- Write a Python script that generates 22 `.qmd` files from a template
- Run it as part of the render process
- Auto-link from main pages

### 2. Client-Side Date Comparison with Observable JS
**Effort**: 3-4 days
**Impact**: HIGH (for superfans)

Right now "O Que Mudou" only shows yesterday→today. Superfans want:
- "Compare Jan 15 vs Jan 20"
- "Show me the week Leandro entered"
- "What changed after the 1º Paredão?"

**Solution**: Use Observable JS (client-side, no server needed)

**How it works**:
1. Pre-compute a daily metrics file: `data/daily_metrics.json`
   ```json
   {
     "2026-01-13": {
       "participants": {"Jordana": {"sentiment": 7.5, ...}, ...},
       "matrix": [[...]],
       ...
     },
     "2026-01-14": {...}
   }
   ```

2. Embed this JSON in the page (or fetch it)

3. Add Observable date pickers:
   ```javascript
   viewof date1 = Inputs.date({label: "Data 1", value: "2026-01-24"})
   viewof date2 = Inputs.date({label: "Data 2", value: "2026-01-25"})
   ```

4. Reactively update charts based on selection

**Constraints**:
- All data must fit in page (90 days × ~50KB each = ~4.5MB — acceptable)
- Or fetch from `/data/daily_metrics.json` (GitHub Pages serves it fine)

**Alternative** (if 4.5MB is too heavy):
- Pre-render 20 most useful comparisons as separate pages
- Add dropdown: "Ver comparações pré-renderizadas"

### 3. Auto-Generated "Report Card" Images for Sharing
**Effort**: 2-3 days
**Impact**: MEDIUM (but viral potential)

Generate shareable images (PNG) programmatically:

**Example**: Daily report card
```
┌─────────────────────────────────────────┐
│  BBB26 QUERIDÔMETRO — 25/01/2026        │
├─────────────────────────────────────────┤
│  📈 SUBIU MAIS: Jordana (+6)            │
│  [avatar] [mini sentiment chart]        │
│                                         │
│  📉 CAIU MAIS: Marcelo (-9)             │
│  [avatar] [mini sentiment chart]        │
│                                         │
│  🔥 DRAMA: 11 mudanças dramáticas       │
│  Marcelo virou 5 ❤️ em 🐍               │
│                                         │
│  🗳️ PAREDÃO: Leandro está no paredão   │
│  [avatar] Recebeu 8 🐍                  │
│                                         │
│  bbb26.github.io                        │
└─────────────────────────────────────────┘
```

**Tech stack**:
- Python: `matplotlib` or `Pillow` to generate image
- Save to `/assets/daily_cards/2026-01-25.png`
- Auto-post to Twitter via GitHub Actions (if you set up API keys)

**Alternatively** (easier):
- Generate HTML "cards" styled for screenshot
- Provide "Share this" button that opens in new window
- User screenshots manually

**Why it's worth it**:
- Gets the dashboard shared outside your site
- Drives traffic back
- Establishes you as THE source for BBB26 data

---

## 1 Wild Idea (Unconventional But Might Work)

### "Blind Spot Alerts" — Push Notification Style Daily Digest

**The idea**: At 13:00 BRT daily (after Raio-X updates), auto-generate a plain-text digest that reads like push notifications:

```
🔔 BBB26 QUERIDÔMETRO — 25/01/2026

🔥 Marcelo teve a maior queda (-9 sentiment)
   Perdeu 5 ❤️, ganhou 3 🐍

⚠️ Leandro está em risco
   No paredão + 8 🐍 recebidos

📈 Jordana subiu mais (+6)
   Ganhou 4 ❤️ novos

💔 Pontos cegos do dia:
   • Gabriela dá ❤️ para Leandro, mas ele dá 🐍
   • Matheus dá ❤️ para Yuri, mas ela dá 💼

🤝 Nova aliança detectada:
   Ana Paula ↔ Solange (7 dias de ❤️ mútuo)

🐍 Maior inimizade:
   Ana Paula ↔ Brigido (10 dias de ataques mútuos)

Ver análise completa: bbb26.github.io
```

**Distribution**:
1. **Email** (if you collect emails — probably not worth it)
2. **Telegram channel** (free, easy to set up)
3. **Twitter thread** (post as 5-6 tweets)
4. **RSS feed** (for the nerds)
5. **Embedded on site** (as a "Daily Digest" card)

**Why it might work**:
- Frictionless consumption (no need to visit site)
- Brings users TO the site for details
- Feels personal ("here's what YOU need to know")
- Builds daily habit

**How to build it**:
- Write a `generate_digest.py` script
- Run it in GitHub Actions after data fetch
- Save to `/digest/2026-01-25.txt` (for RSS)
- Optional: Use GitHub Actions to post to Twitter API (free tier)

**Risk**: Might not get traction. But cost is ~1 day of dev work, and if it works, it's a massive growth lever.

---

## Actionable Priorities (Do This First)

If I were you, here's the order I'd execute:

### Week 1: Fix the Landing Page
1. Add "Destaques do Dia" section (Quick Win #1)
2. Simplify ranking to top 5 + bottom 5 (Quick Win #2)
3. Add avatars everywhere (Quick Win #3)
4. Move current paredão status ABOVE the fold

### Week 2: Improve Shareability
5. Add Open Graph tags (Quick Win #4)
6. Create Methodology page
7. Make repo public + good README
8. Generate first daily digest (Wild Idea)

### Week 3: Build Participant Profiles
9. Create profile page template (Big Bet #1)
10. Generate all 22 profile pages
11. Link from main pages

### Week 4: Consolidate Pages
12. Merge Painel + Trajetória into "Análise"
13. Merge Paredão + Arquivo into "Paredões"
14. Rename "O Que Mudou" → fold into "Hoje"

### Month 2: Add Interactivity
15. Pre-compute daily metrics JSON (Big Bet #2)
16. Add Observable date pickers
17. Let users compare any two dates

### Month 3: Scale & Polish
18. Add shareable report cards (Big Bet #3)
19. Mobile optimization pass
20. Accessibility audit

---

## Final Thoughts

You've built something genuinely valuable. The analysis is sharp, the data is clean, the insights are real. But right now it's packaged for people who ALREADY understand its value.

The redesign isn't about dumbing it down — it's about **guiding people to the good stuff**. Show them the highlights first, THEN let them explore the depths.

Think of it like a museum:
- **Current design**: Here's the archive room, go find what's interesting
- **Proposed design**: Here's the featured exhibit (hoje), here's the gallery (análise), here's the catalog (paredões)

You're 80% of the way to something people will visit daily and share widely. The last 20% is storytelling.

Make it about THEM (the participants, the drama, the strategy) not IT (the data, the charts, the metrics).

**You have the data. Now tell the story.**

---

**Rating Summary**:
- Current state: 7/10
- With Quick Wins: 8/10
- With Big Bets: 9/10
- Full vision realized: 10/10

This can be the definitive BBB26 analytics destination. You just need to make it feel less like a research tool and more like a daily ritual.
