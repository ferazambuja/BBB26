# Manual Events Guide — Full Reference

This document contains the complete schema, fill rules, and update procedures for `data/manual_events.json`.
Referenced from `CLAUDE.md` — read this when adding or modifying manual events.

## Overview

Events **not available from the API** are tracked manually in `data/manual_events.json`.

**Auto-detected from API** (do NOT add manually):
- Líder, Anjo, Monstro, Imune — detected via `characteristics.roles`
- VIP membership — detected via `characteristics.group`
- Paredão — detected via `characteristics.roles`

Cartola role transitions are auto-detected from consecutive snapshots in `build_derived_data.py` → `build_cartola_data()` and persisted to `data/derived/cartola_data.json`.

---

## Structure (manual-only data)

- `participants` — Exit status for people who left (desistente, eliminada, desclassificado)
- `weekly_events` — Per-week: Big Fone, Quarto Secreto, Ganha‑Ganha, Barrado no Baile, notes
- `special_events` — Dinâmicas, new entrants, one-off events
- `power_events` — **Powers and consequences** (immunity, contragolpe, voto duplo, veto, perdeu voto, bate-volta, ganha-ganha, barrado no baile)
- `cartola_points_log` — **Manual point overrides** for events not inferable from API

---

## Manual Categories + AI Fill Rules

### `participants`
Use for **desistência / eliminação / desclassificação**.
- Fields: `status`, `date`, `fonte`.
- Name must match snapshots **exactly**.

### `weekly_events`
Week-scoped dynamics (Big Fone, Quarto Secreto, Ganha‑Ganha, Barrado no Baile, caixas, notes).

**Ganha‑Ganha (manual):**
- Registre em `weekly_events[].ganha_ganha` com `date`, `sorteados`, `veto`, `decisao`, `informacao`.
- Sempre crie **power_events** correspondentes:
  - `veto_ganha_ganha` (ator → vetado, impacto negativo)
  - `ganha_ganha_escolha` (ator → escolhido, impacto positivo leve)

**Barrado no Baile (manual):**
- Registre em `weekly_events[].barrado_baile` (lista) com `date`, `lider`, `alvo`.
- Sempre crie **power_events**: `barrado_baile` (ator = líder, alvo = barrado).
- Always include `week` (int) and `date` (`YYYY-MM-DD`).

### `special_events`
One-off events not tied to a specific week.

### `power_events`
Only powers/consequences **not fully exposed by API** (contragolpe, voto duplo, veto, perdeu voto, bate-volta, ganha-ganha, barrado no baile).
- Fields: `date`, `week`, `type`, `actor`, `target`, `detail`, `impacto`, `origem`, `fontes`.
- Optional: `actors` (array) for **consensus** dynamics (ex.: duas pessoas indicam em consenso).
- `impacto` is **for the target** (positivo/negativo).
- `origem`: `manual` (quando registrado no JSON) ou `api` (quando derivado automaticamente).
- If `actor` is not a person, use standardized labels: `Big Fone`, `Prova do Líder`, `Prova do Anjo`, `Prova Bate e Volta`, `Caixas-Surpresa`.

**Tipos já usados**: `imunidade`, `indicacao`, `contragolpe`, `voto_duplo`, `voto_anulado`, `perdeu_voto`, `bate_volta`, `veto_ganha_ganha`, `ganha_ganha_escolha`, `barrado_baile`.

**Auto-detectados da API** (`scripts/build_derived_data.py`): Líder/Anjo/Monstro/Imune são derivados das mudanças de papéis nos snapshots diários e salvos em `data/derived/auto_events.json` com `origem: "api"`.
- A detecção usa **1 snapshot por dia** (último do dia). Mudanças intra-dia podem não aparecer.
- **Monstro**: o `actor` é o **Anjo da semana** (quando disponível), pois o Anjo escolhe quem recebe o Castigo do Monstro.

### `cartola_points_log`
Only events **not inferable** from snapshots or paredões (salvo, não eliminado, etc.).
- Structure: one entry per participant/week with `events: [{event, points, date, fonte?}]`.
- Always include matching `fontes` in `manual_events.json` for the underlying real-world event.

---

## API vs Manual

- API snapshots **auto-detect** roles (Líder/Anjo/Monstro/Imune/VIP/Paredão).
- Manual events fill **what the API does not expose** (Big Fone, contragolpe, veto, voto duplo, etc.).

---

## When to Update

- After each elimination or desistência (update `participants`)
- After Big Fone (who answered, consequence)
- After special events (dinâmicas like Caixas-Surpresa)
- After Ganha-Ganha (registrar veto + decisão/benefício)
- After Barrado no Baile (líder escolhe quem não vai à festa)
- After any **power effect** (veto, voto duplo, perdeu voto, contragolpe, imunidade)
- After each paredão result to log **salvos/sobreviventes** and any point events not detectable via API
- Depois de qualquer edição manual, rode `python scripts/build_derived_data.py` para atualizar `data/derived/`.

---

## Caixas-Surpresa (referência para preencher `power_events`)

- Caixa 1: poder de **vetar o voto** de alguém.
- Caixa 2: **não vota** no próximo paredão.
- Caixa 3: **voto com peso 2**.
- Caixas 4 e 5: precisam **indicar alguém em consenso** (evento **público**); se não houver consenso, os dois vão ao paredão.

---

## Adding Source URLs (`fontes`)

Each entry in `manual_events.json` has a `fontes` array for GShow/news article URLs that confirm the event.

### How to find sources (search Google in Portuguese)

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
