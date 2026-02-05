# BBB26 Dashboard Review Handout (Jan 2026)

> **Note**: This handout was created Jan 25-26, 2026 to generate AI reviews (see `docs/reviews/`).
> Page references below use the names from that date — some were later renamed/restructured.
> Current page architecture: see `CLAUDE.md` → "Page Architecture".

## TL;DR — Quick Context

- **What**: Dashboard tracking daily emoji reactions between Big Brother Brasil 26 participants
- **Data**: 15+ API snapshots over 12 days, 22 active participants, ~462 daily reactions
- **Tech**: Quarto (Python) → Plotly charts → GitHub Pages (static HTML)
- **Problem**: How to best visualize social dynamics and predict voting behavior
- **Your job**: Propose improvements to information architecture, storytelling, and technical approach

## How to Submit Your Review

**Filename format**: `{MODEL_NAME}_{FOCUS}_{UNIQUE_ID}.md`

Examples:
- `gpt4o_ux_a1b2c3.md`
- `gemini_technical_x7y8z9.md`
- `claude-opus_holistic_m4n5o6.md`

**Save location**: `docs/reviews/` directory

**Focus areas**:
- `ux` — Information architecture, landing page, storytelling (sections 1-7)
- `technical` — Interactivity, deployment, data storage (sections 8-11)
- `polish` — SEO, testing, competitive analysis (sections 12-14)
- `holistic` — Fresh eyes, overall assessment, quick wins
- `dataviz` — Chart types, visual design, accessibility

Use a random 6-character alphanumeric ID to avoid filename conflicts if multiple agents use the same model.

---

## Your Mission

You are reviewing a data dashboard for **Big Brother Brasil 26** (BBB26), a reality TV show where participants live together and vote each other out weekly. The dashboard tracks the **Queridômetro** — a daily reaction system where each participant assigns ONE emoji reaction to every other participant.

**Your task**: Analyze the current dashboard structure and propose improvements for:
1. **Information architecture** — What should users see first? What's the story?
2. **Landing page (index.qmd)** — What key info should appear here?
3. **Section ordering** — What sequence tells the best story?
4. **Cross-page integration** — What data should be repeated vs. linked?
5. **Missing insights** — What analysis would add value?

**Fresh perspective encouraged**: You don't need to know BBB to contribute. Think about this as a social network analysis problem — how do you visualize relationships, changes, and predictions in a dynamic social graph?

---

## The Game Context

### How BBB Works
- ~20 participants live in a house, isolated from the outside world
- Each week, participants go to **Paredão** (elimination vote)
- The public votes to eliminate one participant
- Last person standing wins (prize: R$3 million / ~$600k USD)
- Season runs ~90 days (January → April 2026)

### Participant Groups
Participants are divided into groups that create natural rivalries:

| Group | Portuguese | Description |
|-------|------------|-------------|
| **Pipoca** | "Popcorn" | Unknown people, regular citizens |
| **Camarote** | "VIP Box" | Celebrities, influencers, public figures |
| **Veterano** | "Veteran" | Returning players from past seasons |

Additionally, each week participants are split into:
- **VIP**: Better food, comfort, privileges
- **Xepa**: Basic food, fewer privileges

Group dynamics matter: Do Pipocas band together against Camarotes? Do VIP members favor each other?

### The Queridômetro (Reaction System)
Every morning, participants record a **Raio-X** (video diary) and assign ONE reaction to each housemate:

| Emoji | Name | Meaning | Weight |
|-------|------|---------|--------|
| ❤️ | Coração | Love/support | +1.0 |
| 🌱 | Planta | Boring/wallflower | -0.5 |
| 💼 | Mala | Annoying/baggage | -0.5 |
| 🍪 | Biscoito | Attention-seeker | -0.5 |
| 💔 | Coração partido | Disappointment | -0.5 |
| 🐍 | Cobra | Sneaky/traitor | -1.0 |
| 🎯 | Alvo | Target | -1.0 |
| 🤮 | Vômito | Disgust | -1.0 |
| 🤥 | Mentiroso | Liar | -1.0 |

**Key insight**: Reactions are PUBLIC to other participants but they change daily. Someone who gave ❤️ yesterday can give 🐍 today.

### Strategic Importance
The Queridômetro reveals:
- **Alliances**: Mutual ❤️ pairs are likely allies
- **Rivalries**: Mutual negative pairs are declared enemies
- **Blind spots**: When A gives ❤️ to B, but B gives negative to A — A doesn't know B might vote against them
- **Voting patterns**: House votes often (but not always) correlate with reactions

### Why This Data Is Interesting (For Data/ML Folks)

Think of this as a **dynamic directed graph** with:
- **22 nodes** (participants)
- **462 edges** (each person → every other person)
- **9 edge types** (the emoji reactions)
- **Daily snapshots** (the graph changes every day)

**Interesting problems**:
1. **Community detection**: Can we find clusters/alliances from reaction patterns?
2. **Anomaly detection**: Who changed opinions dramatically? Why?
3. **Prediction**: Can reactions predict voting behavior? Eliminations?
4. **Sentiment analysis**: Aggregate reactions into a "popularity" score
5. **Time series**: How do relationships evolve over 90 days?
6. **Asymmetry analysis**: One-sided relationships (A loves B, B hates A) are strategically important

**Current approach**: We compute a "sentiment score" per participant:
```
sentiment = (hearts × 1.0) + (mild_negative × -0.5) + (strong_negative × -1.0)
```

### Key Metrics Currently Computed

