# Handoff: Votalhada Poll Integration

**Date:** 2026-01-27
**Implemented by:** Claude
**Status:** Complete

---

## What Was Built

A system to track and compare poll predictions from [Votalhada](https://votalhada.blogspot.com/) against actual BBB26 paredão results.

### Purpose

Votalhada aggregates polls from 70+ sources across 4 platforms (Sites, YouTube, Twitter, Instagram) before each elimination. This integration:

1. Stores historical poll data in a structured format
2. Displays poll predictions in the dashboard
3. Compares predictions vs actual results after elimination
4. Tracks accuracy metrics over time

---

## Files Created/Modified

### New Files

| File | Purpose |
|------|---------|
| `data/votalhada/polls.json` | Main poll data storage |
| `data/votalhada/README.md` | Collection workflow documentation |
| `docs/HANDOFF_VOTALHADA.md` | This handoff document |

### Modified Files

| File | Changes |
|------|---------|
| `scripts/data_utils.py` | Added 3 loader functions |
| `paredao.qmd` | Added poll section (~170 lines) |
| `paredoes.qmd` | Added poll section in archive loop (~100 lines) |
| `CLAUDE.md` | Added Votalhada workflow docs |

---

## Data Structure

### polls.json Schema

```json
{
  "_description": "Poll aggregation data from Votalhada",
  "_source": "votalhada.blogspot.com",
  "_last_updated": "2026-01-27",

  "paredoes": [{
    "numero": 1,
    "data_paredao": "2026-01-21",
    "data_coleta": "2026-01-20T21:00:00-03:00",
    "participantes": ["Aline Campos", "Ana Paula Renault", "Milena"],

    "consolidado": {
      "Aline Campos": 46.19,
      "Ana Paula Renault": 9.26,
      "Milena": 44.55,
      "total_votos": 5024890,
      "predicao_eliminado": "Aline Campos"
    },

    "plataformas": {
      "sites": {"Aline Campos": 42.53, "Ana Paula Renault": 11.89, "Milena": 45.59, "votos": 1934238},
      "youtube": {...},
      "twitter": {...},
      "instagram": {...}
    },

    "serie_temporal": [
      {"hora": "19/jan 01:00", "Aline Campos": 48.28, ...},
      {"hora": "20/jan 21:00", "Aline Campos": 46.19, ...}
    ],

    "resultado_real": {
      "Aline Campos": 61.64,
      "Ana Paula Renault": 5.86,
      "Milena": 32.50,
      "eliminado": "Aline Campos",
      "predicao_correta": true
    }
  }]
}
```

### Key Fields

| Field | When to Fill | Source |
|-------|--------------|--------|
| `consolidado` | Tuesday ~21:00 BRT | Votalhada "Consolidados" image |
| `plataformas` | Tuesday ~21:00 BRT | Votalhada platform-specific images |
| `serie_temporal` | Optional | "VARIAÇÃO DAS MÉDIAS" chart |
| `resultado_real` | After elimination | GShow/official sources |

---

## How It Works

### Python Functions (scripts/data_utils.py)

```python
from data_utils import load_votalhada_polls, get_poll_for_paredao, calculate_poll_accuracy

# Load all poll data
polls = load_votalhada_polls()

# Get poll for specific paredão
poll = get_poll_for_paredao(polls, 1)  # Returns poll dict or None

# Calculate accuracy metrics (requires resultado_real)
accuracy = calculate_poll_accuracy(poll)
# Returns: {'predicao_correta': True, 'erro_medio': 10.3, 'erros_por_participante': {...}}
```

### Dashboard Display Logic

**Position:** Poll section appears **right after participant cards**, before historical sections (Formação, Votação da Casa). This is intentional — current predictions come first, historical context below.

**paredao.qmd** (current paredão):
- `em_andamento`: "📊 Previsão das Enquetes" — current poll predictions + platform table
- `finalizado`: "📊 Enquetes vs Resultado" — comparison chart + accuracy metrics

**paredoes.qmd** (archive):
- For each finalized paredão with poll data: Shows "Enquetes vs Resultado" section
- Includes grouped bar chart and platform breakdown table

### Matching Logic

Poll data is matched to paredões by number:
```python
poll = get_poll_for_paredao(polls_data, paredao['numero'])
```

This ensures each paredão displays its own corresponding poll data.

---

## Current Data (1º Paredão)

| Participant | Poll (Consolidado) | Real Result | Error |
|-------------|-------------------|-------------|-------|
| Aline Campos | 46.19% | 61.64% | -15.45 p.p. |
| Ana Paula Renault | 9.26% | 5.86% | +3.40 p.p. |
| Milena | 44.55% | 32.50% | +12.05 p.p. |

**Prediction:** Correct (Aline most voted = eliminated)
**Mean Error:** 10.3 percentage points

### Platform Comparison

| Platform | Aline | Ana Paula | Milena | Most Accurate? |
|----------|-------|-----------|--------|----------------|
| Sites | 42.53% | 11.89% | 45.59% | |
| YouTube | 41.67% | 12.50% | 45.83% | |
| Twitter | 64.88% | 3.78% | 31.35% | Best for Aline |
| Instagram | 46.71% | 6.21% | 47.07% | |
| **Consolidado** | 46.19% | 9.26% | 44.55% | |
| **Real** | 61.64% | 5.86% | 32.50% | |

Twitter was closest to predicting Aline's actual percentage.

---

## How to Add Data for New Paredões

### Streamlined Workflow

```
1. Screenshot Consolidados image → save to data/ folder
2. Tell Claude: "Process Votalhada image data/[filename].png for paredão N"
3. Claude reads image, extracts data, updates polls.json
4. Render dashboard to verify
```

**Only the Consolidados image is needed** — it has all platform aggregates + time series.

### Step 1: Collect Poll Data (Anytime / Tuesday ~21:00 BRT)

1. Go to [votalhada.blogspot.com](https://votalhada.blogspot.com/)
2. Screenshot the **Consolidados** table for current paredão
3. Save to `data/` folder (Claude will organize it)

### Step 2: Claude Processes the Image

Claude will:
1. Read the image and extract all data
2. Move image to `data/votalhada/YYYY_MM_DD/consolidados.png`
3. Update `polls.json` with extracted data

### Step 3: Updating Preliminary Data

Poll numbers change during voting. When updating:

| Field | Action |
|-------|--------|
| `consolidado` | **OVERWRITE** with latest |
| `plataformas` | **OVERWRITE** with latest |
| `data_coleta` | **OVERWRITE** with new timestamp |
| `serie_temporal` | **APPEND** new time points |

This keeps current prediction fresh while preserving evolution history.

### polls.json Entry Structure

```json
{
  "numero": 2,
  "data_paredao": "2026-01-28",
  "data_coleta": "2026-01-27T21:00:00-03:00",
  "participantes": ["Name1", "Name2", "Name3"],
  "consolidado": {
    "Name1": XX.XX,
    "Name2": XX.XX,
    "Name3": XX.XX,
    "total_votos": XXXXXXX,
    "predicao_eliminado": "NameX"
  },
  "plataformas": {
    "sites": {"Name1": XX.XX, "Name2": XX.XX, "Name3": XX.XX, "votos": XXXXXX},
    "youtube": {...},
    "twitter": {...},
    "instagram": {...}
  }
}
```

### Step 3: After Elimination

Add `resultado_real` field:
```json
"resultado_real": {
  "Name1": XX.XX,
  "Name2": XX.XX,
  "Name3": XX.XX,
  "eliminado": "NameX",
  "predicao_correta": true
}
```

### Step 4: Render

```bash
quarto render paredao.qmd paredoes.qmd
```

---

## Name Matching

**Critical:** Participant names in polls.json MUST match exactly with `data/paredoes.json`.

| Votalhada Shows | Use in polls.json |
|-----------------|-------------------|
| "Aline" | "Aline Campos" |
| "Ana Paula" | "Ana Paula Renault" |
| "Cowboy" | "Alberto Cowboy" |
| "Sol" | "Sol Vega" |
| "Floss" | "Juliano Floss" |

Verify names before adding:
```bash
python -c "
import json
p = json.load(open('data/paredoes.json'))
par = next(x for x in p['paredoes'] if x['numero'] == 2)
print([i['nome'] for i in par['indicados_finais']])
"
```

---

## Future Enhancements

After 3+ paredões, consider adding to `trajetoria.qmd`:

1. **Accuracy Leaderboard**: Which individual sources are most accurate?
2. **Platform Trends**: Is Twitter consistently better than YouTube?
3. **Time Series Viz**: How do poll numbers evolve in the last 24h?
4. **Vote Type Comparison**: Do polls match voto_unico or voto_torcida better?

---

## Troubleshooting

### Poll section doesn't show

1. Check if poll data exists for the paredão number:
   ```python
   from data_utils import load_votalhada_polls, get_poll_for_paredao
   polls = load_votalhada_polls()
   print(get_poll_for_paredao(polls, NUMERO))
   ```

2. For finalized paredões, ensure `resultado_real` field exists

### Name mismatch errors

Verify participant names match exactly:
```bash
python -c "
import json
polls = json.load(open('data/votalhada/polls.json'))
paredoes = json.load(open('data/paredoes.json'))
poll_names = set(polls['paredoes'][0]['participantes'])
par_names = {p['nome'] for p in paredoes['paredoes'][0]['indicados_finais']}
print(f'Match: {poll_names == par_names}')
print(f'Diff: {poll_names.symmetric_difference(par_names)}')
"
```

---

## Testing

```bash
# Validate JSON syntax
python -c "import json; json.load(open('data/votalhada/polls.json'))"

# Test loader functions
python -c "
import sys; sys.path.append('scripts')
from data_utils import load_votalhada_polls, get_poll_for_paredao, calculate_poll_accuracy
polls = load_votalhada_polls()
poll = get_poll_for_paredao(polls, 1)
print(f'Poll exists: {poll is not None}')
print(f'Accuracy: {calculate_poll_accuracy(poll)}')
"

# Render and check output
quarto render paredoes.qmd
grep -c "Enquetes vs Resultado" _site/paredoes.html
```

---

## Contact

For questions about this implementation, refer to:
- `data/votalhada/README.md` - Detailed collection workflow
- `CLAUDE.md` - Project-wide documentation
- This handoff document
