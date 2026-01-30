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

**Big Fone (manual):**
- `weekly_events[].big_fone` is an **array** (multiple Big Fones can happen in the same week).
- Each entry: `{"atendeu": "Name", "date": "YYYY-MM-DD", "consequencia": "..."}`.
- Use `null` when no Big Fone occurred that week.
- Always create a corresponding **power_event** for the consequence (e.g., `indicacao`, `veto_prova`).
- Cartola: each answerer gets +30 points (`atendeu_big_fone`).

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

**Tipos já usados**: `imunidade`, `indicacao`, `contragolpe`, `voto_duplo`, `voto_anulado`, `perdeu_voto`, `bate_volta`, `veto_ganha_ganha`, `ganha_ganha_escolha`, `barrado_baile`, `veto_prova`.

**Auto-detectados da API** (`scripts/build_derived_data.py`): Líder/Anjo/Monstro/Imune são derivados das mudanças de papéis nos snapshots diários e salvos em `data/derived/auto_events.json` com `origem: "api"`.
- A detecção usa **1 snapshot por dia** (último do dia). Mudanças intra-dia podem não aparecer.
- **Monstro**: o `actor` é o **Anjo da semana** (quando disponível), pois o Anjo escolhe quem recebe o Castigo do Monstro.

### Vote Visibility Events (in `weekly_events`)

BBB votes are cast in the confessionário (secret to the house, shown to TV audience). Votes can become known to participants through three mechanisms, each tracked separately:

| Key in `weekly_events` | Type | Description | Example |
|------------------------|------|-------------|---------|
| `confissao_voto` | Voluntary | Participant **chose** to tell the target they voted for them | Jordana told Sol after paredão formation |
| `dedo_duro` | Game mechanic | A participant **receives the power** to reveal someone else's vote | (Not yet happened in BBB26) |
| `voto_revelado` | Legacy | **Deprecated** — use `confissao_voto` or `dedo_duro` instead | Treated as `dedo_duro` for scoring |

**Paredão-level open voting** (`votacao_aberta`):
When the entire week uses open voting (all votes cast publicly), set `"votacao_aberta": true` in the paredão entry in `data/paredoes.json`. All votes in that week automatically get `open_vote` classification.

**Schema for `confissao_voto` / `dedo_duro`:**
```json
{
  "date": "YYYY-MM-DD",
  "votante": "Nome de quem votou",
  "alvo": "Nome de quem recebeu o voto",
  "contexto": "Descrição do que aconteceu",
  "fontes": ["https://..."]
}
```

Can be a single object or an array of objects (multiple revelations in the same week).

**How to decide which type:**
- Did the voter **choose** to tell someone? → `confissao_voto`
- Did a game mechanic **force** the revelation? → `dedo_duro`
- Is the entire week's voting public? → Set `votacao_aberta: true` in `data/paredoes.json`

**Scoring impact:**

| Type | Voter→Target | Target→Voter (backlash) | Rationale |
|------|-------------|------------------------|-----------|
| `secret` | -2.0 | 0 | Target doesn't know who voted |
| `confissao` | -2.0 | -1.0 | Voter showed honesty; target resents but respects |
| `dedo_duro` | -2.0 | -1.2 | Involuntary exposure; stronger resentment |
| `open_vote` | -2.5 | -1.5 | Public declaration of hostility |

Note: voter→target weight is the same (-2.0) for secret, confissão, and dedo-duro because the **intent to eliminate** was identical (vote was cast secretly in all three cases). Only `open_vote` gets -2.5 because the voter **chose** to publicly declare hostility.

### Anjo Dynamics (`weekly_events[].anjo`)

Each week's `anjo` object records the full Prova do Anjo dynamics. Schema:

```json
{
  "vencedor": "Jonas Sulzbach",
  "duo": ["Jonas Sulzbach", "Sarah Andrade"],
  "prova_date": "2026-01-17",
  "tipo": "normal",
  "almoco_date": "2026-01-18",
  "almoco_convidados": ["Alberto Cowboy", "Aline Campos", "Sarah Andrade"],
  "escolha": "video_familia",
  "imunizou": "Sarah Andrade",
  "extra_poder": "imunidade_extra",
  "usou_extra_poder": false,
  "notas": "...",
  "fontes": ["..."]
}
```

