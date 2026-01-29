# Scoring & Indexes — Full Specification

This document contains all scoring formulas, weights, and index specifications for the BBB26 project.
Referenced from `CLAUDE.md` — read this when implementing or modifying scoring logic.

## Participant Data Points

### Raw participant data (from snapshots)
- **Reações recebidas**: list of emojis + givers (who gave which reaction).
- **Saldo (balance)**, **grupo** (Vip/Xepa), **roles** (Líder/Anjo/Monstro/Imune/Paredão).
- **Avatar**, **grupo de origem** (Pipoca/Veterano/Camarote).

### Derived per-participant metrics (current snapshot)
- **Sentiment score**: weighted sum of received reactions.
  - Weights: Coração +1; Planta/Mala/Biscoito/💔 −0.5; Cobra/Alvo/Vômito/Mentiroso −1.
- **Aliados / Inimigos / Falsos Amigos / Inimigos Não Declarados**:
  - Built from the **reaction matrix** (giver → receiver).
  - Categories:
    - Aliados: ❤️↔❤️
    - Inimigos declarados: neg↔neg
    - Falsos amigos: A dá ❤️, recebe neg de B
    - Inimigos não declarados: A dá neg, recebe ❤️ de B

### Event data (rare, manual + auto)
- **Power events** (manual + auto events): usually **one actor → one target**.
- These are **sparse** compared to queridômetro (daily), so they should be **modifiers**, not the base.
- Weekly effects (risk) **do not carry**; historical effects (animosity) accumulate without decay (events persist in participants' memory).
- **Sincerão edges** (manual): explicit A → B signals (pódio, "não ganha", bombas/temas).
  - Use as **small modifiers** to the sentiment index (see Sincerão framework below).
- **Bate-Volta** (manual): vencedor sai do paredão e conta como **evento positivo** no Planta Index.

### Why power events are "modifiers"
- They are **rare** and usually **one-to-one** (actor → target).
- Queridômetro is daily and captures **ongoing sentiment**.
- Events should **tilt** the index, not dominate it.

---

## Sentiment Index (A → B)

Purpose: a **directional score** showing how A feels about B, combining private (queridômetro)
and public (power events / Sincerão / votos / VIP) signals.

Computed in `data/derived/relations_scores.json`:
- `pairs_daily` para uso geral diário.
- `pairs_paredao` para análises de coerência na formação do paredão.

### Base (queridômetro)
```
Q(A→B) = weight(reaction_label from A to B)
```

### Janela curta (mais fiel ao jogo)
- O **queridômetro base** usa uma **média móvel curta de 3 dias** (0.6/0.3/0.1),
  centrada na **data de formação** do paredão ativo (ou a última `data_formacao` conhecida).
- Se faltar snapshot no período, cai para o **snapshot mais recente**.

### Event modifiers (weekly + rolling)
- **Power events** (manual + auto, actor → target):
  - `indicacao` −2.8, `contragolpe` −2.8, `monstro` −1.2,
    `voto_anulado` −0.8, `perdeu_voto` −0.6, `imunidade` +0.8
  - `veto_ganha_ganha` −0.4, `ganha_ganha_escolha` +0.3 (baixo impacto)
  - `barrado_baile` −0.4 (baixo impacto, público)
  - Ganha-Ganha é público: quem foi vetado tende a gerar **animosidade leve** contra quem vetou (backlash menor).
  - Sincerão negativo é público: gera **backlash leve** no alvo (bomba/“não ganha”).
  - **Nenhum tipo de evento sofre decay** no rolling — todos acumulam com peso integral. Razão: no BBB, eventos significativos (indicações, Sincerão, votos) criam mágoas duradouras e alianças que não se dissolvem com o tempo. O queridômetro já usa janela curta de 3 dias como base.
  - **Self-inflicted** events do not create A→B edges.
  - **Consensus** (ex.: Alberto + Brigido) = **full weight for each actor**.
  - **Public** indicacao/contragolpe also add **backlash** B→A (peso menor, fator 0.6).
  - **Eventos públicos** são amplificados (fator 1.2); secretos = 0.5.
- **Sincerão edges**:
  - pódio slot 1/2/3 = +0.7/+0.5/+0.3
  - "não ganha" −1.0, "bomba" −0.8
- **VIP** (líder → VIPs da semana): +0.2
  - Usa a lista VIP do **primeiro dia** de cada reinado do líder (antes de novos participantes distorcerem a lista).
  - Novos entrantes que recebem VIP automático do programa (não escolha do líder) são **excluídos**.
  - Cada líder gera edges na **semana correta** (ex.: se o líder ainda aparece na API porque a próxima prova não ocorreu, o week permanece o da sua liderança real).
- **Votos da casa** (A vota em B) — segundo ato mais forte depois da indicação direta, pois é uma tentativa deliberada de eliminar:
  - voto **secreto**: −2.0 (conta para A→B)
  - voto **revelado** (dedo-duro / votação aberta): −2.5 (conta para A→B)
  - votos secretos **não alteram B→A**; só impactam quem votou.
  - voto **revelado ao alvo**: adiciona **backlash** B→A (−1.2) porque o alvo agora sabe quem votou.

### Dois modos de score
- **Diário (`pairs_daily`)**: queridômetro base ancorado em **hoje** (rolling 3 dias) + todos os eventos acumulados.
- **Paredão (`pairs_paredao`)**: queridômetro base ancorado na **data_formacao** do paredão + todos os eventos acumulados. Usada para análise de coerência social.

A diferença entre os dois modos é **apenas o queridômetro base** (qual snapshot de 3 dias). Os eventos são idênticos.

### Score (acumulado, sem decay)
```
Score(A→B) = Q(base 3d) + Σ eventos (peso integral, sem decay)
```

**Por que sem decay?** No BBB, eventos do jogo (indicações, votos, Sincerão, contragolpes) criam impacto duradouro — participantes não "esquecem" uma indicação ou bomba do Sincerão só porque passaram semanas. Exemplos reais: Sarah e Juliano viraram inimigos após Sincerão; Leandro não perdoou Brigido e Alberto após indicação. O queridômetro é o único sinal "fraco" (obrigatório, secreto, sem consequência direta) e já usa janela curta de 3 dias como base — não precisa de decay adicional.

### Relationship Summary Score (A ↔ B)
For symmetric views (alliances / rivalries):
```
score_mutual = 0.5 * Score(A→B) + 0.5 * Score(B→A)
```

---

## Risco Externo (weekly, from events + votes)

Computed **per participant, per week**. Uses weighted negative events + votes received:
```
risco_externo = 1.0 * votos_recebidos
              + Σ pesos_prejuizos_publicos
              + 0.5 * Σ pesos_prejuizos_secretos
              + 0.5 * auto_infligidos
              + 2 (se estiver no Paredão)
```

**Risco (sugestão de cálculo)**:
- Separar em **Risco social (percebido)** vs **Risco externo (real)**.
- `Risco social`: peso maior para eventos **públicos** de prejuízo causados por outros + conflitos/reactions negativas.

---

## Animosidade (historical, sem decay)

Directional: if **A** inflicts negative events on **B**, A accumulates animosity:
```
animosidade = 0.25 * reacoes_negativas_recebidas
            + 0.5 * hostilidades_recebidas
            + 1.5 * Σ peso_evento
```
Sem decay — eventos acumulam com peso integral (mesma política do score rolling).

- **Animosidade index** é **experimental** e deve ser **recalibrado semanalmente** após indicações/contragolpes/votações.
- Registre ajustes no `IMPLEMENTATION_PLAN.md` para manter histórico e evitar esquecimento.

---

## Pesos por tipo de power_event

### Impacto negativo (para o alvo)
- `indicacao`: **2.5**
- `contragolpe`: **2.5**
- `emparedado`: **2.0**
- `veto_prova`: **1.5**
- `monstro`: **1.2**
- `perdeu_voto`: **1.0**
- `voto_anulado`: **0.8**
- `voto_duplo`: **0.6**
- `exposto`: **0.5**

### Pesos para Animosidade (autor do evento)
- `indicacao`, `contragolpe`: **2.0**
- `monstro`: **1.2**
- `perdeu_voto`, `voto_anulado`: **0.8**
- `voto_duplo`: **0.6**
- `exposto`: **0.5**

---

## Planta Index (weekly + rolling)

Goal: quantify how **"planta"** a participant is (low visibility + low participation).
Computed weekly in `data/derived/plant_index.json` with a 2-week rolling average.

### Signals (per week)
- **Invisibilidade**: 1 − percentile(total_reacoes) within the week (peso 0 no score atual).
- **Baixa atividade de poder**: 1 − (atividade_poder / max_atividade_poder).
  Atividade usa pesos por tipo:
  - Líder (ganhou): 4.0
  - Anjo (ganhou): 3.0
  - Monstro (recebeu): 3.0
  - Imunidade: 0.4
  - Indicação/Contragolpe (ator): 2.5
  - Indicação/Contragolpe (alvo): 1.5
  - Voto 2x / Voto anulado (ator): 2.0
  - Perdeu voto (alvo): 1.0
  - Barrado no Baile (alvo): 0.3
  - Bate-Volta (vencedor): 2.5
  - Ganha-Ganha (veto/decisão): **não entra** no Planta Index (baixo impacto de jogo).
  - Ganha-Ganha (sorteados): **leve atividade** (+0.3) só para sinalizar participação mínima.
  - Voltou do paredão: 2.0
- **Indicação/Contragolpe**: contam para quem indicou **e** para o alvo (peso menor).
- **Baixa exposição no Sincerão**: usa **participação + edges**:
  `sinc_activity = (participou ? 1 : 0) + 0.5 * edges`
  `low_sincerao = 1 − (sinc_activity / max_sinc_activity)`
- **Emoji 🌱**: média diária da proporção de "Planta" recebida na semana, com cap de 0.30.
- **Bônus "planta da casa"**: +15 points (plateia escolhe planta no Sincerão).

### Weights (base)
```
0.45 * Baixa atividade de poder
0.35 * Baixa exposição no Sincerão
0.20 * Emoji 🌱
```
Score = base * 100 + bonus (clamped 0–100). Invisibilidade não entra no score atual.

### Manual event required (plateia "planta da casa")
Add to `manual_events.json` under `weekly_events[].sincerao.planta`:
```
{ "target": "Nome do participante", "source": "plateia" }
```
This is a **weekly** signal and does **not** carry to the next week.

### Planta Index breakdown page
Use `planta.qmd` to inspect the full tally per participant (component points + raw signals + events list).

---

## Sincerão (manual framework)

Sincerão is **manual-only** and varies by week. It creates **explicit directional signals** (A → B).
Because it's **rare** and typically **1-to-1**, it should **modify** the sentiment index, not replace it.

### Where to store
- `data/manual_events.json` → `weekly_events[].sincerao`

### Recommended schema (lightweight)
```json
{
  "date": "YYYY-MM-DD",
  "format": "pódio + quem não ganha | bombas | etc",
  "participacao": "todos | protagonistas da semana + plateia",
  "protagonistas": ["..."],
  "temas_publico": ["mais falso", "..."],
  "planta": { "target": "Nome", "source": "plateia" },
  "notes": "...",
  "fontes": ["https://..."]
}
```

### Per-pair edges (for the sentiment index)
Store an optional list of **edges**:
```json
"edges": [
  { "actor": "A", "target": "B", "type": "podio", "slot": 1 },
  { "actor": "A", "target": "C", "type": "podio", "slot": 2 },
  { "actor": "A", "target": "D", "type": "nao_ganha" },
  { "actor": "A", "target": "E", "type": "bomba", "tema": "mais falso" }
]
```

### Derived signal (optional)
- `nao_citado_no_podio`: if **todos participam**, participants not cited in any podium.
  - This is **not directional**, but signals low popularity/visibility.

### Weights used in derived data

**Aggregate (week summary)**:
- `podio_mention`: +0.25 per mention
- `nao_ganha_mention`: −0.5 per mention
- `sem_podio`: −0.4
- `planta` (plateia): −0.3

**Per-pair edges (directional)**:
- `podio slot 1`: +0.6
- `podio slot 2`: +0.4
- `podio slot 3`: +0.2
- `nao_ganha`: −0.8
- `bomba/tema`: −0.6

### Alignment score (Sincerão × Queridômetro)
```
sinc_norm = sinc_score / max_abs_sinc_week
sent_norm = sentiment_score / max_abs_sentiment_day
alignment = 1 - |sinc_norm - sent_norm|
```
Higher = more aligned; lower = contradiction.

### Sincerão workflow
1. After Sincerão (Monday), update `weekly_events[].sincerao` with date/format/notes.
2. If per-pair edges are available, fill `edges`.
3. Add **fontes** (GShow) to the event.
4. Run `python scripts/build_derived_data.py`.
5. Run `python scripts/update_programa_doc.py` (updates internal weekly timeline).

---

## Cartola BBB Points

### Points table
| Event | Points |
|-------|--------|
| Líder | +80 |
| Anjo | +45 |
| Quarto Secreto | +40 |
| Imunizado / Big Fone | +30 |
| Salvo do paredão | +25 |
| Não eliminado no paredão | +20 |
| Não emparedado | +10 |
| VIP / Não recebeu votos | +5 |
| Monstro retirado do VIP | -5 |
| Monstro | -10 |
| Emparedado | -15 |
| Eliminado | -20 |
| Desclassificado | -25 |
| Desistente | -30 |

### Regras oficiais (GShow)
- **Fonte oficial**: https://gshow.globo.com/realities/bbb/bbb-26/cartola-bbb/noticia/o-que-e-cartola-bbb-entenda-como-funciona-a-novidade-do-reality.ghtml
- **Líder (+80)**: maior pontuação; **não acumula com outros itens**.
- **Anjo (+45)**: quando **autoimune**, **acumula com Imunizado**.
- **Quarto Secreto (+40)**.
- **Imunizado por dinâmica (+30)**: não acumula com **Não emparedado**, **Não recebeu votos** e **Salvo do paredão**.
- **Atendeu Big Fone (+30)**: acumula com efeitos do Big Fone (pode somar **Imunizado +30** ou **Emparedado -15**).
- **Salvo do paredão (+25)**: quando emparedado é salvo por dinâmica (ex.: Bate-Volta/Big Fone). **Não recebe "Não emparedado"**, mas acumula com **Emparedado**. Se foi emparedado com janela fechada e salvo com janela aberta, vale apenas **Emparedado**.
- **Não eliminado no paredão (+20)**: indicado que permanece após votação.
- **Não emparedado (+10)**: disponível para votação e não foi ao paredão; **não vale para imunizados (Líder/Anjo) nem salvos**.
- **VIP (+5)**: não acumula com Líder.
- **Não recebeu votos da casa (+5)**: disponíveis para votação **sem votos**; não vale para Líder e imunizados.
- **Palpites (+5)**: pontos extras por acerto de palpites (não modelado no dashboard).
- **Janela de escalação**: quando aberta, **dinâmicas não pontuam** (não modelamos janela; calculamos pelos eventos reais).
- **Nota do dashboard**: calculamos **pontuação por participante**, sem times/palpites individuais.

### Cartola manual events (use `cartola_points_log`)
- Events **not inferable from API snapshots** should be logged here with points and date.
- Examples: `salvo_paredao`, `nao_eliminado_paredao`, `nao_emparedado`, `monstro_retirado_vip`.
- Structure: one entry per participant/week with `events: [{event, points, date, fonte?}]`.
- Always include matching `fontes` in `manual_events.json` for the underlying real-world event.

### Cartola auto-derived points (from `data/paredoes.json`)
- `salvo_paredao` — **Venceu o Bate e Volta** (escapou do paredão). Não acumula com `nao_emparedado`.
- `nao_eliminado_paredao` — Indicados finais que **permaneceram** após o resultado.
- `nao_emparedado` — Participantes **ativos** na semana **fora da lista final** do paredão.

---

## Power Events — Awareness & Visibility

- `actor` e `target` devem sempre existir — o **alvo sabe quem causou** o evento quando a dinâmica é pública (Big Fone, Caixas-Surpresa, Líder/Anjo).
- Para eventos **auto-infligidos** (`actor == target`), trate como **auto-impacto** (ex.: "perdeu voto" ao abrir caixa).
- Campos opcionais:
  - `self_inflicted`: `true|false` (se `actor == target`).
  - `visibility`: `public` (sabido na casa) ou `secret` (só revelado depois).
  - `awareness`: `known`/`unknown` (se o alvo sabe quem causou).

### VIP & Xepa (passe do Líder)
- O Líder recebe **pulseiras de VIP** para distribuir; os escolhidos têm **uma semana de conforto** no VIP.
- **Uso analítico**: quem recebe VIP do Líder é um **sinal positivo de relação/aliança** (peso leve, semanal).
- **Fonte de dados**: a API já expõe `characteristics.group` como `Vip`/`Xepa`, então dá para derivar edges `lider -> vip` (benefício) na semana do Líder.
- Observação: VIP é **dinâmica da semana**, não deve "carregar" para semanas seguintes.
- **Caveat (Quarto Branco / entradas tardias)**: participantes que **entraram após** a vitória do Líder **não recebem** o VIP dele; não criar edge positiva nesses casos.
  (Implementado via `first_seen` <= `leader_start_date` no build).

### Votos da casa (público após formação)
- Estão em `data/paredoes.json` → `votos_casa` e **só são públicos após a formação**.
- Para UI: mostrar como **"votos recebidos"** (sem indicar segredo); não usar como "sinal percebido" antes da revelação.
- Se houver dinâmica tipo **dedo-duro**, registrar em `manual_events.weekly_events`:
  - `dedo_duro`: `{ "votante": "...", "alvo": "...", "detalhe": "...", "date": "YYYY-MM-DD" }`
  - Esses votos passam a ser **públicos na casa**: marcar com 👁️ e permitir uso em análises de percepção.

### Timing — quando algo é "atual" vs "histórico"
- **Papéis ativos (API)**: Líder/Anjo/Monstro/Imune/Paredão são **atuais enquanto o papel existir no último snapshot**. Quando o papel some, vira **histórico**.
- **Paredão em andamento**: use `data/paredoes.json` (`status: em_andamento`) como **semana de referência** para votos e efeitos da formação. Só vira histórico quando `status: finalizado`.
- **Eventos da formação**: **atuais durante o paredão em andamento**; viram **histórico** após o resultado.
- **Sincerão**: impactos são **da semana** (não carregam para a semana seguinte), mas permanecem no histórico com decaimento.
- **Auto-infligidos**: contam como risco **apenas na semana atual**, mas continuam registrados no histórico.

### Perfis Individuais — uso recomendado (UI)
- Mostrar **Poderes recebidos** em duas linhas:
  - `+` (benefícios) e `−` (prejuízos), com chips compactos: ícone + mini-avatar do **ator**.
  - Quando houver repetição, mostrar `2x`/`3x`.
- Para eventos **auto-infligidos**, usar badge `auto` (ex.: ↺) e reduzir peso no "risco social".
- Mostrar **Votos da casa recebidos** como linha separada.
- **Cores dos chips**: seguir as categorias de relação do perfil (Aliados=verde, Inimigos Declarados=vermelho, Falsos Amigos=amarelo, Inimigos Não Declarados=roxo).

---

## Porting Logic to `daily_metrics.json`

Use `data/derived/daily_metrics.json` whenever a chart only needs **per-day aggregates** (no per-giver/per-receiver matrix).

**Good candidates**:
- Sentiment timelines (already ported)
- Daily totals by participant (total_reactions)
- Per-day top 3/bottom 3 sentiment
- Daily participant counts

**Not good candidates (need full matrices)**:
- Cross tables (giver→receiver reactions)
- Mutual hostility/reciprocity analysis
- Sankey of daily reaction shifts

**How to add new fields**:
1. Update `scripts/build_derived_data.py` → `build_daily_metrics()` to compute the metric per snapshot day.
2. Add the new field to each `daily` entry.
3. Rebuild: `python scripts/build_derived_data.py`.
4. In the QMD, load `daily_metrics.json` and **fallback to snapshots** if the field is missing.

**Schema (current)**:
```
data/derived/daily_metrics.json
{
  "_metadata": {...},
  "daily": [
    {
      "date": "YYYY-MM-DD",
      "participant_count": 22,
      "total_reactions": 462,
      "sentiment": { "Nome": 12.5, ... }
    }
  ]
}
```

---

## Cross-Reference Opportunities (ideas for new visuals)

These are **safe cross-page ideas** using only existing data:

1. **Eventos → Mudanças de sentimento** — Overlay `power_events` on daily sentiment timeline to show pre/post shifts.
2. **Voto vs Queridômetro (contradições)** — Highlight cases where someone dá ❤️ but votou contra.
3. **Caminho do Paredão** — Formation flow (Líder/Anjo/indicação/contragolpe/votos) with timestamps + outcomes.
4. **Risco externo calibrado** — Compare weekly risk score vs actual house votes received to validate weights.
5. **Efeito do Monstro/Anjo** — Show how targets' reactions change the day after the event.
6. **Mapa de votos revelados (dedo-duro)** — Surface only revealed votes as public signals in perfis.
7. **Polarização vs Popularidade** — Scatter: sentiment vs #inimigos / falsos amigos.
8. **Coesão por grupo (Pipoca/Veterano/Camarote)** — Group-level affinity + volatility over time.

**Rule of thumb:** Cartola points are precomputed in `data/derived/cartola_data.json`. `cartola.qmd` loads this JSON for rendering only. Cartola points should never drive non-Cartola insights.

---

## Consolidation History

**Implemented (2026-01-26)**:
- `data/derived/participants_index.json` — canonical list (name, grupo, avatar, first/last seen, active, status).
- `data/derived/roles_daily.json` — roles + VIP per day (one snapshot/day).
- `data/derived/auto_events.json` — role-change events (Líder/Anjo/Monstro/Imune) with `origem: api`.
- `data/derived/daily_metrics.json` — per-day sentiment + total reactions.
- `data/derived/validation.json` — warnings for manual data mismatches.
- `scripts/build_derived_data.py` builds all derived files.
- `scripts/fetch_data.py` calls derived builder by default.

**Implemented (2026-01-28)**:
- `data/derived/cartola_data.json` — Cartola BBB points (leaderboard, weekly breakdown, stats, seen/current roles). Computed by `build_cartola_data()` in `build_derived_data.py`.
- `cartola.qmd` now loads precomputed JSON instead of computing ~430 lines inline.
- Cartola constants (`CARTOLA_POINTS`, `POINTS_LABELS`, `POINTS_EMOJI`) and `get_week_number()` moved to `data_utils.py`.
- `scripts/analyze_snapshots.py` fixed: uses relative path, imports from `data_utils`, fixed `Coração partido` misclassification bug (was `STRONG_NEGATIVE`, now correctly `MILD_NEGATIVE`).
