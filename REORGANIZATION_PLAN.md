# Dashboard Reorganization Plan

> **Status**: ✅ Phase 3 Complete (Trajetória Restructure) | Phase 5 Complete (clusters.qmd)
> **Parent document**: See `IMPLEMENTATION_PLAN.md` for overall project status
>
> **Final Summary (2026-01-26)**:
> - ✅ index.qmd reduced from 841KB to ~400KB (-52%)
> - ✅ Created mudancas.qmd (O Que Mudou) — day-over-day changes
> - ✅ Created trajetoria.qmd (Trajetória) — historical analysis with tabs
> - ✅ Created paredao.qmd (Paredão Atual) — current paredão status + analysis
> - ✅ All sections moved to appropriate pages
> - ✅ Navigation callouts and cross-links added
> - ✅ 5-page architecture fully implemented
> - ✅ Cartola BBB page added (cartola.qmd)
> - ✅ Destaques do Dia, KPI boxes, Watchlist de Risco added
> - ✅ Avatars added to paredao.qmd tables
> - ✅ Accessibility toggle (colorblind mode) added
> - ✅ Bump chart added to trajetoria.qmd
>
> **Deferred Features (to re-evaluate)**:
> See "Deferred Features for Re-Evaluation" section below for detailed analysis
>
> **Next: Trajetória Storytelling Reorganization** (see below)

---

## Trajetória Deep Review & Reorganization Plan

> **Status**: ⏳ In Progress — Deep Review Phase
> **Goal**: Transform trajetoria.qmd from a disorganized collection of plots into a coherent storytelling experience
> **Last Updated**: 2026-01-26 (comprehensive review)
> **Approach**: Question-driven storytelling (like paredao.qmd), not chart galleries

### Quick Summary

**Current state**: 5 tabs, 21+ sections, scattered content, no narrative

**New structure**: 4 tabs, ~12 sections, question-driven

| New Tab | Question | Star Content |
|---------|----------|--------------|
| 📊 Quem Lidera? | Who's winning the sentiment game? | Bump Chart |
| ❤️ Aliados | Who are the allies? | Consistent Alliances |
| ⚔️ Conflitos | Where are the rivalries? | Persistent Hostilities + Blind Spots |
| 📈 Tendências | What's changing? | Vira-Casacas with stories |

**Key changes**:
- ✅ "Fatos Rápidos" intros for quick scanning
- ✅ "Destaques" sections with curated insights
- ✅ Clusters moved to separate experimental page (clusters.qmd)
- ✅ Saldo/Balance moved to Cartola page
- ✅ Redundant sections removed
- ✅ Hostility analysis consolidated

---

### What paredao.qmd Does Right (Storytelling Model)

The paredão page works because it:
1. **Answers a clear question**: "What's happening in this paredão?"
2. **Quick summary first**: "Leitura Rápida" table with key metrics before diving deep
3. **Destaques section**: Highlights most interesting data points
4. **Relationship context**: Shows *history* of relationships, not just current state
5. **Narrative text**: Explains *why* things matter, not just what they are
6. **Visual hierarchy**: Cards for participants, then tables, then charts
7. **Human connection**: Avatars, names, specific stories

### Problem with trajetoria.qmd

The current page has 5 tabs with 21+ sections, but:
- **No clear questions answered** — it's a chart gallery, not a story
- **Content is scattered** — hostilities appear in 3 different places
- **"Análise do Dia" is a catch-all** with 10+ unrelated sections
- **No intro summaries** — just dives into charts without context
- **Redundant content** — same data presented multiple ways
- **No narrative** — doesn't tell viewers what to *do* with the information
- **Clusters are experimental** — buried at the end, algorithm needs work

---

### Section-by-Section Critical Review

Rating scale: ⭐⭐⭐ Essential | ⭐⭐ Useful | ⭐ Low value | ❌ Remove/merge

#### Tab 1: Evolução

| Section | Rating | Storytelling Value | Issues | Recommendation |
|---------|--------|-------------------|--------|----------------|
| **Bump Chart (Ranking)** | ⭐⭐⭐ | High — shows who's winning/losing over time | Good as-is | KEEP — anchor of "Quem Lidera?" story |
| **Linhas (Score)** | ⭐⭐ | Medium — detailed but cluttered with 22 lines | Hard to read with many participants | KEEP but add focus mode (select participant) |

**Tab verdict**: Good content, needs intro summary ("Jonas lidera há X dias...")

#### Tab 2: Alianças

| Section | Rating | Storytelling Value | Issues | Recommendation |
|---------|--------|-------------------|--------|----------------|
| **Alianças Mais Consistentes** | ⭐⭐⭐ | High — reveals stable friendships | Just a bar chart, no context | ENHANCE — add "Why this matters" + key pair stories |
| **Rivalidades Mais Persistentes** | ⭐⭐ | Medium | Duplicates "Hostilidades Persistentes" in Histórico tab | MERGE with Histórico version, move to Conflitos tab |

