# BBB26 Operations Guide

> Guia prático para manutenção diária, atualização de dados manuais e sync com GitHub.
>
> **Última atualização**: 2026-02-05

---

## Git Workflow (sync local ↔ GitHub)

The GitHub Actions bot auto-commits `data/` files up to 12× daily (probes + permanent slots). Always pull before working.

```bash
# Before any local work
git pull

# After manual edits
python scripts/build_derived_data.py    # rebuild derived data (hard-fails on errors)
git add data/ && git commit -m "data: <descrição>"
git push

# Deploy immediately (instead of waiting for next cron)
gh workflow run daily-update.yml

# Or wait — permanent cron runs at 06:00, 15:00, 18:00, 00:00 BRT
# Plus hourly probes 10:00–16:00 BRT (temporary, see Capture Timing section)
```

**Key rule**: The bot only touches `data/` files. Your edits to `.qmd`, `scripts/`, `docs/` never conflict.

**Snapshot filenames are UTC**: Files in `data/snapshots/` use UTC timestamps. Game dates (for daily dedup) are derived by converting UTC→BRT with a 06:00 BRT cutoff (captures before 06:00 BRT → previous game day). See `utc_to_game_date()` in `data_utils.py`.

### Handling Extraordinary Events (mid-day manual updates)

When something unexpected happens (e.g., surprise disqualification, mid-week dynamic):

```bash
# 1. Always sync first
git pull

# 2. Make your edits
#    - data/manual_events.json (power events, exits)
#    - data/paredoes.json (formation, votes)
#    - data/provas.json (competition results)

# 3. Rebuild + commit + push
python scripts/build_derived_data.py
git add data/ && git commit -m "data: <what happened>"
git push

# 4. Deploy immediately
gh workflow run daily-update.yml
```

**If push fails** (bot committed while you were editing):
```bash
git pull --rebase
# If conflicts in data/derived/ (always safe to regenerate):
git checkout --theirs data/derived/
git add data/derived/ && git rebase --continue
python scripts/build_derived_data.py
git add data/ && git commit -m "data: rebuild derived after merge"
git push
```

**Timing tip**: The bot runs most frequently between 10:00–16:00 BRT (hourly probes). If you're editing during that window, work quickly: `pull → edit → build → push` in one go to minimize the chance of a concurrent bot commit.

---

## Weekly Calendar

| Dia | Horário (BRT) | O que acontece | Ação necessária |
|-----|---------------|----------------|-----------------|
| **Diário** | ~14h | Queridômetro atualiza na API | Automático (15:00 BRT capture) |
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

The Raio-X has **no fixed time** — it depends on when production wakes the participants:

| Source | Observation | Time (BRT) |
|--------|-------------|------------|
| **API data observed** | Feb 5 (Wed) — data already updated | ~14:00 |
| **API first auto capture** | Feb 6 (Thu) — change detected at 15:46 BRT | between 06:37–15:46 |
| **GShow article** | Feb 5 (Wed) — article published | ~09:00 |
| **Raio-X wake-up** | Normal days | 09h-10h |
| **Raio-X wake-up** | Post-party days | 10h-13h |

**Key finding**: GShow publishes the queridômetro article early (~09:00 BRT), but the API data was observed updating around **~14:00 BRT** (Feb 5). First automated day (Feb 6) confirmed: data stale at 06:37 BRT, fresh at 15:46 BRT.

### Current cron schedule

**Permanent slots** (4×/day):

| UTC | BRT | Purpose |
|-----|-----|---------|
| 03:00 | 00:00 | Night — post-episode changes (Sun Líder/Anjo, Tue elimination) |
| 09:00 | 06:00 | Pre-Raio-X baseline — balance/estalecas (punishments, etc.) |
| 18:00 | 15:00 | Post-Raio-X — **primary capture** |
| 21:00 | 18:00 | Evening — balance/role changes |

**Temporary observation probes** (added 2026-02-06, hourly 10–16 BRT):

| UTC | BRT | Purpose |
|-----|-----|---------|
| 13:00 | 10:00 | Earliest possible Raio-X update |
| 14:00 | 11:00 | Probe |
| 15:00 | 12:00 | Probe |
| 16:00 | 13:00 | Probe |
| 17:00 | 14:00 | Expected API update window |
| 19:00 | 16:00 | Late update safety net |

**Saturday extras** (Anjo challenge + Monstro usually Saturday afternoon):

| UTC | BRT | Purpose |
|-----|-----|---------|
| 20:00 | 17:00 | Post-Anjo challenge (runs ~14h–17h) |
| 23:00 | 20:00 | Post-Monstro pick (Anjo chooses after win) |

**Total**: ~12 runs/day (weekdays), ~14 runs/day (Saturday). Probes are temporary — remove once timing is pinpointed.

Sources: [TVH News](https://tvhnews.com.br/como-funciona-o-raio-x-do-bbb-26-saiba-para-que-serve-a-dinamica/), [DCI](https://www.dci.com.br/dci-mais/bbb-21/bbb-21-que-horas-e-o-raio-x-veja-como-funciona/94397/), [GShow Feb 5](https://gshow.globo.com/realities/bbb/bbb-26/dentro-da-casa/noticia/queridometro-do-bbb-26-reflete-tensao-pos-festa-e-brothers-recebem-emojis-negativos.ghtml)

### Tracking with data

To monitor when reaction changes happen and if the timing is right:

```bash
python scripts/analyze_capture_timing.py
```

This analyzes all snapshots with metadata and reports:
- When reaction changes were detected (by BRT hour)
- Hour-by-hour histogram showing capture distribution
- Whether the probes are catching changes earlier than 15:00 BRT
- Suggested adjustments if the data shows a consistent pattern

**How it works**: Each snapshot has `_metadata.reactions_hash`. The script compares consecutive snapshots — when the hash changes, that capture caught a reaction update.

**Interpreting results** (after ~7 days of probes):
- If probes catch changes at 12:00–13:00 → shift primary capture earlier
- If 15:00 BRT consistently catches changes → probes confirmed the timing, remove them
- If caught at 18:00 instead → data is updating later, keep probes and shift primary
- If caught at 06:00 → reactions updated overnight (unusual, investigate)

**Action after observation period**: Run `analyze_capture_timing.py`, check the hour histogram, remove the temporary probes from `.github/workflows/daily-update.yml`, keep only the permanent slots (adjusted if needed).

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
