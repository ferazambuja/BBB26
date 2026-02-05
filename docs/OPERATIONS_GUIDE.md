# BBB26 Operations Guide

> Guia prático para manutenção diária, atualização de dados manuais e sync com GitHub.
>
> **Última atualização**: 2026-02-05

---

## Git Workflow (sync local ↔ GitHub)

The GitHub Actions bot auto-commits `data/` files up to 4× daily. Always pull before working.

```bash
# Before any local work
git pull

# After manual edits
python scripts/build_derived_data.py    # rebuild derived data (hard-fails on errors)
git add data/ && git commit -m "data: <descrição>"
git push

# Deploy immediately (instead of waiting for next cron)
gh workflow run daily-update.yml

# Or wait — cron runs at 06:00, 12:00, 18:00, 00:00 BRT
```

**Key rule**: The bot only touches `data/` files. Your edits to `.qmd`, `scripts/`, `docs/` never conflict.

---

## Weekly Calendar

| Dia | Horário (BRT) | O que acontece | Ação necessária |
|-----|---------------|----------------|-----------------|
| **Diário** | ~10h-12h | Raio-X (reações atualizam) | Automático (12:00 BRT capture) |
| **Segunda** | ~22h | Dinâmica / Big Fone | Atualizar `manual_events.json` |
| **Terça** | ~21h | Votalhada "Consolidados" | Coletar + atualizar `votalhada/polls.json` |
| **Terça** | ~23h | Eliminação ao vivo | Atualizar `paredoes.json` (resultado) + `votalhada` (resultado_real) |
| **Quarta** | durante o dia | — | Preencher eventos de Quarta (se houver) |
| **Quinta** | ~22h | Prova do Líder | Atualizar `provas.json` + `manual_events.json` (se Big Fone) |
| **Sexta** | ~22h | Anjo / Monstro | Automático (API detecta roles). Manual se houver contragolpe |
| **Sábado** | ~22h | Prova Bate-Volta (se houver) | Atualizar `provas.json` |
| **Domingo** | ~22h45 | Formação do Paredão | Atualizar `paredoes.json` (formação + votos_casa) |

---

## Manual Data Files — When and How

### 1. `data/manual_events.json`

**When**: After any power event, Big Fone, Sincerão, special dynamic, exit, or scheduled event.

**Quick workflow**:
```bash
git pull
# Edit data/manual_events.json (see docs/MANUAL_EVENTS_GUIDE.md for schema)
python scripts/build_derived_data.py    # validates + rebuilds
git add data/ && git commit -m "data: add week N events"
git push
```

**Common entries** (by frequency):
- `power_events` — contragolpe, veto, imunidade, ganha-ganha, barrado
- `weekly_events` — Big Fone, Sincerão, confessão de voto, dedo-duro
- `special_events` — dinâmicas especiais
- `scheduled_events` — próximos eventos (com dedup automático)
- `participants` — desistências, desclassificações

**Pitfalls**:
- Names must match API exactly (see `CLAUDE.md` → Name Matching)
- Consensus events: use `"actor": "A + B + C"` + `"actors": ["A","B","C"]`
- `build_derived_data.py` hard-fails on audit issues — fix before pushing

**Full schema**: `docs/MANUAL_EVENTS_GUIDE.md`

### 2. `data/paredoes.json`

**When**: At paredão formation (Sunday) and after result (Tuesday).

**Formation (Sunday ~22h45)**:
```json
{
    "numero": 4,
    "status": "em_andamento",
    "data": "YYYY-MM-DD",
    "data_formacao": "YYYY-MM-DD",
    "titulo": "4º Paredão — DD de Mês de YYYY",
    "total_esperado": 3,
    "formacao": "Descrição da formação...",
    "lider": "Nome do Líder",
    "indicado_lider": "Indicado pelo Líder",
    "indicados_finais": [
        {"nome": "Name", "grupo": "Pipoca", "como": "Líder"},
        {"nome": "Name", "grupo": "Camarote", "como": "Mais votado"},
        {"nome": "Name", "grupo": "Pipoca", "como": "Contragolpe"}
    ],
    "votos_casa": {"Voter": "Target", "Voter2": "Target2"},
    "fontes": ["https://..."]
}
```

**Resultado (Tuesday ~23h)** — add to existing entry:
```json
{
    "status": "finalizado",
    "resultado": {
        "eliminado": "Name",
        "votos": {
            "Name1": {"voto_unico": 45.23, "voto_torcida": 50.10, "voto_total": 46.69},
            "Name2": {"voto_unico": 54.77, "voto_torcida": 49.90, "voto_total": 53.31}
        }
    }
}
```

**After edit**:
```bash
python scripts/build_derived_data.py
git add data/ && git commit -m "data: paredão N formation/result"
git push
```

### 3. `data/provas.json`

**When**: After Prova do Líder (Thursday), Prova do Anjo (Friday), Bate-Volta (Saturday/Sunday).

**Workflow**: Add entry to the `provas` array, run `build_derived_data.py`, commit, push.

### 4. `data/votalhada/polls.json`

**When**: Tuesday ~21h (before elimination) and after result.

**Workflow**:
1. Screenshot Votalhada "Consolidados" page
2. Use Claude: "Process Votalhada image for paredão N"
3. Claude extracts data → updates `polls.json`
4. After elimination: add `resultado_real` to the entry
5. Run `build_derived_data.py`, commit, push

**Full workflow**: `data/votalhada/README.md`

---

## Quick Reference: Which Script When

