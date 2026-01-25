# BBB26 Dashboard Review Handout

## Your Mission

You are reviewing a data dashboard for **Big Brother Brasil 26** (BBB26), a reality TV show where participants live together and vote each other out weekly. The dashboard tracks the **Queridômetro** — a daily reaction system where each participant assigns ONE emoji reaction to every other participant.

**Your task**: Analyze the current dashboard structure and propose improvements for:
1. **Information architecture** — What should users see first? What's the story?
2. **Landing page (index.qmd)** — What key info should appear here?
3. **Section ordering** — What sequence tells the best story?
4. **Cross-page integration** — What data should be repeated vs. linked?
5. **Missing insights** — What analysis would add value?

---

## The Game Context

### How BBB Works
- ~20 participants live in a house, isolated from the outside world
- Each week, participants go to **Paredão** (elimination vote)
- The public votes to eliminate one participant
- Last person standing wins

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

---

## Constraints

- Dashboard is in **Portuguese (Brazilian)**
- Uses **Quarto** for rendering (`.qmd` files with Python code cells)
- Uses **Plotly** for charts, **Bootstrap** for layout
- Data updates daily (automated via GitHub Actions)
- Manual data entry required for Paredão results and house votes
- **Hosting**: GitHub Pages (static only, no server)
- **Budget**: Free tier only (no paid services)

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

---

## Current Data Available

- **13+ daily snapshots** (Jan 13 - Jan 25, 2026)
- **22 active participants** (after 2 eliminations, 2 quits, 4 late entrants)
- **1 completed paredão** (Aline Campos eliminated Jan 21)
- **1 paredão in progress** (Leandro nominated via dinâmica)
- **Reactions change daily** — 95 changes detected yesterday

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

---

## Reference Links

- **Quarto Dashboards**: https://quarto.org/docs/dashboards/
- **Quarto Interactive**: https://quarto.org/docs/interactive/
- **Quarto Shiny**: https://quarto.org/docs/interactive/shiny/
- **Observable JS in Quarto**: https://quarto.org/docs/interactive/ojs/
- **GitHub Pages**: https://docs.github.com/en/pages
- **GitHub Actions for Quarto**: https://quarto.org/docs/publishing/github-pages.html

---

*This handout was created for AI agents to review the BBB26 dashboard and propose improvements. The dashboard tracks Big Brother Brasil 26 participant reactions (Queridômetro) and provides analysis of relationships, changes, and game dynamics.*
