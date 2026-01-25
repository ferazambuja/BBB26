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
- `data/CHANGELOG.md` — Documents data timeline and findings
- New format wraps data: `{ "_metadata": {...}, "participants": [...] }`
- Old format is just the raw array: `[...]`
- `scripts/fetch_data.py` handles both formats and saves only when data hash changes
- **Synthetic snapshots** have `_metadata.synthetic = true` (see below)

### Reaction Categories
```python
POSITIVE = ['Coração']  # ❤️
MILD_NEGATIVE = ['Planta', 'Mala', 'Biscoito', 'Coração partido']  # 🌱💼🍪💔
STRONG_NEGATIVE = ['Cobra', 'Alvo', 'Vômito', 'Mentiroso']  # 🐍🎯🤮🤥
```

Sentiment weights: positive = +1, mild_negative = -0.5, strong_negative = -1

**Note**: 💔 Coração partido (broken heart) is classified as **mild negative** because it represents disappointment rather than hostility. It's commonly used for participants who were once close but drifted apart.

### Hostility Analysis

The dashboard tracks two types of hostility patterns that are strategically important:

**Two-sided (mutual) hostility**: Both A and B give each other negative reactions.
- These are **declared enemies** — both know where they stand
- Votes between them are predictable
- Example: Ana Paula Renault ↔ Brigido (longest rivalry in BBB26)

**One-sided (unilateral) hostility**: A gives B a negative reaction, but B gives A a ❤️.
- Creates **blind spots** — B thinks they're safe with A, but A may vote against B
- The "friendly" person can be surprised in voting
- Example: In 1º Paredão, Paulo Augusto was voted out by 11 people, 6 of whom had given him ❤️

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

Add a new entry with only the known nominees:

```
"Add new paredão (partial formation) to index.qmd:

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

If partial entry exists, update it. Otherwise create new:

```
"Update/add paredão (em andamento) to index.qmd:

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
"Update paredão Nº to finalizado in index.qmd:

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

### Data Structure in index.qmd

Each paredão is a dict in the `paredoes` list:

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

The `votos_casa` dict uses participant names as keys. These **MUST match exactly** with the names in the API snapshots. The API sometimes uses shortened names.

**Known mismatches (already fixed):**
- API uses `"Edilson"`, NOT `"Edilson Capetinha"`

**Before adding a new paredão**, always verify voter/target names against the snapshot:
```python
# Quick check: print all names from the latest snapshot
import json
with open('data/latest.json') as f:
    data = json.load(f)
participants = data['participants'] if 'participants' in data else data
for p in participants:
    print(p['name'])
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