| Field | Required | Values |
|-------|----------|--------|
| `vencedor` | Yes | API name of the Anjo |
| `duo` | Yes | Array of 2 names (duo partners in the prova) |
| `prova_date` | Yes | Date of the Prova do Anjo |
| `tipo` | Yes | `"normal"` (Anjo chooses who to immunize) or `"autoimune"` (Anjo is self-immune) |
| `almoco_date` | Yes | Date of the Almoço do Anjo |
| `almoco_convidados` | Yes | Array of 3 names invited to the lunch |
| `escolha` | Yes | `"video_familia"` or `"imunidade_extra"` |
| `imunizou` | If applicable | Who received standard immunity (null if autoimune and didn't use power) |
| `extra_poder` | Yes | What power was offered (e.g. `"imunidade_extra"`) |
| `usou_extra_poder` | Yes | `true` if Anjo used the extra power, `false` if chose video/other |
| `notas` | Optional | Contextual notes |
| `fontes` | Yes | Source URLs |

**Scoring edges generated:**
- `almoco_anjo`: Anjo → each invitee (+0.15)
- `duo_anjo`: Mutual between duo partners (+0.10 each way, accumulates per occurrence)
- `anjo_nao_imunizou`: Duo partner → Anjo (−0.15) — only when `tipo: "autoimune"` AND `usou_extra_poder: false`

**When to fill:** After each Prova do Anjo (usually Saturday), with Almoço details from Sunday.

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

---

## Semana 3 — Dinâmica: 4 Big Fones (29 Jan–2 Fev 2026)

Reference: https://gshow.globo.com/realities/bbb/bbb-26/noticia/dinamica-da-semana-do-bbb-26-tem-quatro-ligacoes-do-big-fone-confira.ghtml

**Líder da semana**: Maxiane (venceu Prova do Líder na quinta 29).

### Cronograma

| Dia | Evento | Status | O que registrar |
|-----|--------|--------|-----------------|
| Qui 29 | **Big Fone #1** (prata) | **Feito** | `big_fone[]` + `power_event` veto_prova |
| Qui 29 | Prova do Líder | **Feito** | Auto-detectado (Maxiane = Líder) |
| Sex 30, 7h | **Big Fone #2** (prata, academia) | Pendente | `big_fone[]` entry |
| Sex 30, ao vivo | **Big Fone #3** (dourado, sala/cozinha) | Pendente | `big_fone[]` entry |
| Sáb 31 | Prova do Anjo | Pendente | Auto-detectado |
| Sáb 31, ao vivo | **Big Fone #4** (votação do público) | Pendente | `big_fone[]` entry |
| Sáb 31 | Consenso Big Fone → indicação ao paredão | Pendente | `power_event` indicacao + `paredoes.json` dinamica |
| Dom 1 | Presente do Anjo (troca vídeo por imunidade extra) | Pendente | `power_event` imunidade (se aceitar) |
| Dom 1 | Formação de Paredão triplo | Pendente | `paredoes.json` entrada completa |
| Dom 1 | Prova Bate e Volta | Pendente | `paredoes.json` bate_volta |
| Ter 3 | Eliminação | Pendente | `participants`, `paredoes.json` resultado |

### Big Fone #1 — REGISTRADO

- **Atendeu**: Breno
- **Consequência**: Vetou Brigido das 3 provas da semana
- **power_event**: `veto_prova` (Breno → Brigido, -1.5 weight)

### Big Fone #2 (Sex 7h) — TEMPLATE

Quando acontecer, adicionar em `data/manual_events.json`:

```jsonc
// Em weekly_events[week 3].big_fone (append ao array existente):
{"atendeu": "NOME", "date": "2026-01-30", "consequencia": "DESCREVER"}
```

Consequência ainda desconhecida. Se tiver power_event associado, adicionar também.

### Big Fone #3 (Sex ao vivo) — TEMPLATE

```jsonc
// Em weekly_events[week 3].big_fone (append ao array existente):
{"atendeu": "NOME", "date": "2026-01-30", "consequencia": "DESCREVER"}
```

### Big Fone #4 (Sáb ao vivo) — TEMPLATE

```jsonc
// Em weekly_events[week 3].big_fone (append ao array existente):
{"atendeu": "NOME", "date": "2026-01-31", "consequencia": "DESCREVER"}
```

### Consenso Big Fone → Indicação ao Paredão

Os 3 participantes que atenderam ao Big Fone (#2, #3, #4) devem escolher **em consenso** uma pessoa para ser emparedada. Se não houver consenso, os 3 vão ao paredão.

**Em `data/manual_events.json` — power_events:**
```jsonc
{
  "date": "2026-02-01",
  "week": 3,
  "type": "indicacao",
  "actor": "NOME1 + NOME2 + NOME3",
  "actors": ["NOME1", "NOME2", "NOME3"],
  "target": "INDICADO",
  "source": "Big Fone",
  "detail": "Indicação em consenso pelos participantes do Big Fone",
  "fontes": ["URL"],
  "impacto": "negativo",
  "origem": "manual",
  "visibility": "public",
  "awareness": "known"
}
```

**Em `data/paredoes.json` — formacao.dinamica:**
```jsonc
"dinamica": {
  "nome": "Big Fone (Consenso)",
  "indicaram": ["NOME1", "NOME2", "NOME3"],
  "indicado": "INDICADO"
}
```

> **Nota**: Segue o mesmo padrão da Caixas-Surpresa (Semana 2). O `normalize_actors()` em `build_derived_data.py` distribui o peso de `indicacao` (-2.8) para cada ator→alvo.

### Presente do Anjo — Imunidade Extra

Se o Anjo aceitar trocar o vídeo da família por imunidade:

```jsonc
// Em power_events:
{
  "date": "2026-02-01",
  "week": 3,
  "type": "imunidade",
  "actor": "NOME_ANJO",
  "target": "NOME_ANJO",
  "source": "Presente do Anjo",
  "detail": "Abriu mão do vídeo da família em troca de imunidade extra",
  "fontes": ["URL"],
  "impacto": "positivo",
  "origem": "manual",
  "visibility": "public",
  "awareness": "known"
}
```

Se recusar: nada a registrar (recebe o vídeo normalmente, dá imunidade ao outro como de costume).

### Formação do 3º Paredão (Domingo)

**Paredão triplo** com estas fontes de emparedados:
1. Indicação do Líder (Maxiane)
2. Indicação por consenso dos 3 do Big Fone
3. 2 mais votados pela casa
4. Prova Bate e Volta (escape)

**Template para `data/paredoes.json`:**
```jsonc
{
  "numero": 3,
  "status": "em_andamento",
  "data": "2026-02-03",
  "data_formacao": "2026-02-01",
  "titulo": "3º Paredão — 3 de Fevereiro de 2026",
  "semana": 3,
  "formacao": {
    "resumo": "DESCREVER TODA A FORMAÇÃO",
    "lider": "Maxiane",
    "indicado_lider": "NOME",
    "motivo_lider": "MOTIVO",
    "anjo": "NOME_ANJO",
    "anjo_autoimune": false,
    "imunizado": {"por": "NOME_ANJO", "quem": "NOME_IMUNIZADO"},
    "dinamica": {
      "nome": "Big Fone (Consenso)",
      "indicaram": ["NOME1", "NOME2", "NOME3"],
      "indicado": "NOME"
    },
    "bate_volta": {
      "participantes": ["NOME_A", "NOME_B", "NOME_C"],
      "vencedor": "NOME",
      "prova": "DESCREVER"
    }
  },
  "indicados_finais": [
    {"nome": "NOME", "grupo": "GRUPO", "como": "Líder"},
    {"nome": "NOME", "grupo": "GRUPO", "como": "Big Fone (Consenso)"},
    {"nome": "NOME", "grupo": "GRUPO", "como": "Casa (N votos)"}
  ],
  "votos_casa": {},
  "fontes": ["URL"]
}
```

> **Brigido**: vetado das 3 provas (Líder, Anjo, Bate e Volta). Se cair no paredão, NÃO pode disputar Bate e Volta. Documentar em `bate_volta.impedidos` se relevante.

### Checklist pós-eventos

- [ ] Big Fone #2 registrado em `big_fone[]` + power_event (se aplicável)
- [ ] Big Fone #3 registrado em `big_fone[]` + power_event (se aplicável)
- [ ] Big Fone #4 registrado em `big_fone[]` + power_event (se aplicável)
- [ ] Consenso registrado em power_events (indicacao com actors array)
- [ ] Presente do Anjo registrado (se aceito: imunidade; se não: nada)
- [ ] `data/paredoes.json` com entrada do 3º Paredão
- [ ] `data/provas.json` atualizado (Prova do Líder, Prova do Anjo, Bate e Volta)
- [ ] `python scripts/build_derived_data.py` rodado após cada atualização
- [ ] Fetch API diário para capturar mudanças de roles/VIP