| Metric | Formula | Used In |
|--------|---------|---------|
| **Sentiment Score** | `Σ(weights × reactions_received)` | Rankings, evolution chart |
| **Volatility** | Count of changed reactions given | O Que Mudou page |
| **Alliance Strength** | Days of mutual ❤️ | Trajetória page |
| **Rivalry Duration** | Days of mutual negative | Trajetória page |
| **Vulnerability** | Hearts given to enemies ÷ attacks on friends | Hostility analysis |
| **Group Favoritism** | % in-group ❤️ vs out-group ❤️ | VIP vs Xepa analysis |
| **Vote Coherence** | Did house vote match negative reaction? | Paredão analysis |

**Missing metrics we might want**:
- Trend (rising/falling over N days)
- Influence score (whose opinion changes others?)
- Cluster stability (do alliances hold?)
- Prediction confidence (how likely to be voted?)

---

## Target Audience

The dashboard serves multiple audiences with different needs:

| Audience | What They Want | Visit Pattern |
|----------|----------------|---------------|
| **Casual viewers** | "Who's popular? Who's fighting?" | Quick glance, mobile |
| **Superfans** | Deep analysis, predictions, all data | Daily deep dives |
| **Cartola players** | Fantasy points, strategic picks | Weekly planning |
| **Data enthusiasts** | Methodology, raw data, trends | Occasional exploration |

**Current design leans toward superfans** — lots of detailed charts, long pages. Is this the right balance?

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     GITHUB ACTIONS (4x daily)                    │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  fetch_data  │ →  │  quarto      │ →  │   deploy     │       │
│  │     .py      │    │   render     │    │  to Pages    │       │
│  └──────┬───────┘    └──────────────┘    └──────────────┘       │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                               │
│  │ GloboPlay    │  Only saves if                                │
│  │    API       │  data hash changed                            │
│  └──────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                │
│  ┌────────────────────┐  ┌────────────────────┐                 │
│  │  data/snapshots/   │  │  data/manual_      │                 │
│  │  ├─ 2026-01-13.json│  │  events.json       │                 │
│  │  ├─ 2026-01-14.json│  │  (Líder, Anjo,     │                 │
│  │  ├─ ...            │  │   Paredão results) │                 │
│  │  └─ 2026-01-25.json│  │                    │                 │
│  └────────────────────┘  └────────────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      QUARTO RENDER                               │
│  Each .qmd loads ALL snapshots → computes metrics → Plotly      │
│                                                                  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ index   │ │mudancas │ │trajetoria│ │ paredao │ │paredoes │   │
│  │  .qmd   │ │  .qmd   │ │  .qmd   │ │  .qmd   │ │  .qmd   │   │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘   │
│       │           │           │           │           │         │
│       ▼           ▼           ▼           ▼           ▼         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ index   │ │mudancas │ │trajetoria│ │ paredao │ │paredoes │   │
│  │ .html   │ │ .html   │ │  .html  │ │  .html  │ │  .html  │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     GITHUB PAGES (Static)                        │
│                                                                  │
│  https://username.github.io/BBB26/                              │
│  └── All HTML + Plotly JS + embedded data                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Current Participants (Jan 25, 2026)

22 active participants after 2 quits + 1 elimination + 4 late entrants:

| Name | Group | Status | Notes |
|------|-------|--------|-------|
| Alberto Cowboy | Camarote | Active | Week 1 Líder |
| Ana Paula Renault | Camarote | Active | |
| Babu Santana | Veterano | Active | Week 2 Líder |
| Brigido | Camarote | Active | |
| Chaiany | Pipoca | Active | Entered Jan 18 |
| Edilson | Camarote | Active | |
| Evelyne | Pipoca | Active | |
| Gabriela | Pipoca | Active | Entered Jan 18 |
| Jordana | Pipoca | Active | |
| Jonas Sulzbach | Veterano | Active | Week 2 Anjo |
| Juliano Floss | Camarote | Active | |
| Leandro | Pipoca | Active | Entered Jan 18, nominated via dinâmica |
| Luciano | Pipoca | Active | |
| Marcelo | Camarote | Active | Answered Big Fone |
| Matheus | Pipoca | Active | Entered Jan 18 |
| Milena | Pipoca | Active | |
| Paulo Augusto | Pipoca | Active | |
| Sarah Andrade | Veterano | Active | |
| Sol Vega | Pipoca | Active | |
| Solange Couto | Camarote | Active | |
| Yuri | Pipoca | Active | |
| Zena | Pipoca | Active | |
| ~~Henri Castelli~~ | Camarote | Quit Jan 15 | Desistente |
| ~~Pedro~~ | Pipoca | Quit Jan 19 | Desistente |
| ~~Aline Campos~~ | Camarote | Eliminated Jan 21 | 1º Paredão |

---

## Current Dashboard Structure

### 5 Pages

| Page | File | Purpose | Data Focus |
|------|------|---------|------------|
| **📊 Painel** | index.qmd | Main landing, current state | Today's snapshot |
| **📅 O Que Mudou** | mudancas.qmd | Daily changes | Yesterday → Today |
| **📈 Trajetória** | trajetoria.qmd | Season evolution | All historical data |
| **🗳️ Paredão** | paredao.qmd | Current elimination vote | Manual + API data |
| **📚 Arquivo** | paredoes.qmd | Historical eliminations | Per-paredão analysis |

---

## Page-by-Page Content

### 📊 PAINEL (index.qmd) — Current State

