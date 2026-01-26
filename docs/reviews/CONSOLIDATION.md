# BBB26 Dashboard Review Consolidation

**Date**: 2026-01-25
**Reviews Analyzed**: 14
**Models**: Claude (Opus, Sonnet, Haiku), Cursor, GPT-5

---

## Overview

| Focus | Reviews | Models |
|-------|---------|--------|
| **UX/Architecture** | 3 | Claude Opus, Cursor, GPT-5 |
| **Technical** | 3 | Claude Sonnet, Cursor, GPT-5 |
| **Polish** | 3 | Claude Haiku, Cursor, GPT-5 |
| **Holistic** | 2 | Claude Sonnet, GPT-5 |
| **DataViz** | 3 | Claude Opus, Cursor, GPT-5 |

---

## 1. UX & Information Architecture

### Consensus (All 3 Reviews Agree) — ✅ All Implemented

| Recommendation | Priority | Status |
|----------------|----------|--------|
| **Add "Destaques do Dia"** at top of landing page | Critical | ✅ Done |
| **Paredão card/status** visible above the fold | Critical | ✅ Done (paredao.qmd) |
| **Move Cronologia** from Painel to Trajetória | Medium | ✅ Done |
| **Trajetória too long** (21 sections) — split into tabs | Critical | ✅ Done (5 tabs) |
| **Reduce callout spam** — keep only 2-3 per page | Medium | ✅ Done |

### Proposed Landing Page Order

```
1. Destaques do Dia (NEW)
   - 3-5 auto-generated bullets
   - Top gainer/loser, dramatic change, paredão status

2. Paredão Status Card (NEW)
   - Compact: status + names + CTA "Ver análise →"

3. KPIs/Visão Geral
   - Value boxes: participants, reactions, days, hostilities
   - One-line summary with link to Cronologia

4. Ranking de Sentimento
   - Full chart (or Top 5 + "Ver completo")

5. Tabela Cruzada (Heatmap)
   - Consider Top 10 compact version for mobile

6. Perfis Individuais
   - Accordion, collapsed by default

7. Navigation Cards
   - Links to Mudanças, Trajetória, Paredão, Arquivo
```

### ASCII Mockup (Above the Fold)

```
┌─────────────────────────────────────────────────────────────────┐
│  DESTAQUES DO DIA                                               │
│  • Jonas lidera pelo 3º dia (+14.5)                             │
│  • Marcelo → Solange: de ❤️ para 🐍 (maior mudança)              │
│  • Leandro no Paredão (indicado por dinâmica)                   │
│  • 95 reações mudaram ontem (21% do total)                      │
├─────────────────────────────────────────────────────────────────┤
│  🗳️ PAREDÃO ATUAL                         [Ver análise →]       │
│  Em formação: Leandro + ? + ?                                   │
├─────────────────────────────────────────────────────────────────┤
│  [❤️ 280]  [Neg 182]  [Hostilidades 38]  [Mudanças 95]          │
│  22 participantes • 462 reações • 13-25 jan   [Cronologia →]    │
├─────────────────────────────────────────────────────────────────┤
│  RANKING DE SENTIMENTO                                          │
│  (horizontal bar chart)                                         │
└─────────────────────────────────────────────────────────────────┘
```

### Unique Ideas Worth Considering

| Source | Idea | Impact |
|--------|------|--------|
| GPT-5 | "Watchlist de Risco" — Top 5 most vulnerable | High |
| Cursor | "Mini-mapa de relações" before full heatmap | Medium |
| Claude | Quarto Dashboard format for Painel only | Medium |

---

## 2. Technical Implementation

### Consensus (All 3 Reviews Agree)

| Topic | Verdict |
|-------|---------|
| **Interactivity** | Nice-to-have, NOT essential |
| **Shiny** | ❌ Don't use (breaks static hosting) |
| **Observable JS** | Possible but overkill for now |
| **Best approach** | Pre-render + tabsets + simple JS show/hide |
| **GitHub Pages + Actions** | ✅ Sufficient for 90 days |
| **JSON-per-snapshot** | ✅ Keep it (scales fine to ~32MB) |
| **Pre-compute metrics** | ✅ Yes — speeds rendering ~70% |

### Interactivity Roadmap

| Phase | Feature | Effort | Complexity |
|-------|---------|--------|------------|
| **1** | Pre-rendered tabsets (Today vs -7d vs -14d) | 2h | Low |
| **2** | JS show/hide for group filters | 2h | Low |
| **3** | Date picker with pre-computed JSON | 4h | Medium |

