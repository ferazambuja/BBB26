# BBB26 Operations Guide

> Single source of truth for ALL operational procedures — data updates, event workflows, git sync, and troubleshooting.
>
> **For AI agents without context**: Read the Quick Index below to find exactly what you need to do.
> **For schemas and field specs**: See `docs/MANUAL_EVENTS_GUIDE.md` (events) and `CLAUDE.md` (architecture).
> **For scoring formulas**: See `docs/SCORING_AND_INDEXES.md`.
>
> **Last updated**: 2026-03-04

---

## Quick Index — "I need to..."

| Task | When | Go to |
|------|------|-------|
| **Update after ANY manual edit** | After editing any data file | [Git Workflow](#git-workflow) |
| **New Líder crowned** (Thursday) | Thursday ~22h | [Líder Transition Checklist](#líder-transition-checklist-thursday-night) |
| **Prova do Anjo results** (Saturday) | Saturday afternoon | [Anjo / Monstro Checklist](#anjo--monstro-update-checklist-saturday) |
| **Presente do Anjo** (Sunday afternoon) | Sunday ~14h-17h | [Presente do Anjo Checklist](#presente-do-anjo-checklist-sunday-afternoon) |
| **Paredão formation** (Sunday night) | Sunday ~22h45 | [Paredão Formation Checklist](#paredão-formation-checklist-sunday) |
| **Collect Votalhada polls** (Tuesday) | Tuesday ~21h | [Votalhada Collection Checklist](#votalhada-collection-checklist-tuesday) |
| **Elimination result** (Tuesday) | Tuesday ~23h | [Elimination Result Checklist](#elimination-result-checklist-tuesday) |
| **Sincerão data** (Monday) | Monday ~22h | [Sincerão Update](#sincerão-update-monday) |
| **Ganha-Ganha / Barrado / power events** | Various | [Manual Data Files](#manual-data-files--when-and-how) |
| **Add scheduled events for upcoming week** | After dynamics article | [Scheduled Events](#scheduled-events-upcoming-week) |
| **Participant exit** (quit/disqualified) | When it happens | [Manual Data Files → manual_events.json](#1-datamanual_eventsjson) |
| **Workflow failed on GitHub** | After failure | [Troubleshooting](#troubleshooting) |
| **Push conflict with bot** | After `git push` fails | [Git Workflow → conflict resolution](#handling-push-conflicts) |
| **Which script to run?** | Any time | [Script Reference](#quick-reference-which-script-when) |

---

## Git Workflow

The GitHub Actions bot auto-commits `data/` files up to 6x daily (8 on Saturdays). **Always pull before working.**

```bash
# Before any local work
git pull

# After manual edits (the universal pattern)
python scripts/build_derived_data.py    # rebuild derived data (hard-fails on errors)
git add data/ docs/MANUAL_EVENTS_AUDIT.md && git commit -m "data: <description>"
git push

# Deploy immediately (instead of waiting for next cron)
gh workflow run daily-update.yml
```

**Key rules**:
- The bot only touches `data/` files. Your edits to `.qmd`, `scripts/`, `docs/` never conflict.
- Bot cron runs at **00:00, 06:00, 15:00, 18:00 BRT** (+ 17:00, 20:00 on Saturdays). Work quickly near those times.
- Snapshot filenames are **UTC**. Game dates use `utc_to_game_date()` (UTC→BRT with 06:00 BRT cutoff).

### Handling Push Conflicts

If push fails because the bot committed while you were editing:

```bash
git pull --rebase
# If conflicts in data/derived/ (always safe to regenerate):
git checkout --theirs data/derived/
git add data/derived/ && git rebase --continue
python scripts/build_derived_data.py
git add data/ && git commit -m "data: rebuild derived after merge"
git push
```

Derived files are always regenerated — the source of truth is the manual files + snapshots.

### Handling Extraordinary Events

Surprise disqualification, mid-week dynamic, or any unplanned event:

```bash
git pull                                  # 1. Always sync first
# Edit the relevant data files            # 2. Make your edits
python scripts/build_derived_data.py      # 3. Rebuild
git add data/ && git commit -m "data: <what happened>"
git push                                  # 4. Push
gh workflow run daily-update.yml          # 5. Deploy immediately
```

---

## Weekly Calendar

### Standard Week Pattern (Líder Cycle)

Each BBB week follows a predictable pattern anchored to the Líder cycle. Two recurring event types:
- **Sincerão** (Monday live show) — happens every week with a different format/theme
- **Week Dynamic** (Friday, varies) — the unique dynamic from the weekly dynamics article

| Dia | Horário (BRT) | Evento | Checklist to follow | Data files affected |
|-----|---------------|--------|---------------------|---------------------|
| **Diário** | ~14h | Queridômetro atualiza | Automático (15:00 BRT capture) | `snapshots/` |
| **Segunda** | ~22h | **Sincerão** (ao vivo) | [Sincerão Update](#sincerão-update-monday) | `manual_events.json` |
| **Terça** | ~21h | Votalhada "Consolidados" | [Votalhada Checklist](#votalhada-collection-checklist-tuesday) | `votalhada/polls.json` |
| **Terça** | ~23h | **Eliminação** ao vivo | [Elimination Checklist](#elimination-result-checklist-tuesday) | `paredoes.json` |
| **Terça** | ~23h30 | **Ganha-Ganha** | [Manual Data Files](#1-datamanual_eventsjson) | `manual_events.json` |
| **Quarta** | durante o dia | **Barrado no Baile** | [Manual Data Files](#1-datamanual_eventsjson) | `manual_events.json` |
| **Quinta** | ~22h | **Prova do Líder** | [Líder Checklist](#líder-transition-checklist-thursday-night) | `provas.json`, `paredoes.json` |
| **Sexta** | ~22h | **Week Dynamic** (varies) | Depends on dynamic | varies |
| **Sábado** | ~14h-17h | **Prova do Anjo** | [Anjo Checklist](#anjo--monstro-update-checklist-saturday) | `provas.json`, `manual_events.json` |
| **Sábado** | ~22h | **Monstro** (Anjo escolhe) | [Anjo Checklist](#anjo--monstro-update-checklist-saturday) | `manual_events.json` |
| **Domingo** | ~14h-17h | **Presente do Anjo** (almoço) | [Presente do Anjo Checklist](#presente-do-anjo-checklist-sunday-afternoon) | `manual_events.json` |
| **Domingo** | ~22h45 | **Paredão Formation** | [Paredão Checklist](#paredão-formation-checklist-sunday) | `paredoes.json` |

### Sincerão History (Monday — recurring weekly)

Data goes in `weekly_events[N].sincerao` (single `dict` or `list` of dicts for multiple rounds).

| Week | Date | Format | Notes |
|------|------|--------|-------|
| W1 | Mon Jan 19 | Pódio + quem não ganha | Plateia presente, Pipocômetro |
| W2 | Mon Jan 26 | Bombas com temas do público | Plateia define planta (Solange) |
| W3 | Mon Feb 2 | Pior futebol do mundo | Escalação com papéis negativos |
| W4 | Mon Feb 9 | Quem Sou Eu? (adivinhação) | Plateia define mais apagada (Marciele) |
| W5 | Mon Feb 16 | **MISSING** — needs data | Done hastily on live show, not yet classified |
| W6 | Fri Feb 20 + Mon Feb 23 | Paredão Perfeito + Régua de Prioridade | Two rounds (list format in JSON) |
| W7 | TBD | TBD | |

### Week Dynamic History (Friday — varies each week)

Separate from Sincerão. Announced in the dynamics article (published ~Thursday).

| Week | Dynamic | Category |
|------|---------|----------|
| W1 | — (first week) | — |
| W2 | — | — |
| W3 | Big Fone (multiple) | `big_fone` |
| W4 | Sincerinho / Duelo de Risco | `special_events` |
| W5 | Bloco do Paredão (Máquina do Poder) | `special_events` |
| W6 | Sincerinho Paredão Perfeito + Big Fone + Duelo de Risco | `sincerao` + `special_events` |
| W7 | O Exilado + Paredão Falso + Quarto Secreto | `special_events` |

### Recurring Events Checklist (per week)

When planning `scheduled_events` for a new week, include these recurring items:

- [ ] **Sincerão** (Monday, ~22h) — format varies weekly; `weekly_events[N].sincerao` with edges + stats
- [ ] **Ganha-Ganha** (Tuesday, after elimination) — 3 sorteados, veto + choice
- [ ] **Barrado no Baile** (Wednesday) — Líder bars someone from next party
- [ ] **Prova do Líder** (Thursday) — see Líder Transition Checklist
- [ ] **Week Dynamic** (Friday) — varies, from dynamics article
- [ ] **Prova do Anjo** (Saturday) — API auto-detects winner
- [ ] **Monstro** (Saturday) — Anjo's choice, API auto-detects
- [ ] **Presente do Anjo** (Sunday afternoon) — Anjo's family video vs 2nd immunity choice + almoço guests
- [ ] **Paredão Formation** (Sunday ~22h45) — ceremony flow auto-generates timeline sub-steps (see below)
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
     "formacao": {"lider": "Líder Name", "lideres": ["Líder Name"]},
     "indicados_finais": [],
     "fontes": [{"url": "...", "arquivo": "docs/scraped/...", "titulo": "..."}]
   }
   ```
   **Note**: `formacao.lider` (nested under `formacao`), NOT top-level `lider`.

   **Dual Leadership**: When two Líderes share power (e.g., Week 8 "Liderança em Dobro"):
   ```json
   "formacao": {"lider": "Name A + Name B", "lideres": ["Name A", "Name B"]}
   ```
   - `lider` — display string (joined with ` + `)
   - `lideres` — array of individual names (used for iteration in scoring, Cartola, prediction)
   - The pipeline auto-handles: Cartola points for both, VIP edges from both, prediction per Líder

4. **Update `data/manual_events.json`** — add scheduled events for the new week using the [Recurring Events Checklist](#recurring-events-checklist-per-week). Record power events (Big Fone, etc.) if any.

5. **Rebuild + commit + push**:
   ```bash
   python scripts/build_derived_data.py
   git add data/ docs/MANUAL_EVENTS_AUDIT.md && git commit -m "data: week N Líder transition (Name)"
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

## Anjo / Monstro Update Checklist (Saturday)

When the Prova do Anjo results are published (typically Saturday afternoon article + Saturday night Monstro choice):

### 1. Scrape article(s)

```bash
python scripts/scrape_gshow.py "<prova-do-anjo-url>" -o docs/scraped/
python scripts/scrape_gshow.py "<castigo-do-monstro-url>" -o docs/scraped/  # if separate article
```

### 2. Update `data/provas.json`

Add a new entry to the `provas` array:

```json
{
  "numero": N,
  "tipo": "anjo",
  "week": W,
  "date": "YYYY-MM-DD",
  "nome": "Nª Prova do Anjo — Description",
  "formato": "format_type",
  "vencedor": "Winner Name",
  "participantes_total": 12,
  "excluidos": [{"nome": "Name", "motivo": "reason"}],
  "nota": "Brief description of how the prova worked.",
  "fases": [
    {"fase": 1, "tipo": "...", "classificacao": [{"pos": 1, "nome": "..."}, ...]},
    {"fase": 2, "tipo": "...", "classificacao": [{"pos": 1, "nome": "Winner"}]}
  ],
  "fontes": [{"url": "...", "arquivo": "docs/scraped/...", "titulo": "..."}]
}
```

**Phase rules**: Each phase has its own `classificacao`. For binary-outcome finals (e.g., "correct box"), use **winner only** (no rankings for losers). For timed/scored phases, include all participants with positions.

**Excluded**: Líder always excluded (doesn't play). Others excluded by sorteio, punishment, etc.

### 3. Update `data/manual_events.json` → `weekly_events[N].anjo`

Create or update the week's `weekly_events` entry with the `anjo` object:

```json
{
  "anjo": {
    "vencedor": "Winner Name",
    "prova_date": "YYYY-MM-DD",
    "almoco_date": null,
    "almoco_convidados": [],
    "escolha": null,
    "usou_extra_poder": null,
    "imunizado": null,
    "monstro": "Monstro Name",
    "monstro_tipo": "Monstro Description",
    "monstro_motivo": "Why the Anjo chose this person + consequences",
    "notas": "Brief summary of what happened.",
    "fontes": ["<article-url>"]
  }
}
```

**Fill-later fields** (Sunday [Presente do Anjo](#presente-do-anjo-checklist-sunday-afternoon)): `almoco_date`, `almoco_convidados`, `escolha`, `usou_extra_poder`, `imunizado`. Fill after the Sunday afternoon show.

**Monstro**: API auto-detects the role. Fill `monstro` name from article or API. `monstro_tipo` and `monstro_motivo` when article available.

**Cartola `monstro_retirado_vip`**: Auto-detected. If the Monstro recipient was in VIP in the previous snapshot, the -5 penalty is automatically applied. No manual entry needed.

### 4. Clean up scheduled events

Remove past `scheduled_events` for this date (Prova do Anjo, Monstro) — the auto-dedup handles timeline, but cleaner to remove.

### 5. Rebuild + commit + push

```bash
python scripts/build_derived_data.py
git add data/ docs/MANUAL_EVENTS_AUDIT.md && git commit -m "data: Nª Prova do Anjo (Winner) + Monstro (Name)"
git push
```

### API auto-detects (no manual action needed)

- **Anjo role** — `characteristics.roles` contains `"Anjo"`
- **Monstro role** — `characteristics.roles` contains `"Monstro"`
- Both appear in `auto_events.json` and `roles_daily.json` after rebuild

---

## Presente do Anjo Checklist (Sunday afternoon)

The Presente do Anjo happens Sunday afternoon (~14h-17h BRT). The Anjo invites 2-3 guests for an Almoço do Anjo and makes a choice: watch a family video OR gain a 2nd immunity to give at formation.

**Key fact**: As of W7, every Anjo has chosen `video_familia` (no one has ever used the 2nd immunity).

### 1. Scrape the Presente do Anjo article

```bash
python scripts/scrape_gshow.py "<presente-do-anjo-url>" -o docs/scraped/
```

### 2. Update `data/manual_events.json` → `weekly_events[N].anjo`

Fill the fields that were left `null` on Saturday:

```json
{
  "almoco_date": "YYYY-MM-DD",
  "almoco_convidados": ["Guest1", "Guest2", "Guest3"],
  "escolha": "video_familia",
  "usou_extra_poder": false,
  "imunizado": null
}
```

**Field reference**:

| Field | Values | When to fill |
|-------|--------|-------------|
| `almoco_date` | `"YYYY-MM-DD"` | Sunday — date of the almoço |
| `almoco_convidados` | `["Name1", "Name2"]` | Sunday — who the Anjo invited |
| `escolha` | `"video_familia"` or `"imunidade_extra"` | Sunday — what the Anjo chose |
| `usou_extra_poder` | `false` (chose video) or `true` (chose immunity) | Sunday — always matches `escolha` |
| `imunizado` | `"Name"` or `null` | Sunday night (Paredão formation) — who the Anjo immunized |

**Scoring impact**: Each `almoco_convidados` guest gets a `+0.15` positive `almoco_anjo` edge from the Anjo in the relations scoring. These edges appear in `relations_scores.json`.

**Timeline**: A `presente_anjo` (🎁) event is automatically generated in the game timeline from this data. No manual timeline entry needed.

### 3. Update `data/paredoes.json` → `formacao.anjo_escolha`

Add the `anjo_escolha` descriptive field to the current paredão's `formacao`:

```json
{
  "formacao": {
    "anjo": "Anjo Name",
    "anjo_escolha": "Abriu mão da 2ª imunidade para ver vídeo da família com Guest1, Guest2 e Guest3"
  }
}
```

### 4. Add article to `fontes`

Add the scraped article URL to the anjo's `fontes` array in `weekly_events[N].anjo.fontes`.

### 5. Rebuild + commit + push

```bash
python scripts/build_derived_data.py
git add data/ docs/MANUAL_EVENTS_AUDIT.md && git commit -m "data: Presente do Anjo W{N} (Name chose video/immunity)"
git push
```

### Presente do Anjo History

| Week | Anjo | Escolha | Convidados | Imunizou |
|------|------|---------|------------|----------|
| W1 | Jonas Sulzbach | video_familia | Alberto Cowboy, Aline Campos, Sarah Andrade | Sarah Andrade |
| W2 | Jonas Sulzbach | video_familia | Sarah Andrade, Maxiane, Marciele | — (autoimune) |
| W3 | Sarah Andrade | video_familia | Jonas Sulzbach, Sol Vega, Brigido | Sol Vega |
| W4 | Alberto Cowboy | video_familia | Jonas Sulzbach, Sarah Andrade, Edilson | Edilson |
| W5 | Gabriela | video_familia | Chaiany, Jordana | Chaiany |
| W6 | Chaiany | video_familia | Gabriela, Babu Santana, Solange Couto | Gabriela |
| W7 | Alberto Cowboy | video_familia | Gabriela, Jordana, Marciele | TBD |

**Pattern**: 7/7 Anjos chose family video. The 2nd immunity has never been used.

---

## Paredão Formation Checklist (Sunday)

When the Paredão formation airs (Sunday ~22h45 BRT live show):

### 1. Scrape the formation article

```bash
python scripts/scrape_gshow.py "<formacao-paredao-url>" -o docs/scraped/
```

### 2. Update `data/paredoes.json` (existing skeleton or new entry)

Fill in the formation details. **Key fields** (nested under `formacao`):

```json
{
  "numero": N,
  "status": "em_andamento",
  "data": "YYYY-MM-DD",
  "data_formacao": "YYYY-MM-DD",
  "titulo": "Nº Paredão — DD de Mês de YYYY",
  "semana": N,
  "total_esperado": 3,
  "formacao": {
    "resumo": "Description of how the paredão was formed",
    "lider": "Líder Name",
    "indicado_lider": "Who the Líder nominated",
    "motivo_indicacao": "Why the Líder chose this person",
    "anjo": "Anjo Name",
    "anjo_escolha": "Abriu mão da 2ª imunidade para ver vídeo da família"
  },
  "imunizado": {"por": "Who gave immunity", "quem": "Who received"},
  "indicados_finais": [
    {"nome": "Name", "grupo": "Pipoca", "como": "Líder"},
    {"nome": "Name", "grupo": "Camarote", "como": "Mais votado"},
    {"nome": "Name", "grupo": "Pipoca", "como": "Contragolpe"}
  ],
  "votos_casa": {"Voter1": "Target1", "Voter2": "Target2"},
  "fontes": [{"url": "...", "arquivo": "docs/scraped/...", "titulo": "..."}]
}
```

**Critical**: Use `indicados_finais` (NOT `participantes`). Field `formacao.lider` (nested), NOT top-level `lider`.

### 3. Update `data/manual_events.json`

Add power events for the formation:
- `indicacao` (Líder → nominee)
- `contragolpe` (if applicable)
- `imunidade` (Anjo → imunizado)
- `bate_volta` (winners who escaped)

Also update `weekly_events[N].anjo.imunizado` with who the Anjo immunized at formation. The `escolha` and other Presente do Anjo fields should already be filled from the [Presente do Anjo Checklist](#presente-do-anjo-checklist-sunday-afternoon) (Sunday afternoon).

### 4. Update `data/provas.json` (if Bate e Volta happened)

Add a Bate e Volta prova entry with the results.

### 5. Rebuild + commit + push

```bash
python scripts/build_derived_data.py
git add data/ docs/MANUAL_EVENTS_AUDIT.md && git commit -m "data: Nº Paredão formation"
git push
```

### Auto-generated Ceremony Sub-Steps in Cronologia

When `build_derived_data.py` runs, the timeline builder reads `paredoes.json` and **automatically generates** up to 6 ordered sub-step events for each paredão formation date. No manual timeline entries are needed — just fill `paredoes.json` correctly.

**Standard ceremony flow** (Sunday ~22h45 live show):

| Order | Category | Emoji | What happens | Data source in `paredoes.json` |
|-------|----------|-------|--------------|-------------------------------|
| 1 | `paredao_imunidade` | 🛡️ | Anjo gives immunity (or self-immunizes) | `formacao.imunizado` or `formacao.autoimune` |
| 2 | `paredao_indicacao` | 🎯 | Líder nominates a participant | `formacao.indicado_lider` + `formacao.lider` |
| 3 | `paredao_votacao` | 🗳️ | House votes; most-voted announced | `votos_casa` (vote counts computed) |
| 4 | `paredao_contragolpe` | ⚔️ | Indicado do Líder counter-attacks | `formacao.contragolpe.de` + `.para` |
| 5 | `paredao_bate_volta` | 🔄 | 3 play; indicado do Líder never plays; winner escapes | `formacao.bate_volta` |
| 6 | `paredao_formacao` | 🔥 | Final nominees announced | `indicados_finais` |

**Notes**:
- Steps are only generated when the corresponding data exists (e.g., no `paredao_contragolpe` if `formacao.contragolpe` is empty).
- When a paredão sub-step covers the same event as a `power_event` entry, the redundant power_event is auto-suppressed (dedup by date + mapped category).
- Self-immunity (`formacao.autoimune: true`) shows "se autoimunizou" instead of the normal "X imunizou Y".
- Paredão Falso entries show "Paredão Falso" in the title instead of "Paredão".
- All previous paredões are backfilled automatically from existing data.

**Scheduling future paredão ceremony**: Add a single `paredao_formacao` scheduled event for Sunday (the summary step). The ceremony sub-steps will be auto-generated once the real formation data is entered — no need to schedule each sub-step.

---

## Votalhada Collection Checklist (Tuesday)

Before each elimination (~21h BRT), collect poll data from [Votalhada](https://votalhada.blogspot.com/).

Votalhada updates images roughly at: Mon 01:00, 08:00, 12:00, 15:00, 18:00, 21:00 BRT; Tue 08:00, 12:00, 15:00, 18:00, 21:00 BRT.

### 1. Fetch poll images with the script

```bash
# By paredão number (auto-derives URL from paredoes.json or current month)
python scripts/fetch_votalhada_images.py --paredao N

# Or by direct URL
python scripts/fetch_votalhada_images.py --url "https://votalhada.blogspot.com/YYYY/MM/pesquisaN.html"
```

**URL pattern**: Votalhada always uses `https://votalhada.blogspot.com/{year}/{month}/pesquisa{N}.html`. The script derives this automatically from `paredoes.json` when the skeleton exists. If no skeleton exists yet (e.g., new paredão not created), the script falls back to the **current BRT month/year** — so `--paredao 8` works immediately without needing a `paredoes.json` entry.

Quick URL generation for any paredão:

```bash
# Generate the Votalhada URL for paredão N (replace N with the number)
N=8; echo "https://votalhada.blogspot.com/$(date -u -d '-3 hours' +%Y/%m)/pesquisa${N}.html"

# macOS (BSD date)
N=8; echo "https://votalhada.blogspot.com/$(TZ=America/Sao_Paulo date +%Y/%m)/pesquisa${N}.html"
```

Images are saved to `data/votalhada/YYYY_MM_DD/` with a datetime suffix by default (e.g., `consolidados_2026-03-02_21-05.png`), preserving a history of captures. Use `--no-timestamp` to overwrite instead.

**Run multiple times** (e.g., 01:00 and 21:00 BRT) to capture poll evolution.

### 2. Run OCR parser (Consolidado-only)

Use the OCR parser on the fetched folder:

```bash
python scripts/votalhada_ocr_feasibility.py \
  --images-dir data/votalhada/YYYY_MM_DD \
  --paredao N \
  --debug \
  --output tmp/votalhada_ocr/paredao_N_latest.json
```

The parser is **content-based**:
- It scans all PNGs and selects the best `consolidado_data` image by OCR signature.
- It does **not** rely on fixed filename index (`consolidados_5`, `consolidados_6`, etc.).
- It uses only the selected consolidado card (top+bottom crops from the same file), not platform cards.

The parser supports dynamic top-table schemas seen across BBB25/BBB26:
- 3-platform: `Sites`, `YouTube`, `Twitter`
- 4-platform with `Instagram`
- 4-platform with `Outras Redes`
- split rows `Média Threads` + `Média Instagram`

### 3. Validation gate (must pass before update)

From the OCR output JSON:
- `validation_errors` must be empty
- `parsed.serie_temporal` must be non-empty
- `parsed.capture_hora` must exist

If any validation error appears, stop and inspect with vision before editing `data/votalhada/polls.json`.

### 4. Historical series handling (critical for next week)

`serie_temporal` in consolidado is cumulative: each new capture adds rows over time.

Rules when applying OCR results:
- `serie_temporal`: append only new `hora` entries; never delete existing past rows
- `consolidado` and `plataformas`: overwrite with latest snapshot
- `data_coleta`: overwrite with latest capture timestamp

Quick regression check between two OCR outputs (`prev.json` and `curr.json`):

```bash
python - <<'PY'
import json
from pathlib import Path

prev = json.loads(Path("tmp/votalhada_ocr/prev.json").read_text())
curr = json.loads(Path("tmp/votalhada_ocr/curr.json").read_text())

prev_rows = prev["parsed"]["serie_temporal"]
curr_rows = curr["parsed"]["serie_temporal"]
print("prev_rows:", len(prev_rows), "curr_rows:", len(curr_rows))
print("prev_capture:", prev["parsed"]["capture_hora"])
print("curr_capture:", curr["parsed"]["capture_hora"])
PY
```

Expected behavior:
- `curr_rows >= prev_rows` in most captures
- If `curr_capture_hora` is newer, the latest vote total should not decrease

### 5. Apply to `data/votalhada/polls.json`

After OCR validation passes:
1. append new series rows by `hora`
2. overwrite latest `consolidado` and `plataformas`
3. set `predicao_eliminado` to participant with highest consolidado %
4. update `data_coleta`

**AI Agent Instructions**: See `data/votalhada/README.md` → "AI Agent Instructions" for detailed parsing rules.

### 6. Paredão Falso ("Quem SALVAR?") handling

For Paredão Falso polls, set these extra fields in the poll entry:

```json
{
  "tipo_voto": "salvar",
  "paredao_falso": true
}
```

- **`tipo_voto: "salvar"`** — marks this as a save poll (vote to save, not eliminate). Most voted goes to Quarto Secreto. Prediction logic is the same (most voted = selected).
- **`predicao_eliminado`** in `consolidado` — set to the **most** voted participant (same as normal paredões).
- QMD pages auto-detect `tipo_voto` and display "Quem você quer SALVAR?" header + Paredão Falso warning banner.

### 7. Verify name matching

Votalhada uses short names. Always match to API names:

| Votalhada Shows | Use in polls.json |
|-----------------|-------------------|
| "Aline" | "Aline Campos" |
| "Ana Paula" | "Ana Paula Renault" |
| "Cowboy" / "A Cowboy" | "Alberto Cowboy" |
| "Sol" | "Sol Vega" |
| "Floss" | "Juliano Floss" |

### 8. Rebuild, commit, push + deploy

```bash
# Rebuild derived data (updates prediction model weights)
python scripts/build_derived_data.py

# Commit and push
git add data/ && git commit -m "data: votalhada polls paredão N"
git push

# Deploy immediately (site only updates on cron or manual dispatch, NOT on push)
gh workflow run daily-update.yml
```

**Verify locally** (optional):
```bash
quarto render paredao.qmd    # Check "Enquetes" section renders correctly
```

**Full extraction workflow and AI agent instructions**: See `data/votalhada/README.md`.

---

## Elimination Result Checklist (Tuesday)

After the elimination result is announced (~23h BRT):

> **Paredão Falso**: The same checklist applies. Set `status: "finalizado"`, fill `resultado` with the "eliminated" name (who goes to Quarto Secreto) and vote percentages as normal. The `paredao_falso: true` flag in `paredoes.json` ensures the pipeline treats it correctly (Cartola awards `quarto_secreto` points instead of elimination).

### 0. Scrape the result article

```bash
python scripts/scrape_gshow.py "<resultado-paredao-url>" -o docs/scraped/
```

The article contains exact vote percentages (Voto Único, Voto Torcida, Média) for all nominees.

### 1. Update `data/paredoes.json`

Set the status to `finalizado`, add vote results, and add the article to `fontes`:

```json
{
  "status": "finalizado",
  "resultado": {
    "eliminado": "Name",
    "votos": {
      "Name1": {"voto_unico": 45.23, "voto_torcida": 50.10, "voto_total": 46.69},
      "Name2": {"voto_unico": 54.77, "voto_torcida": 49.90, "voto_total": 53.31}
    }
  },
  "fontes": [
    {"url": "...", "arquivo": "docs/scraped/...", "titulo": "Result article title"}
  ]
}
```

**Voting system (BBB 26)**: Voto Único (CPF, 70%) + Voto da Torcida (unlimited, 30%) = Média Final (`voto_total`).

**Where to find data**: The scraped article, or search `BBB 26 Nº paredão porcentagem resultado`.

### 2. Update `data/votalhada/polls.json`

Add `resultado_real` to the paredão's poll entry:

```json
{
  "resultado_real": {
    "Name1": 45.23,
    "Name2": 54.77,
    "eliminado": "Name2",
    "predicao_correta": true
  }
}
```

- Use `voto_total` (not `voto_unico` or `voto_torcida`) for the percentages — this matches what Votalhada predicted against.
- Set `predicao_correta` to `true` if `consolidado.predicao_eliminado` matches `resultado_real.eliminado`, otherwise `false`.
- For Paredão Falso: "eliminado" = who went to Quarto Secreto (most voted to save).

### 3. Record Ganha-Ganha (same night, ~23h30)

The Ganha-Ganha happens right after elimination. Three participants are drawn by lot. One gets the veto power (eliminates one of the other two from the dynamic). The remaining participant chooses between a cash prize or privileged information.

#### 0. Scrape the article

```bash
python scripts/scrape_gshow.py "<ganha-ganha-url>" -o docs/scraped/
```

The article contains all the details: who was drawn, who vetoed whom, and what the remaining participant chose. Use it as the source for filling the fields below.

Add **two things** to `data/manual_events.json`:

#### A. `weekly_events[N].ganha_ganha`

```json
{
  "ganha_ganha": {
    "date": "YYYY-MM-DD",
    "sorteados": ["Name1", "Name2", "Name3"],
    "cartas": "Description of what happened with the cards/draw",
    "veto": {
      "por": "Who had veto power",
      "quem": "Who was vetoed (eliminated from the dynamic)"
    },
    "decisao": {
      "quem": "Who made the final choice",
      "escolha": "informação privilegiada",
      "abriu_mao": "R$ 10 mil (dobrar para R$ 20 mil)"
    },
    "informacao": "Content of the privileged information revealed (if chosen)",
    "fontes": ["<article-url>"]
  }
}
```

**Field reference**:

| Field | Values | Notes |
|-------|--------|-------|
| `sorteados` | `["A", "B", "C"]` | Always 3 participants drawn by lot |
| `veto.por` | Name | Person who had veto power |
| `veto.quem` | Name | Person removed from the dynamic |
| `decisao.quem` | Name | Person who chose between prize and info |
| `decisao.escolha` | `"informação privilegiada"` or `"R$ X mil"` | What they picked |
| `decisao.abriu_mao` | String | What they gave up |
| `informacao` | String or `null` | Content of privileged info (if chosen) |

#### B. Two `power_events` entries

```json
[
  {
    "date": "YYYY-MM-DD",
    "week": N,
    "type": "veto_ganha_ganha",
    "actor": "Vetoed person",
    "target": "Person who vetoed",
    "source": "Ganha-Ganha",
    "detail": "Foi vetado(a) por X na dinâmica do Ganha-Ganha.",
    "impacto": "negativo",
    "origem": "manual",
    "visibility": "public",
    "awareness": "known"
  },
  {
    "date": "YYYY-MM-DD",
    "week": N,
    "type": "ganha_ganha_escolha",
    "actor": "Person who chose",
    "target": "Person who vetoed",
    "source": "Ganha-Ganha",
    "detail": "Ficou com a decisão na dinâmica após o veto de X em Y.",
    "impacto": "positivo",
    "origem": "manual",
    "visibility": "public",
    "awareness": "known"
  }
]
```

**Note on `actor`/`target` in veto**: The `actor` is the **vetoed person** (they receive the negative impact), `target` is the person who did the veto. This matches the relations scoring direction (impact flows toward the actor).

### 4. Rebuild, commit, push + deploy

```bash
python scripts/build_derived_data.py
git add data/ docs/MANUAL_EVENTS_AUDIT.md && git commit -m "data: paredão N result + ganha-ganha"
git push
gh workflow run daily-update.yml
```

### What auto-updates after rebuild + deploy

Once `build_derived_data.py` runs and the site deploys, the following update **automatically** — no manual action needed:

| What | Where | Details |
|------|-------|---------|
| **Cartola BBB points** | `cartola_data.json` → `cartola.qmd` | `eliminado` (+15 for survivors) or `quarto_secreto` (+40) points awarded. All auto-detected from `paredoes.json` status + `paredao_falso` flag. |
| **Paredão archival** | `paredao_analysis.json` → `paredoes.qmd` | Finalized paredão moves to the archive page with full analysis (votos da casa, reaction heatmap, formation timeline). |
| **Prediction model recalibration** | `vote_prediction.json` → `paredao.qmd` | The **Modelo Ponderado por Precisão** recalculates weights using all finalized `resultado_real` entries. RMSE per platform, weights, and backtest results update automatically. |
| **Votação page** | `votacao.qmd` | Voto Único vs Voto Torcida analysis updates with the new paredão's voting breakdown. |
| **Current paredão page** | `paredao.qmd` | Switches from "EM VOTAÇÃO" to result display. Shows "Enquetes vs Resultado" comparison instead of prediction cards. |
| **Elimination detection** | `eliminations_detected.json` | Participant disappearance from API triggers auto-detection (for real eliminations). For Paredão Falso, participant stays in API. |
| **Game timeline** | `game_timeline.json` → `index.qmd`, `evolucao.qmd` | `paredao_resultado` event auto-generated from finalized paredão. |
| **Relations scores** | `relations_scores.json` | Paredão-anchored scores frozen at formation date snapshot. |

**No manual action needed for any of the above** — just rebuild, push, and deploy.

### Paredão Falso display handling

When `paredao_falso: true` is set in `paredoes.json`, the entire display layer automatically adapts:

| Component | Regular Paredão | Paredão Falso |
|-----------|----------------|---------------|
| **Timeline** (`game_timeline.json`) | "Breno eliminado (54.66%)" 🏁 | "Breno → Quarto Secreto (54.66%)" 🔮 |
| **Transformed resultado** (`load_paredoes_transformed`) | `ELIMINADA` | `QUARTO_SECRETO` |
| **Nominee badge** (`get_nominee_badge()`) | "ELIMINADO" 🔴 red | "🔮 Q. SECRETO" 🔮 purple |
| **paredoes.qmd summary table** | Column: "Eliminado(a)" | Column: "→ Q. Secreto" |
| **paredoes.qmd tab label** | "7º Paredão (Breno)" | "7º Paredão Falso (Breno)" |
| **paredoes.qmd history rows** | "Elim." red | "🔮 Q. Secreto" purple |
| **paredao.qmd precision label** | "(eliminado)" | "(→ quarto secreto)" |
| **paredao.qmd result cards** | "ELIMINADO" red border | "🔮 Q. SECRETO" red border |
| **votacao.qmd health cards** | 🎯/🛡️ icons, "eliminação" language | ⬆️/⬇️ icons, "salvação" language |
| **votacao.qmd editorial** | "forçar eliminação" | "forçar salvação" |
| **Cartola points** | `eliminado` (−20) | `quarto_secreto` (+40) |

Generic analytical text uses "mais votado" instead of "eliminado" across all pattern/accuracy displays (works for both types).

**No manual overrides needed** — the `paredao_falso: true` flag drives all display logic.

---

## Sincerão Update (Monday)

After the Monday live show (~22h BRT):

### 1. Scrape Sincerão articles

```bash
# Main overview article:
python scripts/scrape_gshow.py "<sincerao-url>" -o docs/scraped/

# For "Linha Direta" format (one article per participant), scrape all individual articles:
python scripts/scrape_gshow.py "<url-1>" -o docs/scraped/
python scripts/scrape_gshow.py "<url-2>" -o docs/scraped/
# ... repeat for each participant
```

### 2. Update `data/manual_events.json` → `weekly_events[N].sincerao`

Add a Sincerão entry (single `dict` or `list` of dicts for multiple rounds):

```json
{
  "sincerao": {
    "date": "YYYY-MM-DD",
    "format": "Description of this week's format",
    "participacao": ["Name1", "Name2"],
    "protagonistas": [],
    "notes": "Summary of what happened, key confrontations, target tally",
    "fontes": ["<sincerao-url>"],
    "stats": {
      "most_targeted": [{"name": "X", "count": 4}],
      "not_targeted": ["Y"],
      "mutual_confrontations": [["A", "B"]]
    },
    "edges": [
      {"actor": "A", "target": "B", "type": "bomba", "tema": "maior traidor(a)"}
    ],
    "edges_notes": "Context about edge extraction"
  }
}
```

**Edge types** (must match `builders/sincerao.py` weights):

| Type | Weight | When to use |
|------|--------|-------------|
| `podio` (+ `slot`: 1/2/3) | +0.6 / +0.4 / +0.2 | Participant puts someone on their podium |
| `nao_ganha` | −0.8 | Participant says someone won't win |
| `bomba` (+ `tema`) | −0.6 | Directed confrontation: bomb themes, "maior traidor(a)", etc. |
| `paredao_perfeito` | −0.3 | Participant nominates someone for ideal paredão |
| `prova_eliminou` | −0.15 | Eliminated someone in a Sincerão sub-game |

**Backlash** (auto-generated reverse edge, target → actor): `nao_ganha` 0.3, `bomba` 0.4.

**Full Sincerão schema**: See `docs/SCORING_AND_INDEXES.md` → Sincerão Framework.

### 3. Rebuild + commit + push

```bash
python scripts/build_derived_data.py
git add data/ docs/MANUAL_EVENTS_AUDIT.md && git commit -m "data: week N sincerão"
git push
```

---

## Scheduled Events (upcoming week)

Future events displayed in the Cronologia do Jogo with dashed borders, 🔮 prefix, and yellow time badge.

### Adding scheduled events

Add to `data/manual_events.json` → `scheduled_events` array:

```json
{
  "date": "YYYY-MM-DD",
  "week": N,
  "category": "paredao_formacao",
  "emoji": "🗳️",
  "title": "Event Title",
  "detail": "Brief description",
  "time": "Ao Vivo",
  "fontes": ["<dynamics-article-url>"]
}
```

**Common categories for scheduling**: `sincerao`, `ganha_ganha`, `barrado_baile`, `anjo`, `monstro`, `presente_anjo`, `paredao_formacao`, `paredao_resultado`, `dinamica`.

**Auto-generated categories** (from `paredoes.json`, do NOT schedule these): `paredao_imunidade`, `paredao_indicacao`, `paredao_votacao`, `paredao_contragolpe`, `paredao_bate_volta`. These ceremony sub-steps are created automatically when formation data is filled. See [Paredão Formation → Auto-generated Ceremony Sub-Steps](#auto-generated-ceremony-sub-steps-in-cronologia).

### Auto-dedup behavior

- `build_game_timeline()` merges scheduled events with real events
- If a real event with the same `(date, category)` exists, the scheduled entry is auto-skipped
- Past scheduled events (`date < today`) are dropped from timeline display
- **Clean up periodically**: remove past entries from `scheduled_events` array

---

## Manual Data Files — When and How

### 1. `data/manual_events.json`

**When**: After any power event, Big Fone, Sincerão, special dynamic, exit, or scheduled event.

**Common entries** (by frequency):
- `power_events` — contragolpe, veto, imunidade, ganha-ganha, barrado
- `weekly_events` — Big Fone, Sincerão, Anjo details, confessão de voto, dedo-duro
- `special_events` — dinâmicas especiais
- `scheduled_events` — upcoming events (with auto-dedup)
- `participants` — desistências, desclassificações

**Pitfalls**:
- Names must match API exactly (see `CLAUDE.md` → Name Matching)
- Consensus events: use `"actor": "A + B + C"` + `"actors": ["A","B","C"]`
- `build_derived_data.py` hard-fails on audit issues — fix before pushing

**Full schema**: `docs/MANUAL_EVENTS_GUIDE.md`

### 2. `data/paredoes.json`

**When**: At paredão skeleton creation (Thursday), formation (Sunday), and result (Tuesday).

**Key pitfalls**:
- Use `indicados_finais` (NOT `participantes`) for nominee list
- `formacao.lider` is nested under `formacao`, NOT top-level
- `resultado.votos.{name}.{voto_unico, voto_torcida, voto_total}` — NOT `percentuais`
- `fontes` are objects: `{"url": "...", "arquivo": "docs/scraped/...", "titulo": "..."}`
- For fake eliminations, add `"paredao_falso": true`

**Full schema**: See `CLAUDE.md` → Paredão Workflow → Data Schema.

### 3. `data/provas.json`

**When**: After Prova do Líder (Thursday), Prova do Anjo (Saturday), Bate e Volta (Sunday).

**Workflow**: Add entry to the `provas` array with `numero`, `tipo`, `week`, `date`, `vencedor`, `fases`, `fontes`. See [Anjo Checklist](#anjo--monstro-update-checklist-saturday) and [Líder Checklist](#líder-transition-checklist-thursday-night) for templates.

### 4. `data/votalhada/polls.json`

**When**: Tuesday ~21h (before elimination) and after result.

**Workflow**: See [Votalhada Collection Checklist](#votalhada-collection-checklist-tuesday).

**Full extraction workflow**: `data/votalhada/README.md`.

### `cartola_points_log` (manual overrides)

For Cartola events **not auto-detected** from API snapshots or derived data. Rarely needed — most events are now auto-detected.

**Schema** (in `data/manual_events.json`):
```json
{
  "participant": "Name",
  "week": N,
  "reason": "Why this manual entry is needed",
  "fonte": "https://...",
  "events": [
    {"event": "event_type", "points": N}
  ]
}
```

**Auto-detected types** (will be ignored if added here): `lider`, `anjo`, `monstro`, `emparedado`, `imunizado`, `vip`, `desistente`, `eliminado`, `desclassificado`, `atendeu_big_fone`, `monstro_retirado_vip`, `quarto_secreto`.

**What's auto-detected**:
- From API snapshots: `lider`, `anjo`, `monstro`, `imunizado`, `emparedado`, `vip`
- From manual data: `atendeu_big_fone`, `desistente`, `eliminado`, `desclassificado`
- From paredões: `salvo_paredao`, `nao_eliminado_paredao`, `nao_emparedado`, `nao_recebeu_votos`
- Cross-checked: `monstro_retirado_vip` (Monstro recipient was in VIP in previous snapshot)
- Paredão Falso: `quarto_secreto` (+40, from `paredao_falso: true` + finalized result)

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
| Update PROGRAMA_BBB26.md timeline | `python scripts/update_programa_doc.py` |
| Scrape a GShow article | `python scripts/scrape_gshow.py "<url>" -o docs/scraped/` |

---

## Capture Timing Analysis

### When does the queridômetro actually update?

| Source | Observation | Time (BRT) |
|--------|-------------|------------|
| **Probe data** | Mar 3 — new hash `c143df77` first captured | **10:36** |
| **API data observed** | Feb 5 (Wed) — data already updated | ~14:00 |
| **API first auto capture** | Feb 6 (Thu) — change detected at 15:46 BRT | between 06:37–15:46 |
| **GShow article** | Feb 5 (Wed) — article published | ~09:00 |
| **Raio-X wake-up** | Normal days / Post-party days | 09h-13h |

**Key finding (updated 2026-03-03)**: The queridômetro updates **much earlier than previously estimated**. First probe data (Mar 3) shows new reactions appearing by **10:36 BRT** — the Raio-X happens in the morning and the API publishes shortly after. Previous estimates of ~14:00 BRT were wrong because our captures had wide gaps (06:00 → 15:00 BRT) that missed the actual update window. Temporary probes active to confirm the pattern over multiple days.

### Current cron schedule

**Permanent slots** (4x/day):

| UTC | BRT | Purpose |
|-----|-----|---------|
| 03:00 | 00:00 | Night — post-episode changes (Sun Líder/Anjo, Tue elimination) |
| 09:00 | 06:00 | Pre-Raio-X baseline — balance/estalecas |
| 18:00 | 15:00 | Post-Raio-X — **primary capture** |
| 21:00 | 18:00 | Evening — balance/role changes |

**Saturday extras** (Anjo + Monstro usually Saturday afternoon):

| UTC | BRT | Purpose |
|-----|-----|---------|
| 20:00 | 17:00 | Post-Anjo challenge (runs ~14h-17h) |
| 23:00 | 20:00 | Post-Monstro pick |

**Total**: 6 runs/day (weekdays), 8 on Saturdays.

### Temporary timing probes (added 2026-03-03)

To pinpoint the exact queridômetro update time, extra probes run every 30 min from **09:30 to 16:00 BRT**:

| BRT | UTC | Cron expression |
|-----|-----|-----------------|
| 09:30 | 12:30 | `30 12-18 * * *` |
| 10:00 | 13:00 | `0 13-19 * * *` |
| 10:30 | 13:30 | `30 12-18 * * *` |
| 11:00 | 14:00 | `0 13-19 * * *` |
| 11:30 | 14:30 | `30 12-18 * * *` |
| 12:00 | 15:00 | `0 13-19 * * *` |
| 12:30 | 15:30 | `30 12-18 * * *` |
| 13:00 | 16:00 | `0 13-19 * * *` |
| 13:30 | 16:30 | `30 12-18 * * *` |
| 14:00 | 17:00 | `0 13-19 * * *` |
| 14:30 | 17:30 | `30 12-18 * * *` |
| 15:00 | 18:00 | `0 13-19 * * *` (overlaps permanent slot) |
| 15:30 | 18:30 | `30 12-18 * * *` |
| 16:00 | 19:00 | `0 13-19 * * *` |

**First-appearance log** (when genuinely new reaction data was first captured):

| Date | First seen (BRT) | Notes |
|------|-----------------|-------|
| Mar 3 | **10:36** | First day with probes — new hash between 08:10 and 10:36 |
| Feb 28 | 15:31 | No probes — wide gap (06:00→15:00), likely appeared earlier |
| Feb 27 | 15:40 | Same gap issue |
| Feb 26 | 15:51 | Same gap issue |
| Feb 25 | 12:54 | Elimination day — more captures available |
| Feb 22 | 12:16 | Earliest pre-probe observation |

Note: Pre-probe entries (Feb 22–28) had 9-hour gaps between 06:00 and 15:00 BRT, so the data likely appeared earlier than captured. The API may show different states briefly during the update propagation window.

`fetch_data.py` only saves when data actually changes (hash comparison), so the first new snapshot after the 06:00 BRT baseline reveals the exact update time.

**Analyzing results**:

```bash
# Check which snapshot times captured the queridômetro change today
ls -la data/snapshots/ | grep "$(date -u +%Y-%m-%d)"

# Full timing analysis across all captured days
python scripts/analyze_capture_timing.py
```

**When to remove**: After 3–5 days of data, run `analyze_capture_timing.py` to confirm the update window. Then:
1. Remove the two temporary cron lines from `.github/workflows/daily-update.yml`
2. Adjust the permanent 15:00 BRT slot if the data shows an earlier/later window
3. Update the "Key finding" above with the confirmed time

---

## Troubleshooting

### `build_derived_data.py` fails with audit error

```bash
python scripts/audit_manual_events.py    # check what's wrong
# Fix data/manual_events.json
python scripts/build_derived_data.py     # re-run
```

### Merge conflict on `data/derived/`

See [Handling Push Conflicts](#handling-push-conflicts).

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

The workflow only triggers on **cron** and **manual dispatch**, not on push:
```bash
gh workflow run daily-update.yml    # manual trigger, or wait for next cron (max 6h)
```

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
build_derived_data.py           data/derived/*.json (21 files)
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

| Doc | Purpose |
|-----|---------|
| **`CLAUDE.md`** | Master project guide — architecture, data schema, coding conventions |
| **`docs/MANUAL_EVENTS_GUIDE.md`** | Full schema + fill rules for `manual_events.json` |
| **`docs/SCORING_AND_INDEXES.md`** | Scoring formulas, weights, index specifications |
| **`docs/PROGRAMA_BBB26.md`** | TV show reference — rules, format, dynamics |
| **`data/votalhada/README.md`** | Screenshot-to-data extraction workflow |
| **`data/CHANGELOG.md`** | Snapshot history, dedup analysis, API observations |
