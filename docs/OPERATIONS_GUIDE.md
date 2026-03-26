# BBB26 Operations Guide

> Single source of truth for ALL operational procedures — data updates, event workflows, git sync, and troubleshooting.
>
> **For AI agents without context**: Read the Document Map below, then jump to the section you need with `Read offset=N limit=M`.
> **For schemas and field specs**: See `docs/MANUAL_EVENTS_GUIDE.md` (events) and `docs/ARCHITECTURE.md` (architecture).
> **For scoring formulas**: See `docs/SCORING_AND_INDEXES.md`.
> **For verification strategy**: See `docs/TESTING.md`.
> **For public/private doc boundaries**: See `docs/PUBLIC_PRIVATE_DOCS_POLICY.md`.
>
> **Last updated**: 2026-03-19

---

## Document Map (for AI agents)

This file is ~2,400 lines. **Do not read it all at once.** Use this map to jump to the section you need.

> **Refresh line numbers** (they shift on edits): `grep -n "^## " docs/OPERATIONS_GUIDE.md`

**Setup & Policies** (read once per session if unfamiliar):

| Line | Section | What's there |
|------|---------|-------------|
| ~88 | Common Edit Recipes | Change type → files to edit → scripts to run |
| ~103 | Web Scraping & Source Collection | GShow can't be WebFetched — use `scrape_gshow.py` |
| ~133 | Public vs Private Doc Policy | What can/can't be pushed |
| ~148 | Git Workflow | Main-first workflow, publish, push conflicts, legacy recovery |

