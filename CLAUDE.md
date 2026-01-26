# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Critical: Take Responsibility for Issues

**When Claude introduces bugs, warnings, or errors in code, Claude must:**
1. Take full responsibility — do not blame pre-existing issues or external factors
2. Investigate and fix the issue immediately
3. Never deflect with statements like "this wasn't from my edit" when Claude is the only one editing files

**This is non-negotiable.** If there's an error after Claude's changes, it's Claude's responsibility to fix it.

## Project Overview

BBB26 is a data analysis project that tracks **participant reaction data** from Big Brother Brasil 26 using the GloboPlay API. The main dashboard is `index.qmd` (Quarto), which loads all snapshots, processes reactions, and generates interactive Plotly visualizations.

## Key Commands

```bash
# Fetch new data (saves only if data changed)
python scripts/fetch_data.py

# Build derived data files (auto events, roles, participant index)
python scripts/build_derived_data.py

# Audit all snapshots (find duplicates, unique states)
python scripts/audit_snapshots.py

# Render the dashboard
quarto render index.qmd

# Preview with hot reload
quarto preview
```

## Known Issues

### Quarto render warnings in trajetoria.qmd

When rendering `trajetoria.qmd`, Pandoc reports warnings about unclosed divs:
```
[WARNING] Div at line 437 column 1 unclosed at line 2493...
[WARNING] The following string was found in the document: :::
```

**Investigation results**:
- Source file callouts (`:::`) are balanced
- Final HTML output is valid and renders correctly
- The warning line numbers refer to Pandoc's intermediate document, not the source
- The warnings come from cells with `#| output: asis` that generate markdown dynamically

**Cause**: Pandoc/Quarto processing quirk with complex documents containing fenced divs and dynamic markdown output.

**Impact**: None — the final HTML is valid and renders correctly. The TOC works properly.

## Data Architecture

### API Source
- **Endpoint**: `https://apis-globoplay.globo.com/mve-api/globo-play/realities/bbb/participants/`
- **Returns**: Complete state snapshot — NOT cumulative, NOT additive
- **No timestamp**: API provides no `Last-Modified` header or update timestamp
- **Update frequency**: Data changes daily at unpredictable times, with intraday changes possible

### Critical: Reactions Are Reassigned Daily

The API returns the **current state** of all reactions, not a history. Participants **change** their reactions to others daily:
- Someone who gave ❤️ yesterday can switch to 🐍 today
- Reaction amounts can go up OR down
- The giver lists (who gave which reaction) change between snapshots

This means **every snapshot is a unique complete game state** and must be kept.

### Data Files
- `data/snapshots/YYYY-MM-DD_HH-MM-SS.json` — Full API snapshots (~200-270KB each)
- `data/latest.json` — Copy of most recent snapshot
- `data/paredoes.json` — **Paredão data** (formation, house votes, results) — loaded by `paredao.qmd` and `paredoes.qmd`
- `data/manual_events.json` — **Manual game events** not in the API (Big Fone, exits, special events)
- `data/derived/` — **Derived data** built from snapshots + manual events (auto events, roles per day, participants index, daily metrics)
- `data/CHANGELOG.md` — Documents data timeline and findings
- `scripts/data_utils.py` — Shared loaders/parsers used by QMD pages (load snapshots, parse roles, build reaction matrix)
- New format wraps data: `{ "_metadata": {...}, "participants": [...] }`
- Old format is just the raw array: `[...]`
- `scripts/fetch_data.py` handles both formats and saves only when data hash changes
- **Synthetic snapshots** have `_metadata.synthetic = true` (see below)

**Eliminação no API**:
- O API **não** fornece percentuais de voto do público.
- Participantes eliminados **desaparecem** da lista de `participants` após a eliminação (não há flag confiável de eliminado nos snapshots atuais).
- Por isso, percentuais e resultados precisam ser **registrados manualmente** em `data/paredoes.json`.

### Current Data Flow (what is auto vs manual)
**Auto (from API snapshots):**
- Snapshots (`data/snapshots/*.json`) + `data/latest.json` are produced by `scripts/fetch_data.py`.
- `data/derived/roles_daily.json` stores **roles/VIP per day** (built from snapshots).
- `data/derived/auto_events.json` stores **auto power events** (Líder/Anjo/Monstro/Imune) derived from role changes.
- `data/derived/daily_metrics.json` stores **per-day sentiment totals** and reaction counts (used for faster timelines).
  - Uses the standard sentiment weights (Coração +1, Planta/Mala/Biscoito/💔 -0.5, Cobra/Alvo/Vômito/Mentiroso -1).
- Exit detection is inferred by **absence** across consecutive snapshots (used to set `active` in `participants_index.json`).

**Manual (human-maintained):**
- `data/paredoes.json` — formation + results + **percentuais** (not in API).
- `data/manual_events.json` — Big Fone, contragolpe, voto duplo, veto, perdeu voto, saídas, etc.

**Important fragmentation (current state):**
- `cartola.qmd` computes roles and weekly points **inside the page** (not persisted).
- Multiple pages duplicate snapshot-loading and role-parsing logic.

### Manual Events Data (`data/manual_events.json`)

Events **not available from the API** are tracked manually in this JSON file.

**Auto-detected from API** (do NOT add manually):
- Líder, Anjo, Monstro, Imune — detected via `characteristics.roles`
- VIP membership — detected via `characteristics.group`
- Paredão — detected via `characteristics.roles`

The Cartola page (`cartola.qmd`) auto-detects role transitions by comparing consecutive snapshots.

**Structure** (manual-only data):
- `participants` — Exit status for people who left (desistente, eliminada, desclassificado)
- `weekly_events` — Per-week: Big Fone, Quarto Secreto, notes
- `special_events` — Dinâmicas, new entrants, one-off events
- `power_events` — **Powers and consequences** (immunity, contragolpe, voto duplo, veto, perdeu voto)
- `cartola_points_log` — **Manual point overrides** for events not inferable from API

