# Dashboard Reorganization Plan

> **Status**: In progress — ~60% complete
> **Parent document**: See `IMPLEMENTATION_PLAN.md` for overall project status
>
> **Progress Summary (2026-01-25)**:
> - index.html reduced from 841KB to 584KB (-31%)
> - Created mudancas.qmd (O Que Mudou) — 195KB
> - Created trajetoria.qmd (Trajetória) — 175KB
> - Updated paredao.qmd skeleton — 69KB
> - Remaining: Move Hostilidades Persistentes, Saldo sections (mixed 📸+📈)

## Current State

The `index.qmd` has grown to include **25+ sections** with different data sources:
- 📸 Daily snapshot data (current state)
- 📅 Day-over-day comparisons
- 📈 Accumulated historical data
- 🗳️ Manual paredão data

This mix makes the page heavy and unfocused. Users have different needs:
- **Casual viewer**: "What's happening today?"
- **Strategy analyst**: "How have things evolved?"
- **Paredão tracker**: "What happened in voting?"

---

## Complete Section Audit (Current index.qmd)

Every section currently in `index.qmd`, with proposed destination:

| # | Current Section | Data Type | Destination | Notes |
|---|-----------------|-----------|-------------|-------|
| 1 | Visão Geral | 📸 | **Painel** | Keep — overview stats |
| 2 | Cronologia do Jogo | 📈 | **Trajetória** | Timeline of entries/exits |
| 3 | Resultado do Paredão | 🗳️ | **Paredão** | Current paredão display |
| 4 | Reações Preveem Votos? | 🗳️ | **Paredão** | Vote vs reactions scatter |
| 5 | Votação da Casa vs Reações | 🗳️ | **Paredão** | Coherence table |
| 6 | Ranking de Sentimento | 📸 | **Painel** | Keep — main chart |
| 7 | O Que Mudou Hoje? (parent) | 📅 | **O Que Mudou** | All subsections move |
| 7a | — Quem Ganhou e Quem Perdeu | 📅 | **O Que Mudou** | Diverging bar |
| 7b | — Mapa de Diferenças | 📅 | **O Que Mudou** | Heatmap |
| 7c | — Quem Mais Mudou de Opinião? | 📅 | **O Que Mudou** | Volatility bar |
| 7d | — Fluxo de Reações (Sankey) | 📅 | **O Que Mudou** | Sankey diagram |
| 7e | — Mudanças Dramáticas | 📅 | **O Que Mudou** | Text highlights |
| 7f | — Mudanças em Hostilidades | 📅 | **O Que Mudou** | One/two-sided changes |
| 8 | Evolução do Sentimento | 📈 | **Trajetória** | Line chart over time |
| 9 | Tabela Cruzada de Reações | 📸 | **Painel** | Heatmap who→whom |
| 10 | Alianças Mais Consistentes | 📈 | **Trajetória** | Accumulated |
| 11 | Rivalidades Mais Persistentes | 📈 | **Trajetória** | Accumulated |
| 12 | Grafo de Relações | 📸 | **Painel** | Network viz |
| 13 | Hostilidades do Dia | 📸 | **Painel** | Keep — strategic insight |
| 14 | Hostilidades Persistentes | 📈 | **Trajetória** | Move — accumulated |
| 15 | Insights do Jogo | 📸+📈 | **Painel** | Keep summary, move details |
| 16 | Clusters de Afinidade | 📸 | **Trajetória** | Keep & expand with vote-based clustering |
| 17 | Mudanças Entre Dias | 📈 | **Trajetória** | Reaction changes over all days |
| 18 | Vira-Casacas | 📈 | **Trajetória** | Who changes opinions (accumulated) |
| 19 | Evolução do Saldo | 📈 | **Trajetória** | Balance timeline |
| 20 | Saldo vs Sentimento | 📈 | **Trajetória** | Scatter + correlation |
| 21 | Favoritismo Intragrupo | 📈 | **Trajetória** | Vip vs Xepa |
| 22 | Quem Dá Mais Negatividade? | 📸 | **Painel** | Keep — profile chart |
| 23 | Perfis Individuais | 📸 | **Painel** | Keep — expandable |