**Tab verdict**: "Alianças" should be ONLY about positive relationships, not rivalries

#### Tab 3: Dinâmica

| Section | Rating | Storytelling Value | Issues | Recommendation |
|---------|--------|-------------------|--------|----------------|
| **Mudanças Entre Dias** | ⭐ | Low — hard to interpret bar chart | Not actionable, confusing x-axis | REMOVE — mudancas.qmd covers this better |
| **Vira-Casacas** | ⭐⭐ | Medium — interesting concept | Just a count, no story about *who* changed *what* | ENHANCE or MERGE — needs specific examples |
| **Vip vs Xepa** | ⭐ | Low — niche analysis | May not interest casual viewers | MOVE to separate "Deep Dives" page or REMOVE |

**Tab verdict**: Weak tab, most content duplicated elsewhere or low value

#### Tab 4: Histórico

| Section | Rating | Storytelling Value | Issues | Recommendation |
|---------|--------|-------------------|--------|----------------|
| **Rivalidades Mais Longas (2-sided)** | ⭐⭐⭐ | High — central conflicts | Duplicates Alianças tab rivalries | KEEP as primary, remove duplicate |
| **Hostilidades Unilaterais** | ⭐⭐⭐ | High — reveals blind spots | Good, but needs more context | ENHANCE — connect to voting predictions |
| **Saldo e Economia** | ⭐ | Low — not connected to game dynamics | Balance changes don't predict anything | MOVE to Cartola page or REMOVE |

**Tab verdict**: Hostilities are gold, Saldo is filler

#### Tab 5: Análise do Dia (CATCH-ALL)

| Section | Rating | Storytelling Value | Issues | Recommendation |
|---------|--------|-------------------|--------|----------------|
| **Grafo de Relações** | ⭐⭐ | Medium — pretty but hard to read | Too dense, no clear insight | ENHANCE or MOVE to separate viz page |
| **Hostilidades do Dia** | ⭐⭐⭐ | High — directly relevant to voting | 5 subsections is too many | CONSOLIDATE into 2-3 focused sections |
| ├── Quem Ataca Quem Lhe Dá ❤️ | ⭐⭐⭐ | High — "traitors" | Keep | |
| ├── Quem Dá ❤️ a Inimigos | ⭐⭐⭐ | High — "blind spots" | Keep | |
| ├── Quem Tem Mais Inimigos | ⭐⭐ | Medium | Merge with polarizing | |
| ├── Listas de Hostilidades | ⭐ | Low — raw data dump | REMOVE — move to appendix | |
| └── Insights do Jogo | ⭐⭐⭐ | High — summary | PROMOTE to section intro | |
| **Clusters de Afinidade** | ⭐ | Low currently — experimental | Hardcoded k=4, generic names | MOVE to separate experimental page |
| **Saldo vs Sentimento** | ⭐ | Low — weak correlation | Not interesting insight | REMOVE or move to Cartola |
| **Quem Dá Mais Negatividade** | ⭐⭐ | Medium | Could merge with hostility analysis | MERGE with "Atacantes" section |

**Tab verdict**: Has the best content but worst organization. Needs complete restructure.

---

### Content Classification

**Essential (must keep and enhance):**
- Bump Chart / Sentiment Lines — trajectory visualization
- Alianças Consistentes — reveals stable relationships
- Hostilidades Persistentes (2-sided + 1-sided) — power dynamics
- Pontos Cegos / Vulnerabilidades — voting predictions
- Insights do Jogo — strategic summary

**Useful (keep but may reorganize):**
- Vira-Casacas — needs better storytelling
- Grafo de Relações — needs simplification
- Quem Dá Mais Negatividade — merge with hostility

**Low value (remove or move):**
- Mudanças Entre Dias — duplicated in mudancas.qmd
- Vip vs Xepa — niche, consider removing
- Saldo e Economia — move to Cartola
- Saldo vs Sentimento — weak insight, remove
- Listas de Hostilidades — raw data, move to appendix

**Experimental (move to separate page):**
- Clusters de Afinidade — needs algorithm work, own page

### Current Structure (Verified 2026-01-26)