**Manual categories + AI fill rules**:
- `participants`: use for **desistência / eliminação / desclassificação**.
  - Fields: `status`, `date`, `fonte`.
  - Name must match snapshots **exactly**.
- `weekly_events`: week‑scoped dynamics (Big Fone, Quarto Secreto, caixas, notes).
  - Always include `week` (int) and `date` (`YYYY-MM-DD`).
- `special_events`: one‑off events not tied to a specific week.
- `power_events`: only powers/consequences **not fully exposed by API** (contragolpe, voto duplo, veto, perdeu voto).
  - Fields: `date`, `week`, `type`, `actor`, `target`, `detail`, `impacto`, `origem`, `fontes`.
  - Optional: `actors` (array) for **consensus** dynamics (ex.: duas pessoas indicam em consenso).
  - `impacto` is **for the target** (positivo/negativo).
  - If `actor` is not a person, use standardized labels: `Big Fone`, `Prova do Líder`, `Prova do Anjo`, `Caixas-Surpresa`.
- `cartola_points_log`: only events **not inferable** from snapshots or paredões (salvo, não eliminado, etc.).

**API vs manual**:
- API snapshots **auto-detect** roles (Líder/Anjo/Monstro/Imune/VIP/Paredão).
- Manual events fill **what the API does not expose** (Big Fone, contragolpe, veto, voto duplo, etc.).

**When to update**:
- After each elimination or desistência (update `participants`)
- After Big Fone (who answered, consequence)
- After special events (dinâmicas like Caixas-Surpresa)
- After any **power effect** (veto, voto duplo, perdeu voto, contragolpe, imunidade)
- After each paredão result to log **salvos/sobreviventes** and any point events not detectable via API (see below)
- Depois de qualquer edição manual, rode `python scripts/build_derived_data.py` para atualizar `data/derived/`.

**Caixas‑Surpresa (referência para preencher `power_events`)**:
- Caixa 1: poder de **vetar o voto** de alguém.
- Caixa 2: **não vota** no próximo paredão.
- Caixa 3: **voto com peso 2**.
- Caixas 4 e 5: precisam **indicar alguém em consenso** (evento **público**); se não houver consenso, os dois vão ao paredão.

### Porting logic to `daily_metrics.json` (how to move work out of QMDs)
Use `data/derived/daily_metrics.json` whenever a chart only needs **per‑day aggregates** (no per‑giver/per‑receiver matrix).

**Good candidates**:
- Sentiment timelines (already ported in `index.qmd` and `trajetoria.qmd`)
- Daily totals by participant (total_reactions)
- Per‑day top 3/bottom 3 sentiment (read `sentiment` map)
- Daily participant counts

**Not good candidates (need full matrices)**:
- Cross tables (giver→receiver reactions)
- Mutual hostility/reciprocity analysis
- Sankey of daily reaction shifts

**How to add new fields**:
1. Update `scripts/build_derived_data.py` → `build_daily_metrics()` to compute the metric per snapshot day.
2. Add the new field to each `daily` entry (e.g., `"reaction_counts": {name: {...}}`).
3. Rebuild: `python scripts/build_derived_data.py`.
4. In the QMD, load `daily_metrics.json` and **fallback to snapshots** if the field is missing.

**Schema (current)**:
```
data/derived/daily_metrics.json
{
  "_metadata": {...},
  "daily": [
    {
      "date": "YYYY-MM-DD",
      "participant_count": 22,
      "total_reactions": 462,
      "sentiment": { "Nome": 12.5, ... }
    }
  ]
}
```

**Cartola BBB Points**:
| Event | Points |
|-------|--------|
| Líder | +80 |
| Anjo | +45 |
| Quarto Secreto | +40 |
| Imunizado / Big Fone | +30 |
| Salvo do paredão | +25 |
| Não eliminado no paredão | +20 |
| Não emparedado | +10 |
| VIP / Não recebeu votos | +5 |
| Monstro retirado do VIP | -5 |
| Monstro | -10 |
| Emparedado | -15 |
| Eliminado | -20 |
| Desclassificado | -25 |
| Desistente | -30 |

**Cartola BBB — regras oficiais (GShow)**:
- **Fonte oficial**: https://gshow.globo.com/realities/bbb/bbb-26/cartola-bbb/noticia/o-que-e-cartola-bbb-entenda-como-funciona-a-novidade-do-reality.ghtml
- **Líder (+80)**: maior pontuação; **não acumula com outros itens**.
- **Anjo (+45)**: quando **autoimune**, **acumula com Imunizado**.
- **Quarto Secreto (+40)**.
- **Imunizado por dinâmica (+30)**: não acumula com **Não emparedado**, **Não recebeu votos** e **Salvo do paredão**.
- **Atendeu Big Fone (+30)**: acumula com efeitos do Big Fone (pode somar **Imunizado +30** ou **Emparedado -15**).
- **Salvo do paredão (+25)**: quando emparedado é salvo por dinâmica (ex.: Bate-Volta/Big Fone). **Não recebe “Não emparedado”**, mas acumula com **Emparedado**. Se foi emparedado com janela fechada e salvo com janela aberta, vale apenas **Emparedado**.
- **Não eliminado no paredão (+20)**: indicado que permanece após votação.
- **Não emparedado (+10)**: disponível para votação e não foi ao paredão; **não vale para imunizados (Líder/Anjo) nem salvos**.
- **VIP (+5)**: não acumula com Líder.
- **Não recebeu votos da casa (+5)**: disponíveis para votação **sem votos**; não vale para Líder e imunizados.
- **Palpites (+5)**: pontos extras por acerto de palpites (não modelado no dashboard).
- **Janela de escalação**: quando aberta, **dinâmicas não pontuam** (não modelamos janela; calculamos pelos eventos reais).
- **Nota do dashboard**: calculamos **pontuação por participante**, sem times/palpites individuais.