**Current sections (in order):**
1. Visão Geral — Stats: participant count, reaction count, days of data
2. Cronologia do Jogo — Timeline table of entries/exits
3. Ranking de Sentimento — Bar chart of sentiment scores
4. Tabela Cruzada de Reações — Heatmap of who gave what to whom
5. Reações Recebidas — Table breakdown by emoji type
6. Perfis Individuais — Expandable cards with strategic analysis per person

**Callouts link to**: Paredão, O Que Mudou, Trajetória

**Key visualizations**:
- Horizontal bar chart (sentiment ranking)
- Heatmap with emoji annotations (22×22 reaction matrix)
- Expandable accordion cards (per-participant profiles)

---

### 📅 O QUE MUDOU (mudancas.qmd) — Daily Changes

**Current sections (in order):**
1. Date comparison alert
2. Summary stats (# changes, % relationships changed)
3. Quem Ganhou e Quem Perdeu — Diverging bar of sentiment delta
4. Mapa de Diferenças — Heatmap with emoji transitions, ⭐ for dramatic
5. Volatilidade — Who changed their opinions most
6. Fluxo de Reações — Sankey diagram of reaction migrations
7. Centro do Drama — Scatter of who's involved in dramatic changes
8. Mudanças Dramáticas summary — Count of big swings
9. Evolução das Hostilidades — Bar chart of hostility changes
10. Hostility details — Collapsible list of new/resolved hostilities

---

### 📈 TRAJETÓRIA (trajetoria.qmd) — Season Evolution

**Current sections (in order):**
1. Stats alert (days analyzed)
2. Evolução do Sentimento — Line chart over time
3. Alianças Mais Consistentes — Top 15 mutual ❤️ pairs
4. Rivalidades Mais Persistentes — Top 15 mutual negative pairs
5. Mudanças Entre Dias — Bar chart of ❤️↔Neg transitions per day
6. Vira-Casacas — Who changes opinions most frequently
7. Dinâmica Vip vs Xepa — In-group vs out-group favoritism
8. Rivalidades Mais Longas — Longest mutual hostilities
9. Hostilidades Unilaterais Mais Longas — Longest one-sided attacks
10. Saldo Over Time — Balance (currency) timeline
11. Grafo de Relações — Network visualization
12. Hostilidades do Dia — Current hostility summary
13. Quem Ataca Quem Lhe Dá ❤️ — Attacking friendly people
14. Quem Dá ❤️ a Inimigos — Giving love to enemies (vulnerability)
15. Quem Tem Mais Inimigos — Most polarizing
16. Listas de Hostilidades — Full lists
17. Insights do Jogo — Key strategic findings
18. Clusters de Afinidade — Hierarchical clustering analysis
19. Cluster Heatmap — Reordered by affinity groups
20. Saldo vs Sentimento — Correlation scatter
21. Quem Dá Mais Negatividade — Negative givers profile

---

### 🗳️ PAREDÃO (paredao.qmd) — Current Elimination

**Current sections (in order):**
1. API status alert (who has Paredão role)
2. Status header (em formação / em votação / resultado)
3. Nominee cards with photos
4. Formation narrative
5. Leader & immunity info
6. House votes table
7. Result bar chart (if finalized)
8. Vote vs Reaction coherence table
9. Reações Preveem Votos? — Scatter with correlation
10. Votaram no que mais detestam? — Pie chart
11. O Caso [Most Voted] — Analysis
12. Indicação do Líder — Leader nomination analysis

---

### 📚 ARQUIVO (paredoes.qmd) — Historical Eliminations

**Current sections:**
1. Summary table of all eliminations
2. For each paredão: Full analysis (same as Paredão page) + sentiment ranking + reactions table for that date

---

## Key Questions for Your Review

### 1. Landing Page (Painel) Story

**Current flow**: Stats → Timeline → Ranking → Heatmap → Table → Profiles

**Questions to consider**:
- What do users want to know FIRST when they check the Queridômetro?
- Should we lead with "what changed" instead of static rankings?
- Is the timeline useful on the landing page or better in Trajetória?
- Should we show a "highlights" or "destaques" summary at the top?
- What's the hook that makes someone want to explore more?

### 2. Section Ordering & Storytelling

**Questions**:
- Does the current section order tell a coherent story?
- Should we group by theme (relationships, individuals, changes)?
- What's the narrative arc? (Overview → Details → Insights?)
- Are there sections that should be moved to different pages?

### 3. Cross-Page Data

**Currently duplicated**:
- Sentiment ranking (Painel + Arquivo per paredão)
- Hostility analysis (Trajetória + Paredão)
- Reaction coherence (Paredão + Arquivo)

**Questions**:
- What should appear on the landing page that links to deeper analysis?
- Should "O Que Mudou" highlights appear on Painel?
- Should current paredão status be more prominent on Painel?

### 4. Missing Insights

**Currently NOT shown**:
- Daily "highlights" or "destaques" auto-generated summary
- Predictions (who might be voted out based on hostilities)
- Participant focus mode (deep dive on one person)
- Comparison between any two dates (not just yesterday→today)
- "Watch list" — participants in risky positions
- Trending: who's rising/falling over multiple days

**Questions**:
- What analysis would casual viewers find most interesting?
- What would superfans want that we don't have?
- What game-strategic insights are we missing?

### 5. Visual Hierarchy

**Questions**:
- Are the most important insights visible without scrolling?
- Is there too much content on any page?
- Should some sections be collapsed by default?
- Are charts the right size and type for the data?

---

## Additional Investigation Areas

### 6. Page Layout: Traditional Pages vs Dashboard Format

**Current approach**: 5 separate long-scrolling pages with sections

**Alternative**: Quarto Dashboards — a dedicated dashboard layout format
- Reference: https://quarto.org/docs/dashboards/

**Questions to investigate**:
- Would a dashboard layout (cards, rows, columns, tabsets) work better than long pages?
- Should some pages remain as articles while others become dashboards?
- How would a dashboard layout affect mobile responsiveness?
- What's the trade-off between information density and readability?
- Could we have a "quick glance" dashboard + "deep dive" article pages?

**Consider**:
- Dashboards use `format: dashboard` in YAML
- Support for cards, rows, columns, tabsets, sidebars
- Value boxes for KPIs
- Different from current `page-layout: full` approach

### 7. Interactivity: User-Controlled Date Selection

**Current approach**:
- "O Que Mudou" always compares yesterday → today (hardcoded)
- Users cannot select which dates to compare
- All analysis is pre-rendered (static HTML)

**Alternative**: Quarto Interactive features
- Reference: https://quarto.org/docs/interactive/

**Options to investigate**:

1. **Shiny for Python** (`format: dashboard` + `server: shiny`)
   - Full interactivity with Python backend
   - Requires server to run (not just static hosting)
   - Users could select any date range

2. **Observable JS** (client-side)
   - Runs in browser, no server needed
   - Can create reactive inputs (date pickers, dropdowns)
   - Data must be embedded in page or fetched via API

3. **Widgets (ipywidgets/Jupyter Widgets)**
   - Interactive controls in notebooks
   - Limited support in static HTML output

**Questions to investigate**:
- Is interactivity worth the complexity?
- Can we achieve date selection with client-side JS only?
- What's the impact on GitHub Pages hosting (static only)?
- Could we pre-render multiple date comparisons and use tabsets?
- Is a "date picker" essential or a nice-to-have?

**Specific use cases for interactivity**:
- Compare any two dates (not just yesterday→today)
- Filter participants by group
- Toggle visibility of participants in line charts
- Zoom into specific time periods
- Select a participant to focus on

### 8. Deployment & Hosting Considerations

**Current plan**:
- Host on **GitHub Pages** (static site)
- Automated updates via **GitHub Actions** (4x daily cron)
- Pre-render all pages with Quarto
- No server-side processing

**Architecture**:
```
GitHub Actions (cron) → fetch_data.py → quarto render → GitHub Pages
```

**Questions to investigate**:

1. **Is static hosting sufficient?**
   - Pros: Free, simple, no server maintenance
   - Cons: No real-time interactivity, all data must be pre-baked

2. **Should we consider alternatives?**
   - **Shiny Server** (shinyapps.io, Posit Connect) — for full interactivity
   - **Streamlit** — simpler Python dashboards
   - **Vercel/Netlify** — static but with serverless functions
   - **Self-hosted** — full control but maintenance burden

3. **Robustness concerns**:
   - What if GitHub Actions fails?
   - What if the API is down?
   - How do we handle missing data gracefully?
   - Should we have fallback/cache mechanisms?
   - What's the error notification strategy?

4. **Performance at scale**:
   - Current: ~13 snapshots, renders in ~2-3 minutes
   - End of season: ~90+ snapshots — will render time be acceptable?
   - Should we optimize which pages re-render?
   - Could we use incremental builds?

5. **User experience considerations**:
   - How fresh does the data need to be?
   - Is 4x daily updates enough?
   - Should users know when data was last updated?
   - Do we need a "loading" or "updating" indicator?

**Provide recommendations on**:
- Is GitHub Pages + Actions robust enough for a public-facing dashboard?
- What safeguards should we add?
- Should we change the deployment strategy?
- How do we balance complexity vs reliability?

### 9. New Page: Cartola BBB (Fantasy Game)

**Context**: Cartola BBB is a fantasy game where viewers pick participants and earn points based on in-game events. We want to add a dedicated page tracking Cartola points.

**Reference**: https://gshow.globo.com/realities/bbb/bbb-26/cartola-bbb/noticia/o-que-e-cartola-bbb-entenda-como-funciona-a-novidade-do-reality.ghtml

**Official Point System**:

| Event | Points |
|-------|--------|
| Líder | +80 |
| Anjo | +45 |
| Enviado Para o Quarto Secreto | +40 |
| Imunizado | +30 |
| Atendeu o Big Fone | +30 |
| Salvo do paredão | +25 |
| Não eliminado no paredão | +20 |
| Não emparedado | +10 |
| VIP | +5 |
| Não recebeu votos da casa | +5 |
| Monstro retirado do VIP | -5 |
| Monstro | -10 |
| Emparedado | -15 |
| Eliminado | -20 |
| Desclassificado | -25 |
| Desistente | -30 |

**Data availability**:
- Most events are trackable from the API (`roles` field: Líder, Anjo, Monstro, Paredão)
- Some events require manual tracking (Big Fone, Quarto Secreto, immunity)
- VIP/Xepa is in the `memberOf` field
- House votes are manually tracked in `votos_casa`

**Manual events file**: `data/manual_events.json` — structured JSON with:
- `participants`: Exit status (desistente, eliminada, desclassificado) with dates
- `weekly_events`: Per-week Líder, Anjo, Monstro, Big Fone, immunity, VIP members
- `special_events`: Dinâmicas, new entrants, one-off events
- `cartola_points_log`: Pre-calculated weekly points per participant

**Already tracked exits**:
- Henri Castelli: desistente (Jan 15) → -30 pts
- Pedro: desistente (Jan 19) → -30 pts
- Aline Campos: eliminada (Jan 21, 1º Paredão) → -20 pts

**Questions to investigate**:

1. **Visualizations**: What charts/tables would be most useful?
   - Cumulative points timeline?
   - Points breakdown by event type?
   - Weekly performance comparison?
   - "Best picks" analysis?

2. **Integration with existing data**:
   - Can we auto-calculate most points from existing API data?
   - What manual tracking is needed?
   - Should this link to/from other pages?

3. **User value**:
   - Who plays Cartola BBB? What do they want to see?
   - Is this a primary feature or supplementary?
   - Should there be a "my team" simulator?

4. **Page structure**:
   - Standalone page or section within existing page?
   - How much historical data to show?
   - Real-time leaderboard vs weekly summaries?

**Deliverable**: Propose visualizations and page structure for a Cartola BBB page. Consider what data we can auto-calculate vs. what needs manual entry.

### 10. Data Storage Architecture Review

**Context**: We're 12 days into an ~90-day show. The current data architecture needs to scale well AND support future interactive features.

**Current data storage**:

```
data/
├── snapshots/                    # API snapshots (~270KB each)
│   ├── 2026-01-13_17-18-02.json  # Full participant + reaction state
│   ├── 2026-01-14_15-44-42.json
│   ├── ...                       # Currently 15 files, will grow to ~100+
│   └── 2026-01-25_16-47-24.json
├── latest.json                   # Copy of most recent snapshot
├── manual_events.json            # NEW: Manual game events (see below)
└── CHANGELOG.md                  # Data timeline documentation
```

**Snapshot structure** (each ~270KB):
```json
{
  "_metadata": {
    "fetched_at": "2026-01-25T16:47:24Z",
    "change_types": ["reactions", "balance"],
    "reactions_hash": "abc123..."
  },
  "participants": [
    {
      "name": "Alberto Cowboy",
      "balance": 4500,
      "characteristics": {
        "memberOf": "VIP",
        "roles": ["Líder"],
        "eliminated": false
      },
      "receivedReactions": [
        {"reaction": {"name": "Coração"}, "amount": 15, "givers": [...]},
        {"reaction": {"name": "Cobra"}, "amount": 3, "givers": [...]}
      ]
    },
    // ... 21 more participants
  ]
}
```

**NEW: Manual events file** (`data/manual_events.json`):
```json
{
  "participants": {
    "Henri Castelli": {"status": "desistente", "exit_date": "2026-01-15", "fontes": [...]},
    "Aline Campos": {"status": "eliminada", "exit_date": "2026-01-21", "paredao_numero": 1, "fontes": [...]}
  },
  "weekly_events": [
    {"week": 1, "lider": "Alberto Cowboy", "anjo": null, "big_fone": {...}, "vip_members": [...], "fontes": [...]},
    {"week": 2, "lider": "Babu Santana", "anjo": "Jonas Sulzbach", "monstro": ["Chaiany"], "fontes": [...]}
  ],
  "special_events": [
    {"date": "2026-01-18", "type": "entrada_novos", "participants": ["Chaiany", "Gabriela", ...], "fontes": [...]}
  ],
  "cartola_points_log": [
    {"participant": "Alberto Cowboy", "week": 1, "events": [...], "total": 95}
  ]
}
```

**Scaling projections**:

| Timepoint | Snapshots | Total Size | Unique Days |
|-----------|-----------|------------|-------------|
| Now (Day 12) | 15 | ~4 MB | 12 |
| Day 30 | ~40 | ~11 MB | 30 |
| Day 60 | ~80 | ~22 MB | 60 |
| Day 90 (end) | ~120 | ~32 MB | 90 |

**Current render time**: ~2-3 minutes for 5 pages with 15 snapshots

**Questions to investigate**:

1. **Is JSON the right format?**
   - Pros: Human-readable, easy to diff in git, flexible schema
   - Cons: Verbose, slow to parse at scale, no indexing
   - Alternatives: SQLite, Parquet, DuckDB
   - Would a database help with interactive date queries?

2. **File-per-snapshot vs consolidated storage**:
   - Current: One JSON file per API fetch (fine-grained history)
   - Alternative: Single file with all daily data (faster to load)
   - Alternative: One file per day with multiple captures (balance granular + fast)
   - How does this affect the ability to select arbitrary dates?

3. **Manual events storage**:
   - Current: Single JSON file with nested structure
   - Scales linearly (90 weeks worth of events is small)
   - Should this be integrated with API data or kept separate?
   - How do we ensure `fontes` (source URLs) are filled in?

4. **Interactive date selection requirements**:
   - User wants to compare ANY two dates (not just yesterday→today)
   - Currently all snapshots are loaded into memory at render time
   - For client-side interactivity: all data must be embedded or fetchable
   - For server-side (Shiny): data can be loaded on-demand

5. **Pre-computation vs on-demand**:
   - Current: All analysis computed at render time
   - Alternative: Pre-compute daily metrics into a summary file
   - Example: `data/daily_metrics.json` with sentiment scores, change counts, etc.
   - Would speed up rendering AND enable client-side date comparison

6. **Git repository size**:
   - ~32 MB of JSON by end of season is acceptable
   - But frequent commits of large files bloat git history
   - Consider: `.gitattributes` with LFS for snapshots?
   - Consider: Only commit daily summaries, keep raw snapshots elsewhere?

7. **Backward compatibility**:
   - Old snapshots are raw arrays `[...]`, new ones have `{_metadata: ..., participants: [...]}`
   - Code handles both, but should we migrate old files?
   - What happens if schema changes mid-season?

**Specific scenarios to design for**:

A. **"Show me the queridômetro for January 18"**
   - Need to find/load snapshot for that date
   - Currently: Load all, filter in Python
   - Better: Index by date, load only needed file

B. **"Compare Aline's reactions Jan 15 vs Jan 20"**
   - Need two snapshots, extract one participant
   - Current: Not possible in UI (hardcoded yesterday→today)
   - Desired: Date pickers, participant selector

C. **"What was Leandro's Cartola score in Week 2?"**
   - Need manual_events.json + potentially API data
   - Manual file has the calculation
   - Should we auto-calculate from API where possible?

D. **"Show all Big Fone events"**
   - Need to query across weekly_events
   - Current: Manual file has per-week structure
   - Easy to filter in Python, harder in pure client-side JS

**Deliverable**: Evaluate whether current storage approach scales well. Propose alternatives if needed, considering:
- Interactive date selection (any-to-any comparison)
- Client-side vs server-side data access
- Git repository size over 90 days
- Render time at scale
- Manual events integration
- Migration complexity (if recommending changes)

### 11. Mobile & Accessibility

**Current state**:
- Bootstrap grid provides basic responsiveness
- Charts use Plotly's built-in responsive mode
- No specific mobile optimization done
- No accessibility audit performed
- Dark theme may have contrast issues

**Questions to investigate**:

1. **Mobile experience**:
   - Are heatmaps readable on phone screens? (22×22 matrix)
   - Should we have a mobile-specific view?
   - Are touch interactions working well with Plotly?
   - Is the navbar usable on mobile?

2. **Accessibility**:
   - Do charts have alt text?
   - Is color the only way to convey information? (color blindness)
   - Are emoji readable by screen readers?
   - Is the contrast ratio sufficient in dark theme?
   - Can users navigate with keyboard only?

3. **Performance on low-end devices**:
   - Page load time with many Plotly charts?
   - Memory usage with large heatmaps?
   - Should we lazy-load charts below the fold?

**Deliverable**: Assess mobile usability and accessibility. Recommend specific improvements.

### 12. SEO, Social Sharing & Discoverability

**Current state**:
- Basic Quarto-generated meta tags
- No Open Graph / Twitter Card metadata
- No structured data (JSON-LD)
- Site not yet indexed by search engines

**Questions to investigate**:

1. **SEO**:
   - What search terms should this rank for?
   - Should each page have unique meta descriptions?
   - Is the URL structure SEO-friendly?

2. **Social sharing**:
   - What should the preview look like when shared on Twitter/WhatsApp?
   - Should we generate shareable images (charts as PNGs)?
   - Would a "share this participant" feature add value?

3. **Discoverability**:
   - How will BBB fans find this dashboard?
   - Should there be a sitemap.xml?
   - Would embedding in fan forums/Reddit drive traffic?

**Deliverable**: Recommend SEO and social sharing improvements compatible with static hosting.

### 13. Testing & Quality Assurance

**Current state**:
- No automated tests
- Manual verification after each render
- Some Quarto warnings (Pandoc div issues) that don't affect output

**Questions to investigate**:

1. **What should be tested?**
   - Data loading (all snapshots parse correctly)
   - Calculations (sentiment scores, change detection)
   - Chart rendering (no errors, correct data)
   - Links (no broken internal links)

2. **Testing approaches for static sites**:
   - Python unit tests for data processing?
   - Visual regression testing for charts?
   - Link checking in CI?
   - Lighthouse performance audits?

3. **Error handling**:
   - What happens if API returns unexpected data?
   - What if a snapshot file is corrupted?
   - Should we have fallback displays?

**Deliverable**: Recommend a testing strategy appropriate for a Quarto static site.

### 14. Comparison with Similar Projects

**Question**: Are there other BBB fan dashboards or similar reality TV analytics we can learn from?

**Things to research**:
- Other BBB fan sites (Twitter accounts, blogs)
- Reality TV analytics for Survivor, Love Island, etc.
- Sports analytics dashboards (similar data viz challenges)
- Social network visualization best practices

**Deliverable**: Identify 2-3 comparable projects and what we can learn from them.

---

## Visual Design & Technical Details

### Current Theme
- **Dark theme**: Bootswatch "darkly" theme (#222 background)
- **Custom Plotly template**: `bbb_dark` with #303030 chart backgrounds
- **Full-width layout**: `page-layout: full` (no sidebar margins)
- **TOC sidebar**: Table of contents on right side for navigation
- **Responsive**: Bootstrap grid, but not optimized for mobile

### Chart Features
- **Fullscreen mode**: All Plotly charts have an "Expandir" button (top-left) that opens a modal
- **Interactive**: Plotly charts support hover, zoom, pan
- **Emoji rendering**: Native emoji in heatmap cells (font-size 14px)

### Code Structure
Each `.qmd` page follows this pattern:
```
1. YAML header (title, format options)
2. Setup cell (imports, constants, theme)
3. Data loading cell (load all snapshots)
4. Processing cells (compute metrics)
5. Visualization cells (Plotly figures)
6. Markdown narrative between cells
```

**No shared state between pages** — each page loads data independently.

---

## Constraints

- Dashboard is in **Portuguese (Brazilian)**
- Uses **Quarto** for rendering (`.qmd` files with Python code cells)
- Uses **Plotly** for charts, **Bootstrap** for layout
- Data updates daily (automated via GitHub Actions)
- Manual data entry required for Paredão results and house votes
- **Hosting**: GitHub Pages (static only, no server)
- **Budget**: Free tier only (no paid services)
- **No login/auth**: Public dashboard, no user accounts
- **No real-time**: Data refreshes 4x daily, not live

### What NOT to Suggest (Impractical Given Constraints)

To save time, avoid suggesting:
- ❌ **Paid services** (AWS, paid Shiny hosting, databases-as-a-service)
- ❌ **User accounts/login** (would require backend)
- ❌ **Real-time updates** (API updates ~1x daily, we fetch 4x)
- ❌ **Machine learning models requiring training** (no compute budget)
- ❌ **Mobile app** (out of scope — web only)
- ❌ **Scraping additional data sources** (legal/ethical concerns)
- ❌ **Replacing Quarto** (too much existing investment)

**DO suggest**: Static-site-friendly solutions, client-side JS, pre-computation strategies, UX improvements, new visualizations, better storytelling

---

## Deliverables

Please provide:

1. **Executive Summary** (3-5 bullet points of biggest opportunities)

2. **Landing Page Recommendations**
   - Proposed section order
   - New sections to add
   - Sections to move/remove
   - Key "above the fold" content

3. **Cross-Page Architecture**
   - What should be on multiple pages
   - What should only be on specialized pages
   - Navigation flow improvements

4. **New Features/Insights**
   - Ranked by impact and feasibility
   - Brief description of each

5. **Section Ordering Recommendations**
   - For each page, proposed new order
   - Rationale for changes

6. **Storytelling Narrative**
   - What's the story the dashboard should tell?
   - How should users progress through the content?

7. **Layout Format Recommendation**
   - Should we use Quarto Dashboards for any/all pages?
   - Pros and cons of dashboard vs article layout
   - Specific pages that would benefit from dashboard format
   - Mock layout description if recommending change

8. **Interactivity Assessment**
   - Is interactivity essential, nice-to-have, or unnecessary?
   - Recommended approach (Shiny, Observable, pure JS, or none)
   - Specific interactive features worth implementing
   - Trade-offs with static hosting

9. **Deployment & Robustness Review**
   - Is the current GitHub Pages + Actions plan sufficient?
   - Recommended safeguards or improvements
   - Alternative hosting options to consider (if any)
   - Performance concerns and mitigations

10. **Cartola BBB Page Design**
    - Proposed visualizations (charts, tables, cards)
    - Page structure and section order
    - Data that can be auto-calculated vs manual entry
    - Integration points with existing pages
    - Target audience considerations (casual vs serious Cartola players)

11. **Data Storage Architecture Assessment**
    - Is current JSON-per-snapshot approach optimal for 90+ days?
    - Recommendations for interactive date selection support
    - Pre-computation strategies for faster rendering
    - Manual events file structure evaluation
    - Git repository size management
    - Migration path if recommending changes

12. **Mobile & Accessibility Review**
    - Mobile usability assessment
    - Accessibility gaps and fixes
    - Performance on low-end devices
    - Recommended improvements

13. **SEO & Social Sharing Strategy**
    - Meta tags and Open Graph setup
    - Shareable content features
    - Discoverability recommendations

14. **Testing Strategy Proposal**
    - What to test and how
    - CI/CD integration suggestions
    - Error handling improvements

15. **Competitive Analysis** (Optional)
    - Similar projects and learnings
    - Best practices from other domains

---

## Current Data Available

- **15+ snapshots** across 12 unique days (Jan 13 - Jan 25, 2026)
- **22 active participants** (after 2 eliminations, 2 quits, 4 late entrants)
- **1 completed paredão** (Aline Campos eliminated Jan 21)
- **1 paredão in progress** (Leandro nominated via dinâmica)
- **Reactions change daily** — 95 changes detected yesterday
- **Manual events file** (`data/manual_events.json`) — tracking non-API game events

**Data from API** (automatic):
- `roles`: Líder, Anjo, Monstro, Paredão
- `memberOf`: VIP or Xepa group
- `balance`: Estalecas currency
- `receivedReactions`: Full reaction graph

**Data from manual tracking** (`manual_events.json`):
- Desistentes/eliminados with dates and reasons
- Weekly events: Líder, Anjo, Monstro, Big Fone, VIP members
- Special events: Dinâmicas, new entrants
- Cartola points log (calculated weekly)
- Source URLs (`fontes`) for each entry

### Sample Data (For Understanding)

**Example: One participant's received reactions**
```json
{
  "name": "Jordana",
  "receivedReactions": [
    {"reaction": {"name": "Coração"}, "amount": 12, "givers": ["Alberto Cowboy", "Ana Paula Renault", ...]},
    {"reaction": {"name": "Cobra"}, "amount": 5, "givers": ["Brigido", "Edilson", ...]},
    {"reaction": {"name": "Planta"}, "amount": 3, "givers": ["Leandro", "Matheus", ...]},
    {"reaction": {"name": "Mala"}, "amount": 1, "givers": ["Chaiany"]}
  ]
}
```

**Example: Day-over-day change**
```
Jan 24 → Jan 25:
  Marcelo: gave Solange ❤️ → now gives 🐍 (dramatic shift!)
  Jordana: gave Babu ❤️ → now gives 💔 (mild shift)
  Ana Paula: gave Brigido 🐍 → still gives 🐍 (no change)
```

**Example: Hostility detection**
```
Two-sided (mutual enemies):
  Ana Paula Renault ↔ Brigido (both give negative since Day 1)

One-sided (blind spot):
  Leandro gives 🐍 to Gabriela
  Gabriela gives ❤️ to Leandro (she doesn't know!)
```

---

## Open Questions We're Uncertain About

These are decisions where we'd love multiple perspectives:

1. **Should the landing page lead with "what changed" or "current state"?**
   - Argument for changes: More engaging, news-like, daily hook
   - Argument for state: Simpler mental model, overview first

2. **Is 5 pages too many or not enough?**
   - Could combine some pages (e.g., merge Paredão + Arquivo)
   - Could split Trajetória (it has 21 sections!)
   - Could add new pages (Cartola, Participant Focus)

3. **How important is interactivity really?**
   - Is date comparison essential or a nice-to-have?
   - Would pre-rendered tabs (Jan 13, Jan 14, ...) be enough?
   - Is the complexity of Observable/Shiny worth it?

4. **What's the right balance for mobile?**
   - Redesign everything for mobile-first?
   - Keep desktop-focused with basic mobile fallback?
   - Create a separate mobile view?

5. **Should we pursue Cartola BBB integration?**
   - Lots of manual data entry required
   - Different audience than Queridômetro analysis
   - Could be a differentiator vs other fan sites

6. **How much prediction/speculation should we include?**
   - "Who's at risk?" analysis could be valuable
   - But predictions can be wrong and misleading
   - Line between analysis and speculation?

---

## Success Criteria

A good review will:
- Prioritize the **user's perspective** (what do they want to know?)
- Consider **casual viewers** AND **superfans**
- Be **actionable** (specific recommendations, not vague suggestions)
- Respect the **existing work** while identifying improvements
- Think about **storytelling** — what narrative are we telling?
- Be **realistic** about constraints (free hosting, static site, manual data entry)
- Consider **technical trade-offs** (complexity vs value)
- Provide **specific examples** when recommending changes
- **Answer the open questions** above with clear reasoning

---

## Reference Links

- **Quarto Dashboards**: https://quarto.org/docs/dashboards/
- **Quarto Interactive**: https://quarto.org/docs/interactive/
- **Quarto Shiny**: https://quarto.org/docs/interactive/shiny/
- **Observable JS in Quarto**: https://quarto.org/docs/interactive/ojs/
- **GitHub Pages**: https://docs.github.com/en/pages
- **GitHub Actions for Quarto**: https://quarto.org/docs/publishing/github-pages.html

---

## Known Issues & Limitations

Things we already know need work:

1. **Trajetória page is very long** — 21 sections, hard to navigate
2. **Heatmaps are hard to read on small screens** — 22×22 matrix with emoji
3. **No "quick summary"** — users must scroll to find insights
4. **Manual data entry is tedious** — paredão info entered by hand
5. **No predictions** — we analyze past data but don't project future
6. **Network graph is CPU-intensive** — loads slowly
7. **Missing Jan 18 data** — gap in historical snapshots (unrecoverable)
8. **Render time will grow** — currently 2-3 min, may increase with more data

---

## How to Use This Handout with Multiple AI Models

This handout is designed to get diverse perspectives from different AI models. Suggested approach:

### Assign Different Focus Areas

| Model | Focus | Why |
|-------|-------|-----|
| **Model A** | UX/Information Architecture (#1-6) | Storytelling, user flow |
| **Model B** | Technical Implementation (#7-11) | Interactivity, data, hosting |
| **Model C** | Polish & Growth (#12-15) | Mobile, SEO, testing, competitors |

### Suggested Prompts

**For UX focus**:
> "Review the BBB26 dashboard handout focusing on sections 1-6. Prioritize actionable recommendations for landing page design and storytelling. Think from a casual viewer's perspective."

**For Technical focus**:
> "Review the BBB26 dashboard handout focusing on sections 7-11. Evaluate the interactivity vs static trade-offs. Propose a data architecture that enables date comparison while staying on free hosting."

**For Polish focus**:
> "Review the BBB26 dashboard handout focusing on sections 12-15. Identify quick wins for mobile, accessibility, and SEO. Find comparable projects we can learn from."

### Consolidation

After collecting responses, look for:
- **Consensus**: Ideas multiple models suggest → high confidence
- **Conflicts**: Contradictory recommendations → need human decision
- **Unique insights**: Ideas only one model had → worth exploring
- **Impractical suggestions**: Ideas that violate constraints → filter out

---

## Appendix: File Structure

```
BBB26/
├── index.qmd              # 📊 Painel (landing page)
├── mudancas.qmd           # 📅 O Que Mudou (daily changes)
├── trajetoria.qmd         # 📈 Trajetória (season evolution)
├── paredao.qmd            # 🗳️ Paredão (current elimination)
├── paredoes.qmd           # 📚 Arquivo (historical eliminations)
├── _quarto.yml            # Site configuration
├── data/
│   ├── snapshots/         # API snapshots (15+ JSON files)
│   ├── latest.json        # Most recent snapshot
│   ├── manual_events.json # Manual game events
│   └── CHANGELOG.md       # Data timeline
├── scripts/
│   ├── fetch_data.py      # API fetcher
│   └── audit_snapshots.py # Data audit tool
├── assets/
│   ├── plotly-fullscreen.css
│   └── plotly-fullscreen.js
├── docs/
│   └── AI_REVIEW_HANDOUT.md  # This file
├── .github/workflows/
│   └── daily-update.yml   # GitHub Actions (4x daily)
├── CLAUDE.md              # Project documentation
├── IMPLEMENTATION_PLAN.md # Development roadmap
└── requirements.txt       # Python dependencies
```

---

*This handout was created for AI agents to review the BBB26 dashboard and propose improvements. The dashboard tracks Big Brother Brasil 26 participant reactions (Queridômetro) and provides analysis of relationships, changes, and game dynamics.*

**Version**: 2026-01-25 | **Author**: Human + Claude collaboration
