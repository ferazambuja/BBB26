# BBB26 Operations Guide

> Guia prático para manutenção diária, atualização de dados manuais e sync com GitHub.
>
> **Última atualização**: 2026-02-27

---

## Git Workflow (sync local ↔ GitHub)

The GitHub Actions bot auto-commits `data/` files up to 6× daily (8 on Saturdays). Always pull before working.

```bash
# Before any local work
git pull

# After manual edits
python scripts/build_derived_data.py    # rebuild derived data (hard-fails on errors)
git add data/ && git commit -m "data: <descrição>"
git push

# Deploy immediately (instead of waiting for next cron)
gh workflow run daily-update.yml

# Or wait — permanent cron runs at 00:00, 06:00, 15:00, 18:00 BRT (+ 17:00, 20:00 on Saturdays)
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

**Timing tip**: The bot runs at fixed slots (00:00, 06:00, 15:00, 18:00 BRT). If you're editing near those times, work quickly: `pull → edit → build → push` in one go to minimize the chance of a concurrent bot commit.

---

## Weekly Calendar

### Standard Week Pattern (Líder Cycle)

Each BBB week follows a predictable pattern anchored to the Líder cycle. The "week dynamic" on Friday is the only thing that varies significantly each week (Sincerão, Big Fone, Exilado, Bloco, etc.).

| Dia | Horário (BRT) | Evento | Ação necessária | Dados afetados |
|-----|---------------|--------|-----------------|----------------|
| **Diário** | ~14h | Queridômetro atualiza | Automático (15:00 BRT capture) | `snapshots/` |
| **Terça** | ~21h | Votalhada "Consolidados" | Coletar `votalhada/polls.json` | `votalhada/polls.json` |
| **Terça** | ~23h | **Eliminação** ao vivo | `paredoes.json` (resultado) + `votalhada` (resultado_real) | `paredoes.json` |
| **Terça** | ~23h30 | **Ganha-Ganha** (após eliminação) | `manual_events.json` → `weekly_events[N].ganha_ganha` + `power_events` (veto) | `manual_events.json` |
| **Quarta** | durante o dia | **Barrado no Baile** | `power_events` (type: `barrado_baile`) | `manual_events.json` |
| **Quinta** | ~22h | **Prova do Líder** → new week starts | **Líder Transition Checklist** (see below) | `provas.json`, `paredoes.json` |
| **Sexta** | ~22h | **Week Dynamic** (varies) | `manual_events.json` (see below) | varies |
| **Sábado** | ~14h-17h | **Prova do Anjo** | Automático (API detecta Anjo). `provas.json` se detalhes disponíveis | `provas.json` |
| **Sábado** | ~22h | **Monstro** (Anjo escolhe) | Automático (API detecta). Se artigo disponível, atualizar `weekly_events[N].anjo.monstro` | `manual_events.json` |
| **Domingo** | ~22h45 | **Presente do Anjo** + **Paredão** | `paredoes.json` (formação + votos_casa + contragolpe + bate_volta) | `paredoes.json` |

### Week Dynamic (Friday — varies each week)

The Friday dynamic is the main source of variety between weeks. Past examples:

| Week | Dynamic | Category |
|------|---------|----------|
| W1 | — (first week) | — |
| W2 | Sincerão | `sincerao` |
| W3 | Sincerão + Big Fone (multiple) | `sincerao` + `big_fone` |
| W4 | Sincerão + Sincerinho (Duelo de Risco) | `sincerao` + `special_events` |
| W5 | Bloco do Paredão (Máquina do Poder) | `special_events` |
| W6 | Sincerinho Paredão Perfeito + Régua de Prioridade + Big Fone + Duelo de Risco | `sincerao` + `special_events` |
| W7 | O Exilado + Paredão Falso + Quarto Secreto | `special_events` |

**Note**: Sincerão does NOT happen every week. It alternates and is announced in the week's dynamics article.

### Recurring Events Checklist (per week)

When planning `scheduled_events` for a new week, include these recurring items:

- [ ] **Ganha-Ganha** (Tuesday, after elimination) — 3 sorteados, veto + choice
- [ ] **Barrado no Baile** (Wednesday) — Líder bars someone from next party
- [ ] **Prova do Líder** (Thursday) — see Líder Transition Checklist
- [ ] **Week Dynamic** (Friday) — varies, from dynamics article
- [ ] **Prova do Anjo** (Saturday) — API auto-detects winner
- [ ] **Monstro** (Saturday) — Anjo's choice, API auto-detects
- [ ] **Presente do Anjo** (Sunday) — immunity choice
- [ ] **Paredão Formation** (Sunday) — contragolpe + bate e volta
- [ ] **Eliminação** (Tuesday) — paredão result

**Scrape the dynamics article** (published Thursday) to know the week-specific events and add all scheduled events at once.

---

## Líder Transition Checklist (Thursday night)

When a new Líder is crowned (typically Thursday ~22h BRT), follow these steps **in order**:

### Immediate (Thursday night / Friday morning)

1. **Scrape articles** — save `.md` copies for provenance:
   ```bash
   python scripts/scrape_gshow.py "<prova-do-lider-url>" -o docs/scraped/
   python scripts/scrape_gshow.py "<vip-xepa-url>" -o docs/scraped/
   python scripts/scrape_gshow.py "<dinamica-semana-url>" -o docs/scraped/  # if available
   ```

2. **Update `data/provas.json`** — add Prova do Líder results (phases, scores, placements).
   Include `fontes` with `{url, arquivo, titulo}` format pointing to scraped files.

3. **Create paredão skeleton in `data/paredoes.json`** — even before formation details.
   This is **critical** for `leader_periods` to show the correct Líder for the week.
   ```json
   {
     "numero": N,
     "status": "em_andamento",
     "data": "YYYY-MM-DD",
     "data_formacao": "YYYY-MM-DD",
     "titulo": "Nº Paredão — DD de Mês de YYYY",
     "semana": N,
     "total_esperado": 3,
     "formacao": {"lider": "Líder Name"},
     "indicados_finais": [],
     "fontes": [{"url": "...", "arquivo": "docs/scraped/...", "titulo": "..."}]
   }
   ```

4. **Update `data/manual_events.json`** — add scheduled events for the new week (if dynamics article available). Record power events (Big Fone, etc.) if any.

5. **Rebuild + commit + push**:
   ```bash
   python scripts/build_derived_data.py
   git add data/ && git commit -m "data: week N Líder transition (Name)"
   git push
   ```

### API auto-detects (no manual action needed)

These are picked up automatically by `build_daily_roles()` from snapshots:
- **Líder role** — appears in `characteristics.roles` (usually within hours of the ceremony)
- **VIP/Xepa groups** — appears in `characteristics.group` (same timing)
- **Roles cleared briefly** during transition (roles empty for a few hours → normal)

### Later (when Líder term ends)

6. **Update `WEEK_END_DATES`** in `scripts/data_utils.py` — add the last day of the completed week (day before next Prova do Líder). Cannot do this until the next Líder is crowned.

### Verification

After rebuilding, verify:
```bash
python3 -c "
import json
with open('data/derived/index_data.json') as f:
    idx = json.load(f)
for lp in idx['leader_periods']:
    print(f'Week {lp[\"week\"]}: {lp[\"leader\"]} | VIP={lp[\"vip\"][:3]}...')
"
```

Check that the new week shows the correct Líder (not `null`) and VIP composition.

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

**Saturday extras** (Anjo challenge + Monstro usually Saturday afternoon):

| UTC | BRT | Purpose |
|-----|-----|---------|
| 20:00 | 17:00 | Post-Anjo challenge (runs ~14h-17h) |
| 23:00 | 20:00 | Post-Monstro pick (Anjo chooses after win) |

**Total**: 6 runs/day (weekdays), 8 on Saturdays.

**Timing confirmed** (median 15:00 BRT, 2026-02-26). Hourly probes removed; permanent slots sufficient. Run `python scripts/analyze_capture_timing.py` to verify ongoing capture quality.

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