```
📊 Visão Geral (outside tabs)
├── Stats overview (participants, snapshots, date range)
└── Late entrants note

📅 Cronologia do Jogo (outside tabs)
└── Timeline of entries/exits

::: {.panel-tabset}

## Evolução
├── Late entrants caption
├── Sentiment timeline prep (hidden)
└── ::: {.panel-tabset}
    ├── #### Bump Chart (Ranking) — position over time
    └── #### Linhas (Score) — sentiment lines with paredão dates

## Alianças
├── ### Alianças e Rivalidades {#aliancas}
│   ├── #### Alianças Mais Consistentes — mutual hearts over time
│   └── #### Rivalidades Mais Persistentes — mutual negativity

## Dinâmica
├── ### Dinâmica das Reações {#dinamica}
│   ├── #### Mudanças Entre Dias — reaction changes
│   └── #### Quem Muda Mais de Opinião? ("Vira-Casacas")
└── ### Dinâmica Vip vs Xepa {#grupos}
    └── In-group vs out-group favoritism analysis

## Histórico
├── ### Hostilidades Persistentes {#hostilidades}
│   ├── #### Rivalidades Mais Longas — two-sided, duration tracked
│   └── #### Hostilidades Unilaterais Mais Longas — one-sided
└── ### Saldo e Economia {#saldo}
    └── Balance timeline over all snapshots

## Análise do Dia (CATCH-ALL — 10+ sections)
├── ### Grafo de Relações {#grafo} — network visualization
├── ### Hostilidades do Dia {#hostilidades-dia}
│   ├── #### Quem Mais Ataca Quem Lhe Dá Coração
│   ├── #### Quem Mais Dá Coração a Inimigos
│   ├── #### Quem Tem Mais Inimigos Declarados
│   ├── #### Listas de Hostilidades
│   └── #### Insights do Jogo (vulnerabilities, polarizing)
├── ### Clusters de Afinidade {#clusters}
│   ├── Grupos Identificados (4 clusters)
│   ├── Dinâmica Entre Clusters
│   ├── Participantes Mais Polarizadores
│   └── Cluster heatmap (reordered matrix)
├── #### Saldo vs Sentimento — scatter correlation
└── ### Quem Dá Mais Negatividade? {#emissores}

:::
```

**Issues identified:**
1. "Análise do Dia" has 10+ sections — too dense, no clear narrative
2. "Alianças" tab has rivalries (should be in Conflitos)
3. Clusters are buried at the end but could anchor an "Alianças" narrative
4. "Histórico" mixes hostilities and economics
5. No intro summaries to help viewers scan quickly

---

### Cluster Calculation Review

The current cluster implementation uses **hierarchical clustering** with Ward's method. Here's how it works:

#### Algorithm

```python
# 1. Build sentiment matrix from latest snapshot
#    - Each cell [i,j] = sentiment weight of reaction i→j
#    - Weights: Coração = +1, mild_negative = -0.5, strong_negative = -1

# 2. Create mutual sentiment matrix
mutual_mat = (sent_mat + sent_mat.T) / 2
#    - Averages A→B and B→A to get symmetric relationship strength
#    - Range: -1 (mutual hostility) to +1 (mutual love)

# 3. Convert to distance matrix
dist_mat = 2 - mutual_mat
#    - Higher sentiment = lower distance (closer in cluster space)
#    - Range: 1 (best friends) to 3 (bitter enemies)

# 4. Hierarchical clustering with Ward's method
Z = linkage(condensed, method='ward')
clusters = fcluster(Z, 4, criterion='maxclust')
#    - Ward minimizes within-cluster variance
#    - Fixed at 4 clusters (arbitrary choice)
```

#### Current Output

| Section | What it shows |
|---------|---------------|
| **Grupos Identificados** | 4 clusters with member lists and group composition |
| **Dinâmica Entre Clusters** | Inter-cluster average sentiment (tensions vs affinities) |
| **Participantes Mais Polarizadores** | Most negativity given/received, most mutual enemies |
| **Cluster Heatmap** | Reordered heatmap showing cluster boundaries |

#### Evaluation Questions

| Question | Current State | Possible Improvement |
|----------|---------------|----------------------|
| Why 4 clusters? | Hardcoded | Use silhouette score to find optimal k |
| Cluster labels? | Generic "Grupo A/B/C/D" | Auto-name by dominant trait (e.g., "Veteranos Unidos") |
| Stability? | Single snapshot only | Track cluster membership over time |
| Vote alignment? | Not considered | Add voting pattern correlation |
| Group bias? | Shows composition | Quantify how much Pipoca/Camarote/Veterano split |

#### Alternative Approaches to Consider

1. **Vote-based clustering**: Group by who they vote for (as more paredões happen)
2. **Combined clustering**: Weight both reactions AND votes
3. **Temporal clustering**: Track how clusters form/dissolve over time
4. **Dynamic k**: Let algorithm choose optimal cluster count per day

#### Decision Needed

- [ ] Keep current implementation (simple, works)
- [ ] Improve with silhouette-based k selection
- [ ] Add vote-based clustering as separate view
- [ ] Track cluster evolution over time
- [ ] Remove clusters entirely (low value?)

---

### Proposed Structure (After) — Question-Driven Storytelling

Each tab answers **one clear question** with:
1. **Fatos Rápidos** intro (like paredao.qmd) — 3-5 key metrics
2. **Main visualization** — the star of the tab
3. **Destaques** — most interesting findings with context
4. **Supporting details** — for those who want more