**Already in `paredoes.qmd`:**
- Resumo das Eliminações (summary table)
- Per-paredão analysis (result, votes, coherence, scatter, pie, ranking, reactions)

---

## Proposed Architecture

### 5-Page Website Structure

| Page | File | Focus | Data Source |
|------|------|-------|-------------|
| **Painel** | `index.qmd` | Today's snapshot — quick daily overview | 📸 Latest |
| **O Que Mudou** | `mudancas.qmd` | Day-to-day changes — what changed since yesterday | 📅 Comparison |
| **Trajetória** | `trajetoria.qmd` | Historical analysis — evolution over time | 📈 Accumulated |
| **Paredão** | `paredao.qmd` | Current paredão status + vote analysis | 🗳️ Current |
| **Arquivo** | `paredoes.qmd` | Paredão history (already exists) | 🗳️ Historical |

---

## Page Details

### 1. Painel (index.qmd) — "O Jogo Hoje"

**Purpose**: Quick daily snapshot for casual viewers. Light, fast-loading.

**Sections to KEEP**:
- Visão Geral (participant count, group breakdown, reaction totals)
- Ranking de Sentimento (horizontal bar chart)
- Tabela Cruzada de Reações (heatmap)
- Grafo de Relações (network visualization)
- Hostilidades do Dia (one-sided/two-sided summary)
- Perfis Individuais (expandable per-participant details)

**Sections to MOVE**:
- ❌ Cronologia do Jogo → Trajetória
- ❌ Resultado do Paredão → Paredão
- ❌ O Que Mudou Hoje? → O Que Mudou
- ❌ Evolução do Sentimento → Trajetória
- ❌ Alianças e Rivalidades (accumulated) → Trajetória
- ❌ Hostilidades Persistentes → Trajetória
- ❌ Clusters de Afinidade → Trajetória (or remove - less useful)
- ❌ Dinâmica das Reações → O Que Mudou
- ❌ Vira-Casacas → O Que Mudou
- ❌ Saldo e Economia → Trajetória
- ❌ Dinâmica Vip vs Xepa → Trajetória

**New content**:
- Alert box linking to Paredão page if paredão em andamento
- "Destaques do Dia" summary box (auto-generated insights)
- Quick navigation cards to other pages

**Estimated weight**: ~40% of current page

---

### 2. O Que Mudou (mudancas.qmd) — "O Que Mudou"

**Purpose**: Deep dive into daily changes. For engaged viewers tracking day-to-day dynamics.

**Sections from index.qmd**:
- O Que Mudou Hoje? (all subsections)
  - Resumo de mudanças
  - Quem Ganhou e Quem Perdeu
  - Mapa de Diferenças (heatmap)
  - Quem Mais Mudou de Opinião?
  - Fluxo de Reações (Sankey)
  - Mudanças Dramáticas
  - Mudanças em Hostilidades
- Dinâmica das Reações
  - Mudanças Entre Dias
  - Vira-Casacas

**New content**:
- Date picker to compare any two dates (not just yesterday/today)
- "Maiores mudanças da semana" summary
- Reaction flow animation (optional, future)

---

### 3. Trajetória (trajetoria.qmd) — "A Temporada"

**Purpose**: Historical analysis for strategy enthusiasts. Shows evolution over the entire season.

**Sections from index.qmd**:
- Cronologia do Jogo (entry/exit timeline)
- Evolução do Sentimento (line chart over time)
- Alianças Mais Consistentes
- Rivalidades Mais Persistentes
- Hostilidades Persistentes (one-sided and two-sided)
- Saldo e Economia
  - Evolução do Saldo
  - Saldo vs Sentimento
- Dinâmica Vip vs Xepa (favoritism over time)
- Clusters de Afinidade (optional — consider removing)

**New content**:
- "Arcos narrativos" — key storylines of the season
- Participant trajectory charts (individual sentiment over time)
- "Semana a semana" summary accordion

---

### 4. Paredão (paredao.qmd) — "Paredão Atual"

**Purpose**: Current paredão focus. Vote analysis, predictions, formation details.