| Situation | Command |
|-----------|---------|
| After editing any manual data file | `python scripts/build_derived_data.py` |
| Fetch fresh API data manually | `python scripts/fetch_data.py` |
| Deploy to site immediately | `gh workflow run daily-update.yml` |
| Verify site rendering locally | `quarto render` (~3 min) |
| Preview with hot reload | `quarto preview` |
| Check snapshot dedup/integrity | `python scripts/audit_snapshots.py` |
| Analyze capture timing | `python scripts/analyze_capture_timing.py` |

---

## Capture Timing Analysis

### When does the queridômetro actually update?

The Raio-X has **no fixed time** — it depends on when production wakes the participants. But GShow publishes the queridômetro article early:

| Source | Observation | Time (BRT) |
|--------|-------------|------------|
| **GShow article** | Feb 5 (Wed, post-elimination) — published | ~09:00 |
| **Raio-X wake-up** | Normal days | 09h-10h |
| **Raio-X wake-up** | Post-party days | 10h-13h |
| **API data ready** | Normal days (estimated) | ~09h-11h |
| **API data ready** | Post-party days (estimated) | ~12h-15h |

**Key finding (Feb 5 data point)**: GShow published the queridômetro article around 09:00 BRT, which means the API data was already available by then. The 12:00 BRT cron capture should catch it on normal days with margin to spare.

**Current cron schedule assessment**:
- **06:00 BRT**: Pre-Raio-X baseline (data from yesterday, useful for comparison).
- **12:00 BRT**: Primary capture. Catches normal days with ~2-3h margin. May miss very late post-party days.
- **18:00 BRT**: Safety net — catches anything the 12:00 run missed.
- Both 12:00 + 18:00 together cover all scenarios.

Sources: [TVH News](https://tvhnews.com.br/como-funciona-o-raio-x-do-bbb-26-saiba-para-que-serve-a-dinamica/), [DCI](https://www.dci.com.br/dci-mais/bbb-21/bbb-21-que-horas-e-o-raio-x-veja-como-funciona/94397/), [GShow Feb 5](https://gshow.globo.com/realities/bbb/bbb-26/dentro-da-casa/noticia/queridometro-do-bbb-26-reflete-tensao-pos-festa-e-brothers-recebem-emojis-negativos.ghtml)

### Tracking with data

To check empirically if the 12:00 BRT capture is catching reaction updates:

```bash
python scripts/analyze_capture_timing.py
```

This analyzes all snapshots with metadata and reports:
- When reaction changes were detected (by BRT hour)
- Whether the 12:00 BRT window is catching them
- Suggested adjustments if the data shows a consistent pattern

**How it works**: Each snapshot has `_metadata.reactions_hash`. The script compares consecutive snapshots — when the hash changes, that capture caught a reaction update. By tracking *which capture slot* (06:00, 12:00, 18:00, 00:00) detected the change, we can see if 12:00 is right or needs shifting.

**Interpreting results**:
- If most reaction changes are caught at 12:00 → timing is correct
- If caught at 18:00 instead → Raio-X is happening later, consider shifting to 14:00 or 15:00
- If caught at 06:00 → reactions updated overnight (unusual, investigate)

**When to check**: Run the script weekly after a full week of cron captures. The first meaningful analysis will be around Feb 12 (7 days of 4×/day data).

---

## Troubleshooting

### `build_derived_data.py` fails with audit error

The script hard-fails if manual events have issues (duplicate entries, invalid names, missing fields).

```bash
# Check what's wrong
python scripts/audit_manual_events.py
# Fix data/manual_events.json
# Re-run
python scripts/build_derived_data.py
```

### Merge conflict on `data/derived/`

The bot rebuilt derived data while you had local changes.

```bash
git pull --rebase    # or: git pull (accept theirs for derived files)
python scripts/build_derived_data.py    # regenerate from your local manual data
git add data/ && git commit -m "data: rebuild derived after merge"
git push
```

Derived files are always regenerated — the source of truth is the manual files + snapshots.

### Workflow failed on GitHub

```bash
gh run list --limit 5          # find the run ID
gh run view <run-id> --log     # see full logs
```

Common causes:
- API temporarily down → re-trigger: `gh workflow run daily-update.yml`
- Quarto render error → test locally with `quarto render`
- Audit failure → fix manual data, push, re-trigger

### Site not updating after push

The workflow only triggers on **cron** and **manual dispatch**, not on push. Either:
```bash
gh workflow run daily-update.yml    # manual trigger
```
Or wait for the next cron run (max 6 hours).

### Name mismatch errors

Verify names against current API:
```bash
python3 -c "
import json
with open('data/latest.json') as f:
    data = json.load(f)
for p in data['participants']:
    print(p['name'])
"
```

---

## Data Flow Summary

```
Manual edits (you)              Auto fetch (GitHub Actions bot)
       ↓                                    ↓
manual_events.json              data/snapshots/*.json
paredoes.json                   data/latest.json
provas.json                            ↓
votalhada/polls.json       build_derived_data.py
       ↓                                    ↓
build_derived_data.py           data/derived/*.json (20 files)
       ↓                                    ↓
data/derived/*.json             quarto render → _site/
       ↓                                    ↓
git push                        deploy to GitHub Pages
       ↓
gh workflow run (or wait)
       ↓
quarto render → deploy
```

---

## Related Documentation

| Doc | What it covers |
|-----|----------------|
| `CLAUDE.md` | Master project guide — architecture, data schema, conventions |
| `IMPLEMENTATION_PLAN.md` | Deployment infrastructure — Actions, Pages, pipeline |
| `docs/MANUAL_EVENTS_GUIDE.md` | Full schema + fill rules for `manual_events.json` |
| `docs/SCORING_AND_INDEXES.md` | Scoring formulas, weights, index specifications |
| `data/votalhada/README.md` | Screenshot-to-data workflow for poll collection |
| `data/CHANGELOG.md` | Snapshot history, dedup analysis, API observations |