```
📊 Quem Lidera? (Ranking)
├── Fatos Rápidos: "Jonas lidera há 5 dias. Brigido caiu 7 posições. 3 novos no Top 5."
├── Bump Chart (posições ao longo do tempo) ⭐ STAR
├── Destaques: Maior subida, maior queda, mais estável
└── Linhas de Sentimento (scores detalhados, com selector de participante)

❤️ Quem São os Aliados? (Alianças)
├── Fatos Rápidos: "15 alianças estáveis. 3 participantes isolados. Veteranos: mais coesos."
├── Alianças Mais Consistentes (laços mais fortes) ⭐ STAR
├── Destaques: Aliança mais longa, grupo mais unido, quem está sozinho
├── Grafo de Relações (simplificado: só alianças, não hostilidades)
└── Dinâmica de Grupo (Vip vs Xepa favoritism — OPTIONAL, collapsed)

⚔️ Onde Estão os Conflitos? (Conflitos)
├── Fatos Rápidos: "12 rivalidades mútuas. 26 hostilidades unilaterais. 5 pontos cegos críticos."
├── Inimigos Declarados (rivalidades mútuas persistentes) ⭐ STAR
├── Pontos Cegos (quem dá ❤️ a quem os detesta) — VOTING RELEVANCE
├── Destaques: Rivalidade mais longa, maior ponto cego, mais polarizante
├── Atacantes e Vítimas (consolidado: quem ataca amigos + quem ama inimigos)
└── Perfil de Emissão (quem dá mais negatividade)

📈 O Que Está Mudando? (Tendências)
├── Fatos Rápidos: "95 reações mudaram ontem. Volatilidade: alta. Direção: polarização crescendo."
├── Vira-Casacas (quem muda de opinião — with specific stories) ⭐ STAR
├── Destaques: Maior virada, relacionamento que inverteu, quem ficou estável
└── Cronologia do Jogo (timeline de eventos — currently in "Visão Geral")

───────────────────────────────────────────────────────────────────
📊 Saldo e Economia (STANDALONE — outside tabs, at the bottom)
├── Evolução do Saldo (balance timeline)
└── Note: Odd section, kept for completeness but not part of main narrative
```

**What got removed/moved:**
- ❌ Mudanças Entre Dias → mudancas.qmd (duplicate)
- 📊 Saldo e Economia → **stays in trajetória** (standalone section, odd one out)
- ❌ Saldo vs Sentimento → removed (weak insight)
- ❌ Listas de Hostilidades → removed (raw data dump)
- ❌ Clusters de Afinidade → **NEW clusters.qmd experimental page**

**Key changes:**
1. **4 tabs instead of 5** — each with clear purpose
2. **"Fatos Rápidos" intros** — quick scan for casual viewers
3. **"Destaques" sections** — curated insights, not just charts
4. **Consolidated hostility analysis** — no more 5 subsections
5. **Grafo simplified** — show alliances only, not the whole mess
6. **Vira-Casacas enhanced** — with specific relationship stories

---

### New Page: clusters.qmd (Experimental Lab)

**Purpose**: Dedicated experimental page for clustering and grouping analysis

**Why separate page:**
- Algorithm is hardcoded (k=4) and needs experimentation
- Results are interesting but not actionable yet
- Keeping it separate allows iteration without affecting main pages
- Can add new clustering approaches without clutter

**Content:**
```
🧪 Laboratório de Clusters (Experimental)

├── Fatos Rápidos: "4 clusters identificados. Maior: 8 membros (Veteranos+Pipoca). Tensão máxima: Cluster 1 vs 3."

├── Clustering por Sentimento (current implementation)
│   ├── Dendrograma interativo
│   ├── Grupos identificados (with better naming)
│   └── Heatmap reordenado por cluster

├── Dinâmica Entre Clusters
│   ├── Tensões (which clusters don't like each other)
│   └── Afinidades (which clusters are friendly)

├── Alternativas (future)
│   ├── Vote-based clustering (after more paredões)
│   ├── Temporal clustering (how clusters evolve)
│   └── Optimal k selection (silhouette score)

└── Participantes Polarizadores
    ├── Most negativity given
    ├── Most negativity received
    └── Most mutual enemies
```

**Algorithm improvements to implement:**
- [ ] Dynamic k using silhouette score
- [ ] Auto-name clusters by dominant trait (e.g., "Núcleo Veterano", "Grupo Pipoca Isolado")
- [ ] Track cluster membership over time
- [ ] Add vote-based clustering when we have 3+ paredões

---

### Section Mapping (Old → New)