### Safeguards to Add to CI/CD

```yaml
# Add to daily-update.yml
- name: Validate snapshots
  run: |
    python -c "
    import json, glob, sys
    for f in glob.glob('data/snapshots/*.json'):
        try:
            json.load(open(f))
        except Exception as e:
            print(f'Invalid: {f}: {e}')
            sys.exit(1)
    print('All snapshots valid')
    "

- name: Render with fail-fast
  run: quarto render || exit 1
```

### Cartola BBB Page

| Aspect | Details |
|--------|---------|
| Auto-calculable from API | ~60% (Líder, Paredão, VIP, Monstro) |
| Manual entry needed | ~40% (Big Fone, immunity, Quarto Secreto) |
| Weekly maintenance | ~20 minutes |
| MVP effort | ~3 hours |
| Key visualizations | Cumulative line + weekly stacked bar |

### Data Storage Verdict

**Keep current approach.** JSON-per-snapshot is optimal:
- Scales to 90 days (~32MB uncompressed, ~8MB in git)
- Easy to debug (human-readable)
- Works with git versioning
- No database needed

**Add pre-computed metrics:**
```
data/
├── snapshots/           # Keep as-is
├── daily_metrics.json   # NEW: pre-computed for fast client-side
└── manual_events.json   # Keep as-is
```

---

## 3. Data Visualization

### Chart-by-Chart Assessment

| Chart | Verdict | Action |
|-------|---------|--------|
| **Horizontal bar** (ranking) | ✅ Keep | Highlight Top 5/Bottom 5 |
| **22×22 Heatmap** | ⚠️ Problematic | Mobile: Top 10 only |
| **Diverging bar** (changes) | ✅ Perfect | Order by magnitude |
| **Difference heatmap** | ⚠️ Heavy | Show only changed cells |
| **Sankey** | ⚠️ Hard to read | Filter changes > 3 |
| **Line charts** | ⚠️ Cluttered (22 lines) | Default to Top/Bottom 5 |
| **Network graph** | ⚠️ CPU heavy | Filter to mutual only |
| **Pie charts** | ❌ Replace | Use horizontal bar or waffle |

### New Visualizations to Consider

| Visualization | Purpose | Effort |
|---------------|---------|--------|
| **Bump chart** | Rank evolution without crossing lines | 2h |
| **Lollipop chart** | Lighter alternative to bars | 1h |
| **Sparse heatmap** | Only cells that changed | 1h |
| **Small multiples** | Per-participant mini-cards | 3h |

### Accessibility Fixes

| Issue | Fix | Effort |
|-------|-----|--------|
| Red-green colorblind | Use blue-orange or add patterns | 1h |
| Emoji too small (14px) | Increase to 18px minimum | 30m |
| No alt text | Add figure descriptions | 1h |
| Screen reader support | Add text summaries | 2h |

---

## 4. Holistic Assessment

### Ratings from Fresh Eyes

| Model | Score | Summary |
|-------|-------|---------|
| Claude Sonnet | 7/10 | "Excellent foundation, poor presentation" |
| GPT-5 | 6.5/10 | "Strong data, weak productization" |

### Single Biggest Problem

> **The landing page buries the hook.** Users want "What happened today?" in 30 seconds, but get a long report instead.

### Single Best Thing

> **The data model is genuinely unique.** Daily full reaction graph with asymmetry analysis (blind spots) is analytically valuable.

### What Would Make People Visit Daily

1. Daily highlight cards (drama in 30 seconds)
2. Paredão status always visible
3. "Heat of the day" ranking
4. Shareable cards for WhatsApp/Twitter

### What Would Make Data People Share

1. Methodology transparency
2. Novel visualizations (bump chart, network)
3. Interesting findings (blind spots, predictions)
4. Clean, shareable stat cards

### Wild Ideas

| Source | Idea |
|--------|------|
| Claude Sonnet | Daily digest with blind spot alerts |
| GPT-5 | "BBB26 Heat Index" — single composite score per person |

---

## 5. Polish & Quality

### Testing Strategy (Consensus)

| What | How | Priority |
|------|-----|----------|
| JSON parsing | pytest: all snapshots load | High |
| Calculations | pytest: sentiment, hostility formulas | High |
| Render smoke | CI: `quarto render` exits 0 | High |
| Internal links | Script to verify no broken links | Medium |

### Quick Polish Wins

| Item | Effort | Impact |
|------|--------|--------|
| "Last updated" timestamp | 15m | Medium |
| Favicon | 10m | Low |
| Mobile heatmap (Top 10) | 1h | High |
| Lazy-load charts below fold | 30m | Medium |