**Cartola manual events (use `cartola_points_log`)**:
- Events **not inferable from API snapshots** should be logged here with points and date.
- Examples: `salvo_paredao`, `nao_eliminado_paredao`, `nao_emparedado`, `monstro_retirado_vip`.
- Structure: one entry per participant/week with `events: [{event, points, date, fonte?}]`.
- Always include matching `fontes` in `manual_events.json` for the underlying real-world event.

**Cartola auto-derived points (from `data/paredoes.json`)**:
- `salvo_paredao` — **Venceu o Bate e Volta** (escapou do paredão). Não acumula com `nao_emparedado`.
- `nao_eliminado_paredao` — Indicados finais que **permaneceram** após o resultado.
- `nao_emparedado` — Participantes **ativos** na semana **fora da lista final** do paredão.

**Power events (`power_events`)**:
- Armazenados em `data/manual_events.json` (lista manual).
- Campos: `date`, `week`, `type`, `actor`, `target`, `source`, `detail`, `impacto`, `origem`, `fontes`.
- `impacto` refere-se ao efeito **para quem recebeu** (`positivo` ou `negativo`).
- `origem`: `manual` (quando registrado no JSON) ou `api` (quando derivado automaticamente).
- Tipos já usados: `imunidade`, `indicacao`, `contragolpe`, `voto_duplo`, `voto_anulado`, `perdeu_voto`.
- **Auto‑detectados da API (trajetoria.qmd)**: Líder e Anjo são derivados das mudanças de papéis nos snapshots diários e **não são salvos** em `manual_events.json`. Esses eventos entram no painel apenas no momento do render e **não ficam disponíveis para outras páginas**.
- Se precisar persistir/compartilhar ou adicionar fontes, registre manualmente em `data/manual_events.json` (ou criar um arquivo dedicado para eventos auto‑detectados).
  - Observação: a detecção usa **1 snapshot por dia** (último do dia). Mudanças intra‑dia podem não aparecer.

**Power events — awareness & visibility (para UI / risco)**:
- `actor` e `target` devem sempre existir — o **alvo sabe quem causou** o evento quando a dinâmica é pública (Big Fone, Caixas‑Surpresa, Líder/Anjo).
- Para eventos **auto‑infligidos** (`actor == target`), trate como **auto‑impacto** (ex.: “perdeu voto” ao abrir caixa).  
- Para evitar ambiguidades, quando possível adicione campos opcionais:
  - `self_inflicted`: `true|false` (se `actor == target`).
  - `visibility`: `public` (sabido na casa) ou `secret` (só revelado depois).
  - `awareness`: `known`/`unknown` (se o alvo sabe quem causou).

**Votos da casa (secretos)**:
- Estão em `data/paredoes.json` → `votos_casa` e **só são públicos após a formação**.
- Para UI: marcar como **“voto secreto (para participantes)”** e **não usar** como “sinal percebido” antes da revelação.
- Se houver dinâmica tipo **dedo‑duro**, registrar em `manual_events.weekly_events`:
  - `dedo_duro`: `{ "votante": "...", "alvo": "...", "detalhe": "...", "date": "YYYY-MM-DD" }`
  - Esses votos passam a ser **públicos** e podem entrar em análises de percepção.

**Perfis Individuais — uso recomendado (UI)**:
- Mostrar **Poderes recebidos** em duas linhas:
  - `+` (benefícios) e `−` (prejuízos), com chips compactos: ícone + mini‑avatar do **ator**.
  - Quando houver repetição, mostrar `2x`/`3x`.
- Para eventos **auto‑infligidos**, usar badge `auto` (ex.: ↺) e reduzir peso no “risco social”.
- Mostrar **Votos da casa recebidos** como linha separada:
  - Avatares pequenos de quem votou + contagem `2x` se voto duplo.
  - Label “voto secreto (para participantes)” para deixar claro que não é percepção imediata.

**Risco (sugestão de cálculo)**:
- Separar em **Risco social (percebido)** vs **Risco externo (real)**.
- `Risco social`: peso maior para eventos **públicos** de prejuízo causados por outros + conflitos/reactions negativas.
- `Risco externo` (proposta atual):
  - `1.0 × votos_recebidos` +
  - `1.5 × prejuízos públicos` +
  - `0.75 × prejuízos secretos` +
  - `0.5 × auto‑infligidos` +
  - `+2` se está no Paredão.
- **Animosidade index** é **experimental** e deve ser **recalibrado semanalmente** após indicações/contragolpes/votações.
  - Registre ajustes no `IMPLEMENTATION_PLAN.md` para manter histórico e evitar esquecimento.
 - **Animosidade usa histórico com decaimento**: eventos negativos antigos continuam afetando a percepção, mas com peso menor (ex.: `peso = 1/(1 + semanas_passadas)`).

### Proposed consolidation (not implemented yet)
**Goal**: reduce fragmentation and make derived data reusable across pages.
**Implemented (2026-01-26)**:
- `data/derived/participants_index.json` — canonical list (name, grupo, avatar, first/last seen, active, status).
- `data/derived/roles_daily.json` — roles + VIP per day (one snapshot/day).
- `data/derived/auto_events.json` — role-change events (Líder/Anjo/Monstro/Imune) with `origem: api`.
- `data/derived/daily_metrics.json` — per-day sentiment + total reactions.
- `data/derived/validation.json` — warnings for manual data mismatches.
- `scripts/build_derived_data.py` builds all derived files.
- `scripts/fetch_data.py` calls derived builder by default.

**Adding source URLs (`fontes`):**

Each entry in `manual_events.json` has a `fontes` array for GShow/news article URLs that confirm the event.