| Old Location | Section | New Location | Action |
|--------------|---------|--------------|--------|
| Evolução | Bump Chart | 📊 Quem Lidera? | KEEP — star of tab |
| Evolução | Linhas | 📊 Quem Lidera? | KEEP — add participant selector |
| Alianças | Alianças Mais Consistentes | ❤️ Aliados | KEEP — star of tab |
| Alianças | Rivalidades Mais Persistentes | ⚔️ Conflitos | MOVE — merge with Histórico version |
| Dinâmica | Mudanças Entre Dias | ❌ | REMOVE — mudancas.qmd covers this |
| Dinâmica | Vira-Casacas | 📈 Tendências | ENHANCE — add specific stories |
| Dinâmica | Vip vs Xepa | ❤️ Aliados (collapsed) | OPTIONAL — keep but collapsible |
| Histórico | Hostilidades Persistentes (2-sided) | ⚔️ Conflitos | KEEP — star of tab |
| Histórico | Hostilidades Persistentes (1-sided) | ⚔️ Conflitos | KEEP — "Pontos Cegos" |
| Histórico | Saldo e Economia | 📊 Standalone section | KEEP — odd one, stays in trajetória as its own section |
| Análise do Dia | Grafo de Relações | ❤️ Aliados | SIMPLIFY — alliances only |
| Análise do Dia | Hostilidades do Dia | ⚔️ Conflitos | CONSOLIDATE — 5 sections → 2 |
| Análise do Dia | Clusters de Afinidade | 🧪 clusters.qmd | MOVE — experimental page |
| Análise do Dia | Saldo vs Sentimento | ❌ | REMOVE — weak insight |
| Análise do Dia | Quem Dá Mais Negatividade | ⚔️ Conflitos | MERGE with hostility analysis |
| Visão Geral | Cronologia do Jogo | 📈 Tendências | MOVE — fits "what's changing" |

### New Intro Sections: "Fatos Rápidos"

Each tab starts with a **dynamic "Fatos Rápidos"** section (computed from data, not hardcoded):

| Tab | Fatos Rápidos (auto-computed) |
|-----|-------------------------------|
| 📊 Quem Lidera? | `f"**{leader}** lidera há **{days_leading}** dias. **{biggest_drop}** caiu **{positions}** posições esta semana. **{n_new_top5}** novatos no Top 5."` |
| ❤️ Aliados | `f"**{n_stable_alliances}** alianças estáveis (>70% dos dias). **{n_isolated}** participantes sem alianças consistentes. **{most_connected}** é o mais conectado."` |
| ⚔️ Conflitos | `f"**{n_mutual}** rivalidades mútuas. **{n_one_sided}** pontos cegos. Conflito mais longo: **{longest_rivalry}** ({days} dias)."` |
| 📈 Tendências | `f"**{n_changes}** reações mudaram ontem. Volatilidade: **{volatility_level}**. Maior virada: **{biggest_flip}** ({from_rxn}→{to_rxn})."` |

**Implementation**: Each intro is a Python code block that computes metrics from data.

### Implementation Phases

#### Phase 1: Structure Reorganization ✅ COMPLETE (2026-01-26)

| Step | Task | Status | Notes |
|------|------|--------|-------|
| 1.1 | Rename tabs | ✅ | 📊 Quem Lidera?, ❤️ Aliados, 📈 Tendências, 📜 Histórico, ⚔️ Conflitos |
| 1.2 | Move sections to correct tabs | ✅ | Vip vs Xepa → Aliados |
| 1.3 | Remove redundant sections | ✅ | Mudanças Entre Dias, Saldo vs Sentimento, Listas de Hostilidades |
| 1.4 | Create clusters.qmd | ✅ | With silhouette k evaluation |
| 1.5 | Move cluster code | ✅ | Added callout link in trajetória |
| 1.6 | Keep Saldo in place | ✅ | Stays in Histórico tab |
| 1.7 | Update _quarto.yml | ✅ | Added clusters.qmd to render list |

**Note**: Kept 5 tabs instead of 4 due to content dependencies (shared computation between Alianças/Rivalidades). Consolidating further requires refactoring. Marked for future work.

#### Phase 2: Add "Fatos Rápidos" Intros

| Step | Task | Tab |
|------|------|-----|
| 2.1 | Compute leader stats dynamically | 📊 Quem Lidera? |
| 2.2 | Compute alliance stats dynamically | ❤️ Aliados |
| 2.3 | Compute conflict stats dynamically | ⚔️ Conflitos |
| 2.4 | Compute volatility stats dynamically | 📈 Tendências |

#### Phase 3: Add "Destaques" Sections

| Step | Task | Tab |
|------|------|-----|
| 3.1 | Highlight biggest mover, most stable | 📊 Quem Lidera? |
| 3.2 | Highlight longest alliance, most isolated | ❤️ Aliados |
| 3.3 | Highlight critical blind spots for voting | ⚔️ Conflitos |
| 3.4 | Highlight dramatic relationship changes | 📈 Tendências |

#### Phase 3.5: Fix Data Freshness Issues (CRITICAL) ✅ COMPLETE

> **Purpose**: Ensure paredão analysis uses correct snapshot (paredão-date, not latest)
> **Priority**: HIGH — affects data integrity
> **Completed**: 2026-01-26

**Problem identified**: Some sections in `paredao.qmd` used `latest['participants']` instead of paredão-date snapshot.

| Step | Task | Status | Notes |
|------|------|--------|-------|
| 3.5.1 | **Fix Leitura Rápida** | ✅ | Now uses `snap_for_analysis` conditionally based on status |
| 3.5.2 | **Audit all `latest` uses** | ✅ | Only 1 occurrence needed fixing (line 706→729) |
| 3.5.3 | **Add data source indicator** | ✅ | Shows "📅 Dados de [date] (dia do paredão)" for finalizado |
| 3.5.4 | **Verify paredoes.qmd** | ✅ | Already uses `get_snapshot_for_date()` correctly |