**Sections from index.qmd**:
- Resultado do Paredão (current paredão display)
- Reações Preveem Votos? (correlation analysis)
- Voto da Casa vs O Que Mudou (coherence table)
- Votaram no que mais detestam? (pie chart)
- O caso [mais votado] (analysis)
- Indicação do Líder (coherence check)

**New content**:
- "Quem está em risco?" — sentiment ranking of current nominees
- "Previsão baseada em reações" — who would be voted based on current hostility
- Historical comparison: how did similar situations end in past paredões?

**Conditional display**:
- If `em_andamento`: Show formation, nominees, predictions
- If `finalizado`: Show results, vote breakdown, analysis
- If no current paredão: Show "Próximo paredão: domingo" message

---

### 5. Arquivo de Paredões (paredoes.qmd) — Already Exists

**Keep as-is** with minor improvements:
- Add summary table at top (already done)
- Consider adding "compare paredões" feature (future)

---

## Navigation Design

### Navbar (in _quarto.yml)

```yaml
website:
  navbar:
    left:
      - href: index.qmd
        text: "📊 Painel"
      - href: mudancas.qmd
        text: "📅 O Que Mudou"
      - href: trajetoria.qmd
        text: "📈 Trajetória"
      - href: paredao.qmd
        text: "🗳️ Paredão"
      - href: paredoes.qmd
        text: "📚 Arquivo"
```

### Cross-linking

Each page should have:
- Header with page description
- Navigation cards at bottom linking to related pages
- "Voltar ao Painel" link

---

## Implementation Order

### Phase 1: Create new pages (skeleton)
1. Create `mudancas.qmd` with setup cells (copy from index.qmd)
2. Create `trajetoria.qmd` with setup cells
3. Create `paredao.qmd` with setup cells
4. Update `_quarto.yml` navbar

### Phase 2: Move sections
1. Move day-over-day sections to `mudancas.qmd`
2. Move accumulated sections to `trajetoria.qmd`
3. Move paredão sections to `paredao.qmd`
4. Remove moved sections from `index.qmd`

### Phase 3: Polish
1. Add navigation cards to each page
2. Add page descriptions and context
3. Test all pages render correctly
4. Update CLAUDE.md documentation

### Phase 4: Enhancements (future)
1. Date picker for queridômetro comparisons
2. Paredão predictions based on hostility
3. Individual participant trajectory pages
4. Mobile-responsive improvements

---

## File Size Estimates

| Page | Sections | Est. Charts | Est. Load Time |
|------|----------|-------------|----------------|
| Painel | 6 | 5-6 | Fast (~2s) |
| O Que Mudou | 8 | 6-8 | Medium (~3s) |
| Trajetória | 10 | 8-10 | Medium (~4s) |
| Paredão | 6 | 4-5 | Fast (~2s) |
| Arquivo | Per-paredão | 5×N | Scales with N |

---

## Benefits

1. **Faster page loads**: Each page is focused, lighter
2. **Better UX**: Users find what they need quickly
3. **Clearer mental model**: Daily vs Historical vs Paredão
4. **Easier maintenance**: Each file has single responsibility
5. **SEO-friendly**: Distinct URLs for different content

---

## Questions to Resolve

1. Should "Clusters de Afinidade" be kept? It's computationally heavy and less actionable.
2. Should "Quem Dá Mais Negatividade?" go to Painel or O Que Mudou?
3. Do we want a separate "Participantes" page with individual profiles?
4. Should the navbar use icons? (📊 Painel, 📅 O Que Mudou, 📈 Trajetória, 🗳️ Paredão, 📚 Arquivo)

---

## Improvements to Existing Sections

### Painel (index.qmd) — Improvements

| Section | Current State | Improvement |
|---------|---------------|-------------|
| **Visão Geral** | Basic counts | Add "Destaques do Dia" auto-generated summary |
| **Ranking de Sentimento** | Static bar chart | Add mini-sparklines showing trend (up/down) |
| **Tabela Cruzada** | Full heatmap | Add filter by group (Pipoca/Camarote/Veterano) |
| **Grafo de Relações** | NetworkX static | Consider interactive Plotly network graph |
| **Hostilidades do Dia** | Tables only | Add visual "danger cards" for biggest blind spots |
| **Perfis Individuais** | Text blocks | Add collapsible accordion, avatar prominence |