**How to find sources** (search Google in Portuguese):
| Event Type | Search Pattern |
|------------|----------------|
| Líder | `"BBB 26 líder semana [N]" site:gshow.globo.com` |
| Anjo | `"BBB 26 anjo semana" site:gshow.globo.com` |
| Monstro | `"BBB 26 monstro castigo" site:gshow.globo.com` |
| Big Fone | `"BBB 26 big fone" site:gshow.globo.com` |
| Desistência | `"BBB 26 [nome] desistiu" site:gshow.globo.com` |
| Eliminação | `"BBB 26 [Nº] paredão eliminado" site:gshow.globo.com` |
| New entrants | `"BBB 26 novos participantes" site:gshow.globo.com` |
| Caixas/Dinâmicas | `"BBB 26 caixas surpresa" site:gshow.globo.com` |
| VIP members | `"BBB 26 VIP semana" site:gshow.globo.com` |

**Best sources**: GShow (official), UOL, Terra, Exame, NSC Total, Rádio Itatiaia

### Reaction Categories
```python
POSITIVE = ['Coração']  # ❤️
MILD_NEGATIVE = ['Planta', 'Mala', 'Biscoito', 'Coração partido']  # 🌱💼🍪💔
STRONG_NEGATIVE = ['Cobra', 'Alvo', 'Vômito', 'Mentiroso']  # 🐍🎯🤮🤥
```

Sentiment weights: positive = +1, mild_negative = -0.5, strong_negative = -1

**Note**: 💔 Coração partido (broken heart) is classified as **mild negative** because it represents disappointment rather than hostility. It's commonly used for participants who were once close but drifted apart.

### Important: Queridômetro is SECRET

**Participants do NOT see each other's reactions.** The queridômetro is only visible to:
- The TV audience (shown daily during the program)
- Participants after they leave the house

This means:
- A participant giving ❤️ to someone does NOT mean they "declared" friendship
- A participant giving 🐍 does NOT mean they "declared" hostility
- All reactions are **private opinions** visible only to viewers
- Participants can only guess each other's feelings based on behavior, not the queridômetro

**Language to AVOID** in the dashboard:
- ❌ "traíram a amizade declarada" (betrayed declared friendship)
- ❌ "inimigos declarados" (declared enemies)
- ❌ "demonstravam afeto público" (showed public affection)

**Correct language:**
- ✅ "davam ❤️" (gave heart) — factual, no assumption of knowledge
- ✅ "contradição entre reação e voto" (contradiction between reaction and vote)
- ✅ "hostilidade mútua" (mutual hostility) — both dislike each other, but secretly

### Hostility Analysis

The dashboard tracks two types of hostility patterns that are strategically important:

**Two-sided (mutual) hostility**: Both A and B give each other negative reactions.
- Both secretly dislike each other (but may not know it's mutual)
- Votes between them are **consistent** with their private feelings
- Example: Ana Paula Renault ↔ Brigido (longest mutual hostility in BBB26)

**One-sided (unilateral) hostility**: A gives B a negative reaction, but B gives A a ❤️.
- Creates **blind spots** — B likes A, but A secretly dislikes B
- B may be surprised when A votes against them
- Example: In 1º Paredão, Paulo Augusto received votes from 6 people who gave him ❤️

**Vulnerability ratio**: `(hearts given to enemies) / (attacks on friends + 1)`
- High ratio = participant has major blind spots
- Gabriela and Matheus have the highest vulnerability in BBB26

### Data Update Timing

The API data has **three distinct update patterns**:

| Data Type | Update Time (BRT) | Stability |
|-----------|-------------------|-----------|
| **Reactions (Queridômetro)** | ~10h-12h daily | Stable after morning Raio-X |
| **Balance (Estalecas)** | Any time | Changes with purchases, rewards, punishments |
| **Roles** | During/after episodes | Líder, Anjo, Monstro, Paredão ceremonies |

**Key weekly events:**
- **Daily**: Raio-X ~10h-12h BRT (reactions update)
- **Sunday**: Líder ceremony, Anjo ceremony, Paredão formation ~22h-23h BRT
- **Tuesday**: Elimination ~23h BRT (participant disappears from API)
- **Any day**: Balance changes from purchases, rewards, or punishments

### Multi-Capture Strategy

GitHub Actions runs **4x daily** to catch different types of changes:

| UTC | BRT | Purpose |
|-----|-----|---------|
| 09:00 | 06:00 | Pre-Raio-X baseline (yesterday's reactions) |
| 15:00 | 12:00 | **Primary capture** — today's reactions after Raio-X |
| 21:00 | 18:00 | Evening — catches afternoon balance/role changes |
| 03:00 | 00:00 | Night — catches post-episode changes (Sun/Tue) |

**How it works:**
- `fetch_data.py` saves **only if data hash changed**
- Multiple snapshots per day are normal — they track different game states
- Each snapshot records `change_types` in metadata: `reactions`, `balance`, `roles`, `elimination`, `new_entrants`

### Two Data Views in Dashboard

The dashboard maintains two perspectives:

1. **All captures** (`snapshots`) — Used by:
   - Balance timeline charts
   - Role change tracking
   - Intraday analysis

2. **Daily captures** (`daily_snapshots`) — One per date (last capture). Used by:
   - Reaction-based charts (heatmap, ranking, profiles)
   - Day-over-day comparisons
   - Sentiment evolution

A capture before the morning Raio-X may still reflect **yesterday's reactions**.
The 12:00 BRT capture is the **primary** one for reaction analysis.

### Volatile Fields (change daily)
- `balance` — decreases over time
- `roles` — rotates (Líder, Paredão, etc.)
- `group` — can change (Vip ↔ Xepa)
- `receivedReactions` — amounts AND givers change daily
- `eliminated` — **always false in practice**; participants who leave simply disappear from subsequent snapshots

### Synthetic Snapshots (Filling Gaps)

When a date is missed (no API capture), we can build a **synthetic snapshot** from the GShow queridômetro article for that day. The article publishes who gave which negative/mild reaction to whom.

**Key insight**: The queridômetro is a **complete directed graph** — every active participant gives exactly ONE reaction to every other participant. GShow only publishes negative/mild reactions. **Hearts are inferred**: if giver X gave negative reactions to targets A, B, C → X gave hearts to all remaining targets. This makes the inferred data logically certain.

**How to identify**: `_metadata.synthetic == true` in the JSON file.

**How to build one**:
1. Find the GShow queridômetro article: search `"queridômetro BBB 26" site:gshow.globo.com`
2. Use `scripts/build_jan18_snapshot.py` as a template
3. Clone structural fields from the nearest real snapshot
4. Parse the article's negative/mild reaction lists
5. Infer hearts: fill remaining giver→target pairs with Coração
6. Check for punished participants (e.g., Milena on Jan 18) — they may or may not have participated
7. Save with `_metadata.synthetic = true` and document methodology

**Current synthetic snapshots**:
- `2026-01-18_12-00-00.json` — Complete reaction graph (552 reactions: 453 hearts + 99 negative/mild)

### Participant Timeline

| Date | Count | Event |
|------|-------|-------|
| Jan 13 | 21 | Initial cast |
| Jan 15 | 20 | Henri Castelli **desistiu** (quit) |
| Jan 18 | 24 | Chaiany, Gabriela, Leandro, Matheus enter |
| Jan 19 | 23 | Pedro **desistiu** (quit) |
| Jan 21 | 22 | Aline Campos **eliminada** (1º Paredão) |

**Important**: The API `eliminated` field is **never set to true**. Participants who leave simply disappear from the next snapshot. Track exits by comparing participant lists between consecutive snapshots.

## Repository Structure

```
BBB26/
├── index.qmd               # Main dashboard — overview, paredão, rankings, profiles
├── mudancas.qmd            # Day-over-day changes (O Que Mudou)
├── trajetoria.qmd          # Trajectory analysis — evolution, hostilities, clusters, graphs
├── paredao.qmd             # Current paredão status
├── paredoes.qmd            # Paredão archive — historical analysis per paredão
├── _quarto.yml             # Quarto configuration (5-page website with navbar)
├── data/
│   ├── snapshots/           # Canonical JSON snapshots (one per unique data state)
│   ├── latest.json          # Most recent snapshot
│   ├── paredoes.json        # Paredão data (formation, house votes, results)
│   ├── manual_events.json   # Manual game events (Big Fone, exits, special events)
│   └── CHANGELOG.md         # Data timeline documentation
├── scripts/
│   ├── fetch_data.py        # Fetch API, save if changed (hash comparison)
│   ├── audit_snapshots.py   # Audit tool for deduplication
│   └── build_jan18_snapshot.py  # Template for building synthetic snapshots
├── _legacy/                 # Old assets (gitignored)
│   ├── BBB.ipynb            # Original notebook (replaced by index.qmd)
│   └── historico.qmd        # Archived history page (lazy JS rendering, not working)
├── requirements.txt         # Python dependencies
└── IMPLEMENTATION_PLAN.md   # GitHub Actions + Quarto + Pages plan
```

## Five-Page Architecture

The site has five pages, all rendered by Quarto:

| Page | File | Purpose |
|------|------|---------|
| **📊 Painel** | `index.qmd` | Main dashboard: overview, ranking, heatmap, profiles (links to paredão) |
| **📅 O Que Mudou** | `mudancas.qmd` | Day-over-day changes: winners/losers, volatility, Sankey diagrams |
| **📈 Trajetória** | `trajetoria.qmd` | Evolution over time: sentiment, alliances, hostilities, clusters, graphs |
| **🗳️ Paredão** | `paredao.qmd` | Current paredão: formation, votes, vote-reaction analysis (**paredões data lives here**) |
| **📚 Arquivo** | `paredoes.qmd` | Paredão archive: historical analysis per elimination |

**Key design decisions:**

- Each `.qmd` renders independently — no shared Python state. Pages duplicate the setup/load-data cells from `index.qmd`. This is intentional and acceptable since data loading is fast.
- The navbar (`_quarto.yml`) links all pages.
- Dark theme (`darkly`) with custom `bbb_dark` Plotly template for consistent styling.
- Full-width layout (`page-layout: full`) with TOC sidebar for navigation within pages.

## Page Content Summary

Each section is tagged with its data source:
- 📸 **Dado do dia** — uses only the most recent snapshot
- 📅 **Comparação dia-a-dia** — compares the two most recent daily snapshots
- 📈 **Dado acumulado** — uses all historical snapshots
- 🗳️ **Paredão-anchored** — uses snapshot from paredão date (not latest)

## Critical: Data Freshness and Paredão Archival

### Principle: Live Pages vs Archived Analysis

| Page Type | Data Source | Why |
|-----------|-------------|-----|
| **Live pages** (Painel, Mudanças, Trajetória) | `latest` / `snapshots[-1]` | Show current game state |
| **Paredão em andamento** | `latest` for status, paredão-date for analysis | Current status matters, but analysis should use vote-day data |
| **Paredão finalizado** | Paredão-date snapshot ONLY | Historical archive must be frozen |
| **Arquivo de Paredões** | Each paredão's date snapshot | Each analysis is a time capsule |

### Why This Matters

When analyzing "did reactions predict votes?", we MUST use data from **before/during** voting, NOT after:
- Votes happen Tuesday night
- Reactions can change Wednesday morning
- Using Wednesday's data to analyze Tuesday's votes is **invalid**

### Implementation Requirements

**For `paredao.qmd` (current paredão):**
```python
# When status == 'em_andamento': OK to use latest for status display
# When status == 'finalizado': ALL analysis must use paredão-date snapshot

if ultimo.get('status') == 'finalizado':
    # Use paredão-date snapshot for ALL sections
    snap, matrix, idx = get_snapshot_for_date(paredao_date)
else:
    # em_andamento: can use latest for current status
    # but analysis sections should still use paredão-date when available
```

**For `paredoes.qmd` (archive):**
```python
# ALWAYS use paredão-date snapshot - this is historical analysis
snap_p, matrix_p, idx_p = get_snapshot_for_date(par_date, snapshots, all_matrices)
```

### Sections That Must Use Paredão-Date Data

When `status == 'finalizado'`:

| Section | Current | Should Be |
|---------|---------|-----------|
| Leitura Rápida dos Indicados | `latest['participants']` ❌ | `snap_paredao['participants']` ✅ |
| Vote Analysis | `closest_idx` ✅ | Correct |
| Relationship History | Stops at `paredao_date` ✅ | Correct |

### Archival Process

When a paredão is finalized:
1. Ensure we have a snapshot from the paredão date (or day before)
2. Update `data/paredoes.json` with results
3. All analysis in both `paredao.qmd` and `paredoes.qmd` will use frozen data
4. Future renders will show the same analysis (historical consistency)

### Common Mistake to Avoid

❌ **Wrong**: Using `latest` or `snapshots[-1]` in paredão analysis
```python
# BAD - this changes every time we get new data
for p in latest['participants']:
    sent_hoje[name] = calc_sentiment(p)
```

✅ **Correct**: Using paredão-date snapshot
```python
# GOOD - this is frozen at vote time
snap_p, matrix_p, _ = get_snapshot_for_date(paredao_date)
for p in snap_p['participants']:
    sent_paredao[name] = calc_sentiment(p)
```

### index.qmd (📊 Painel)

| Section | Tag | Description |
|---------|-----|-------------|
| Visão Geral | 📸 | Overview stats: participants, reactions, groups |
| Cronologia do Jogo | 📈 | Timeline of entries/exits |
| Ranking de Sentimento | 📸 | Horizontal bar chart of sentiment scores |
| Tabela Cruzada | 📸 | Heatmap of who gave what to whom |
| Perfis Individuais | 📸 | Per-participant strategic analysis with relationship categories |

Note: Paredão content was moved to `paredao.qmd`. The main page has a callout linking to the paredão page.

### paredao.qmd (🗳️ Paredão)

**This is where paredão data (the `paredoes` list) is maintained.**

| Section | Tag | Description |
|---------|-----|-------------|
| Paredão Atual | API+Manual | Status from API + manual formation details |
| Resultado do Paredão | Manual | Vote percentages, cards with avatars |
| Voto da Casa vs Queridômetro | Manual+📸 | Coherence table: did votes match reactions? |
| Reações Preveem Votos? | Manual+📸 | Scatter plot, pie chart, "O caso X" analysis |

### mudancas.qmd (📅 O Que Mudou)

| Section | Tag | Description |
|---------|-----|-------------|
| Ganhadores e Perdedores | 📅 | Who improved/declined most |
| Mapa de Diferenças | 📅 | Heatmap of reaction changes |
| Volatilidade | 📅 | Who changed most reactions |
| Fluxo de Reações (Sankey) | 📅 | Flow diagram of reaction migrations |
| Mudanças Dramáticas | 📅 | Biggest individual shifts |
| Hostilidades Novas | 📅 | New one-sided hostilities |

### trajetoria.qmd (📈 Trajetória)

| Section | Tag | Description |
|---------|-----|-------------|
| Evolução do Sentimento | 📈 | Line chart of sentiment over time |
| Alianças e Rivalidades | 📈 | Most consistent mutual hearts/negativity |
| Dinâmica das Reações | 📈 | Reaction changes between days |
| Vira-Casacas | 📈 | Who changes opinions most often |
| Dinâmica Vip vs Xepa | 📈 | In-group vs out-group favoritism |
| Hostilidades Persistentes | 📈 | Longest-running hostilities over time |
| Saldo e Economia | 📈 | Balance over time |
| Grafo de Relações | 📸 | Network visualization |
| Hostilidades do Dia | 📸 | Who attacks friends, who loves enemies |
| Clusters de Afinidade | 📸 | Hierarchical clustering + reordered heatmap |
| Saldo vs Sentimento | 📸 | Correlation between balance and sentiment |
| Quem Dá Mais Negatividade | 📸 | Top negative reaction givers |
| Insights do Jogo | 📸+📈 | Key findings: blind spots, voting relevance |

## Histórico de Paredões Page (paredoes.qmd)

Per-paredão analysis with these sections:
- **Resultado** — grouped bar chart (voto único, torcida, final)
- **Como foi formado** — narrative of paredão formation
- **Votação da Casa** — table of who voted for whom
- **Voto da Casa vs Reações** — table comparing votes with reactions given
- **Reações Preveem Votos?** — scatter plot with correlation
- **Votaram no que mais detestam?** — pie chart of vote coherence
- **O caso [mais votado]** — analysis of the most-voted participant
- **Indicação do Líder** — whether leader's nomination was consistent with reactions
- **Ranking de Sentimento** — bar chart for that paredão date
- **Reações Recebidas** — table with emoji breakdown per participant

## Dashboard Structure (index.qmd)

The dashboard has two types of data:

### Automatic Data (API)
Fetched from the GloboPlay API — reactions, sentiment, balance, groups, roles.
Updated automatically by `scripts/fetch_data.py`.

### Manual Data (Paredão)
Game events not available from the API. Hardcoded in **`paredao.qmd`** in the `paredoes` list.
**Must be updated manually after each elimination.**

Note: The paredão data was moved from `index.qmd` to `paredao.qmd` as part of the 5-page reorganization.

## Paredão Status System

Each paredão has a `status` field that controls what is displayed:

| Status | When | Dashboard Shows |
|--------|------|-----------------|
| `'em_andamento'` | Sunday night → Tuesday night | Nominees, formation, house votes. NO results. |
| `'finalizado'` | After Tuesday result | Full results: vote %, who was eliminated |

## Paredão Update Workflow

### Mid-Week (Dinâmicas) — Partial Formation

Some weeks, a dinâmica (e.g., Caixas-Surpresa, Big Fone) nominates someone to the paredão **before Sunday**. When this happens:

**Step 1: Fetch fresh data and check API**
```bash
python scripts/fetch_data.py
python3 -c "
import json
with open('data/latest.json') as f:
    data = json.load(f)
participants = data['participants'] if 'participants' in data else data
for p in participants:
    roles = p.get('characteristics', {}).get('roles', [])
    role_labels = [r.get('label') if isinstance(r, dict) else r for r in roles]
    if 'Paredão' in role_labels:
        print(f\"{p['name']} ({p['characteristics'].get('memberOf', '?')})\")
"
```

**Step 2: Create partial entry (if new paredão)**

Add a new entry to `data/paredoes.json`:

```
"Add new paredão (partial formation) to data/paredoes.json:

NÚMERO: [N]
DATA PREVISTA: [next Tuesday, YYYY-MM-DD]
DINÂMICA: [what happened, who was nominated, how]
INDICADO(S) ATÉ AGORA: [list with 'como' field]
"
```

The dashboard will show "FORMAÇÃO EM ANDAMENTO" with placeholder cards for missing nominees.

### Sunday Night (~22h45 BRT) — Full Formation

The full paredão formation happens live on TV.

**Step 1: Fetch fresh data from API**
```bash
python scripts/fetch_data.py
```

**Step 2: Check who has the Paredão role**
```bash
python3 -c "
import json
with open('data/latest.json') as f:
    data = json.load(f)
participants = data['participants'] if 'participants' in data else data
for p in participants:
    roles = p.get('characteristics', {}).get('roles', [])
    role_labels = [r.get('label') if isinstance(r, dict) else r for r in roles]
    if 'Paredão' in role_labels:
        print(f\"{p['name']} ({p['characteristics'].get('memberOf', '?')})\")
"
```

**Step 3: Update or create `em_andamento` entry**

If partial entry exists, update it in `data/paredoes.json`. Otherwise create new:

```
"Update/add paredão (em andamento) to data/paredoes.json:

FORMAÇÃO:
- Líder da semana: [name]
- Indicação do líder: [name] (motivo: ...)
- Big Fone / Contragolpe / Anjo: [details if applicable]
- Imunizado: [name] por [who gave immunity]
- INDICADOS: [list with 'como' for each: Dinâmica/Líder/Casa]
VOTAÇÃO DA CASA: [who voted for whom]
- [voter1] → [target]
- [voter2] → [target]
- ... (all house votes)
BATE E VOLTA: [who competed, who won/escaped]
"
```

### Tuesday Night (~23h BRT) — Result

After the elimination is announced on TV:

**Step 1: Update status to `finalizado` and add results**

```
"Update paredão Nº to finalizado in data/paredoes.json:

RESULTADO: [who was eliminated] with [X]% of the vote
PERCENTAGENS:
- Voto Único (CPF): [name1] X%, [name2] X%, [name3] X%
- Voto Torcida: [name1] X%, [name2] X%, [name3] X%
- Média Final: [name1] X%, [name2] X%, [name3] X%
"
```

### Where to Find This Data

Search for these terms (in Portuguese) right after the elimination episode:

| Data | Search Terms | Best Sources |
|------|-------------|-------------|
| Vote percentages (total) | `BBB 26 Nº paredão porcentagem resultado` | GShow, Terra, UOL |
| Voto Único / Torcida breakdown | `BBB 26 paredão voto único voto torcida` | Portal Alta Definição, Rádio Itatiaia |
| House votes (who voted whom) | `BBB 26 quem votou em quem Nº paredão` | Exame, GShow, UOL |
| Leader nomination reason | `BBB 26 líder indicou paredão` | GShow, NSC Total |
| Formation details | `BBB 26 como foi formado paredão` | GShow |

### Data Structure in data/paredoes.json

Each paredão is an object in the `paredoes` array. The JSON file has this structure:

```python
{
    'numero': N,
    'status': 'em_andamento' | 'finalizado',  # Controls display mode
    'data': 'YYYY-MM-DD',                      # Date of elimination (or expected)
    'titulo': 'Nº Paredão — DD de Mês de YYYY',
    'total_esperado': 3,                       # Expected number of nominees (for placeholders)
    'formacao': 'Description of how the paredão was formed...',
    'lider': 'Leader Name',                    # Can be None if not yet defined
    'indicado_lider': 'Who the leader nominated',  # Can be None
    'imunizado': {'por': 'Who gave immunity', 'quem': 'Who received'},
    'participantes': [
        # For em_andamento: 'nome', 'grupo', and optionally 'como' (how they were nominated)
        # For finalizado: full data with vote percentages
        {'nome': 'Name', 'grupo': 'Pipoca', 'como': 'Líder'},  # como = how nominated
        {'nome': 'Name', 'voto_unico': XX.XX, 'voto_torcida': XX.XX,
         'voto_total': XX.XX, 'resultado': 'ELIMINADA', 'grupo': 'Camarote'},
    ],
    'votos_casa': {
        'Voter Name': 'Target Name',  # one entry per voter
    },
    'fontes': ['https://source1.com', 'https://source2.com'],
}
```

### Flexible Display Logic

The dashboard **automatically adapts** the display based on available data:

| Condition | Display |
|-----------|---------|
| `len(participantes) < total_esperado` | "FORMAÇÃO EM ANDAMENTO" with placeholder "?" cards |
| `len(participantes) >= total_esperado` but no `resultado` | "EM VOTAÇÃO" with all nominee cards |
| Has `resultado` fields | Full results with vote percentages |

This means you can add partial data as it becomes available, and the UI will adapt:
- Saturday: Dinâmica gives first nominee → add entry with 1 participant
- Sunday night: Leader + house votes complete it → add remaining participants + votos_casa
- Tuesday night: Results announced → add vote percentages + resultado

**Minimal paredão entry (partial formation):**
```python
{
    'numero': N,
    'status': 'em_andamento',
    'data': 'YYYY-MM-DD',  # Expected elimination date (Tuesday)
    'titulo': 'Nº Paredão — EM FORMAÇÃO',
    'total_esperado': 3,   # Shows (3 - len(participantes)) placeholder cards
    'formacao': 'What we know so far...',
    'lider': None,         # Can be None until Sunday
    'indicado_lider': None,
    'participantes': [
        {'nome': 'Participant1', 'grupo': 'Pipoca', 'como': 'Dinâmica'},
    ],
    # No votos_casa yet
}
```

**Complete em_andamento entry (ready for popular vote):**
```python
{
    'numero': N,
    'status': 'em_andamento',
    'data': 'YYYY-MM-DD',
    'titulo': 'Nº Paredão — EM VOTAÇÃO',
    'total_esperado': 3,
    'formacao': 'Full formation description...',
    'lider': 'Leader Name',
    'indicado_lider': 'Nominated participant',
    'participantes': [
        {'nome': 'Participant1', 'grupo': 'Pipoca', 'como': 'Dinâmica'},
        {'nome': 'Participant2', 'grupo': 'Camarote', 'como': 'Líder'},
        {'nome': 'Participant3', 'grupo': 'Veterano', 'como': 'Casa'},
    ],
    'votos_casa': {...},
}
```

### Voting System (BBB 26)
- **Voto Único** (CPF-validated, 1 per person): weight = **70%**
- **Voto da Torcida** (unlimited): weight = **30%**
- **Formula**: `(Voto Único × 0.70) + (Voto Torcida × 0.30) = Média Final`
- Changed from BBB 25 (which had equal weights) to reduce mutirão influence

### Critical: Name Matching Between Manual Data and API

The `votos_casa` dict and all manual data use participant names as keys. These **MUST match exactly** with the names in the API snapshots.

**Official API Names (as of Jan 2026):**

| API Name | Group | Notes |
|----------|-------|-------|
| `Alberto Cowboy` | Veterano | Full name used |
| `Ana Paula Renault` | Veterano | Full name used |
| `Babu Santana` | Veterano | Full name used |
| `Breno` | Pipoca | First name only |
| `Brigido` | Pipoca | First name only (not "Brígido") |
| `Chaiany` | Pipoca | First name only (entered Jan 18) |
| `Edilson` | Camarote | **NOT** "Edilson Capetinha" |
| `Gabriela` | Pipoca | First name only (entered Jan 18) |
| `Jonas Sulzbach` | Veterano | Full name used |
| `Jordana` | Pipoca | First name only |
| `Juliano Floss` | Camarote | Full name used |
| `Leandro` | Pipoca | First name only (entered Jan 18) |
| `Marcelo` | Pipoca | First name only |
| `Marciele` | Pipoca | First name only |
| `Matheus` | Pipoca | First name only (entered Jan 18) |
| `Maxiane` | Pipoca | First name only |
| `Milena` | Pipoca | First name only |
| `Paulo Augusto` | Pipoca | Full name used |
| `Samira` | Pipoca | First name only |
| `Sarah Andrade` | Veterano | Full name used |
| `Sol Vega` | Veterano | Full name used |
| `Solange Couto` | Camarote | Full name used |

**Eliminated/Exited (no longer in API):**
- `Aline Campos` — Eliminada (1º Paredão, Jan 21)
- `Henri Castelli` — Desistente (Jan 15)
- `Pedro` — Desistente (Jan 19)

**Before adding manual data**, always verify names against the snapshot:
```python
# Quick check: print all names from the latest snapshot
python3 -c "
import json
with open('data/latest.json') as f:
    data = json.load(f)
participants = data['participants'] if 'participants' in data else data
for p in participants:
    print(p['name'])
"
```

### Snapshot Timing for Paredão Archive

The "Arquivo de Paredões" section in `index.qmd` displays reaction data **anchored to each paredão date**. It uses `get_snapshot_for_date(paredao_date)` which finds the **last snapshot on or before** the given date.

**How the timing works:**
- House votes happen **during the live elimination episode** (typically Tuesday night ~22h BRT)
- Reactions visible to participants are the ones they assigned **that day or earlier**
- The API snapshot captures the **full reaction state** at the moment it was fetched
- We use the snapshot from the **paredão date itself** (or the closest earlier one)

**Ideal snapshot timing per paredão:**
- **Best**: A snapshot fetched on the paredão date, **before** the live show starts (~18h-20h BRT)
- **Good**: Any snapshot from the paredão date (the day's reaction state)
- **Acceptable**: A snapshot from the day before (reactions may have already shifted toward voting)
- **Last resort**: The closest earlier snapshot available

**To ensure good archive data for future paredões:**
1. Run `python scripts/fetch_data.py` **on the paredão date** (ideally afternoon, before the show)
2. Run it again **the day after** to capture the post-elimination state
3. The archive will automatically use the best available snapshot

**Current snapshot coverage per paredão:**

| Paredão | Date | Snapshot Used | Quality |
|---------|------|---------------|---------|
| 1º | 2026-01-20 | 2026-01-20_18-57-19 | Good (same day, 18:57 BRT) |

**When fetching data for a new paredão, tell Claude:**
```
"Fetch new data and update paredão. The Nº paredão was on YYYY-MM-DD.
Here is the info: [paste resultado, percentages, votos da casa, formação]"
```

Claude will:
1. Run `python scripts/fetch_data.py` to get the latest snapshot
2. Verify participant names match between votos_casa and API
3. Add the new paredão entry to `index.qmd`
4. The archive tab will automatically appear after `quarto render`

## Future Plans

See `IMPLEMENTATION_PLAN.md` for GitHub Actions + Quarto + GitHub Pages automation setup.