**Changes made to paredao.qmd**:
- Added `snap_for_analysis` variable that uses paredão-date snapshot when `is_finalizado`
- Added `analysis_date_label` to show data source to users
- Renamed variables: `sent_hoje` → `sent_paredao`, `neg_hoje` → `neg_paredao`
- Updated column names: "Sentimento hoje" → "Sentimento", "Rank hoje" → "Rank"

**Rule documented in CLAUDE.md**:
- `status == 'em_andamento'`: OK to use `latest` for status display
- `status == 'finalizado'`: ALL analysis MUST use paredão-date snapshot

#### Phase 4: Deep Data Analysis & Module Improvement

> **Purpose**: After reorganization, analyze the data more deeply to improve visualizations and insights

| Step | Task | Description |
|------|------|-------------|
| 4.1 | **Improve Bump Chart** | Add participant highlight on hover, smooth animation |
| 4.2 | **Simplify Grafo** | Show only alliances (hearts), remove hostility edges |
| 4.3 | **Enhance Vira-Casacas** | Add specific stories: "X went from ❤️ to 🐍 for Y on [date]" |
| 4.4 | **Voting Connection** | Connect hostility analysis to actual paredão votes |
| 4.5 | **Cluster Algorithm** | Implement silhouette-based k selection |
| 4.6 | **Cluster Naming** | Auto-name clusters by composition |
| 4.7 | **Temporal Tracking** | Track cluster membership evolution |
| 4.8 | **Vote-based Clustering** | Add when we have 3+ paredões |

#### Phase 5: Deferred Features Reconsideration

| Feature | Priority | When to Implement | Notes |
|---------|----------|-------------------|-------|
| **Participant Focus Mode** | HIGH | After Phase 3 | Click name → see full journey |
| **Accuracy Tracking** | HIGH | After 3rd paredão | Did predictions match results? |
| **Date Picker** | MEDIUM | If users request | Compare any two dates |
| **Arcos Narrativos** | MEDIUM | Mid-season | Auto-detect storylines |

---

### Benefits of New Structure

| Benefit | Before | After |
|---------|--------|-------|
| **Clear narrative** | Chart gallery | Question-driven storytelling |
| **Tab purpose** | Random collections | Each answers one question |
| **Hostility analysis** | Scattered in 3 tabs | Consolidated in ⚔️ Conflitos |
| **Quick scanning** | No summaries | "Fatos Rápidos" intros |
| **Experimental work** | Mixed with main content | Separate clusters.qmd |
| **Cognitive load** | 5 tabs, 21+ sections | 4 tabs, ~12 focused sections |
| **Voting relevance** | Unclear connection | "Pontos Cegos" directly connects |

### New Site Structure (7 Pages)

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
      - href: cartola.qmd
        text: "🎩 Cartola"
      - href: clusters.qmd
        text: "🧪 Lab"  # Or hide from main nav, link from trajetória