**Event Checklists** (read the one matching today's task):

| Line | Section | When |
|------|---------|------|
| ~582 | Líder Transition | Thursday night |
| ~789 | Anjo / Monstro | Saturday |
| ~954 | Presente do Anjo | Sunday afternoon |
| ~1039 | Paredão Formation | Sunday night |
| ~1143 | Votalhada Collection | Tuesday ~21h |
| ~1452 | Elimination Result | Tuesday ~23h |
| ~1727 | Barrado no Baile | Wednesday |
| ~1793 | Sincerão Update | Monday |

**Reference** (read on demand):

| Line | Section | What's there |
|------|---------|-------------|
| ~424 | Triggering Site Updates | How/when GitHub Pages deploys |
| ~467 | Weekly Calendar | Standard week pattern + week rollover runbook + history tables |
| ~1879 | Scheduled Events | How to add future events |
| ~1951 | Manual Data Files | Schema summaries for each data file |
| ~2079 | Economia / Compras | Balance auto-detection rules |
| ~2114 | Script Reference | Which script to run for each task |
| ~2140 | Screenshot Pipeline | Layout review with Playwright |
| ~2302 | Troubleshooting | Build failures, conflicts, stale data |

---

## Quick Index — "I need to..."

| Task | When | Go to |
|------|------|-------|
| **Update after ANY manual edit** | After editing any data file | [Git Workflow](#git-workflow-main-first) |
| **Review archived `local/private-main` history (legacy)** | Only if you still have old local commits | [Git Workflow](#git-workflow-main-first) |
| **Close old week / open new week** | Thursday/Friday after dynamics article | [Week Rollover Runbook](#week-rollover-runbook-thursdayfriday) |
| **New Líder crowned** (Thursday) | Thursday ~22h | [Líder Transition Checklist](#líder-transition-checklist-thursday-night) |
| **Prova do Anjo results** (Saturday) | Saturday afternoon | [Anjo / Monstro Checklist](#anjo--monstro-update-checklist-saturday) |
| **Presente do Anjo** (Sunday afternoon) | Sunday ~14h-17h | [Presente do Anjo Checklist](#presente-do-anjo-checklist-sunday-afternoon) |
| **Paredão formation** (Sunday night) | Sunday ~22h45 | [Paredão Formation Checklist](#paredão-formation-checklist-sunday) |
| **Collect Votalhada polls** (Tuesday) | Tuesday ~21h | [Votalhada Collection Checklist](#votalhada-collection-checklist-tuesday) |
| **Elimination result** (Tuesday) | Tuesday ~23h | [Elimination Result Checklist](#elimination-result-checklist-tuesday) |
| **Cartola stale after elimination** | Tuesday ~23h | [Elimination Result Checklist → participant exit + Cartola sanity check](#elimination-result-checklist-tuesday) |
| **Recalibrate Votalhada model after result** | Tuesday ~23h | [Elimination Result Checklist → model sanity check](#elimination-result-checklist-tuesday) |
| **Barrado no Baile** (Wednesday) | Wednesday daytime | [Barrado no Baile Checklist](#barrado-no-baile-checklist-wednesday) |
| **Sincerão data** (Monday) | Monday ~22h | [Sincerão Update](#sincerão-update-monday) |
| **Ganha-Ganha / Barrado / power events** | Various | [Manual Data Files](#manual-data-files--when-and-how) |
| **Add scheduled events for upcoming week** | After dynamics article | [Week Rollover Runbook](#week-rollover-runbook-thursdayfriday) + [Scheduled Events](#scheduled-events-upcoming-week) |
| **Participant exit** (quit/disqualified) | When it happens | [Manual Data Files → manual_events.json](#1-datamanual_eventsjson) |
| **Workflow failed on GitHub** | After failure | [Troubleshooting](#troubleshooting) |
| **Merge feature branch to main** | Feature work done | [Git Workflow → feature branch](#feature-branch--main-multi-commit-features) |
| **Commit and publish to GitHub** | After any checklist step | [Commit & Publish Workflow](#commit--publish-workflow) |
| **Push conflict with bot** | After `git push` fails | [Git Workflow → conflict resolution](#handling-push-conflicts) |
| **Check public/private doc policy** | Before commit/push | [Public vs Private Docs Policy](#public-vs-private-documentation-policy-agents) |
| **Decide what to verify after a change** | Any time | [Common Edit Recipes](#common-edit-recipes-fast-path) + `docs/TESTING.md` |
| **Deploy / render the site on GitHub** | After push to `main` | [Triggering Site Updates](#triggering-site-updates) |
| **Which script to run?** | Any time | [Script Reference](#quick-reference-which-script-when) |

---

## Common Edit Recipes (Fast Path)

Use this table when you already know **what changed** and need the shortest safe path.

| Change type | Usually edit | Must run | Usually inspect next |
|-------------|-------------|----------|----------------------|
| Manual event / paredão / prova / poll data | `data/manual_events.json`, `data/paredoes.json`, `data/provas.json`, `data/votalhada/polls.json` | `python scripts/build_derived_data.py` | `docs/MANUAL_EVENTS_AUDIT.md` + affected page |
| Shared scoring / loader / date logic | `scripts/data_utils.py`, `scripts/builders/*`, `scripts/derived_pipeline.py` | targeted `pytest` + `python scripts/build_derived_data.py` | affected derived JSON + affected page |
| Reusable render helper | `scripts/*_viz.py` | targeted `pytest` + `python scripts/quarto_render_safe.py <affected-page>.qmd` | rendered HTML / page screenshots |
| Page-only composition / prose / layout | `*.qmd`, `assets/*`, `_quarto.yml` | targeted `pytest` + `python scripts/quarto_render_safe.py <affected-page>.qmd` | local page render and, when needed, screenshot capture |
| Git/publication workflow | `.githooks/pre-push`, `.github/workflows/public-policy-report.yml`, `scripts/sync_public.sh` (legacy), workflow docs | `bash -n .githooks/pre-push` when the hook changes; `pytest tests/test_sync_public_script.py -q` only if the legacy helper changed | push policy and legacy recovery flow |
| Documentation only | `README.md`, `docs/*.md`, `data/votalhada/README.md` | consistency check of links/cross-references | no site rebuild required unless instructions or examples changed materially |

For the exact test families and recommended commands, see `docs/TESTING.md`.

## Agent: Web Scraping & Source Collection

**CRITICAL**: GShow (gshow.globo.com) and other Globo properties **cannot be fetched via WebFetch, web scraping AI tools, or direct HTTP clients**. These domains block automated access. **Always use the project's dedicated scraper**:

```bash
python scripts/scrape_gshow.py "<url>" -o docs/scraped/
```

The scraper uses Playwright (headless browser) to render the page and extract content as Markdown. Output goes to `docs/scraped/` (gitignored, local reference only).

### Source images (broadcast screenshots, Twitter/X)

When prova results, duel scores, or other game data are captured as screenshots:

1. **Never leave images at the repo root.** Move them immediately to `docs/scraped/` with descriptive names:
   ```
   prova_anjo_9_qf1_leandro_vs_jonas.jpeg    # format: prova_{tipo}_{numero}_{fase}_{description}
   prova_lider_8_fase1_grupo4.jpeg
   ```
2. **Use Claude Code's vision** (Read tool on image files) to extract scores, names, and results from screenshots.
3. **Create an archive file** for social media sources: `docs/scraped/prova_{tipo}_{numero}_twitter_{account}.md` with tweets in chronological order, extracted scores, and image cross-references.
4. **Add to `fontes`** in `provas.json` or `manual_events.json`:
   ```json
   {"url": "https://x.com/Dantinhas/", "arquivo": "docs/scraped/prova_anjo_9_twitter_dantinhas.md", "titulo": "Cobertura ao vivo @Dantinhas — 9ª Prova do Anjo"}
   ```

### GShow article accuracy

GShow articles can contain factual errors (e.g., omitting excluded participants, wrong scores). **Always cross-verify with multiple sources** (Twitter live coverage, broadcast screenshots, other fan accounts) before recording data. When a discrepancy is found, note it in the data (e.g., `"nota"` field in `provas.json`).

## Public vs Private Documentation Policy (Agents)

This repository is public. Agents must enforce a strict documentation boundary:

- Public docs: only approved pillar docs (see `docs/PUBLIC_PRIVATE_DOCS_POLICY.md`).
- Private docs/tooling: local-only and never pushed (`.private/**`, `CLAUDE.md`, `.claude/**`, `.worktrees/**`, WIP/review/planning docs).
- If visibility is unclear, default to private and place under `.private/docs/`.

Pre-push checklist:

1. Confirm current branch is intended for push: normally `main`, or `feature/*` only when intentionally opening a PR. Never push `local/*`.
2. Check staged files: `git diff --cached --name-only`.
3. Confirm no private-denylist paths are staged/tracked for push.
4. If needed, install/use `.githooks/pre-push` to block accidental exposure.

## Git Workflow (Main-First)

This repo now uses a **main-first workflow**. Day-to-day work happens on `main`. Private material stays local because it is ignored or explicitly blocked from public history.

| Branch | Purpose | Push? |
|--------|---------|-------|
| `main` | Normal working branch + public branch | Yes |
| `local/*` | Local-only archive/recovery branches | **NEVER** push |
| `feature/*` | Optional short-lived feature branches | Only when intentionally opening a PR |

Human commits on `main` use normal descriptive subjects. GitHub Actions bot commits on `main` still use the `data:` prefix.

The GitHub Actions bot polls every 15 minutes and auto-commits `data/` files when the API data changes (~5–15 snapshots/day). See [Triggering Site Updates](#triggering-site-updates).

### Daily Work (on `main`)

```bash
git checkout main
git pull --rebase origin main

# After manual edits (the universal pattern)
python scripts/build_derived_data.py    # rebuild derived data (hard-fails on errors)
git add data/ docs/MANUAL_EVENTS_AUDIT.md docs/SCORING_AND_INDEXES.md
git commit -m "<description>"
git push origin main

# Optional immediate deploy (instead of waiting for next cron)
gh workflow run daily-update.yml
```

### Private Material

- Keep local-only notes and WIP docs under `.private/docs/` whenever possible.
- Never track private/denylist paths on `main` (`CLAUDE.md`, `.private/**`, `.claude/**`, `.worktrees/**`, `docs/superpowers/**`, and similar WIP docs).
- If a file is public-safe only in some cases, default to treating it as private until reviewed.

### Commit & Publish Workflow

All checklists end with "Rebuild + commit + publish". This is the standard procedure:

```bash
# 1. Rebuild derived data (validates schemas, hard-fails on errors)
python scripts/build_derived_data.py

# 2. Stage and commit
git add data/ docs/MANUAL_EVENTS_AUDIT.md docs/SCORING_AND_INDEXES.md
git commit -m "<description>"

# 3. Push and optionally deploy immediately
git push origin main
gh workflow run daily-update.yml
```

If you are on `feature/*`, finish the feature-branch flow below first. If you are on `local/*`, stop and review whether the work belongs on `main` at all before pushing anything.

> **Pre-push hook**: `.githooks/pre-push` blocks pushes from `local/*` branches, tracked private paths, bad bot commit prefixes, and gitlinks.

### Handling Push Conflicts

Most conflicts come from bot-written generated files on `main` (`data/snapshots/*`, `data/latest.json`, `data/derived/*`, and `docs/MANUAL_EVENTS_AUDIT.md`). Standard recovery flow when conflicts are limited to those files:

```bash
git pull --rebase origin main

# If conflicts are only in bot-written generated files, keep main's copy and rebuild
git checkout --ours data/snapshots/ data/latest.json data/derived/ docs/MANUAL_EVENTS_AUDIT.md
git add data/snapshots/ data/latest.json data/derived/ docs/MANUAL_EVENTS_AUDIT.md
git rebase --continue
python scripts/build_derived_data.py

# Commit only if the rebuild produced a diff
git add data/ docs/MANUAL_EVENTS_AUDIT.md
git commit -m "rebuild derived after rebase"

git push origin main
```

If `docs/SCORING_AND_INDEXES.md` conflicts, do **not** blindly take either side. That file contains a bot-managed block inside a human-maintained doc. Resolve it manually or abort and let the next successful bot run regenerate the managed block.

Derived files are always regenerated — the source of truth is manual files + snapshots.

### Legacy `local/private-main` Recovery (optional)

If you still have a stale `local/private-main`, treat it as archival history, not as the normal working branch.

Useful inspection commands:

```bash
git cherry -v main local/private-main
git log --oneline --no-merges main..local/private-main
git stash list
```

`scripts/sync_public.sh` remains available as a **legacy reconciliation helper** for reviewed commits from `local/private-main`, but it is no longer the recommended daily workflow.

```bash
scripts/sync_public.sh
scripts/sync_public.sh --apply --report .private/docs/CONFLICT_REPORTS/<report>.md
```

Use it only when you are intentionally reconciling old local commits back onto `main`.

### Bot-managed vs Manual-managed files

Current `daily-update.yml` behavior:

- GitHub Actions bot updates:
  - `data/snapshots/*`
  - `data/latest.json`
  - `data/derived/*`
  - `docs/MANUAL_EVENTS_AUDIT.md`
  - bot-managed block inside `docs/SCORING_AND_INDEXES.md`
- Manual source files (not bot-written by current workflow):
  - `data/manual_events.json`
  - `data/paredoes.json`
  - `data/provas.json`
  - `data/votalhada/polls.json`

### Feature Branch → `main` (Multi-Commit Features)

For features developed on `feature/*` branches (multi-file refactors, new cards, new scripts):

```bash
# 1. Finish and test on feature branch
pytest tests/ -x -q
python scripts/build_derived_data.py

# 2. Switch to main — pull latest (bot may have committed data)
git checkout main
git pull --rebase origin main

# 3. Squash-apply ALL code changes from feature branch (exclude derived data)
#    Use --no-commit to stage without committing, then rebuild
git merge --squash feature/<name>

# 4. If merge conflicts are limited to bot-written generated files:
#    accept main's version for `data/snapshots/*`, `data/latest.json`,
#    `data/derived/*`, and `docs/MANUAL_EVENTS_AUDIT.md`, then rebuild
git checkout --ours data/snapshots/ data/latest.json data/derived/ docs/MANUAL_EVENTS_AUDIT.md
git add data/snapshots/ data/latest.json data/derived/ docs/MANUAL_EVENTS_AUDIT.md

# 5. If `docs/SCORING_AND_INDEXES.md` conflicts, resolve it manually or
#    abort and let the next successful bot run regenerate the managed block.
#
# 6. If merge conflicts in code files (e.g., index_data_builder.py):
#    Resolve MANUALLY — understand both sides before choosing
#    Main may have added features (saldo_card, link fixes) that your branch doesn't have
#    Never blindly take --ours or --theirs for code files

# 7. Rebuild derived data with main's latest snapshots + your code changes
python scripts/build_derived_data.py

# 8. Run full test suite — fix any failures from integration
pytest tests/ -x -q

# 9. Stage everything and commit
git add -A
git commit -m "<description>"

# 10. Push and deploy
git push origin main
gh workflow run daily-update.yml

# 11. Clean up
git branch -d feature/<name>
```

**Key rules for feature branches**:
- Human commits on `feature/*` and `main` use normal descriptive subjects
- `sync_public.sh` is legacy only; it is not part of the normal feature-branch flow
- Always resolve `data/derived/*` conflicts by accepting main's version then rebuilding
- Never take `--ours` for code files without reading both sides — main may have changes your branch is missing
- Close any open PR before squash-merging locally (avoids duplicate merge)
- Pre-push hook allows `feature/*` branches but validates no private files are tracked

### Handling Extraordinary Events

Surprise disqualification, mid-week dynamic, or any unplanned event:

```bash
git checkout main
git pull --rebase origin main             # 1. Sync first
# Edit the relevant data files            # 2. Make your edits
python scripts/build_derived_data.py      # 3. Rebuild
git add data/ docs/MANUAL_EVENTS_AUDIT.md docs/SCORING_AND_INDEXES.md
git commit -m "<what happened>"
git push origin main
gh workflow run daily-update.yml          # 4. Deploy immediately
```

---

## Triggering Site Updates

The GitHub Pages site at `ferazambuja.github.io/BBB26/` updates through the `daily-update.yml` workflow. **Pushing to `main` does NOT trigger a render** — the workflow runs on cron and manual dispatch only.

### Three ways the site updates

| Method | When it runs | What happens |
|--------|-------------|--------------|
| **Auto (cron)** | Every 15 minutes | Fetches API → saves snapshot if data changed → builds + renders + deploys |
| **Manual dispatch** | On demand | Runs the full pipeline immediately (fetch + build + render + deploy) |
| **After push** | Never (automatic) | Push alone does **not** trigger a build — you must dispatch manually or wait for the next cron |

### Manual dispatch (most common for code/layout changes)

After pushing code, QMD, CSS, or manual data changes to `main`:

```bash
gh workflow run daily-update.yml
```

This triggers the full pipeline: fetch → pytest → build_derived_data → quarto render → deploy to Pages.

### Monitoring a run

```bash
gh run list --limit 5                  # find recent runs
gh run watch                           # live-follow the latest run
gh run view <run-id> --log             # full logs for a specific run
```

### When to dispatch manually

- After pushing **any** change to `main` (code, QMD, CSS, docs, manual data)
- After a failed run that you've fixed locally
- When you need the site updated faster than the 15-minute cron cycle

### When you DON'T need to dispatch

- After the bot auto-commits a new snapshot (the workflow already handles the full pipeline)
- If only `data/` changed via the bot's cron poll (build+deploy runs automatically when data changes)

---

## Weekly Calendar

### Standard Week Pattern (Líder Cycle)

Each BBB week follows a predictable pattern anchored to the Líder cycle.

> **Key rule**: The **Prova do Líder is the FIRST event of the new week**. Everything before it on the same day (e.g., afternoon Anjo prova) belongs to the PREVIOUS week. `WEEK_END_DATES` stores the last day of each week = the day BEFORE the Prova do Líder. When assigning `week` to events in `provas.json` or `manual_events.json`, use the **operational week** (which Líder presided), not `get_week_number(date)` — they can differ on Prova do Líder day.

### Week Rollover Runbook (Thursday/Friday)

Use this as the default workflow when the "Dinâmica da Semana" article lands and the next week opens.

**Mental model**:
- You do not "end week `N`" in isolation. You end it by opening week `N+1`.
- `weekly_events[N+1].notes` should describe only what is unusual about that week.
- The open cycle now gets the recurring Thursday→Wednesday schedule automatically. Add manual entries only for custom copy, non-standard mechanics, or `lider_classificatoria`.

**Always repeats every week**

| Repeat | Action now | Where | Manual `scheduled_events`? |
|--------|------------|-------|----------------------------|
| Week boundary | Set `weekly_events[N].end_date` to Wednesday and append `weekly_events[N+1]` with Thursday `start_date` | `data/manual_events.json` | No |
| Source capture | Scrape the dynamics article and store both URL + scraped file path | `docs/scraped/` + `fontes` | n/a |
| Thursday Líder slot | Default `lider` row is scaffolded for the open cycle. Add `lider_classificatoria` only if the source splits the Prova do Líder. | `scheduled_events` | Only when split/custom |
| Friday custom dynamic | Add the Friday `dinamica` from the article | `scheduled_events` | Yes |
| Saturday baseline visibility | Default `anjo` / `monstro` rows are scaffolded for the open cycle | manual override optional | No, unless custom |
| Rebuild sanity | Rebuild and inspect the next week in timeline + program summary | derived files + docs | n/a |

**Scaffolded every week — override only when this week is special**

| Slot | Default source | Add a manual override when... |
|------|----------------|-------------------------------|
| `lider` (Thursday) | scaffold on the open cycle | timing/copy needs to be more specific before the result exists |
| `anjo` (Saturday) | scaffold on the open cycle | the article gives useful custom copy or a non-standard rule |
| `monstro` (Saturday) | scaffold on the open cycle | the article already states a special Monstro mechanic |
| `presente_anjo` (Sunday) | scaffold | the rule changes (e.g. double immunity / family video tradeoff) |
| `paredao_imunidade` / `paredao_indicacao` / `paredao_votacao` / `paredao_contragolpe` / `paredao_bate_volta` (Sunday) | scaffold on the open cycle; real `paredoes.json` later | the week article needs a more specific public-facing step description |
| `paredao_formacao` (Sunday) | scaffold | formation has custom mechanics (contragolpe, extra emparedado, split show, etc.) |
| `sincerao` (Monday) | scaffold | the article already gives a week-specific format worth surfacing early |
| `paredao_resultado` (Tuesday) | scaffold | unusual timing or custom copy matters |
| `ganha_ganha` (Tuesday) | scaffold | the article announces a non-generic twist |
| `barrado_baile` (Wednesday) | scaffold | the article announces a special rule/time; otherwise record the real result on Wednesday |

**Special only for that week**
- One-off Friday/Saturday mechanics such as Exilado, Máquina do Poder, rescue games, extra emparedado, etc. Model these as `scheduled_events[].category = "dinamica"` until they resolve.
- Any rule that changes the normal Sunday ceremony should appear in the Sunday override detail, not buried in a generic note.
- Dual leadership, consensus mechanics, or other unusual governance rules should be summarized once in `weekly_events[N+1].notes`.
- Once outcomes become real, move them to the authoritative layer: `provas.json`, `paredoes.json`, `weekly_events`, `power_events`, or `special_events`.

**Same-day sequence rule**
- If the article/video explicitly breaks a day into ordered steps, store separate scheduled entries instead of one compressed summary.
- Thursday default split when available: `lider_classificatoria` (afternoon) then `lider` (live final). After classificatórias resolve: (a) update the `lider_classificatoria` event with results + fontes, (b) update the `lider` event title with finalist names, (c) create the provas.json entry with `vencedor: null` + classificatória fases, (d) update any downstream `dinamica` that references "os eliminados da liderança" with actual names.
- Sunday default split in the open cycle: `presente_anjo`, `paredao_imunidade`, `paredao_indicacao`, `paredao_votacao`, `paredao_contragolpe`, `paredao_bate_volta`, `paredao_formacao`.
- Resolved archive cycles do not get fake Sunday mechanics backfilled; the detailed Sunday sub-steps come from authoritative `paredoes.json` data once they exist.

**Schedule profile hook**
- Optional: set `weekly_events[N].schedule_profile` when the cycle rhythm is not the standard Thursday→Wednesday order.
- Supported profiles today:
  - `standard` — normal BBB cadence
  - `accelerated_finale` — altered late-game cadence; Wednesday carries the elimination slot instead of `barrado_baile`

Two recurring event types:
- **Sincerão** (Monday live show) — happens every week with a different format/theme
- **Week Dynamic** (Friday, varies) — the unique dynamic from the weekly dynamics article

| Dia | Horário (BRT) | Evento | Checklist to follow | Data files affected |
|-----|---------------|--------|---------------------|---------------------|
| **Diário** | manhã/tarde (janela em validação) | Queridômetro atualiza | Automático (multi-captura + probes 09:30–16:00 BRT) | `snapshots/` |
| **Segunda** | ~22h | **Sincerão** (ao vivo) | [Sincerão Update](#sincerão-update-monday) | `manual_events.json` |
| **Terça** | ~21h | Votalhada "Consolidados" | [Votalhada Checklist](#votalhada-collection-checklist-tuesday) | `votalhada/polls.json` |
| **Terça** | ~23h | **Eliminação** ao vivo | [Elimination Checklist](#elimination-result-checklist-tuesday) | `paredoes.json` |
| **Terça** | ~23h30 | **Ganha-Ganha** | [Manual Data Files](#1-datamanual_eventsjson) | `manual_events.json` |
| **Quarta** | durante o dia | **Barrado no Baile** | [Barrado no Baile Checklist](#barrado-no-baile-checklist-wednesday) | `manual_events.json` |
| **Quinta** | ~22h | **Prova do Líder** | [Líder Checklist](#líder-transition-checklist-thursday-night) | `provas.json`, `paredoes.json` |
| **Sexta** | ~22h | **Week Dynamic** (varies) | Depends on dynamic | varies |
| **Sábado** | ~14h-17h | **Prova do Anjo** | [Anjo Checklist](#anjo--monstro-update-checklist-saturday) | `provas.json`, `manual_events.json` |
| **Sábado** | ~22h | **Monstro** (Anjo escolhe) | [Anjo Checklist](#anjo--monstro-update-checklist-saturday) | `manual_events.json` |
| **Domingo** | ~14h-17h | **Presente do Anjo** (almoço) | [Presente do Anjo Checklist](#presente-do-anjo-checklist-sunday-afternoon) | `manual_events.json` |
| **Domingo** | ~22h45 | **Paredão Formation** | [Paredão Checklist](#paredão-formation-checklist-sunday) | `paredoes.json` |

### Compressed Cycles (Top 10+, W11 onward)

When the show enters the final phase, Líder cycles compress to **2–4 days** instead of the standard ~7. The standard weekly pattern table above no longer applies. Key differences:

- **Some dynamics are dropped entirely**: Sincerão, Barrado no Baile, and Ganha-Ganha may not occur in compressed cycles. Do not add scheduled events for them unless the article/show confirms them.
- **Anjo and Formation may happen on the same day** (e.g., W11: both on Friday).
- **Elimination + Líder + Formation can all occur on the same day** (e.g., W12: all three on Sunday Mar 29).
- **Use manual `scheduled_events` for all events** in compressed cycles. The scaffold profiles assume standard weekday assignments (Thu Líder, Sat Anjo, Sun Formation, Tue Elimination) which are wrong for compressed cycles. Manual events override scaffolds via singleton dedup.
- **`WEEK_END_DATES` entries will be very close together** (1–3 days apart instead of 6–8). This is expected.
- **Rollover may happen within hours of the previous elimination.** The "Thursday/Friday" rollover timing assumption from the standard runbook does not apply. Follow the same Líder Transition Checklist steps but adapt timing to the actual Prova do Líder date.
- **P11 skeleton safety**: do NOT set `"status": "em_andamento"` until formation data exists. Use `"preparando"` when creating the skeleton after the Líder is crowned. The LXC scheduler triggers Votalhada bootstrap from `em_andamento` entries.
- **Votalhada collection timing shifts**: if elimination is Sunday (not Tuesday), collect Votalhada data Saturday night or Sunday morning.

**Reference schedule for W11–W12 (Top 10, Mar 26–31):**

| Date | Day | Cycle | Events |
|------|-----|-------|--------|
| Thu Mar 26 | Thu | W11 | Prova do Líder |
| Fri Mar 27 | Fri | W11 | Prova do Anjo + Paredão Formation (same night) |
| Sun Mar 29 | Sun | W11→W12 | Elimination (11º) + Prova do Líder (W12) + Formation (12º) |
| Tue Mar 31 | Tue | W12 | Elimination (12º) |

### Sincerão History (Monday — recurring weekly)

Data goes in `weekly_events[N].sincerao` (single `dict` or `list` of dicts for multiple rounds).

| Week | Date | Format | Notes |
|------|------|--------|-------|
| W1 | Mon Jan 19 | Pódio + quem não ganha | Plateia presente, Pipocômetro |
| W2 | Mon Jan 26 | Bombas com temas do público | Plateia define planta (Solange) |
| W3 | Mon Feb 2 | Pior futebol do mundo | Escalação com papéis negativos |
| W4 | Mon Feb 9 | Quem Sou Eu? (adivinhação) | Plateia define mais apagada (Marciele) |
| W5 | Mon Feb 16 | Cancelado (Carnaval) | Globo exibiu desfiles. Sincerão feito ao vivo de forma abreviada. Dados mínimos registrados (3 edges: previsões dos emparedados). |
| W6 | Fri Feb 20 + Mon Feb 23 | Paredão Perfeito + Régua de Prioridade | Two rounds (list format in JSON) |
| W7 | Mon Mar 2 | Linha Direta — maior traidor(a) | Each participant calls one person they consider the biggest traitor |
| W8 | Mon Mar 9 | Pódio dos Medrosos | 3 medalhas (covarde, frouxo/a, arregão/a). Cowboy mais visado (6×), Leandro zero |
| W9 | Mon Mar 16 | Quem faz alguém de bobo + quem está sendo feito de bobo | Placa dupla negativa. No agregado, Alberto Cowboy e Gabriela empataram como mais visados (7×); por placa, Alberto liderou “faz alguém de bobo” (7×) e Gabriela liderou “feito de bobo” (5×). |

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
| W8 | Liderança Dupla + Consenso Anjo/Monstro + Contragolpe | `special_events` |
| W9 | TBD | TBD |

### Recurring Events Checklist (per week)

**Auto-scaffolding**: The open cycle now gets the recurring backbone automatically: `lider`, `anjo`, `monstro`, `presente_anjo`, the Sunday Paredão sub-steps, `paredao_formacao`, `sincerao`, `paredao_resultado`, `ganha_ganha`, and `barrado_baile` (or the selected `schedule_profile`). You do **not** need to add manual `scheduled_events` for those unless you want to override title/detail/time.

Use the [Week Rollover Runbook](#week-rollover-runbook-thursdayfriday) first. Quick decision rule:

- Add manual `scheduled_events` every week for: each extra `dinamica`.
- Add `lider_classificatoria` only when Thursday is explicitly split in the source.
- Override scaffolded recurring slots only when the current article makes them non-generic: `lider`, `anjo`, `monstro`, Sunday Paredão sub-steps, `presente_anjo`, `paredao_formacao`, `sincerao`, `paredao_resultado`, `ganha_ganha`, `barrado_baile`.

**Week-close invariant**:
- Do not "end a week" without opening the next one.
- `weekly_events[N+1].notes` should answer only one question: what is special about this week?
- Every rollover entry should cite both the original GShow URL and `docs/scraped/<arquivo>.md`.

**Operational invariant**:
- Real events (from API, paredoes, weekly_events, power_events) and manual scheduled events take priority over scaffold placeholders.
- Use manual `scheduled_events` for week-specific dynamics and optional overrides (e.g. custom time or description).

### Baseline weekly template (reference; most slots auto-scaffolded)

The table below answers the practical question "does this repeat automatically, or do I need to add it manually?" for week `N`:

| Day | Category | Default source | Add manually when... |
|-----|----------|----------------|----------------------|
| Thursday | `lider_classificatoria` | manual | the source/video announces qualifying rounds before the live final |
| Thursday | `lider` | scaffold on the open cycle, then real `provas.json` fallback | the source has better pre-result wording or a custom time |
| Friday | `dinamica` | manual | the article announces any week-specific mechanic |
| Saturday | `anjo` | scaffold on the open cycle, then `provas.json` real event | the article gives useful custom copy |
| Saturday | `monstro` | scaffold on the open cycle, then `weekly_events.anjo.monstro` / API real event | the article already defines a special Monstro rule |
| Sunday (afternoon) | `presente_anjo` | scaffold | the week changes the rule or the article gives meaningful custom detail |
| Sunday (night) | `paredao_imunidade` / `paredao_indicacao` / `paredao_votacao` / `paredao_contragolpe` / `paredao_bate_volta` | scaffold on the open cycle, then real `paredoes.json` steps | the week article requires more specific copy |
| Sunday (night) | `paredao_formacao` | scaffold | the formation is non-generic (contragolpe, extra emparedado, split show, etc.) |
| Monday | `sincerao` | scaffold | the format is already known and worth surfacing early |
| Tuesday | `paredao_resultado` | scaffold | timing/copy is unusually specific |
| Tuesday | `ganha_ganha` | scaffold | the article announces a non-generic twist |
| Wednesday | `barrado_baile` | scaffold in `standard` profile | the article announces a special rule/time |

**Verification (required before commit)**:
Baseline recurring events (Sincerão, Ganha-Ganha, Barrado, Presente do Anjo, Formação do Paredão, Eliminação) are **auto-scaffolded** by the timeline builder — they do not need manual `scheduled_events` entries. To verify scaffolds appear correctly in the built timeline:
```bash
python scripts/build_derived_data.py
jq '[.[] | select(.source == "scaffold" and .week == 9)] | group_by(.category) | map({category: .[0].category, count: length})' data/derived/game_timeline.json
```

---

## Líder Transition Checklist (Thursday night)

> **The Prova do Líder is the first event of the new week.** All events before it on the same day belong to the previous week. This checklist marks the start of a new game week.

When a new Líder is crowned (typically Thursday ~22h BRT), follow these steps **in order**:

### Immediate (Thursday night / Friday morning)

1. **Scrape articles** — save `.md` copies for provenance (see [Agent: Web Scraping](#agent-web-scraping--source-collection) — **never use WebFetch on GShow URLs**):
   ```bash
   python scripts/scrape_gshow.py "<prova-do-lider-url>" -o docs/scraped/
   python scripts/scrape_gshow.py "<vip-xepa-url>" -o docs/scraped/
   python scripts/scrape_gshow.py "<dinamica-semana-url>" -o docs/scraped/  # if available
   ```

   **If the official Prova/VIP article is not out yet (live operation window):**
   - Create a provisional markdown record in `docs/scraped/` with timestamp + all known facts from the live feed/operation log.
   - Reference this provisional file in `provas.json.fontes`.
   - Use `vip_source: "api_fallback"` until the official VIP source is published.
   - Once official source arrives, replace/append sources and switch to `vip_source: "oficial_gshow"` if confirmed.

   **VIP article sourcing**: The VIP composition article is typically published within hours of the Prova do Líder result. Search the Líder's GShow profile page or the Cartola BBB section for the VIP/Xepa article. Add to `fontes` in both `paredoes.json` and `provas.json`.
   - **Required field in `provas.json` (tipo=`lider`)**: add `vip` (array with point-eligible VIP names for the round) and `vip_source`.
   - `vip_source` values:
     - `oficial_gshow` when list is confirmed by article.
     - `api_fallback` only when no reliable article/list is available yet.
     - Temporary exception: if official VIP is known but Cartola strict validation is failing due stale API extras, keep `api_fallback` until API syncs, keep official URLs in `fontes`, then switch to `oficial_gshow`.
   - Cartola safeguard uses `provas.lider.vip` as primary source and API as fallback. Unexpected extra names from API in strict weeks fail the build.

2. **Update `data/provas.json`** — add Prova do Líder results (phases, scores, placements).
   Include `fontes` with `{url, arquivo, titulo}` format pointing to scraped files.
   See templates below (standard and resistance prova formats).

   **Cronologia guardrail (required)**:
   - `cronologia` now has a Líder fallback sourced from `provas.json` (`tipo=lider`) when API role sync is delayed.
   - Minimum required fields for fallback: `tipo`, `date`, and `vencedor` (or `vencedores`).
   - After updating `provas.json`, rebuild and confirm a `lider` event exists in `data/derived/game_timeline.json` even if API is lagging.

   **Phase-by-phase live updates are allowed**:
   - If only phase 1 is known, save phase 1 immediately with a provisional `nota`.
   - Append/update phase 2 as soon as it finishes (same prova entry).
   - Keep provenance explicit for each update (provisional + official when available).

   **Split Prova do Líder (classificatórias + final ao vivo)**:
   When the Prova do Líder is split into afternoon classificatórias and evening final:
   1. Create the prova entry with `vencedor: null` after classificatórias finish (don't wait for the final).
   2. Use 2 `fases`: (1) `eliminatoria` for those eliminated in qualifying rounds, (2) `classificatoria` for the finalists vs eliminated intermediates.
   3. Add `nota_ranking` explaining the entry is intentionally partial ("Classificatórias apenas — final ao vivo pendente").
   4. After the final: fill `vencedor`, add a phase 3 with the final result, update `nota`, and remove the "pendente" note from `nota_ranking`.
   5. **Cross-reference with scheduled events (MANDATORY — do this immediately after recording the prova)**:
      - Update the `lider_classificatoria` scheduled event with result details: new `title` (who advanced), new `detail` (format, top 3, DQ if any), updated `fontes`.
      - **CRITICAL: Remove the `time` field** when updating with real results. The `time` field keeps the event as "pending" (dashed border, 🔮 prefix). Removing it triggers immediate resolution (solid border). Without this, the cronologia shows a stale "A definir" badge on an event that already happened.
      - Update the `lider` scheduled event with finalist names if known before the final.
      - Also update Friday `dinamica` if the first-eliminated feed into it.
   6. **Phase mapping**: When the classificatória has multiple sub-stages (e.g., 3 stages of "senses") but the article only names eliminations from the first sub-stage and the final classifiers, consolidate the intermediate sub-stages into a single `classificatoria` fase (pattern: "Eliminatória + finalists but not intermediate rounds" from [How to extract positions](#how-to-extract-positions-from-articles)).

   **Resistance/dupla provas — full elimination order**:
   - For resistance or elimination-format provas, record **ALL participants** in order of exit (last out = pos 1)
   - For dupla provas, both members share the same position
   - `participantes_total` = number who actually competed (total active minus excluded)
   - `excluidos: []` required even if empty
   - Reference: Prova #1 (26h resistance, 20 participants fully ranked) is the model
   - Source: GShow publishes individual "Nª dupla a deixar a prova" articles — scrape each for provenance

   **Why complete rankings matter**: Every `classificacao` position feeds into `prova_rankings.json` scoring. Unranked participants receive 0 points. Record ALL positions — not just the winner. For multi-phase provas, include both phase results so the builder can compute final positions with offsets. See [How to extract positions from articles](#how-to-extract-positions-from-articles) in the Anjo checklist for a step-by-step guide on turning article text into `classificacao` entries.

   **Scoring reference** (hardcoded in `scripts/builders/provas.py`):

   | Position | Base Points | × Líder (1.5) | × Anjo (1.0) | × Bate e Volta (0.75) |
   |----------|------------|---------------|--------------|----------------------|
   | 1st      | 10         | 15.0          | 10.0         | 7.5                  |
   | 2nd      | 7          | 10.5          | 7.0          | 5.25                 |
   | 3rd      | 5          | 7.5           | 5.0          | 3.75                 |
   | 4th      | 4          | 6.0           | 4.0          | 3.0                  |
   | 5th      | 3          | 4.5           | 3.0          | 2.25                 |
   | 6th      | 2          | 3.0           | 2.0          | 1.5                  |
   | 7th-8th  | 1          | 1.5           | 1.0          | 0.75                 |
   | 9th+     | 0.5        | 0.75          | 0.5          | 0.375                |
   | DQ       | 0          | 0             | 0            | 0                    |

   **`participantes_total` validation**: Must equal the number of active participants who competed (house count minus `excluidos`). Cross-check against the participant count for the current week.

   **Líder prova template** (add to `provas` array):
   ```json
   {
     "numero": N,
     "tipo": "lider",
     "week": W,
     "date": "YYYY-MM-DD",
     "nome": "Nª Prova do Líder — Description",
     "formato": "format_type",
     "vencedor": "Winner Name",
     "vip": ["Name1", "Name2", "Name3", "Name4"],
     "vip_source": "oficial_gshow",
     "participantes_total": 14,
     "excluidos": [],
     "nota": "Brief description of how the prova worked and who won.",
     "fases": [
       {"fase": 1, "tipo": "...", "classificacao": [{"pos": 1, "nome": "Winner"}, ...]}
     ],
     "fontes": [{"url": "...", "arquivo": "docs/scraped/...", "titulo": "..."}]
   }
   ```

   **Resistance prova template** (full elimination order):
   ```json
   {
     "numero": N,
     "tipo": "lider",
     "week": W,
     "date": "YYYY-MM-DD",
     "nome": "Nª Prova do Líder — Resistência em Duplas",
     "formato": "resistencia_duplas",
     "vencedor": "Winner Name",
     "vencedores": ["Winner1", "Winner2"],
     "vip": ["Name1", "Name2", "Name3"],
     "vip_source": "oficial_gshow",
     "participantes_total": 14,
     "excluidos": [],
     "nota": "Description of the resistance prova.",
     "fases": [
       {
         "fase": 1,
         "tipo": "resistencia_duplas",
         "classificacao": [
           {"pos": 1, "nome": "Winner1", "nota": "Última dupla (7ª)"},
           {"pos": 1, "nome": "Winner2", "nota": "Última dupla (7ª)"},
           {"pos": 3, "nome": "Name3", "nota": "6ª dupla a sair"},
           {"pos": 3, "nome": "Name4", "nota": "6ª dupla a sair"},
           {"pos": 13, "nome": "NameN", "nota": "1ª dupla a sair"}
         ]
       }
     ],
     "fontes": [{"url": "...", "arquivo": "docs/scraped/...", "titulo": "..."}]
   }
   ```

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

5. **Rebuild + commit + publish** — follow [Commit & Publish Workflow](#commit--publish-workflow):
   ```bash
   python scripts/build_derived_data.py
   git add data/ docs/MANUAL_EVENTS_AUDIT.md docs/SCORING_AND_INDEXES.md
   git commit -m "week N Líder transition (Name)"
   # Then push origin/main and trigger deploy if needed — see Commit & Publish Workflow
   ```

### API auto-detects (no manual action needed)

These are picked up automatically by `build_daily_roles()` from snapshots:
- **Líder role** — appears in `characteristics.roles` (usually within hours of the ceremony)
- **VIP/Xepa groups** — appears in `characteristics.group` (fallback/audit source; official VIP scoring source is `provas.lider.vip`)
- **Roles cleared briefly** during transition (roles empty for a few hours → normal)

### Later (when Líder term ends)

6. **Week boundary handling (confirmed + inferred)**:
   - `scripts/data_utils.py` now computes **effective** boundaries:
     - confirmed boundaries from static `WEEK_END_DATES`
     - inferred boundary for an open week when week `N+1` already has dated signals in data (e.g., `scheduled_events`, `provas`, `paredoes`, `power_events`).
   - This avoids getting "stuck" in the old week when the next cycle is already dated in operations data, even if a new Líder is not fully confirmed yet.
   - Practical rule: the week should naturally roll once next-week entries are dated; no emergency hardcode is needed for day-to-day ops.

7. **Still keep `WEEK_END_DATES` curated for history**:
   - After the next Líder cycle is confirmed, append the final boundary date to static `WEEK_END_DATES` as archival truth.
   - Example: if week 8 effectively closed on `2026-03-13` from next-week signals, later confirm and persist that boundary in `WEEK_END_DATES`.

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

Additional week-boundary sanity check:
```bash
python - <<'PY'
import sys
sys.path.append('scripts')
from data_utils import get_week_number
for d in ["2026-03-13", "2026-03-14", "2026-03-17"]:
    print(d, "-> week", get_week_number(d))
PY
```
Expected behavior: dates after the inferred boundary roll to the next week (no stale week lock).

---

## Anjo / Monstro Update Checklist (Saturday)

When the Prova do Anjo results are published (typically Saturday afternoon article + Saturday night Monstro choice):

### 1. Scrape article(s) + collect source images

> **Do NOT use WebFetch or AI web tools for GShow URLs** — they will fail. See [Agent: Web Scraping & Source Collection](#agent-web-scraping--source-collection).

```bash
python scripts/scrape_gshow.py "<prova-do-anjo-url>" -o docs/scraped/
python scripts/scrape_gshow.py "<castigo-do-monstro-url>" -o docs/scraped/  # if separate article
```

If broadcast screenshots or Twitter screenshots are available (e.g., duel scores, bracket results), move them from repo root to `docs/scraped/` with descriptive names and create a Twitter archive `.md` file. See [Source images](#source-images-broadcast-screenshots-twitterx).

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

**`nota_ranking`**: When the source only reveals finalists, classificados, or the winner, add a short `nota_ranking` explaining exactly what is missing. This marks the prova as intentionally partial, keeps the limitation explicit in the data, and suppresses the generic completeness warning during `build_derived_data.py`.

**Scoring**: Every position feeds into `prova_rankings.json`. Record ALL placements, not just the winner. The build will **warn** if `participantes_total` doesn't match the number of ranked participants, and **hard-fail** if the winner isn't at position 1. See scoring table in [Líder Checklist](#líder-transition-checklist-thursday-night).

**`participantes_total` validation**: Must equal the number of active participants who competed (house count minus `excluidos`). Cross-check against the participant count for the current week.

**Excluded**: Líder always excluded (doesn't play). For dual leadership weeks, **both Líderes** are excluded (reduces field by 2). Others excluded by sorteio, punishment, etc.

#### How to extract positions from articles

Articles rarely give clean rankings. Follow this process to turn article text into `classificacao` entries:

**Step 1 — Count participants.** Active house count minus `excluidos` = `participantes_total`. All of them must appear in at least one phase's `classificacao`.

**Step 2 — Identify what the article tells you.** Typical patterns:
- Names of eliminated participants per round
- Names of finalists
- Winner

**Step 3 — Deduce missing positions.** If the article names 6 eliminated in round 1 and 3 finalists, the remaining participants (total minus eliminated minus finalists) were eliminated in intermediate rounds. Use tied positions for them.

**Step 4 — Choose phase structure.** Use the minimum number of phases that captures all known data:

| Article gives you | Use this structure |
|---|---|
| Full per-round results | One fase per round, each with complete classificacao |
| Eliminatória results + final winner only | 2 fases: (1) eliminatória pass/fail, (2) winner-only final |
| Eliminatória + finalists but not intermediate rounds | 2 fases: (1) eliminatória, (2) classificatória with finalists ranked + intermediates tied |
| Only the winner | 1 fase with winner at pos 1 (other participants get `null` — no ranking points) |

**Step 5 — Assign positions.** Rules:
- **Survivors of a pass/fail phase**: all share `pos: 1` (they all "won" that phase)
- **Eliminated together**: all share the same position (e.g., 6 eliminated share `pos: 7` if 6 advanced)
- **Unknown ordering within a group**: use `"tied": true` on each entry
- **Phase offsets (2-phase provas)**: the builder auto-adds `n_phase2` to phase 1 positions, so phase 1 eliminated at `pos: 7` become final position `7 + 6 = 13` (if phase 2 has 6 entries)

**Example** — 12 participants, article says "6 eliminated in round 1; finalists were Milena, Samira, Leandro; Milena won":
```json
{"fase": 1, "tipo": "eliminatoria", "classificacao": [
  {"pos": 1, "nome": "Milena", "nota": "Avançou"},
  {"pos": 1, "nome": "Samira", "nota": "Avançou"},
  {"pos": 1, "nome": "Leandro", "nota": "Avançou"},
  {"pos": 1, "nome": "Ana Paula Renault", "nota": "Avançou"},
  {"pos": 1, "nome": "Babu Santana", "nota": "Avançou"},
  {"pos": 1, "nome": "Solange Couto", "nota": "Avançou"},
  {"pos": 7, "nome": "Breno", "nota": "Eliminado na eliminatória"},
  {"pos": 7, "nome": "Chaiany", "nota": "Eliminada na eliminatória"},
  {"pos": 7, "nome": "Gabriela", "nota": "Eliminada na eliminatória"},
  {"pos": 7, "nome": "Jordana", "nota": "Eliminada na eliminatória"},
  {"pos": 7, "nome": "Juliano Floss", "nota": "Eliminado na eliminatória"},
  {"pos": 7, "nome": "Marciele", "nota": "Eliminada na eliminatória"}
]},
{"fase": 2, "tipo": "classificatoria", "classificacao": [
  {"pos": 1, "nome": "Milena"},
  {"pos": 2, "nome": "Samira", "nota": "Finalista", "tied": true},
  {"pos": 2, "nome": "Leandro", "nota": "Finalista", "tied": true},
  {"pos": 4, "nome": "Ana Paula Renault", "nota": "Eliminada na classificatória", "tied": true},
  {"pos": 4, "nome": "Babu Santana", "nota": "Eliminado na classificatória", "tied": true},
  {"pos": 4, "nome": "Solange Couto", "nota": "Eliminada na classificatória", "tied": true}
]}
```

This produces final rankings: Milena 1st (10pts), Samira/Leandro tied 2nd (7pts each), Ana Paula/Babu/Solange tied 4th (4pts each), 6 eliminated share 13th (0.5pts each via offset: pos 7 + 6 phase2 entries).

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

**Monstro**: API auto-detects the role. Fill `monstro` name from article or API.
- `monstro_tipo`: descriptive name of the castigo (e.g., "Monstro Movendo Areia", "Castigo do Monstro — Fantasia de abóbora")
- `monstro_motivo`: Anjo's stated reason + consequences (e.g., loss of estalecas, VIP→Xepa)
- Note: GShow sometimes publishes a separate "Castigo do Monstro" article — scrape it if available and add to `fontes`

**Cartola `monstro_retirado_vip`**: Auto-detected. If the Monstro recipient was in VIP in the previous snapshot, the -5 penalty is automatically applied. No manual entry needed.

### 4. Update scheduled events (do NOT delete)

**Update** the `scheduled_events` for this date's `anjo` and `monstro` entries with the real results (winner name, castigo details). **Do NOT remove them.**

Why: Anjo timeline events have a `provas.json` fallback (like Líder), and Monstro has a `weekly_events.anjo.monstro` fallback. These create real timeline entries immediately after updating `provas.json` and `manual_events.json` — no need to wait for the API. However, deleting the scheduled events prematurely removes the safety net if the fallback fails for any reason.

**What to do**:
- Update `title` to include the result (e.g., `"Prova do Anjo — Breno vence"`)
- Update `detail` with what happened
- Update `fontes` with the scraped article URL
- Keep the entries in `scheduled_events` — auto-dedup will suppress them once the API captures the new roles. The `time` field is ignored for past events (automatic lifecycle), so removing it is optional

**When to clean up**: Remove past scheduled events during the **next week's setup** (Líder Transition Checklist), not on the same day they happen. By then, the API will have captured the roles and the auto-dedup makes the scheduled entries invisible anyway.

### 5. Rebuild + commit + publish

Follow [Commit & Publish Workflow](#commit--publish-workflow):
```bash
python scripts/build_derived_data.py
git add data/ docs/MANUAL_EVENTS_AUDIT.md docs/SCORING_AND_INDEXES.md
git commit -m "Nª Prova do Anjo (Winner) + Monstro (Name)"
# Then push origin/main and trigger deploy if needed — see Commit & Publish Workflow
```

### Timeline fallback system (how Cronologia stays complete)

The Cronologia do Jogo timeline has **multiple sources per event type**. When the API hasn't captured a snapshot yet, fallbacks from manual data ensure the timeline is never missing entries:

| Category | Primary source | Fallback source | When fallback kicks in |
|----------|---------------|-----------------|----------------------|
| **Líder** | API auto-detection | `provas.json` (tipo=lider) | API hasn't captured role change yet |
| **Anjo** | API auto-detection | `provas.json` (tipo=anjo) | API hasn't captured role change yet |
| **Monstro** | API auto-detection | `weekly_events.anjo.monstro` | API hasn't captured role change yet |
| **Imune** | API auto-detection | `paredoes.json` (formacao.imunizado) | Covered by `paredao_imunidade` ceremony step |
| **Sincerão** | `weekly_events.sincerao` | — | Manual-only (fill after Monday show) |
| **Ganha-Ganha** | `weekly_events.ganha_ganha` | — | Manual-only (fill after Tuesday show) |
| **Barrado** | `power_events` (barrado_baile) | — | Manual-only (fill after Wednesday) |
| **Presente Anjo** | `weekly_events.anjo.escolha` | — | Manual-only (fill after Sunday almoço) |
| **Paredão formation** | `paredoes.json` (indicados_finais) | — | Ceremony sub-steps auto-generated |
| **Paredão resultado** | `paredoes.json` (resultado) | — | Fill after elimination |

**Key**: Once you update `provas.json` and `manual_events.json`, rebuild creates real timeline events immediately — no need to wait for the API. The scheduled_events (if any) are auto-deduped by `(date, category)`.

### API auto-detects (no manual action needed)

- **Anjo role** — `characteristics.roles` contains `"Anjo"`
- **Monstro role** — `characteristics.roles` contains `"Monstro"`
- Both appear in `auto_events.json` and `roles_daily.json` after rebuild
- **Timeline fallback**: If the API hasn't detected the role yet, `provas.json` (Anjo) and `weekly_events.anjo.monstro` (Monstro) create real timeline entries automatically

### Note on Cartola articles

GShow publishes Cartola-specific recap articles for Líder, Anjo, VIP, Monstro, etc. (e.g., "Alberto Cowboy soma pontos no Cartola BBB"). These are **informational/provenance only** — all Cartola points are auto-detected by `build_derived_data.py`. Optionally scrape and add to `fontes` in `provas.json` or `paredoes.json` for traceability.

---

## Presente do Anjo Checklist (Sunday afternoon)

The Presente do Anjo happens Sunday afternoon (~14h-17h BRT). The Anjo invites 2-3 guests for an Almoço do Anjo and makes a choice: watch a family video OR gain a 2nd immunity to give at formation.

**Key fact**: As of W10, every Anjo has chosen `video_familia` (no one has ever used the 2nd immunity).

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

### 5. Rebuild + commit + publish

Follow [Commit & Publish Workflow](#commit--publish-workflow):
```bash
python scripts/build_derived_data.py
git add data/ docs/MANUAL_EVENTS_AUDIT.md docs/SCORING_AND_INDEXES.md
git commit -m "Presente do Anjo W{N} (Name chose video/immunity)"
# Then push origin/main and trigger deploy if needed — see Commit & Publish Workflow
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
| W7 | Alberto Cowboy | video_familia | Gabriela, Jordana, Marciele | Jonas Sulzbach |
| W8 | Milena | video_familia | Ana Paula Renault, Juliano Floss, Samira | Ana Paula Renault |
| W9 | Breno | video_familia | Samira, Juliano Floss, Milena | Samira |
| W10 | Leandro | video_familia | Chaiany, Juliano Floss, Solange Couto | Solange Couto |

**Pattern**: 10/10 Anjos chose family video. The 2nd immunity has never been used.

---

## Paredão Formation Checklist (Sunday)

When the Paredão formation airs (Sunday ~22h45 BRT live show):

**Split-formation paredões**: Some weeks split the formation across two live shows (e.g., Saturday dynamic + Sunday completion). In that case:
- **Saturday**: Scrape the dynamic article, fill `paredoes.json` with partial data (group structure, initial nominees in `indicados_finais` with `"como": "Dinâmica (...)"`), add fonte, update the Saturday dynamic's scheduled event in `manual_events.json → scheduled_events` with the real result (step 4b), rebuild, commit.
- **Sunday**: Complete the formation (Máquina do Poder, Líder indication, house votes, contragolpe, Bate e Volta). Update `indicados_finais` to reflect the final state, add power events to `manual_events.json`, scrape the Sunday article, rebuild, commit.
- Steps 1–5 below apply to the **Sunday completion**. For the Saturday step, do steps 1, 2 (partial), 4b, and 5.

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
    "anjo_escolha": "Abriu mão da 2ª imunidade para ver vídeo da família",
    "imunizado": {"por": "Who gave immunity", "quem": "Who received"}
  },
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

**Dual Líderes consensus**: When dual Líderes indicate in consensus, record as a single `indicacao` power_event with `"actor": "Name1 + Name2"` (display string) and `"actors": ["Name1", "Name2"]` (array for edge creation). Fill `formacao.indicado_lider` as normal. This produces 1 timeline row + 2 correct relationship edges.

**Consenso Anjo + Monstro**: When the week's dynamic requires Anjo and Monstro to consensus-nominate:
- If consensus reached: add a `power_event` with `"type": "consenso_anjo_monstro"`, `"actor": "Anjo + Monstro"`, `"actors": ["Anjo Name", "Monstro Name"]`, `"target": "Nominee"`. Add to `indicados_finais` with `"como": "Consenso Anjo+Monstro"`.
- If no consensus: both Anjo and Monstro go to paredão. Add each to `indicados_finais` with `"como": "Consenso falhou"`. No `power_event` needed.

**Two immunity fields** (both must be filled at formation):
- `weekly_events[N].anjo.imunizado` = simple string name (used for scoring edges)
- `paredoes[N].formacao.imunizado` = object `{"por": "Anjo Name", "quem": "Immunized Name"}` (used for display)

### 4. Update `data/provas.json` (if Bate e Volta happened)

Add a Bate e Volta prova entry with the results.

### 4b. Update scheduled events in Cronologia

If `data/manual_events.json → scheduled_events` has entries for events that just happened (e.g., a `dinamica` for the week's dynamic, `monstro` for the Castigo), update them with the real result:
- Replace the placeholder `title` and `detail` with what actually happened
- Add the formation article URL to `fontes`
- **Remove the `time` field** when filling real results. The `time` field keeps same-day events pending (🔮 + dashed borders). If a build runs between the event and the 06:00 BRT game-date flip, the event will incorrectly show as pending even though it already happened. Removing `time` ensures immediate resolution on the event date

The `paredao_formacao` sub-step is auto-generated from `paredoes.json`, but custom dynamics and other scheduled events must be manually updated.

### 5. Rebuild + commit + publish

Follow [Commit & Publish Workflow](#commit--publish-workflow):
```bash
python scripts/build_derived_data.py
git add data/ docs/MANUAL_EVENTS_AUDIT.md docs/SCORING_AND_INDEXES.md
git commit -m "Nº Paredão formation"
# Then push origin/main and trigger deploy if needed — see Commit & Publish Workflow
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

### Automated Pipeline (Primary Path)

The LXC handles Votalhada collection automatically when `--votalhada --votalhada-auto-update` flags are enabled on the systemd timer.

**Architecture:**
```
systemd timer (every 15 min)
  → schedule_data_fetch.py --votalhada --votalhada-auto-update
    1. Detects active paredão (paredoes.json → status: "em_andamento")
    2. Bootstraps polls.json entry if missing (get_final_nominees extracts nominees after Bate e Volta)
    3. fetch_votalhada_images.py --paredao N --dedupe size+sha256
    4. If new images detected:
       → deploy/votalhada_claude_update.sh <N> <images_dir>  (gitignored, LXC-only)
         → Claude Code headless reads consolidado card via vision
         → Updates polls.json (consolidado, plataformas, serie_temporal)
    5. git commit + push + trigger deploy
```

**What happens automatically for a brand-new paredão:**
1. Paredão formation recorded in `paredoes.json` (Sunday night checklist)
2. Next scheduler cycle detects `em_andamento` → `_bootstrap_polls_entry()` creates skeleton in `polls.json` with correct nominees
3. `fetch_votalhada_images.py` attempts to download from Votalhada (exits gracefully with code 3 if page doesn't exist yet)
4. When Votalhada publishes the post (typically Monday morning), images are captured and Codex extracts values
5. Each subsequent Votalhada update is captured, validated, and processed automatically through elimination day
6. **Auto-stop**: once the 21:00 BRT capture on elimination day is recorded in `serie_temporal`, the scheduler stops fetching Votalhada images for that paredão (Votalhada's last update is always 21:00 BRT)

**Pipeline**: Codex (gpt-5.4) extracts → deterministic validation (platform sums, CPF total, ESTIMATIVA formula, monotonic series) → Claude Opus verifies → apply to polls.json. Legacy Claude-as-extractor kept as fallback.

**Votalhada card validation math** (used to catch extraction errors):
- Platform percentages sum ~100 per platform
- Média = simple_avg(YouTube, Twitter, Instagram)
- CPF votos sum = YouTube + Twitter + Instagram votos
- Total de Votos = Sites votos + CPF votos sum
- ESTIMATIVA = 0.3 × Sites + 0.7 × Média
- Vote-weighted consolidado recomputes from platform rows

**Monitoring:**
```bash
# Follow live
journalctl -u bbb26-fetch -f

# Filter for votalhada lines today
journalctl -u bbb26-fetch --since today | grep -i votalhada

# Check latest polls.json update
ssh BBB "sudo su - bbb26 -c 'cd ~/BBB26 && python3 -c \"import json; p=json.load(open(\\\"data/votalhada/polls.json\\\")); e=p[\\\"paredoes\\\"][-1]; print(f\\\"P{e[\\\\\\\"numero\\\\\\\"]}: {e.get(\\\\\\\"data_coleta\\\\\\\",\\\\\\\"no coleta\\\\\\\")} — {len(e.get(\\\\\\\"serie_temporal\\\\\\\",[])) } series rows\\\")\"'"

# Quick status check
journalctl -u bbb26-fetch -n 5 --no-pager
```

**Manual trigger (immediate cycle):**
```bash
ssh BBB "sudo su - bbb26 -c 'cd ~/BBB26 && python3 scripts/schedule_data_fetch.py --once --run-now --votalhada --votalhada-auto-update --build --trigger-deploy 2>&1'"
```

**Troubleshooting:**

| Problem | Cause | Fix |
|---------|-------|-----|
| No images fetched | Votalhada post not published yet | Wait — scheduler retries every 15 min (exit code 3 = not found yet) |
| Images fetched but no polls.json update | Claude headless failed or no new data | Check `journalctl -u bbb26-fetch -n 100`, run Claude script manually |
| Wrong nominees in polls.json | Bate e Volta not recorded in paredoes.json | Update paredoes.json first, delete wrong polls.json entry, re-bootstrap |
| All images "Skipped duplicate" | Votalhada hasn't updated since last capture | Normal — dedup working correctly |
| Claude reads wrong values | Low-res image or column mismatch | Verify with vision in conversation, manually correct polls.json |

### Manual Fallback (when automation is unavailable)

If the LXC automation is unavailable, use manual fetches + Claude vision in a conversation:

**Vote-window baseline (for trend projections):**
- Voting usually opens on Sunday/Monday after the live show.
- Voting usually closes around **Tuesday 22:45 BRT** (official result shortly after).
- Near finals, this close window can shift. In those weeks, set an explicit close override in `data/votalhada/polls.json` for that paredão:
  - `fechamento_votacao` (ISO, with timezone), e.g. `"2026-04-14T23:15:00-03:00"`.
  - If missing, dashboards assume Tuesday 22:45 BRT by default.

### 1. Fetch poll images

```bash
python scripts/fetch_votalhada_images.py --paredao N
```

**URL pattern**: `https://votalhada.blogspot.com/{year}/{month}/pesquisaN.html`. Auto-derived from `paredoes.json` `data_formacao`. Falls back to current BRT month if no entry exists.

Images saved to `data/votalhada/YYYY_MM_DD/` with datetime suffix (e.g., `consolidados_2026-03-22_21-05.png`).

### 2. Extract values with Claude vision

In a Claude Code conversation, read the consolidado card and update polls.json:
1. Read the latest `consolidados_5_*.png` (or `consolidados_6_*.png` for series) with the Read tool
2. Extract: card date/time, platform Média rows (Sites, YouTube, Twitter, Instagram + vote counts), ESTIMATIVA VOTALHADA row, total votes
3. Update `data/votalhada/polls.json`:
   - recompute `consolidado` with the **legacy vote-weighted formula** (platform percentages weighted by each platform's vote count)
   - overwrite `plataformas` with the latest platform rows
   - append `serie_temporal` with the **displayed** ESTIMATIVA / VARIAÇÃO DAS MÉDIAS values (dedupe by `hora`)
   - keep post-10/mar/2026 polls on `metodologia.modo = manual_vision_legacy_weighted`

### 3. Rebuild, commit, publish

```bash
python scripts/build_derived_data.py
git add data/ && git commit -m "public: votalhada P{N} update"
git push origin main
gh workflow run daily-update.yml
```

### Data update rules

- `serie_temporal`: append-only by `hora` — never delete existing rows
- `serie_temporal` stores the **displayed 0,3 x 0,7 ESTIMATIVA VOTALHADA** values after 10/mar/2026
- `consolidado`: overwrite with the **legacy vote-weighted average** recalculated from `plataformas`
- `plataformas`: overwrite with the latest platform rows and vote counts
- `data_coleta`: overwrite with latest capture timestamp
- `predicao_eliminado`: participant with highest consolidado %

### Paredão Falso ("Quem SALVAR?") handling

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

### Verify name matching

Votalhada uses short names. Always match to API names:

| Votalhada Shows | Use in polls.json |
|-----------------|-------------------|
| "Aline" | "Aline Campos" |
| "Ana Paula" | "Ana Paula Renault" |
| "Cowboy" / "A Cowboy" | "Alberto Cowboy" |
| "Sol" | "Sol Vega" |
| "Floss" | "Juliano Floss" |

### Rebuild, commit, publish + deploy

**This step is critical** — without it, poll data won't appear on the live site (index.qmd AND paredao.qmd both need a fresh deploy).

```bash
# 1. Rebuild derived data
python scripts/build_derived_data.py

# 2. Verify locally (recommended — catches rendering issues before deploy)
quarto render paredao.qmd    # Check "Enquetes" section renders correctly

# 3. Commit
git add data/ && git commit -m "votalhada polls paredão N"

# 4. Push to main
git push origin main

# 5. Deploy (REQUIRED — push alone does NOT trigger a render)
gh workflow run daily-update.yml
```

**Common mistake**: Pushing to `main` without dispatching the workflow. The cron only deploys when the API data hash changes — manual data updates (polls.json, paredoes.json) require explicit `gh workflow run`.

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

### 1b. Update `data/manual_events.json` → `participants` (required for real elimination)

For a normal (non-fake) elimination, register the participant exit entry:

```json
{
  "participants": {
    "Name": {
      "status": "eliminado",
      "exit_date": "YYYY-MM-DD",
      "paredao_numero": N,
      "fontes": ["<resultado-url>"]
    }
  }
}
```

- Use `status: "eliminado"` or `status: "eliminada"` (both accepted).
- For `desistente`/`desclassificado`, the same shape applies: `status` + `exit_date` + `fontes`.
- **Do not use legacy keys** like `date`, `week`, `paredao`, `detail` in `participants` — they are not the operational contract for Cartola exit scoring.
- **Paredão Falso**: do not add participant exit in `participants` (the person remains active and gets `quarto_secreto` points from `paredoes.json`).
- **Why this is mandatory**: without this entry, Cartola may keep the eliminated participant as active and miss the `eliminado` (−20) event.

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

### 2b. Rebuild + Cartola + model sanity check (required before commit)

**How the poll model updates automatically:**

Adding `resultado_real` to a poll entry is the ONLY manual step. Everything else recalculates:

| Component | What happens | Where |
|-----------|-------------|-------|
| **Precision weights** | `calculate_precision_weights()` recalculates RMSE per platform and inverse-RMSE² weights using ALL finalized polls | `data_utils.py` |
| **Back-test (LOO)** | `backtest_precision_model()` re-runs leave-one-out cross-validation on all finalized polls | `data_utils.py` |
| **Vote prediction** | `build_derived_data.py` → `vote_prediction.json` uses updated weights for the current paredão | `builders/vote_prediction.py` |
| **Archive page** | `paredoes.qmd` renders the back-test table and methodology text dynamically at build time — no hardcoded text to update | `paredoes.qmd` |
| **Paredão page** | `paredao.qmd` renders ⚖️ Volume, 🔬 Fórmula, and 📚 Histórico insights dynamically | `paredao.qmd` |

**Nothing is hardcoded** — weights, RMSE values, back-test results, and methodology text all derive from the data. Just add `resultado_real`, rebuild, and verify below.

**Three models to compare after each result**:
- **Votalhada 70/30** (their displayed formula): `0.3 × Sites + 0.7 × avg(YouTube, Twitter, Instagram)` — gives Sites 30% fixed weight
- **Votalhada ponderada** (our consolidado): weighted by vote count per platform — gives Sites even more weight (typically largest volume)
- **Nosso Modelo** (precision-weighted): `inverse-RMSE²` weights derived from historical accuracy — Sites typically gets ~5% (historically least accurate)

```bash
python scripts/build_derived_data.py

# Normal elimination: eliminated participant must have week-N "eliminado" and active=false
jq '.leaderboard[] | select(.name=="Name") | {name,active,week_events:(.events|map(select(.week==N)))}' data/derived/cartola_data.json

# Paredão falso: selected participant must have "quarto_secreto" (not "eliminado")
jq '.leaderboard[] | select(.name=="Name") | {name,active,week_events:(.events|map(select(.week==N)))}' data/derived/cartola_data.json
```

Expected:
- Normal elimination: event list includes `["eliminado", -20, "YYYY-MM-DD"]`, and `active: false`.
- Paredão Falso: event list includes `["quarto_secreto", 40, "YYYY-MM-DD"]`, and participant remains active.

Model sanity check (Votalhada + Nosso Modelo, after `resultado_real` update):

```bash
python - <<'PY'
import json
import sys
from pathlib import Path

sys.path.append("scripts")
from data_utils import calculate_precision_weights, backtest_precision_model

polls = json.loads(Path("data/votalhada/polls.json").read_text(encoding="utf-8"))
finalized = [p for p in polls.get("paredoes", []) if p.get("resultado_real")]
precision = calculate_precision_weights(polls)
backtest = backtest_precision_model(polls) or {}
agg = (backtest.get("aggregate") or {})

print({
    "finalized_with_resultado_real": len(finalized),
    "precision_n_paredoes": precision.get("n_paredoes"),
    "weights": precision.get("weights"),
    "model_correct": agg.get("model_correct"),
    "votalhada_correct": agg.get("consolidado_correct"),
    "n_paredoes_backtest": agg.get("n_paredoes"),
})
PY
```

Expected:
- `precision_n_paredoes` equals `finalized_with_resultado_real`
- `n_paredoes_backtest` equals `finalized_with_resultado_real`
- `weights` are non-empty when enough finalized paredões exist

**Back-test verification (required after every `resultado_real` update)**:

After rebuild, verify the back-test updated correctly and review the weight shifts. This is important because each new result recalibrates the entire model — RMSE per platform changes, weights shift, and the leave-one-out back-test re-runs across ALL finalized paredões.

```bash
python - <<'PY'
import json, sys, copy
from pathlib import Path
sys.path.append("scripts")
from data_utils import calculate_precision_weights, backtest_precision_model

polls = json.loads(Path("data/votalhada/polls.json").read_text(encoding="utf-8"))

# Current weights
precision = calculate_precision_weights(polls)
backtest = backtest_precision_model(polls) or {}
agg = backtest.get("aggregate", {})

print("=== PRECISION WEIGHTS ===")
for plat, w in sorted(precision["weights"].items(), key=lambda x: -x[1]):
    print(f"  {plat:12s}: {w:.1%}  (RMSE {precision['rmse'][plat]:.2f})")

print(f"\n=== BACK-TEST (LOO, {agg.get('n_paredoes')} paredões) ===")
print(f"  Nosso Modelo:  {agg.get('model_correct')}/{agg.get('n_paredoes')}")
print(f"  Votalhada:     {agg.get('consolidado_correct')}/{agg.get('n_paredoes')}")
PY
```

Check:
- All 4 platforms have non-zero weights that sum to ~100%
- `model_correct` and `consolidado_correct` are plausible (model should be ≥ votalhada)
- RMSE values are in a reasonable range (lower = more accurate platform)
- If a platform's RMSE changed significantly, investigate whether the new paredão was an outlier for that platform

**What the back-test measures**: Leave-one-out cross-validation — for each finalized paredão, the model is retrained on all OTHER paredões and tested on the held-out one. This avoids overfitting and gives an honest accuracy estimate. A perfect model score means the precision-weighting strategy is robust across all historical data, not just fitted to it.

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
    "informacao": "Content of the privileged information if disclosed in the article",
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
| `informacao` | String or `null` | Content of privileged info when the article reveals it, even if the participant chose the cash instead |

If the participant takes the money, keep `decisao.escolha` / `decisao.abriu_mao` aligned with the cash outcome and still fill `informacao` whenever gshow reveals the hidden message to the audience after the choice.

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

**Reminder**: Every `power_event` entry **must** include a `fontes` array with the source URL. The audit (`build_derived_data.py`) will hard-fail if `fontes` is missing.

### 4. Rebuild, verify cronologia, commit, publish + deploy

```bash
# 1. Rebuild derived data
python scripts/build_derived_data.py

# 2. Verify cronologia has the new events
python3 -c "
import json
gt = json.load(open('data/derived/game_timeline.json'))
events = gt.get('events', gt) if isinstance(gt, dict) else gt
today = [e for e in events if isinstance(e, dict) and e.get('date') == 'YYYY-MM-DD']
for e in today:
    print(f'  {e.get(\"category\"):25s} | {e.get(\"title\",\"\"):50s} | source={e.get(\"source\")}')
"
# Expected: paredao_resultado + ganha_ganha + power_events all present
# If missing: check that manual_events.json and paredoes.json are saved correctly

# 3. Commit
git add data/ docs/MANUAL_EVENTS_AUDIT.md docs/SCORING_AND_INDEXES.md
git commit -m "public: data: paredão N result + ganha-ganha"

# 4. Push + deploy
git pull --rebase origin main && git push origin main
gh workflow run daily-update.yml
```

**Always verify the cronologia after rebuild** — it's the single source of truth for the game timeline on index.qmd and evolucao.qmd. Missing events here means they won't appear on the site.

**Cronologia display order**: Latest event on top within each day (consistent with newest-first for weeks and dates). Controlled by `CATEGORY_ORDER` in `scripts/builders/timeline.py` (lower number = earlier in the day = displayed at bottom).

Expected display order (top → bottom):

```
Elim night: ganha_ganha_escolha → veto_ganha_ganha → ganha_ganha → paredao_resultado  ← top (latest)
Live show:  barrado_baile → sincerao
Ceremony:   paredao_formacao → paredao_bate_volta → paredao_contragolpe →
            dinamica → paredao_votacao → paredao_indicacao → paredao_imunidade
Afternoon:  presente_anjo → big_fone
Morning:    anjo → monstro → lider
Meta:       saida → entrada                                                            ← bottom (earliest)
```

**Note**: Presente do Anjo happens early in the day (Almoço do Anjo, afternoon) — it just gets shown on the live TV show later. The `CATEGORY_ORDER` reflects when the event actually occurs, not when it airs.

If events appear in the wrong order, check `CATEGORY_ORDER` values.

**Cronologia detail text**: The timeline builder auto-generates details from structured data:
- `paredao_resultado`: from `paredoes.json` resultado (e.g., "Breno eliminado (58.96%)")
- `ganha_ganha`: built from `veto`/`decisao` fields (e.g., "Marciele vetou Samira; Jordana escolheu R$ 20 mil")
- `power_events`: uses the `detail` field directly
- Scaffolds (generic placeholders) are suppressed when real events exist for the same (date, category) or (week, category) for singletons

### What auto-updates after rebuild + deploy

Once `build_derived_data.py` runs and the site deploys, the following update **automatically** — no manual action needed:

| What | Where | Details |
|------|-------|---------|
| **Cartola BBB points** | `cartola_data.json` → `cartola.qmd` | For normal paredão: `emparedado` (−15), `eliminado` (−20), `nao_eliminado_paredao` (+20), plus `nao_emparedado` (+10)/`nao_recebeu_votos` (+5) when applicable. For fake: selected participant gets `quarto_secreto` (+40). |
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
| **paredoes.qmd summary table** | "Eliminado(a)" (normal) | Same column; fake week marked by 🔮 in "Nº" |
| **paredoes.qmd tab label** | "7º Paredão (Breno)" | "7º Paredão Falso (Breno)" |
| **paredoes.qmd history rows** | "Elim." red | "🔮 Q. Secreto" purple |
| **paredao.qmd precision label** | "(eliminado)" | "(→ quarto secreto)" |
| **paredao.qmd result cards** | "ELIMINADO" red border | "🔮 Q. SECRETO" red border |
| **votacao.qmd health cards** | 🎯/🛡️ icons, "eliminação" language | ⬆️/⬇️ icons, "salvação" language |
| **votacao.qmd editorial** | "forçar eliminação" | "forçar salvação" |
| **Cartola points** | `eliminado` (−20) | `quarto_secreto` (+40) |

Generic analytical text uses "mais votado" instead of "eliminado" across all pattern/accuracy displays (works for both types).

**No manual overrides needed** — the `paredao_falso: true` flag drives all display logic.

### Quarto Secreto Return

When a participant returns from Quarto Secreto:
- **API auto-detects** the `Imune` role — no manual participant entry needed.
- The returned participant has full queridômetro data (reactions given and received).
- `weekly_events[N].quarto_secreto` schema (see W7 data for reference): `{"retorno_date": "YYYY-MM-DD", "convidado": "Name", "escolha": "..."}`.
- `quarto_secreto_convite` edge (+0.20) is auto-created from `weekly_events[N].quarto_secreto.convidado` in the relations builder.
- Immunity lasts for the next paredão formation only.

---

## Barrado no Baile Checklist (Wednesday)

Use this checklist when the Líder (or liderança dupla) bars someone from the Festa do Líder.

### 0. Scrape the source article

```bash
python scripts/scrape_gshow.py "<barrado-no-baile-url>" -o docs/scraped/
```

Example source (liderança dupla):
- `https://gshow.globo.com/realities/bbb/bbb-26/festa/noticia/barrado-no-baile-ana-paula-renault-e-escolhida-pelos-lideres-jonas-sulzbach-e-alberto-cowboy.ghtml`

If the task description and the source URL/title disagree, trust the **article title/body** and update the event the source actually describes. Wednesday `festa/` links often describe **Barrado no Baile**, even when a request casually says "ganha-ganha".

### 1. Add/update `data/manual_events.json` → `weekly_events[N].barrado_baile` + `power_events`

First, keep the week-level mirror in sync:

```json
{
  "barrado_baile": [
    {
      "date": "YYYY-MM-DD",
      "lider": "Lider A",
      "alvo": "Emparedado"
    }
  ]
}
```

Then add one `barrado_baile` power event:

```json
{
  "date": "YYYY-MM-DD",
  "week": N,
  "type": "barrado_baile",
  "actor": "Lider A + Lider B",
  "actors": ["Lider A", "Lider B"],
  "target": "Emparedado",
  "source": "Barrado no Baile",
  "detail": "Líder(es) escolheu(ram) X para ficar fora da festa e enfrentar desafio.",
  "fontes": ["<barrado-no-baile-url>"],
  "impacto": "negativo",
  "origem": "manual",
  "visibility": "public",
  "awareness": "known"
}
```

Single-líder case: keep only `actor: "Name"` (the optional `actors` array is mainly for consensus/duo actions).
Keep `weekly_events[].barrado_baile` updated because `scripts/update_programa_doc.py` renders `docs/PROGRAMA_BBB26.md` from week-level metadata, while the timeline/scoring layers consume the `power_events` entry.

### 2. Rebuild + validate

```bash
python scripts/build_derived_data.py
python scripts/update_programa_doc.py
```

### 3. Verify data + cronologia

```bash
# Verify the week mirror was stored as expected
jq '.weekly_events[] | select(.week==N) | .barrado_baile' data/manual_events.json

# Verify the power event was stored as expected
jq '.power_events[] | select(.type=="barrado_baile" and .date=="YYYY-MM-DD")' data/manual_events.json

# Verify cronologia event appears in game_timeline.json
jq '.events[] | select(.date=="YYYY-MM-DD" and .category=="barrado_baile") | {date, title, source}' data/derived/game_timeline.json
```

Expected:
- week mirror includes `lider` / `alvo` / `desafio` (optional)
- `type = "barrado_baile"`
- `actor`/`target` names match API spelling exactly
- source URL present in `fontes`
- **cronologia event with `source = "power_events"` on the correct date** — if missing, the event won't appear on index.qmd or evolucao.qmd

**Always verify the cronologia after rebuild** — the game timeline is the single source of truth for `index.qmd` and `evolucao.qmd`. A missing event here means it won't appear on the site even if the data is correct in `manual_events.json`.

### 4. Commit + publish

Follow [Commit & Publish Workflow](#commit--publish-workflow):
```bash
git add data/ docs/MANUAL_EVENTS_AUDIT.md docs/SCORING_AND_INDEXES.md docs/PROGRAMA_BBB26.md
git commit -m "barrado no baile W{N} (Target)"
# Then push origin/main and trigger deploy if needed — see Commit & Publish Workflow
```

### 4. Update scheduled event

If `scheduled_events` has a `barrado_baile` placeholder for that date/week, **update it** with the real result (who was barred, by whom). Do NOT delete it — the auto-dedup suppresses it once the real event is recorded, and deleting prematurely leaves a timeline gap.

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
      {"actor": "A", "target": "B", "type": "ataque", "tema": "maior traidor(a)"}
    ],
    "edges_notes": "Context about edge extraction"
  }
}
```

**Aggregation rule for `stats`**:
- `most_targeted`, `not_targeted`, and `mutual_confrontations` should reflect the **aggregate round**, not just one plaque/sub-step.
- If the format has multiple negative choices per participant (for example, 2 plaques in the same round), count **all directed signals together** in `most_targeted`.
- If a format also has meaningful per-plaque leaders, keep those details in `notes` instead of inventing ad-hoc top-level keys.

**Edge types** (must match Sincerão builders):

| Type | Weight | When to use |
|------|--------|-------------|
| `elogio` (+ `slot`: 1/2/3) | +0.6 / +0.4 / +0.2 | Directed positive endorsement (e.g., positive podium “quem ganha”) |
| `regua` | +0.25 (aggregate mention) | Participant places someone in Top-3 priority/régua |
| `nao_ganha` | −0.8 | Participant says someone won't win |
| `regua_fora` | −0.5 (aggregate mention) | Participant leaves someone out of the régua |
| `ataque` (+ `tema`) | −0.6 | Directed negative confrontation: themes, medals, accusations, etc. |
| `paredao_perfeito` | −0.3 | Participant nominates someone for ideal paredão |
| `prova_eliminou` | −0.15 | Eliminated someone in a Sincerão sub-game |
| `quem_sai` | contextual (negative signal) | Explicit “quem sai hoje” indication |

**Negative podium formats** (e.g., “Pódio dos Medrosos” W8): When the podium theme is negative (calling someone cowardly, etc.), use `ataque` with `tema` = the specific medal/label given (e.g., `”covarde”`, `”frouxo”`, `”arregão”`). Add `”slot”: 1/2/3` to preserve rank position (scoring is flat −0.8 per edge, but slot preserves data granularity). Do **NOT** use `elogio` for negative podiums — `elogio` is hardcoded positive in the scoring pipeline.

**Dual-label negative formats** (for example, “quem faz alguém de bobo” + “quem está sendo feito de bobo”):
- Record **one directed edge per plaque**.
- If both plaques are negative judgments, keep them on `type = "ataque"` and distinguish them with `tema`.
- Prefer existing types (`ataque`, `elogio`, `nao_ganha`) unless the format truly introduces a new semantic category that cannot be represented safely.

**When article bullets conflict with the spoken justification**:
- Treat the **spoken justification as canonical** for actor → target extraction.
- Preserve the discrepancy in `notes` so future editors understand why the JSON does not mirror the bullet list literally.
- If the article text is clearly truncated and only explains one of two picks, it is acceptable to preserve the unexplained pick from the bullet list and document that fallback in `notes`.

**`stats` structure varies by format:**
- Positive formats: use `podio_top` (most podium placements), `sem_podio` (not placed), `nao_ganha_top`
- Negative / ataque formats: use `most_targeted` (most targeted), `not_targeted` (not targeted), `mutual_confrontations`
- Directed formats (Linha Direta): use `most_targeted`, `not_targeted`, `mutual_confrontations`

After rebuild, verify type coverage and unknown types:

```bash
jq '.sincerao.type_coverage' data/derived/index_data.json
```

If `.unknown` is non-empty, update `SINC_TYPE_META` in `scripts/builders/index_data_builder.py` before publishing.

**Current index card support**:
- The current Sincerão highlight card in `index_data.json` only surfaces the contradiction/alignment pair lanes from `elogio`, `nao_ganha`, and `ataque`.
- The radar can still count other mapped Sincerão types when they have valence metadata.
- If you add a brand-new edge type and expect it to appear in the current card, update both `SINC_TYPE_META` **and** the highlight filters in `scripts/builders/index_data_builder.py`.

**Backlash** (auto-generated reverse edge, target → actor): `nao_ganha` 0.3, `ataque` 0.4.

**Full Sincerão schema**: See `docs/SCORING_AND_INDEXES.md` → Sincerão Framework.

### 3. Rebuild + commit + publish

Follow [Commit & Publish Workflow](#commit--publish-workflow):
```bash
python scripts/build_derived_data.py
git add data/ docs/MANUAL_EVENTS_AUDIT.md docs/SCORING_AND_INDEXES.md
git commit -m "week N sincerão"
# Then push origin/main and trigger deploy if needed — see Commit & Publish Workflow
```

**Required post-rebuild spot checks**:
```bash
# 1. Cronologia event
jq '.events[] | select(.date=="YYYY-MM-DD" and .category=="sincerao") | {date, source, detail}' data/derived/game_timeline.json

# 2. Index highlight card
jq '.highlights.cards[] | select(.type=="sincerao") | {title, format, reaction_reference_date}' data/derived/index_data.json

# 3. Type coverage (no unknown types)
jq '.sincerao.type_coverage' data/derived/index_data.json

# 4. Sincerao edge count for the week
jq '[.[] | select(.week==N)] | length' data/derived/sincerao_edges.json
```

Expected:
- `game_timeline.json` shows the real Monday event with `source = "weekly_events"` (not `scaffold`)
- `index_data.json` exposes a `type = "sincerao"` card for the current week when supported edge types are present
- `type_coverage.unknown` is empty — if not, update `SINC_TYPE_META` in `scripts/builders/index_data_builder.py`
- Edge count matches the number of edges you added in `weekly_events[N].sincerao.edges`

**Index card rendering**: The Sincerão card on `index.qmd` renders **automatically** from `index_data.json`. No manual QMD edits needed. The card code (line ~434 in `index.qmd`) handles both `neg_lanes` (multi-plaque formats like "bobo") and `neg_ranked` (single-plaque formats like "Chato de Galocha"). After deploy, verify the card appears at the top of the Painel page with the correct format title, radar lanes, contradiction/alignment pairs, and "Poupados" section.

---

## Tá Com Nada Checklist (when Vacilômetro explodes)

**Tá Com Nada** is a collective house punishment triggered when the Vacilômetro (infraction counter) explodes. ALL privileges are suspended: fridge sealed, only basic items (rice, beans, salt, oil, coffee). Even VIP loses advantages. Lasts until lifted (typically 1-3 days). Happened twice in BBB 26: W3 (Feb 2, Ana Paula + Milena) and W10 (Mar 20, Jonas).

### When it happens

- [ ] Scrape the GShow article about the punishment
- [ ] Identify: who triggered it (instigador), what they did (motivo), who was in VIP (vip_afetados)

### Data updates

- [ ] Add `ta_com_nada` block to the relevant week in `manual_events.json` → `weekly_events`:

```json
"ta_com_nada": {
  "date": "YYYY-MM-DD",
  "instigadores": ["Name"],
  "motivos": {
    "Name": "What they did (punição gravíssima description)"
  },
  "vip_afetados": ["VIP members who lost privileges"],
  "consequencia": "Full description of what happened and when it ended",
  "notas": "Context notes",
  "fontes": ["url", "docs/scraped/slug.md"]
}
```

- [ ] Update the week's `notes` field to mention the Tá Com Nada

### What is auto-detected (no manual action needed)

| What | How | Where |
|------|-----|-------|
| Balance → 0 transitions | `balance.py` detects any balance dropping to zero in snapshots | `balance_events.json` |
| Timeline event | `timeline.py` reads `ta_com_nada` from `weekly_events` | `game_timeline.json` |
| Individual punição suppression | Power events with type `punicao_gravissima` / `punicao_coletiva` on the same date are suppressed in the timeline (dedup with the collective Tá Com Nada event) | `timeline.py` |

### What is NOT needed

- **Individual power_events per participant** — the W3 Tá Com Nada had individual entries for every participant (16 entries). This is optional and only useful if you want relationship edges (instigador → each victim). The timeline builder handles the collective event from the `weekly_events` block alone.
- **Manual balance adjustments** — the balance builder auto-detects balance→0 from snapshots. The `-500 estalecas` punição is captured as a balance change in the API.
- **Cartola overrides** — no Cartola points are scored for Tá Com Nada itself.

### Economy impact

Tá Com Nada affects the `economia.qmd` page:
- Balance drops visible in the balance timeline chart
- The `saldo_zero` event type in `balance_events.json` tracks transitions to zero
- VIP members are most visibly affected (lose 1000→0 instead of 500→0)
- The `ta_com_nada_dates` field in `daily_metrics.json` tracks occurrences per participant

### Rebuild + commit

```bash
python scripts/build_derived_data.py
git add data/ docs/MANUAL_EVENTS_AUDIT.md docs/SCORING_AND_INDEXES.md
git commit -m "public: W{N} Tá Com Nada — {instigador} ({motivo})"
git push origin main
gh workflow run daily-update.yml
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

**`time` field rules**:
- `"Ao Vivo"` — event will happen during the **daily prime-time TV show** (the evening broadcast). Future events only.
- `"A definir"` — time/broadcast not confirmed yet. Future events only.
- `"7h"`, `"14h"`, etc. — specific scheduled or known time. Can be used for **both** future and past events when the event had a specific announced time (e.g., Big Fone at 14h, pre-announced dynamic at 7h).
- **After the event happens**: **remove the `time` field** when updating with real results. The `time` field keeps same-day events pending — builds between the event and 06:00 BRT game-date flip will show the event as pending (🔮 + dashed) even though it already happened. Removing `time` ensures immediate resolution.

**Automatic lifecycle**: The timeline builder uses the event date to determine display style — **no manual flag needed**:
- **Past** (date < today) → always displayed as a real event (solid borders, no 🔮). If a real auto-generated event already exists for the same `(date, category)`, the entry is suppressed as redundant.
- **Today with `time`** → still scheduled (event is tonight — **remove `time` once the event happens**)
- **Today without `time`** → resolved (already happened today)
- **Future** → always scheduled (dashed borders, 🔮 prefix, yellow time badge)

This means you can schedule events, update their title/detail/fontes when they happen, and **remove the `time` field** so the Cronologia immediately transitions from scheduled→real styling. No `resolved` flag is needed — just removing `time` is sufficient.

**Common categories for scheduling**: `lider_classificatoria`, `dinamica`, and any recurring slot that needs a more specific override than the generic scaffold.

**Auto-generated categories** (generally do NOT schedule these unless you need a custom override): `lider`, `anjo`, `monstro`, `presente_anjo`, `paredao_imunidade`, `paredao_indicacao`, `paredao_votacao`, `paredao_contragolpe`, `paredao_bate_volta`, `paredao_formacao`, `sincerao`, `paredao_resultado`, `ganha_ganha`, `barrado_baile`. The timeline builder creates these automatically for the open cycle, and `paredoes.json` replaces the Sunday ceremony steps with authoritative data once the formation resolves.

### Minimal week rollover template

Use this as the copy-paste starting point when the dynamics article opens a new week.

```jsonc
// In weekly_events:
{
  "week": 10,
  "start_date": "2026-03-19",
  "end_date": null,
  "schedule_profile": "standard",
  "notes": "Only what is special about this week.",
  "fontes": [
    "<dynamics-article-url>",
    "docs/scraped/<arquivo>.md"
  ]
}
```

```jsonc
// Minimum manual scheduled events for the new week:
[
  {
    "date": "2026-03-19",
    "week": 10,
    "category": "lider_classificatoria",
    "emoji": "🏁",
    "title": "Prova do Líder — etapas classificatórias",
    "detail": "Classificatórias durante a tarde.",
    "time": "Tarde",
    "fontes": ["<dynamics-article-url>", "docs/scraped/<arquivo>.md"]
  },
  {
    "date": "2026-03-20",
    "week": 10,
    "category": "dinamica",
    "emoji": "⚡",
    "title": "Dinâmica da semana",
    "detail": "Describe only the week-specific mechanic.",
    "fontes": ["<dynamics-article-url>", "docs/scraped/<arquivo>.md"]
  }
]
```

`schedule_profile` is optional. Leave it as `standard` unless the cycle cadence changes late in the season. Today the only non-standard profile is `accelerated_finale`.

Add more entries only when the current week changes a recurring slot or introduces extra mechanics.
If the source/video enumerates a same-day sequence, append those entries in chronological order in the JSON.

### Weekly schedule from dynamics article (required)

When a "Dinâmica da Semana" article is published, register the week schedule using this exact order:

1. Scrape first:
   ```bash
   python scripts/scrape_gshow.py "<dinamica-semana-url>" -o docs/scraped/
   ```
2. Do the **always-repeat** rollover work from [Week Rollover Runbook](#week-rollover-runbook-thursdayfriday):
   - close week `N` and open week `N+1` in `weekly_events`
   - add the Thursday `lider` placeholder, plus `lider_classificatoria` when the source/video shows afternoon qualifying rounds
   - add optional Saturday `anjo` / `monstro` placeholders if you want them visible before results
3. Add only the **special-this-week** items from the article:
   - every extra Friday/Saturday mechanic goes in `scheduled_events` as `dinamica`
   - override scaffolded slots only when the article makes them non-generic
   - if the source/video enumerates same-day ceremony steps, split them into separate scheduled entries in source order instead of compressing them into one summary
   - if you create a same-day placeholder that should still render as upcoming (for example Thursday's `Prova do Líder` before the live final), include a non-empty `time`; same-day scheduled events without `time` render as resolved
4. Keep unresolved roles explicit:
   - If Líder is not known yet, keep wording generic (`indicação do Líder vigente (a definir)`).
   - If VIP list is not known yet, do not infer names; wait for the VIP source and update only when confirmed.
5. Link provenance in each entry (`fontes`):
   - dynamics article URL
   - `docs/scraped/<arquivo>.md`
6. Run the baseline verification command in [Baseline weekly template (reference; most slots auto-scaffolded)](#baseline-weekly-template-reference-most-slots-auto-scaffolded) before commit.

**Example mapped from**  
`https://gshow.globo.com/realities/bbb/bbb-26/noticia/dinamica-da-semana-tem-maquina-do-poder-e-participantes-emparedados-no-sabado-14-entenda.ghtml`

| Date | Category | Suggested title | Operational note |
|------|----------|-----------------|------------------|
| 2026-03-14 | `anjo` | Prova do Anjo | Standard Saturday flow |
| 2026-03-14 | `monstro` | Castigo do Monstro | Recurring weekly event (even if not explicit in article) |
| 2026-03-14 | `dinamica` | Dinâmica ao vivo: 3 emparedados | These 3 feed Sunday formation |
| 2026-03-15 | `presente_anjo` | Presente do Anjo | Anjo escolhe entre vídeo da família ou 2ª imunidade + almoço |
| 2026-03-15 | `paredao_formacao` | Formação do Paredão (duas partes) | Include `indicação do Líder vigente (a definir)` until Líder is confirmed |
| 2026-03-15 | `dinamica` | Máquina do Poder (salvação de emparedado) | Winner of caixa premiada can save one of Saturday's 3 emparedados |
| 2026-03-16 | `sincerao` | Sincerão | Recurring weekly Monday live event |
| 2026-03-17 | `paredao_resultado` | Eliminação | Normal Tuesday result |
| 2026-03-17 | `ganha_ganha` | Ganha-Ganha | Recurring Tuesday post-elimination dynamic |
| 2026-03-18 | `barrado_baile` | Barrado no Baile | Recurring Wednesday event |

**Important**: do not fill `formacao.lider`, `formacao.indicado_lider`, or `provas.lider.vip` from the dynamics schedule article alone. Use the dedicated Líder/VIP source flow in [Líder Transition Checklist](#líder-transition-checklist-thursday-night).

### Auto-dedup behavior

- `build_game_timeline()` merges scheduled events with real events
- Two-tier dedup: **singleton categories** (anjo, lider, paredao_formacao, sincerao, ganha_ganha, etc.) are always suppressed when a real event exists on the same `(date, category)`. **Non-singleton categories** (monstro, dinamica) are suppressed when *resolved* (past date, or same-day without `time`) or by exact title match
- **Lifecycle**: past events (`date < reference_date`) are always *resolved* (solid display, category-deduped). Same-day without `time` → resolved. Same-day with `time` or future → *pending* (dashed border + 🔮). Removing `time` is optional — past events transition automatically
- Líder source priority: API `auto_events` first; fallback to `provas.json` (`tipo=lider`) when API data is late
- **Never delete scheduled events prematurely** — always update them with real results first. Clean up old entries only during the next week's Líder Transition setup, after the API has captured the roles

---

## Manual Data Files — When and How

### 1. `data/manual_events.json`

**When**: After any power event, Big Fone, Sincerão, special dynamic, exit, or scheduled event.

**Common entries** (by frequency):
- `power_events` — contragolpe, veto, imunidade, ganha-ganha, barrado
- `weekly_events` — Big Fone, Sincerão, Anjo details, confessão de voto, dedo-duro
- `special_events` — dinâmicas especiais
- `scheduled_events` — upcoming events (with auto-dedup)
- `participants` — **all exits** (eliminações, desistências, desclassificações)

**Pitfalls**:
- Names must match API exactly (see `docs/ARCHITECTURE.md` → data contracts)
- Consensus events: use `"actor": "A + B + C"` + `"actors": ["A","B","C"]`
- Barrado no Baile with liderança dupla: use both `actor` (joined string) and `actors` (array) to preserve attribution.
- `participants` must use the current contract:
  - required keys: `status`, `exit_date`
  - recommended: `paredao_numero` (for eliminações), `fontes`
  - avoid legacy keys in this object (`date`, `week`, `paredao`, `detail`)
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
- At new paredão creation, always confirm this question: **"Fechamento previsto continua terça ~22:45 BRT?"**
  - If the answer is "no" (common near finals), register the real closing schedule in `data/votalhada/polls.json` using `fechamento_votacao`.

**Full schema**: See `docs/ARCHITECTURE.md` (data contracts) + templates in this guide.

### 3. `data/provas.json`

**When**: After Prova do Líder (Thursday), Prova do Anjo (Saturday), Bate e Volta (Sunday).

**Workflow**: Add entry to the `provas` array with `numero`, `tipo`, `week`, `date`, `vencedor`, `fases`, `fontes`. See [Anjo Checklist](#anjo--monstro-update-checklist-saturday) and [Líder Checklist](#líder-transition-checklist-thursday-night) for templates.

If the ranking is intentionally partial, include `nota_ranking` in the prova entry instead of leaving the limitation implicit.

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
- VIP strict source: `provas.json` (`tipo=lider` → `vip`, `vip_source`) plus `power_events.type=troca_vip`
- From manual data: `atendeu_big_fone`, `desistente`, `eliminado`, `desclassificado`
- From paredões: `salvo_paredao`, `nao_eliminado_paredao`, `nao_emparedado`, `nao_recebeu_votos`
  - Window exception: when `formacao.bate_volta.salvacao_com_janela_aberta: true` (or `janela_escalacao_aberta: true`), score only `emparedado` (skip `salvo_paredao`).
- Cross-checked: `monstro_retirado_vip` (Monstro recipient was in VIP in previous snapshot)
- Paredão Falso: `quarto_secreto` (+40, from `paredao_falso: true` + finalized result)

**Quick rule for `salvacao_com_janela_aberta`:**
- Set `true` only if the participant was emparedado while the Cartola window was closed, and escaped when the window was open.
- If uncertain, keep `false` and add a source note in `fontes` before changing scoring behavior.

### Janela de escalação (Cartola): como registrar e como funciona

Context: GShow can announce that the round window closed and that game dynamics start counting points from that moment (example, rodada 9):
- https://gshow.globo.com/realities/bbb/bbb-26/cartola-bbb/noticia/cartola-bbb-janela-de-escalacao-da-nona-rodada-fecha-e-dinamicas-passam-a-valer-ponto.ghtml

Operational registration:
1. Scrape and archive the supporting GShow page before any scoring change:
   ```bash
   python scripts/scrape_gshow.py "<url_cartola_janela>" -o docs/scraped/
   ```
2. In `data/paredoes.json` → `formacao.bate_volta`, set:
   - `"salvacao_com_janela_aberta": true`
   only when the participant entered paredão with window closed and escaped with window open.
3. Keep normal flow (`false` or omitted) for regular Bate e Volta cases.
4. If the closure schedule changed, also register the real voting close time in `data/votalhada/polls.json` (`fechamento_votacao`) for consistency in Tuesday operations.
5. Always add the supporting article URL and scraped file path in `fontes` before enabling the flag.

Scoring behavior in the pipeline:
- With `salvacao_com_janela_aberta: true`:
  - keeps `emparedado` (−15)
  - skips `salvo_paredao` (+25)
- Without the flag (`false`/omitted):
  - normal Bate e Volta applies (`emparedado` + `salvo_paredao`)

Important scope note:
- This flag is the explicit operational switch currently modeled for the Cartola window edge case in paredão salvation.
- Do not infer other window effects ad hoc; only encode what is backed by source and supported by current scoring rules.

### VIP scoring references (for audits)

Scrape and keep these pages in `docs/scraped/` for future verification:
- https://gshow.globo.com/realities/bbb/bbb-26/cartola-bbb/noticia/o-que-e-cartola-bbb-entenda-como-funciona-a-novidade-do-reality.ghtml
- https://gshow.globo.com/realities/bbb/bbb-26/cartola-bbb/noticia/lider-samira-define-novo-vip-saiba-como-fica-a-pontuacao-na-setima-rodada-do-cartola-bbb.ghtml
- https://gshow.globo.com/realities/bbb/bbb-26/cartola-bbb/noticia/bloco-do-paredao-termina-com-tres-emparedados-e-pontuacao-negativa-no-cartola-bbb.ghtml
- https://gshow.globo.com/realities/bbb/bbb-26/cartola-bbb/noticia/cartola-bbb-janela-de-escalacao-da-nona-rodada-fecha-e-dinamicas-passam-a-valer-ponto.ghtml
- https://gshow.globo.com/realities/bbb/bbb-26/noticia/bloco-do-paredao-samira-altera-vip-e-xepa-e-troca-edilson-por-ana-paula-renault.ghtml
- https://gshow.globo.com/realities/bbb/bbb-26/cartola-bbb/noticia/ana-paula-renault-recebe-o-castigo-do-monstro-e-sofre-duas-pontuacoes-negativas-no-cartola-bbb.ghtml

---

## Economia / Compras Detection (automatic vs manual)

### How compras is detected today

`compras` is **auto-detected** in the derived pipeline from snapshot balance deltas.

- Source builder: `scripts/builders/balance.py` (`build_balance_events()`).
- Rule of thumb:
  - If losses affect >=80% of active participants (collective pattern), classify as `compras`.
  - Tiny gains in the same transition are tolerated (keeps event as `compras`).
  - Significant mixed gains/losses become `dinamica`.
- Output artifact: `data/derived/balance_events.json`:
  - `events[]` (includes `type="compras"`)
  - `compras_fairness.events[]` (VIP/Xepa percentages + per-capita economics fields)

### What is manual (and what is not)

- There is **no dedicated manual compras event entry** in `manual_events.json`.
- Manual files still matter for context:
  - `special_events` can reclassify certain balance events as special dynamics (e.g., Máquina do Poder).
  - Sources and narrative context are documented manually in weekly/special event records.

### Operator checks when numbers look suspicious

1. Confirm snapshots exist around the date (`data/snapshots/` cadence and timestamps).
2. Rebuild derived data:
   ```bash
   python scripts/build_derived_data.py
   ```
3. Inspect the detected event in `data/derived/balance_events.json` (`events` + `compras_fairness`).
4. Compare against official/source notes for that week (`docs/PROGRAMA_BBB26.md`, scraped sources).
5. If a special dynamic was misclassified, update `manual_events.json` (`special_events`) and rebuild.

---

## Quick Reference: Which Script When

| Situation | Command |
|-----------|---------|
| After editing any manual data file | `python scripts/build_derived_data.py` |
| Legacy: analyze archived `local/private-main` conflicts | `scripts/sync_public.sh` |
| Legacy: apply archived-branch reconciliation after report approval | `scripts/sync_public.sh --apply --report <path>` |
| Fetch fresh API data manually | `python scripts/fetch_data.py` |
| Deploy to site immediately | `gh workflow run daily-update.yml` |
| Verify site rendering locally | `quarto render` (~3 min) |
| Preview with hot reload | `quarto preview` |
| Check snapshot dedup/integrity | `python scripts/audit_snapshots.py` |
| Retake full layout screenshots (desktop+mobile, page-by-page verbose) | `./scripts/capture_layout_screenshots.sh --output-dir tmp/page_screenshots/<label>` |
| Retake with fresh render first | `./scripts/capture_layout_screenshots.sh --render --output-dir tmp/page_screenshots/<label>` |
| Install/update chromium once for captures | `./scripts/capture_layout_screenshots.sh --install-browser --output-dir tmp/page_screenshots/<label>` |
| Capture one page with verbose diagnostics | `python scripts/capture_quarto_screenshots.py --profiles mobile --page index.html --verbose --output-dir tmp/page_screenshots/<label>` |
| Capture mobile slices (top/mid/bottom) for long pages | `python scripts/capture_mobile_slices.py --output-dir tmp/page_screenshots/<label>-slices` |
| Analyze capture timing | `python scripts/analyze_capture_timing.py` |
| Update PROGRAMA_BBB26.md timeline | `python scripts/update_programa_doc.py` |
| Scrape a GShow article | `python scripts/scrape_gshow.py "<url>" -o docs/scraped/` |
| Scrape BBB 26 agenda (what happened on a date) | `python scripts/scrape_gshow_agenda.py YYYY-MM-DD` |
| Scrape agenda range with JSON | `python scripts/scrape_gshow_agenda.py --start YYYY-MM-DD --end YYYY-MM-DD --json` |
| Scrape agenda without browser (limited) | `python scripts/scrape_gshow_agenda.py YYYY-MM-DD --static` |

---

## Screenshot Pipeline (Layout/Plot Review)

Use this pipeline when reviewing responsive layout, spacing, alignment, plots, and readability across all Quarto pages.

### Prerequisites

```bash
pip install -r requirements.txt
quarto --version
npx --version
```

If needed, install Playwright chromium once:

```bash
./scripts/capture_layout_screenshots.sh --install-browser --output-dir tmp/page_screenshots/bootstrap
```

### Recommended run sequence

1. Render site if data/templates changed:
```bash
quarto render
```
2. Run page-by-page full-page capture (desktop + mobile):
```bash
./scripts/capture_layout_screenshots.sh --output-dir tmp/page_screenshots/<label>
```
3. For very long pages or suspected mobile blank segments, run slice captures:
```bash
python scripts/capture_mobile_slices.py --output-dir tmp/page_screenshots/<label>-slices
```
4. Inspect manifests:
```bash
cat tmp/page_screenshots/<label>/manifest.json
cat tmp/page_screenshots/<label>-slices/manifest.json
```

### Sincerão QA checklist (mobile + desktop)

Run this checklist page-by-page after each capture cycle (`index`, `relacoes`, debug pages where applicable):

- Dense week (many Sincerão events): top entries are readable without horizontal scroll; overflow is accessible through `<details>`/expanded blocks.
- Sparse week (few events): no empty/broken containers; layout remains balanced.
- One-sided week (only positive or only negative): missing lanes show neutral empty-state text instead of blank space.
- Mixed week: `Atacados`, `Elogiados`, and `Contradições` are all visible and legible.
- Profile cards (`Recebeu`/`Fez`): chips wrap naturally on mobile; no clipped labels or forced horizontal swipe.
- Contradiction consistency: contradiction values in profile summaries and top-level radar/pairs are coherent for the same week.
- Visual density: desktop remains compact/scannable; mobile remains tappable with clear hierarchy.

### Core commands

Wrapper (recommended, page-by-page progress logs):

```bash
./scripts/capture_layout_screenshots.sh --render --output-dir tmp/page_screenshots/<label>
```

Direct script (fine-grained control):

```bash
python scripts/capture_quarto_screenshots.py \
  --render \
  --profiles desktop,mobile \
  --output-dir tmp/page_screenshots/<label>
```

Single page debug (helps detect slow/hanging perception):

```bash
python scripts/capture_quarto_screenshots.py \
  --profiles mobile \
  --page index.html \
  --verbose \
  --fail-fast \
  --output-dir tmp/page_screenshots/<label>
```

### Key flags

- `--render`: render Quarto before captures.
- `--install-browser`: wrapper option to install/update Playwright chromium.
- `--profiles desktop,mobile`: choose capture profiles.
- `--page <name>`: limit to a single page (`index.html`, `paredao.html`, etc.).
- `--verbose`: print per-page command and stitch diagnostics.
- `--fail-fast`: stop on first failure instead of finishing the whole run.
- `--mobile-stitch-threshold N`: enable/disable stitched fallback for very tall mobile captures (`0` disables).
- `--mobile-stitch-viewport-height N`: larger stitch viewport to reduce tile count/time.

### Expected outputs

- Full-page run:
  - `tmp/page_screenshots/<label>/desktop/*.png`
  - `tmp/page_screenshots/<label>/mobile/*.png`
  - `tmp/page_screenshots/<label>/manifest.json`
- Slice run:
  - `tmp/page_screenshots/<label>-slices/*_{top,mid,bottom}.png`
  - `tmp/page_screenshots/<label>-slices/manifest.json`

`manifest.json` is the canonical evidence for counts, failures, and capture mode (`full-page`, `stitched-scroll`, etc.).

### Troubleshooting

- "Looks stuck" on long pages:
  - Run one page first with `--page ... --verbose`.
  - Use slice captures as primary review artifact for extremely tall pages.
- Intermittent stitch drop (`browser 'default' is not open`):
  - The script now auto-recovers by reopening the page at the current tile.
  - In verbose mode you may see `stitch recover: reopening browser at tile ...`.
- Port in use:
  - Script auto-selects another local port; no manual action needed.
- Browser/tool missing:
  - Use `--install-browser` and verify `npx` exists.
- Blank/full-page artifacts on very tall mobile pages:
  - Prefer slice captures and/or stitched fallback output reported in manifest.

### Repository hygiene

- Capture outputs under `tmp/page_screenshots/` are review artifacts and should not be committed.
- Before commit/push:

```bash
git status --short
```

Ensure no `tmp/` capture artifacts are staged.

---

## Capture Timing & Polling Strategy

### Current strategy (as of 2026-03-18)

**Primary: Local polling on Proxmox LXC** — true 15-minute intervals via systemd timer. Fetches API, builds derived data, pushes to `main`, triggers GitHub Actions for Quarto render + Pages deploy. See `deploy/README.md` for setup.

**Fallback: GitHub Actions cron** (`*/15 * * * *`) — still configured but unreliable. Measured actual gaps: avg **67 minutes** (min 18, max 191). Only 1 out of 29 measured gaps was near 15 minutes. GitHub Actions cron has no SLA and is routinely throttled to 30–120 min intervals.

- `fetch_data.py` only takes ~30 seconds (uses `--fetch-only`, no heavy deps).
- Snapshots are saved **only when the data hash changes** — dedup rate ~61%.
- Expected: ~5–15 actual snapshots/day.
- Both local and GitHub polling use the same hash dedup — no duplicate snapshots regardless of who fetches.

**Resilience**: If the LXC is down, GitHub Actions cron continues as fallback (full pipeline: fetch + build + render + deploy). Timing degrades to ~1h gaps but data is never lost. When the LXC triggers a manual dispatch, GitHub skips fetch/build/tests and only renders + deploys (~2 min instead of ~4 min).

### Why 15-minute polling

Probe-era analysis (Mar 3–8) confirmed that queridômetro reactions, balance changes, and role updates happen at **unpredictable times** throughout the day — not just around 15:00 BRT as previously assumed. Examples: 10:36 BRT on Mar 3; 11:50, 12:45, 13:52 BRT on Mar 4. High-frequency polling catches all granular events (punições, compras, mesada, role changes) as they happen.

### How dedup works

- Source of truth: `_metadata.reactions_hash` in each snapshot.
- Detection method: `fetch_data.py` computes a hash of the full API payload; saves only if the hash differs from the last snapshot.
- No duplicate snapshots are created — same data = no new file.

### Verification

```bash
# Check cron schedule
head -20 .github/workflows/daily-update.yml

# Timing analysis (historical)
python scripts/analyze_capture_timing.py --full-history
```

---

## Troubleshooting

### `build_derived_data.py` fails with audit error

```bash
python scripts/audit_manual_events.py    # check what's wrong
# Fix data/manual_events.json
python scripts/build_derived_data.py     # re-run
```

### Cartola did not update after elimination (stale leaderboard)

Symptoms:
- Paredão is `finalizado` in `data/paredoes.json`, but eliminated participant still appears `active: true` in `data/derived/cartola_data.json`.
- Missing `eliminado` (−20) event in the elimination week.

Checklist:
```bash
# 1) Ensure participant exit exists in manual_events contract (not legacy keys)
jq '.participants["Name"]' data/manual_events.json

# 2) Rebuild
python scripts/build_derived_data.py

# 3) Confirm week events + active flag
jq '.leaderboard[] | select(.name=="Name") | {name,active,week_events:(.events|map(select(.week==N)))}' data/derived/cartola_data.json
```

Expected for normal elimination:
- `active: false`
- week `N` includes `["eliminado", -20, "YYYY-MM-DD"]`

If still wrong:
- Verify `data/manual_events.json -> participants["Name"]` uses `status`, `exit_date`, `paredao_numero`, `fontes`.
- Remove legacy participant keys (`date`, `week`, `paredao`, `detail`) for that entry.
- Rebuild again.

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

### Parallel page renders fail with `database is locked` or missing `_site/data/derived/*.json`

Symptom:
- Two `quarto render <page>.qmd` commands run at the same time in the same project.
- One render aborts with errors such as:
  - `database is locked`
  - `NotFound: ... utime '_site/data/derived/relations_scores.json'`

Root cause:
- Quarto project renders are **not concurrency-safe** inside the same repo/output dir. The project cache and `_site/` resource copy step race with each other.

Use the repo wrapper instead of raw parallel `quarto render` calls:
```bash
python scripts/quarto_render_safe.py index.qmd
python scripts/quarto_render_safe.py evolucao.qmd
```

Notes:
- `scripts/quarto_render_safe.py` uses a project-wide lock under `.quarto/render.lock` and serializes concurrent callers.
- If a raw `quarto render` command already failed, rerun it through the wrapper or run a single full-site render: `python scripts/quarto_render_safe.py`

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
| **`docs/ARCHITECTURE.md`** | Public technical architecture and data-flow reference |
| **`docs/MANUAL_EVENTS_GUIDE.md`** | Full schema + fill rules for `manual_events.json` |
| **`docs/SCORING_AND_INDEXES.md`** | Scoring formulas, weights, index specifications |
| **`docs/TESTING.md`** | Verification matrix, test ownership, and minimum checks by change type |
| **`docs/PROGRAMA_BBB26.md`** | TV show reference — rules, format, dynamics |
| **`docs/PUBLIC_PRIVATE_DOCS_POLICY.md`** | Public/private documentation boundaries + push checklist |
| **`docs/GIT_PUBLIC_PRIVATE_WORKFLOW.md`** | Main-first workflow, local-only material, and legacy recovery notes |
| **`data/votalhada/README.md`** | Screenshot-to-data extraction workflow |
| **`data/CHANGELOG.md`** | Snapshot history, dedup analysis, API observations |