### SEO (Deprioritized — Fan Project)

Basic setup only:
- Open Graph image (1 default)
- Site description in `_quarto.yml`
- Sitemap (auto-generated by Quarto)

---

## Priority Matrix

### 🔴 Phase 1: Critical ✅ COMPLETE

| Task | Effort | Impact | Status |
|------|--------|--------|--------|
| Add "Destaques do Dia" to Painel | 2h | Critical | ✅ Done |
| Add Paredão status card to Painel | 1h | Critical | ✅ Done (in paredao.qmd) |
| Add KPI value boxes | 1h | High | ✅ Done |
| Split Trajetória into tabs (5 groups) | 2h | High | ✅ Done |
| Move Cronologia to Trajetória | 30m | Medium | ✅ Done |

**Phase 1: ✅ Complete**

### 🟡 Phase 2: Important (Partially Complete)

| Task | Effort | Impact | Status |
|------|--------|--------|--------|
| Pre-render date comparisons (tabsets) | 2h | High | ✅ Done (trajetoria tabs) |
| Mobile heatmap (Top 10 only) | 1h | Medium | ✅ Done (text tables) |
| Pre-compute daily_metrics.json | 2h | High | ⏳ Pending |
| Add CI validation for snapshots | 30m | Medium | ⏳ Pending |
| Add "last updated" timestamp | 15m | Low | ✅ Done |
| Replace pie charts with bars | 30m | Low | ⏳ Pending |

**Phase 2: ~65% Complete**

### 🟢 Phase 3: Nice to Have

| Task | Effort | Impact |
|------|--------|--------|
| Cartola BBB page (MVP) | 3h | Medium |
| JS group filters (Pipoca/Camarote) | 2h | Medium |
| Bump chart for evolution | 2h | Low |
| Accessibility fixes (colorblind) | 2h | Medium |
| Watchlist de Risco section | 1h | Medium |

**Total Phase 3: ~10 hours**

### ❌ Don't Do

| Item | Reason |
|------|--------|
| Shiny interactivity | Breaks static hosting |
| Observable JS | Overkill, adds complexity |
| Full SEO optimization | Fan project, not commercial |
| User accounts/login | Out of scope |
| Real-time updates | API updates 1x/day anyway |

---

## Consensus Summary

**15 items all reviewers agreed on:**

1. ✅ Add "Destaques do Dia" to landing page
2. ✅ Add Paredão status card above the fold
3. ✅ Trajetória is too long — needs tabs/split
4. ✅ Move Cronologia from Painel to Trajetória
5. ✅ Reduce excessive callouts
6. ✅ Interactivity is nice-to-have, not essential (decided: static first)
7. ✅ Don't use Shiny (breaks static hosting) — using Quarto
8. ✅ Use pre-render + tabsets for date comparison
9. ✅ GitHub Pages + Actions is sufficient — workflow created
10. ✅ Keep JSON-per-snapshot storage
11. ⏳ Pre-compute metrics for faster renders
12. ✅ 22×22 heatmap needs mobile alternative — changed to text tables
13. ⏳ Replace pie charts
14. ⏳ Add basic testing (JSON validation, smoke test)
15. ✅ The data model is the dashboard's biggest strength

---

## Files Reference

```
docs/reviews/
├── CONSOLIDATION.md                    # This file
├── PROMPTS.md                          # Prompts for external models
├── claude-haiku_polish_5t2r9y.md       # 1,149 lines
├── claude-opus_dataviz_1x7z3m.md       # 843 lines
├── claude-opus_ux_7k9m2x.md            # 541 lines
├── claude-sonnet_holistic_8n4v6c.md    # 642 lines
├── claude-sonnet_technical_3p8q1w.md   # 1,674 lines
├── cursor_dataviz_5n2w8q.md            # 699 lines
├── cursor_polish_7x2k9m.md             # 656 lines
├── cursor_technical_4n8r2t.md          # 891 lines
├── cursor_ux_2h4j6k.md                 # 724 lines
├── gpt5_dataviz_k9m3t7.md              # 93 lines
├── gpt5_holistic_j4f8p0.md             # 47 lines
├── gpt5_polish_z8r4k1.md               # 128 lines
├── gpt5_technical_q7n3v2.md            # 188 lines
└── gpt5_ux_p5k2x9.md                   # 166 lines
```

**Total: ~8,400+ lines of analysis**

---

*Generated from 14 AI reviews on 2026-01-25*