```

**Option**: Keep clusters.qmd as a "hidden" page (not in navbar) and link to it from trajetória's Alianças tab with "🧪 Ver análise experimental de clusters".

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

| New Section | Description | Priority | Status |
|-------------|-------------|----------|--------|
| **Alert Box** | If paredão em andamento, show prominent link | High | ✅ Done |
| **Destaques do Dia** | 3-5 auto-generated insights (biggest gainer, biggest loser, new hostility) | High | ✅ Done |
| **Quick Stats Cards** | Card layout: total hearts, total negative, balance sum | Medium | ✅ Done (KPIs) |
| **Navigation Footer** | Cards linking to other pages with preview | Medium | ✅ Done |
| **Watchlist de Risco** | Participants at risk of surprise votes | High | ✅ Done |

### For O Que Mudou

| New Section | Description | Priority | Status |
|-------------|-------------|----------|--------|
| **Date Comparison Tool** | Dropdown to select any two dates, not just today/yesterday | High | ❌ Deferred |
| **Maiores Mudanças da Semana** | Summary of top 5 changes across the week | Medium | ⚠️ Partial (daily) |
| **Mudança Acumulada** | Total change from day 1 to today per participant | Medium | ❌ Deferred |
| **Reaction Flow Animation** | Animated Sankey over multiple days | Low | ❌ Deferred |

### For Trajetória

| New Section | Description | Priority | Status |
|-------------|-------------|----------|--------|
| **Bump Chart** | Rank evolution visualization | Medium | ✅ Done |
| **Arcos Narrativos** | Manual/auto storylines (e.g., "A redemption arc of X") | Medium | ❌ Deferred |
| **Participant Focus Mode** | Click participant to see their full journey | High | ❌ Deferred |
| **Semana a Semana** | Accordion with weekly highlights | Medium | ❌ Deferred |
| **Correlation Dashboard** | Balance vs sentiment vs group vs votes | Low | ❌ Deferred |

### For Paredão

| New Section | Description | Priority | Status |
|-------------|-------------|----------|--------|
| **Quem Está em Risco?** | Sentiment ranking of current nominees | High | ✅ Done (Leitura Rápida) |
| **Previsão Baseada em Hostilidades** | Who would be voted out based on current data | High | ✅ Done (vote analysis) |
| **Avatars in Tables** | Participant photos in all analysis tables | Medium | ✅ Done |
| **Histórico Similar** | "In past paredões with similar sentiment, X went home" | Medium | ❌ Deferred |
| **Votação Live** | If BBB shows live %, embed or link | Low | ❌ Out of scope |

### For Arquivo

| New Section | Description | Priority | Status |
|-------------|-------------|----------|--------|
| **Compare Paredões** | Side-by-side comparison of any two paredões | Medium | ❌ Deferred |
| **Accuracy Tracking** | Did our reaction-based predictions match reality? | High | ❌ Deferred |
| **Patterns** | Common patterns (e.g., "most voted always had low sentiment") | Medium | ❌ Deferred |

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

### Phase 2.7: Enhancements

| Task | Priority | Description | Status |
|------|----------|-------------|--------|
| 2.7.1 | High | Date picker for queridômetro | ❌ Deferred |
| 2.7.2 | High | Paredão predictions based on hostility | ✅ Done (Watchlist de Risco) |
| 2.7.3 | Medium | Participant focus mode in trajetória | ❌ Deferred |
| 2.7.4 | Medium | Compare paredões feature | ❌ Deferred |
| 2.7.5 | Low | Mobile-responsive improvements | ✅ Done (text tables) |

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

## Deferred Features for Re-Evaluation

> **Purpose**: Track features that were deferred but may be worth implementing as the season progresses.
> **Last reviewed**: 2026-01-26

### High Priority (Consider implementing soon)

| Feature | Description | Value | Effort | When to implement |
|---------|-------------|-------|--------|-------------------|
| **Participant Focus Mode** | Click participant → see their full journey (sentiment, votes, relationships) | High — answers "tell me about X" | Medium | After trajetória reorg |
| **Accuracy Tracking** | Did reaction-based predictions match paredão results? | High — validates methodology | Low | After 3+ paredões |
| **Date Picker** | Compare any two dates (not just yesterday/today) | Medium — power user feature | Medium | When users request it |

### Medium Priority (Nice to have)

| Feature | Description | Value | Effort | When to implement |
|---------|-------------|-------|--------|-------------------|
| **Compare Paredões** | Side-by-side comparison of two paredões | Medium — pattern analysis | Medium | After 5+ paredões |
| **Arcos Narrativos** | Auto-detect storylines (redemption, downfall, rivalry) | Medium — engagement | High | Mid-season |
| **Semana a Semana** | Accordion with weekly highlights | Medium — navigation | Low | After week 4 |
| **Mudança Acumulada** | Total sentiment change from day 1 to today | Medium — trajectory | Low | Any time |

### Low Priority (Future consideration)

| Feature | Description | Value | Effort | When to implement |
|---------|-------------|-------|--------|-------------------|
| **Reaction Flow Animation** | Animated Sankey over multiple days | Low — novelty | High | Never? |
| **Correlation Dashboard** | Balance vs sentiment vs group vs votes | Low — niche | Medium | If requested |
| **Histórico Similar** | "In past BBBs with similar sentiment, X went home" | Low — no historical data | Very High | Never (no data) |

### Cluster Improvements (Separate track)

| Improvement | Current State | Proposed | Decision |
|-------------|---------------|----------|----------|
| **Dynamic k** | Fixed 4 clusters | Use silhouette score | [ ] Yes [ ] No |
| **Vote-based clustering** | Not implemented | Cluster by voting patterns | [ ] After 3+ paredões |
| **Temporal tracking** | Single snapshot | Track cluster evolution | [ ] Yes [ ] No |
| **Auto-naming** | "Grupo A/B/C/D" | Name by dominant trait | [ ] Yes [ ] No |

### Features Explicitly NOT Doing

| Feature | Reason |
|---------|--------|
| **Votação Live** | Out of scope — requires external data source |
| **Mobile App** | Out of scope — web-only project |
| **Push Notifications** | Out of scope — static site |
| **User Accounts** | Out of scope — no backend |

---

## Decisions Made (2026-01-26)

### Structure Decisions
| # | Question | Decision | Notes |
|---|----------|----------|-------|
| 1 | 4-tab structure? | ✅ Yes for now | **Review later** after implementation |
| 2 | Visão Geral/Cronologia outside tabs? | ✅ Yes | Stay at top, always visible |
| 3 | Section mappings correct? | ✅ Approved | Will reconsider when making things more interesting |

### Cluster Decisions
| # | Question | Decision | Notes |
|---|----------|----------|-------|
| 4 | Keep current algorithm? | ✅ Yes for now | Add improvements to Phase 6 |
| 5 | Move to separate page? | ✅ Yes | Create clusters.qmd experimental page |
| 6 | Add silhouette k selection? | ✅ Create for evaluation | Implement in clusters.qmd, evaluate results |

### Feature Decisions
| # | Question | Decision | Notes |
|---|----------|----------|-------|
| 7 | Deferred features? | Create Phase 7 | Don't lose track of them |
| 8 | Participant Focus Mode? | Add to Phase 7 | Future feature, not now |

### Implementation Decisions
| # | Question | Decision | Notes |
|---|----------|----------|-------|
| 9 | Big change or increments? | **Small increments** | Commit constantly |
| 10 | Preview or full render? | **Full render** | Verify each step works |

---

## Updated Phase Structure

| Phase | Focus | Status |
|-------|-------|--------|
| **Phase 1-2** | 5-page architecture | ✅ Complete |
| **Phase 3** | Trajetória 4-tab restructure | 🔜 Next |
| **Phase 3.5** | Data freshness fixes | ✅ Complete |
| **Phase 4** | Fatos Rápidos + Destaques | 🔜 After Phase 3 |
| **Phase 5** | clusters.qmd creation | 🔜 After Phase 3 |
| **Phase 6** | Cluster algorithm improvements | 🔜 Future |
| **Phase 7** | Deferred features review | 🔜 Future |

---

## Phase 5: Create clusters.qmd (NEW)

> **Purpose**: Move cluster analysis to dedicated experimental page
> **Priority**: Part of trajetória reorganization

### Tasks

| Step | Task | Description |
|------|------|-------------|
| 5.1 | Create clusters.qmd skeleton | Setup cells, page header |
| 5.2 | Move cluster code from trajetoria.qmd | Cut/paste existing implementation |
| 5.3 | Add silhouette k evaluation | Show scores for k=2,3,4,5,6 |
| 5.4 | Add dendrogram visualization | Interactive cluster tree |
| 5.5 | Update _quarto.yml | Add to navbar (or hide, link from trajetória) |
| 5.6 | Add "🧪 Lab" link in trajetória | Cross-reference to experimental page |

### Silhouette K Selection (to implement)

```python
from sklearn.metrics import silhouette_score
import plotly.graph_objects as go

