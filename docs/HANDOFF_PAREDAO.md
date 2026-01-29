# Paredão Workflow — Full Reference

This document contains the step-by-step paredão update workflow, data schemas, display logic, and snapshot timing details.
Referenced from `CLAUDE.md` — read this when updating paredão data.

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

---

## Where to Find Paredão Data

Search for these terms (in Portuguese) right after the elimination episode:

| Data | Search Terms | Best Sources |
|------|-------------|-------------|
| Vote percentages (total) | `BBB 26 Nº paredão porcentagem resultado` | GShow, Terra, UOL |
| Voto Único / Torcida breakdown | `BBB 26 paredão voto único voto torcida` | Portal Alta Definição, Rádio Itatiaia |
| House votes (who voted whom) | `BBB 26 quem votou em quem Nº paredão` | Exame, GShow, UOL |
| Leader nomination reason | `BBB 26 líder indicou paredão` | GShow, NSC Total |
| Formation details | `BBB 26 como foi formado paredão` | GShow |

---

## Data Structure in data/paredoes.json

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

---

## Flexible Display Logic

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

### Minimal paredão entry (partial formation)
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

### Complete em_andamento entry (ready for popular vote)
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

---

## Voting System (BBB 26)
- **Voto Único** (CPF-validated, 1 per person): weight = **70%**
- **Voto da Torcida** (unlimited): weight = **30%**
- **Formula**: `(Voto Único × 0.70) + (Voto Torcida × 0.30) = Média Final`
- Changed from BBB 25 (which had equal weights) to reduce mutirão influence

---

## Data Freshness — Implementation Details

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

---

## Snapshot Timing for Paredão Archive

The "Arquivo de Paredões" section displays reaction data **anchored to each paredão date**. It uses `get_snapshot_for_date(paredao_date)` which finds the **last snapshot on or before** the given date.

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
3. Add the new paredão entry to `data/paredoes.json`
4. The archive tab will automatically appear after `quarto render`

---

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