### O Que Mudou (mudancas.qmd) — Improvements

| Section | Current State | Improvement |
|---------|---------------|-------------|
| **Quem Ganhou e Quem Perdeu** | Today vs yesterday | Add date picker for any two dates |
| **Mapa de Diferenças** | Full heatmap | Highlight only cells that changed (sparse view) |
| **Sankey** | All flows | Filter to show only significant changes (>1) |
| **Mudanças em Hostilidades** | Text tables | Add visual timeline of hostility changes |
| **Vira-Casacas** | Cumulative count | Add "consistency score" (inverse of changes) |

### Trajetória (trajetoria.qmd) — Improvements

| Section | Current State | Improvement |
|---------|---------------|-------------|
| **Evolução do Sentimento** | All participants | Add per-participant selector/focus mode |
| **Alianças/Rivalidades** | Counts only | Add duration (days active) and stability score |
| **Hostilidades Persistentes** | Tables | Add visual timeline bars |
| **Saldo vs Sentimento** | Scatter | Add time animation (watch correlation evolve) |
| **Clusters** | Static clustering | Consider removing or making optional |

### Paredão (paredao.qmd) — Improvements

| Section | Current State | Improvement |
|---------|---------------|-------------|
| **Resultado** | Bar chart | Add vote trend if available (Globoplay live %) |
| **Reações Preveem Votos?** | Scatter | Add prediction: "based on hostility, [X] would go" |
| **Votação da Casa** | Table | Add visual flow diagram (voter → target) |
| **Coherence Analysis** | Pie chart | Add individual voter "coherence score" |

### Arquivo (paredoes.qmd) — Improvements

| Section | Current State | Improvement |
|---------|---------------|-------------|
| **Summary Table** | Basic stats | Add "accuracy" column (did reactions predict result?) |
| **Per-Paredão Analysis** | Static | Add "compare with..." feature |

---

## New Section Ideas

### For Painel

| New Section | Description | Priority |
|-------------|-------------|----------|
| **Alert Box** | If paredão em andamento, show prominent link | High |
| **Destaques do Dia** | 3-5 auto-generated insights (biggest gainer, biggest loser, new hostility) | High |
| **Quick Stats Cards** | Card layout: total hearts, total negative, balance sum | Medium |
| **Navigation Footer** | Cards linking to other pages with preview | Medium |

### For O Que Mudou

| New Section | Description | Priority |
|-------------|-------------|----------|
| **Date Comparison Tool** | Dropdown to select any two dates, not just today/yesterday | High |
| **Maiores Mudanças da Semana** | Summary of top 5 changes across the week | Medium |
| **Mudança Acumulada** | Total change from day 1 to today per participant | Medium |
| **Reaction Flow Animation** | Animated Sankey over multiple days | Low |

### For Trajetória

| New Section | Description | Priority |
|-------------|-------------|----------|
| **Arcos Narrativos** | Manual/auto storylines (e.g., "A redemption arc of X") | Medium |
| **Participant Focus Mode** | Click participant to see their full journey | High |
| **Semana a Semana** | Accordion with weekly highlights | Medium |
| **Correlation Dashboard** | Balance vs sentiment vs group vs votes | Low |

### For Paredão

| New Section | Description | Priority |
|-------------|-------------|----------|
| **Quem Está em Risco?** | Sentiment ranking of current nominees | High |
| **Previsão Baseada em Hostilidades** | Who would be voted out based on current data | High |
| **Histórico Similar** | "In past paredões with similar sentiment, X went home" | Medium |
| **Votação Live** | If BBB shows live %, embed or link | Low |

### For Arquivo

| New Section | Description | Priority |
|-------------|-------------|----------|
| **Compare Paredões** | Side-by-side comparison of any two paredões | Medium |
| **Accuracy Tracking** | Did our reaction-based predictions match reality? | High |
| **Patterns** | Common patterns (e.g., "most voted always had low sentiment") | Medium |

---

## Sections to Consider Merging