# Test different k values
k_range = range(2, 7)
scores = []

for k in k_range:
    clusters = fcluster(Z, k, criterion='maxclust')
    score = silhouette_score(condensed, clusters, metric='precomputed')
    scores.append({'k': k, 'score': score})

# Find optimal k
optimal_k = max(scores, key=lambda x: x['score'])['k']

# Visualization: bar chart of silhouette scores per k
fig = go.Figure(go.Bar(x=[s['k'] for s in scores], y=[s['score'] for s in scores]))
fig.update_layout(title=f'Silhouette Score por Número de Clusters (Ótimo: k={optimal_k})')
```

**Output**: Shows which k value produces the best-defined clusters.

---

## Phase 6: Cluster Algorithm Improvements (NEW)

> **Purpose**: Enhance clustering after initial implementation works
> **Priority**: Future (after clusters.qmd is stable)

| Step | Task | Description |
|------|------|-------------|
| 6.1 | Dynamic k selection | Use silhouette score to auto-select k |
| 6.2 | Auto-naming clusters | Name by dominant trait (e.g., "Núcleo Veterano") |
| 6.3 | Temporal tracking | Track cluster membership evolution over snapshots |
| 6.4 | Vote-based clustering | Add when we have 3+ paredões |
| 6.5 | Combined clustering | Weight both reactions AND votes |

---

## Phase 7: Deferred Features Review (NEW)

> **Purpose**: Systematic review of deferred features — don't lose track
> **Priority**: After trajetória reorg is stable

### High Priority Features

| Feature | Description | When to implement |
|---------|-------------|-------------------|
| **Participant Focus Mode** | Click name → full journey (sentiment, votes, relationships) | After Phase 4 |
| **Accuracy Tracking** | Did predictions match paredão results? | After 3+ paredões |
| **Date Picker** | Compare any two dates | When users request |

### Medium Priority Features

| Feature | Description | When to implement |
|---------|-------------|-------------------|
| **Compare Paredões** | Side-by-side comparison | After 5+ paredões |
| **Arcos Narrativos** | Auto-detect storylines | Mid-season |
| **Semana a Semana** | Weekly highlights accordion | After week 4 |

### Review Criteria

When reviewing deferred features, evaluate:
1. **User value**: How much does this help viewers?
2. **Data availability**: Do we have enough data?
3. **Implementation effort**: Hours to implement?
4. **Maintenance cost**: Will it break with new data?

---

## Post-Implementation Review Items

Items to review after Phase 3-4 are complete:

- [ ] Is the 4-tab structure intuitive? (Decision #1)
- [ ] Are the section mappings working? (Decision #3)
- [ ] Does silhouette k selection improve clusters? (Decision #6)
- [ ] Which deferred features should we prioritize? (Phase 7)