| Section | Issue | Recommendation |
|---------|-------|----------------|
| **Mudanças Entre Dias** vs **Vira-Casacas** | Overlap in purpose | Merge into single "Quem Muda de Opinião?" |

### Clusters — Dedicated Section (Keep & Expand)

Clusters are important and will improve with more data. Consider expanding to include:
- **O Que Mudou-based clustering** — Current implementation (mutual sentiment)
- **Vote-based clustering** — People who vote for the same targets may be aligned
- **Combined clustering** — Weight both reactions and votes

Future enhancement: As more paredões occur, voting patterns become a strong signal for alliances.

---

## Implementation Phases (Detailed)

### Phase 2.1: Create Page Skeletons

| Task | File | Description |
|------|------|-------------|
| 2.1.1 | `mudancas.qmd` | Copy setup cells from index.qmd, add page header |
| 2.1.2 | `trajetoria.qmd` | Copy setup cells, add page header |
| 2.1.3 | `paredao.qmd` | Copy setup cells, add page header |
| 2.1.4 | `_quarto.yml` | Add all 5 pages to navbar + render list |

### Phase 2.2: Move Sections (O Que Mudou)

| Task | Section | Source Lines (approx) |
|------|---------|----------------------|
| 2.2.1 | O Que Mudou Hoje? parent | 1215-1700 |
| 2.2.2 | Mudanças Entre Dias | 2683-2740 |
| 2.2.3 | Vira-Casacas | 2743-2815 |

### Phase 2.3: Move Sections (Trajetória)

| Task | Section | Source Lines (approx) |
|------|---------|----------------------|
| 2.3.1 | Cronologia do Jogo | 543-600 |
| 2.3.2 | Evolução do Sentimento | 1708-1805 |
| 2.3.3 | Alianças Mais Consistentes | 1834-1915 |
| 2.3.4 | Rivalidades Mais Persistentes | 1916-1964 |
| 2.3.5 | Hostilidades Persistentes | 2314-2505 |
| 2.3.6 | Clusters de Afinidade | 2507-2680 |
| 2.3.7 | Evolução do Saldo | 2817-2908 |
| 2.3.8 | Saldo vs Sentimento | 2909-2960 |
| 2.3.9 | Favoritismo Intragrupo | 2961-3048 |

### Phase 2.4: Move Sections (Paredão)

| Task | Section | Source Lines (approx) |
|------|---------|----------------------|
| 2.4.1 | Resultado do Paredão | 600-1200 (paredão block) |
| 2.4.2 | Reações Preveem Votos? | 990-1200 |

### Phase 2.5: Clean Up Painel

| Task | Description |
|------|-------------|
| 2.5.1 | Remove all moved sections from index.qmd |
| 2.5.2 | Add paredão alert box (links to paredao.qmd) |
| 2.5.3 | Add navigation cards at bottom |
| 2.5.4 | Add "Destaques do Dia" auto-summary |

### Phase 2.6: Polish and Test

| Task | Description |
|------|-------------|
| 2.6.1 | Add page headers with descriptions |
| 2.6.2 | Add cross-links between pages |
| 2.6.3 | Test all pages render without errors |
| 2.6.4 | Update CLAUDE.md with new architecture |

### Phase 2.7: Enhancements (Future)

| Task | Priority | Description |
|------|----------|-------------|
| 2.7.1 | High | Date picker for queridômetro |
| 2.7.2 | High | Paredão predictions based on hostility |
| 2.7.3 | Medium | Participant focus mode in trajetória |
| 2.7.4 | Medium | Compare paredões feature |
| 2.7.5 | Low | Mobile-responsive improvements |

---

## Section Count Summary

| Page | Existing | New | Total |
|------|----------|-----|-------|
| Painel | 7 | 2 | 9 |
| O Que Mudou | 9 | 2 | 11 |
| Trajetória | 10 | 2 | 12 |
| Paredão | 6 | 2 | 8 |
| Arquivo | existing | 2 | +2 |

---

## Decision Needed

Before implementing, please confirm:
1. Does this 5-page structure make sense?
2. Are the section assignments correct?
3. Any sections to add/remove?
4. Which improvements are highest priority?
5. Implementation priority?
