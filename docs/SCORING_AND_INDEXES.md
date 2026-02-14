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
- **Aliados / Inimigos / Falsos Amigos / Alvos Ocultos**:
  - Built from the **composite pair score** (`pair_sentiment()` using `pairs_daily` from `relations_scores.json`).
  - Score includes: queridômetro (streak-aware: 70% 3-day reactive window + 30% streak memory + break penalty) + power events + votes + Sincerão + VIP (all at full weight, no decay).
  - Categories (based on sign of composite score, not raw emoji):
    - Aliados: score A→B > 0 AND score B→A > 0
    - Inimigos: score A→B < 0 AND score B→A < 0
    - Falsos amigos: score A→B > 0 AND score B→A < 0
    - Alvos ocultos: score A→B < 0 AND score B→A > 0
  - Prediction accuracy: 68% of house votes (vs 37% using queridômetro only). 0% ally betrayals.

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

### Base (queridômetro) — Streak-Aware Scoring

O queridômetro base combina três sinais:

```
Q_reactive(A→B) = Σ w_i * sentiment(emoji_i)   for last 3 days
                  where w = [0.6, 0.3, 0.1]

streak_len      = consecutive days of same sentiment category ending today
consistency     = min(streak_len, 10) / 10       # 0.0–1.0, caps at 10 days
Q_memory(A→B)   = consistency * sentiment(latest_category)

break_penalty   = -0.15 * min(prev_streak, 15) / 15
                  if previous positive streak ≥ 5 broke to negative, else 0

Q_final(A→B)    = 0.7 * Q_reactive + 0.3 * Q_memory + break_penalty
```

**Pesos:**
- **70% reativo** — o emoji de hoje é o sinal mais importante (o jogo é ao vivo)
- **30% memória** — sequências longas reforçam o sinal (15 dias de ❤️ é aliança real)
- **Penalidade de ruptura** é aditiva (máx. −0.15) — sinal de "confiança quebrada"

**Categorias de sentimento:**
- `positive`: ❤️ (Coração)
- `mild_negative`: 🌱💼🍪💔 (Planta, Mala, Biscoito, Coração partido)
- `strong_negative`: 🐍🎯🤮🤥 (Cobra, Alvo, Vômito, Mentiroso)

### Janela curta (mais fiel ao jogo)
- O **queridômetro reativo** usa uma **média móvel curta de 3 dias** (0.6/0.3/0.1),
  centrada na **data de formação** do paredão ativo (ou a última `data_formacao` conhecida).
- A **memória de sequência** considera todo o histórico do par.
- Se faltar snapshot no período, cai para o **snapshot mais recente**.

### Raio-X Ausente (Carry-Forward)

Quando um participante não faz o Raio-X (queridômetro matinal), a API retorna 0 reações para ele naquele dia. Sem tratamento, isso corrompe:
- Continuidade de streaks (gap no `pair_history`)
- Média ponderada de 3 dias (dia mais recente sem dados)
- Pulso diário (mostra perda de todas as reações)

**Detecção** (automática, via `patch_missing_raio_x()` em `data_utils.py`):
- Participante presente no snapshot (não eliminado)
- Zero reações de saída na `build_reaction_matrix()`

**Tratamento**: copia as reações do dia anterior (carry-forward). Aplicado em:
- `compute_streak_data()` — loop principal de histórico de pares
- `compute_base_weights()` / `compute_base_weights_all()` — janela de 3 dias
- `build_daily_changes_summary()` — comparação dia-a-dia

**Não aplicado** em páginas QMD (display) — estas mostram os dados reais da API.

**Metadata**: `relations_scores.json` → campo `missing_raio_x`:
```json
[{"date": "2026-02-01", "participants": ["Juliano Floss"]}]
```

A detecção é puramente baseada nos dados — nenhum nome ou data é hardcoded.

### Detecção de Rupturas de Aliança (Streak Breaks)

Uma ruptura é detectada quando:
1. O par teve **5+ dias consecutivos** de categoria `positive` (❤️)
2. A categoria mudou para `mild_negative` ou `strong_negative`
3. A nova sequência tem no máximo 3 dias (ruptura recente)

**Severidade:**
- `strong`: nova categoria é `strong_negative` (🐍🎯🤮🤥)
- `mild`: nova categoria é `mild_negative` (🌱💼🍪💔)

**Output:** `streak_breaks` list in `relations_scores.json`:
```json
{
  "giver": "Nome",
  "receiver": "Nome",
  "previous_streak": 14,
  "previous_category": "positive",
  "new_emoji": "Cobra",
  "new_category": "strong_negative",
  "date": "2026-01-27",
  "severity": "strong"
}
```

### Event modifiers (weekly + rolling)
- **Power events** (manual + auto, actor → target):
  - `indicacao` −2.8, `contragolpe` −2.8, `monstro` −1.2,
    `voto_anulado` −0.8, `perdeu_voto` −0.6, `imunidade` +0.8
  - `veto_ganha_ganha` −0.4, `ganha_ganha_escolha` +0.3 (baixo impacto)
  - `barrado_baile` −0.4 (baixo impacto, público)
  - `troca_vip` +0.4 (promovido à VIP por dinâmica), `troca_xepa` −0.4 (rebaixado à Xepa por dinâmica, backlash 0.5)
  - `mira_do_lider` −0.5 (público, backlash 0.5; descontinuado após semana 1)
  - Ganha-Ganha é público: quem foi vetado tende a gerar **animosidade leve** contra quem vetou (backlash menor).
  - Sincerão negativo é público: gera **backlash leve** no alvo (bomba/“não ganha”).
  - **Nenhum tipo de evento sofre decay** no rolling — todos acumulam com peso integral. Razão: no BBB, eventos significativos (indicações, Sincerão, votos) criam mágoas duradouras e alianças que não se dissolvem com o tempo. O queridômetro usa scoring streak-aware (70% reativo + 30% memória + penalidade de ruptura).
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
- **Anjo dynamics** (Almoço, Duo, Não-Imunização):

  | Tipo | Direção | Peso | Significado |
  |------|---------|------|-------------|
  | **Almoço do Anjo** | Anjo → convidado | +0.15 | Anjo escolhe 3 pessoas para almoço especial (declaração pública de afinidade) |
  | **Duo Anjo** | Mútuo (A ↔ B) | +0.10 cada | Dupla na Prova do Anjo (colaboração; acumula se repetir) |
  | **Não imunizou** | Aliado mais próximo → Anjo | −0.15 | Anjo autoimune tinha poder extra de imunizar, mas escolheu não usar (decepção sutil do aliado) |

  - Almoço do Anjo é um sinal público — todos na casa sabem quem foi convidado.
  - Duo é parcialmente sorte (sorteio ou contexto), mas repetição (Jonas + Sarah 2×) indica afinidade real.
  - Não-imunizou aplica-se **apenas** quando Anjo autoimune + poder extra disponível + não usado. O aliado mais próximo é o duo partner. Quando o Anjo já imunizou alguém com o poder padrão (semana 1), a recusa do extra é menos impactante e não gera edge.
  - Dados em `manual_events.json` → `weekly_events[].anjo`.

- **Votos da casa** (A vota em B) — segundo ato mais forte depois da indicação direta, pois é uma tentativa deliberada de eliminar.
  Quatro níveis de visibilidade, cada um com pesos diferentes:

  | Tipo | A→B (voter) | B→A (backlash) | Quando usar |
  |------|------------|----------------|-------------|
  | **Secreto** | −2.0 | 0 | Padrão (confessionário). Alvo não sabe quem votou. |
  | **Confissão** | −2.0 | −1.0 | Votante **escolheu** contar ao alvo. Honestidade atenua ressentimento. |
  | **Dedo-duro** | −2.0 | −1.2 | Dinâmica do jogo **revelou** o voto. Exposição involuntária. |
  | **Votação aberta** | −2.5 | −1.5 | Toda a casa viu. Votante **escolheu** hostilidade pública. |

  - Voter→Target é −2.0 para secreto, confissão e dedo-duro — a **intenção** de eliminar é idêntica (voto foi dado no confessionário nos três casos). Votação aberta é −2.5 porque o votante **escolheu** declarar hostilidade publicamente.
  - Votos secretos **não geram backlash** (alvo não sabe).
  - Registro em `manual_events.json`: `confissao_voto`, `dedo_duro`, ou `votacao_aberta` no paredão. Ver `docs/MANUAL_EVENTS_GUIDE.md`.

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

### Três modos de pares

- **`pairs_daily`**: ativos apenas (21 participantes). Queridômetro ancorado em hoje.
- **`pairs_paredao`**: ativos apenas. Queridômetro ancorado na formação do paredão.
- **`pairs_all`**: todos os participantes (ativos + eliminados, exceto Henri Castelli — apenas 1 dia de dados). Cada par inclui `"active_pair": bool` (true se ambos ativos). Q_base de participantes eliminados usa seu último snapshot (`last_seen`).

### Contradição voto × queridômetro

Quando A dá reação positiva (Q > 0) a B mas vota para eliminar B, há uma contradição. O campo `contradictions` no JSON agrega:
- `vote_vs_queridometro`: lista de entradas com actor, target, Q, peso do voto, semana
- `total`, `total_vote_edges`, `rate`: totais e taxa de contradição
- `context_notes`: notas contextuais (ex.: impacto da desistência de Pedro na semana 1)
- Per-pair: `vote_contradiction: true` em `pairs_all` e `pairs_daily`

### Impacto recebido (`received_impact`)

Agregação por participante do peso total de edges recebidas (incoming):
- `positive`: soma de edges positivas recebidas
- `negative`: soma de edges negativas recebidas
- `total`: soma total
- `count`: número de edges recebidas

### Blocos de votação (`voting_blocs`)

Semanas com 4+ participantes votando no mesmo alvo. Cada entrada: `week`, `date`, `target`, `voters` (lista), `count`.

### Anjo autoimune (`anjo_autoimune_events`)

Metadado em `_metadata`: lista de semanas em que o Anjo escolheu autoimunidade (vídeo de família) em vez de imunizar outro participante. Campos: `anjo`, `week`, `date`.

Além do metadado, quando o Anjo é autoimune e não usa o poder extra, uma edge `anjo_nao_imunizou` (−0.15) é gerada do aliado mais próximo (duo partner) → Anjo. Ver seção de pesos acima.

---

## Impacto Negativo Recebido (acumulado)

Reads directly from `received_impact.negative` in `relations_scores.json`. This value is the sum of all negative event edges targeting a participant (power events, votes, Sincerão, visibility factors, backlash), using the same calibrated weights as the Sentiment Index — no separate constants or decay.

Thresholds: 🟢 **NENHUM** (0), 🟡 **BAIXO** (< 0), 🟠 **MÉDIO** (≤ -5), 🔴 **ALTO** (≤ -10).

---

## Hostilidade Gerada (acumulada)

Sums outgoing negative event edges from `pairs_daily` components (excluding `queridometro`). For each target, sums `min(0, component_weight)` for all non-queridômetro components (power events, votes, Sincerão edges, visibility). Uses the same calibrated weights as the pairs system — no separate constants or decay.

Thresholds: 🟢 **NENHUMA** (0), 🟡 **BAIXA** (< 0), 🟠 **MÉDIA** (≤ -4), 🔴 **ALTA** (≤ -8).

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
- `mira_do_lider`: **0.5**

### Na Mira do Líder (descontinuado)

Dinâmica usada apenas na semana 1 (liderança de Alberto Cowboy) e descontinuada após backlash do público.

**Regra**: O líder escolhe **5 participantes** como alvos potenciais na sexta-feira. No domingo, deve indicar **exatamente 1 dos 5** ao paredão — não pode escolher fora da lista.

**Peso no scoring**: −0.5 (actor → target) para cada um dos 5 alvos. O indicado final recebe adicionalmente `indicacao` (−2.8). Backlash factor: 0.5 (target → leader). Visibilidade: pública (fator 1.2×).

**Planta Index**: target activity 0.5 (ser alvo gera visibilidade moderada).

**Por que −0.5?** É uma declaração pública de distância/desconfiança do líder, mas sem consequência direta para 4 dos 5 alvos. Similar a `exposto` ou `barrado_baile` em gravidade.

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
  - Na Mira do Líder (alvo): 0.5
  - Bate-Volta (vencedor): 2.5
  - Ganha-Ganha (veto/decisão): **não entra** no Planta Index (baixo impacto de jogo).
  - Ganha-Ganha (sorteados): **leve atividade** (+0.3) só para sinalizar participação mínima.
  - Voltou do paredão: 2.0
- **Indicação/Contragolpe**: contam para quem indicou **e** para o alvo (peso menor).
- **Baixa exposição no Sincerão**: usa **participação + edges**:
  `sinc_activity = (participou ? 1 : 0) + 0.5 * edges`
  `low_sincerao = 1 − (sinc_activity / max_sinc_activity)`
- **Emoji 🌱**: média diária da proporção de "Planta" recebida na semana, com cap de 0.30.
- **Consenso ❤️ (heart_uniformity)**: avg daily(hearts_received / total_received), cap 85%.
  Soft-gated: `effective = raw × low_power_events`. Active players → ~0 contribution.
- **Bônus "planta da casa"**: +15 points (plateia escolhe planta no Sincerão).

### Weights (base)
```
0.10 * Invisibilidade
0.35 * Baixa atividade de poder
0.25 * Baixa exposição no Sincerão
0.15 * Emoji 🌱
0.15 * Consenso ❤️
```
Score = base * 100 + bonus (clamped 0–100).

### Sincerão carry-forward
When no Sincerão in current week, previous week's `low_sincerao` value × 0.7 decay.
Two consecutive weeks without Sincerão → 0.49× of original value.

### Manual event required (plateia "planta da casa")
Add to `manual_events.json` under `weekly_events[].sincerao.planta`:
```
{ "target": "Nome do participante", "source": "plateia" }
```
This is a **weekly** signal and does **not** carry to the next week.

### Planta Index breakdown page
Use `planta_debug.qmd` to inspect the full tally per participant (component points + raw signals + events list).

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

**Per-pair edges (directional)** — used in `build_relations_scores()`:
- `podio slot 1`: +0.7
- `podio slot 2`: +0.5
- `podio slot 3`: +0.3
- `nao_ganha`: −1.0
- `bomba/tema`: −0.8
- Backlash factors: `nao_ganha` 0.3, `bomba` 0.4 (target → actor)

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

## Prova Rankings (competition performance)

Per-participant ranking based on placement in each BBB26 competition. Computed in `data/derived/prova_rankings.json` from `data/provas.json`.

### Competition types and multipliers

| Type | Multiplier | Description |
|------|-----------|-------------|
| `lider` | 1.5× | Prova do Líder — highest stakes, winner leads the house |
| `anjo` | 1.0× | Prova do Anjo — winner protects someone |
| `bate_volta` | 0.75× | Bate e Volta — paredão escape, fewer participants |

### Placement points

| Position | Base Points |
|----------|-------------|
| 1st | 10 |
| 2nd | 7 |
| 3rd | 5 |
| 4th | 4 |
| 5th | 3 |
| 6th | 2 |
| 7th-8th | 1 |
| 9th+ | 0.5 |
| DQ | 0 |

**Weighted points** = base_points × type_multiplier

### Position assignment logic

- **Single phase**: positions come directly from `classificacao`.
- **Multi-phase (duo → individual)**: Phase 2 finalists get Phase 2 positions. Phase 1 non-finalists get their Phase 1 position + offset (number of Phase 2 slots).
- **Duo phases**: both members of a duo share the duo's position.
- **Ties**: all tied participants get the same position points.
- **DQ**: 0 points.
- **Excluded** (líder, lottery, medical): `null` — not counted in averages.
- **Unknown position**: `null` — only score what we know.

### Per-participant aggregation

- `total_points`: sum of all weighted points
- `avg_points`: total / participated
- `provas_participated`: count where points ≠ null
- `provas_available`: total provas while in the house
- `participation_rate`: participated / available
- `wins`: 1st place finishes
- `top3`: top-3 finishes
- `best_position`: best placement achieved

### Bracket data structure (duel-format)

Provas with duel/elimination formats (e.g., `eliminacao_duelos`) use a richer bracket structure in their phase data:

- `classificacao_quartas`: array of quarterfinal duels `{duelo, jogadores, vencedor, nota?}`
- `classificacao_semis`: array of semifinal duels
- `classificacao_final`: array of final duels

These are rendered as a visual bracket tree in `provas.qmd`. The standard `classificacao` array still exists alongside for ranking purposes.

### Data source

`data/provas.json` — manual data with competition results, phases, and standings.
Built by `build_prova_rankings()` in `scripts/build_derived_data.py`.

---

## VIP/Xepa Tracking

A **VIP period** corresponds to one Líder's reign. VIP group is set once when a new Líder takes power.

### How VIP weeks are counted
- Walk `roles_daily.json` and detect dates where the Líder role changes to a new person.
- On each leader transition date, the last daily snapshot reflects the new leader's VIP selection.
- Count +1 VIP or +1 Xepa per participant per leader period.
- Maximum VIP selections = number of distinct leaders.

### Leader periods (`leader_periods` in `index_data.json`)
Each entry contains:
- `leader`: name of the Líder
- `start`: date the Líder took power
- `end`: date the next Líder took power (or latest date if current)
- `vip`: list of participants in VIP during this period
- `xepa`: list of participants in Xepa during this period

### Why not track VIP composition changes?
VIP composition can change for reasons other than leader selection (late entrants joining the house, participants quitting). Tracking leader transitions from `roles_daily.json` ensures we count only actual leader selections.

### Data source
Built by `build_index_data.py`. Uses `roles_daily.json` for leader transitions and daily snapshots for VIP/Xepa group membership.

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
- **Cores dos chips**: seguir as categorias de relação do perfil (Aliados=verde, Inimigos=vermelho, Falsos Amigos=amarelo, Alvos Ocultos=roxo).

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
4. **Impacto Negativo calibrado** — Compare cumulative negative impact vs actual house votes received to validate weights (now uses same weights as pairs system).
5. **Efeito do Monstro/Anjo** — Show how targets' reactions change the day after the event.
6. **Mapa de votos revelados (dedo-duro)** — Surface only revealed votes as public signals in perfis.
7. **Polarização vs Popularidade** — Scatter: sentiment vs #inimigos / falsos amigos.
8. **Coesão por grupo (Pipoca/Veterano/Camarote)** — Group-level affinity + volatility over time.

**Rule of thumb:** Cartola points are precomputed in `data/derived/cartola_data.json`. `cartola.qmd` loads this JSON for rendering only. Cartola points should never drive non-Cartola insights.

---

## Game Timeline (`game_timeline.json`)

Unified chronological timeline merging **all** event sources into a single feed. Displayed as "Cronologia do Jogo" in both `index.qmd` (first section) and `evolucao.qmd`.

### Sources (merged in order)
1. **Entries & exits** — from `eliminations_detected.json` + `manual_events.participants`
2. **Auto roles** — Líder, Anjo, Monstro, Imune from `auto_events.json`
3. **Power events** — from `manual_events.power_events` (indicação, contragolpe, veto, etc.)
4. **Weekly events** — Big Fone, Sincerão, Ganha-Ganha, Barrado no Baile from `manual_events.weekly_events`
5. **Paredão** — formation + resultado from `paredoes.json`
6. **Special events** — dinâmicas from `manual_events.special_events`
7. **Scheduled events** — future events from `manual_events.scheduled_events` (tagged `status: "scheduled"`)

### Event schema
```json
{
  "date": "2026-01-30",
  "week": 3,
  "category": "big_fone",
  "emoji": "📞",
  "title": "Big Fone — Babu Santana atendeu",
  "detail": "Recebeu pulseira prateada...",
  "participants": ["Babu Santana"],
  "source": "weekly_events",
  "status": "scheduled",  // only for future events; absent for past events
  "time": "Ao Vivo"       // only for scheduled events
}
```

### Deduplication
Scheduled placeholders are skipped when a real event already exists with the same `(date, category)`.
Final timeline dedup keeps the first occurrence of exact `(date, category, title)` duplicates.

### Rendering
- **Past events**: solid border, filled badge, plain detail text
- **Scheduled events**: dashed border, outlined badge, 🔮 prefix on detail, yellow time badge

---

## Líder Nomination Prediction

**Location**: `paredao.qmd` (primary) + `relacoes_debug.qmd` (debug copy)

**Purpose**: Forward-looking section that predicts who the current Líder is most likely to nominate, based on accumulated relationship scores.

### Visibility Conditions

Auto-gated: shows between paredões (`ultimo.status == 'finalizado'`) or during incomplete formation (`em_andamento` with fewer than expected nominees). Hides once formation is complete (vote analysis takes over).

### Algorithm

1. **Detect Líder** from `roles_daily.json` → `daily[-1].roles.Líder[0]`
2. **Load Líder → all scores** from `relations_scores.json` → `pairs_daily[lider_name]`
3. **Filter** to active participants only (from `participants_index.json`), excluding the Líder
4. **Sort ascending** by `score` — most negative = most likely nomination target
5. **Flag VIP members** as unlikely targets (Líder chose them)
6. **Flag immune** participants from active paredão entry

### Score Decomposition

Each pair entry in `pairs_daily` contains:
```python
{
    "score": float,          # Total composite score
    "components": {
        "queridometro": float,  # Streak-aware: 70% reactive + 30% memory + break penalty
        "power_event": float,   # Monstro, indicação, contragolpe, etc. (accumulated)
        "sincerao": float,      # Sincerão direct + backlash edges (accumulated)
        "vote": float,          # House votes (accumulated)
        "vip": float,           # VIP alliance signal
        "anjo": float,          # Anjo protection signal
    },
    "streak_len": int,       # Days of current reaction streak
    "break": bool,           # True if a long positive streak recently broke negative
}
```

### Reciprocity Analysis

For each target, the reverse score (`target → Líder`) is loaded to classify the relationship:

| Líder → Target | Target → Líder | Label | Color |
|---------------|---------------|-------|-------|
| < 0 | < 0 | ⚔️ Mútua | Red |
| < 0 | ≥ 0 | 🔍 Alvo cego | Orange |
| ≥ 0 | < 0 | ⚠️ Risco oculto | Orange |
| ≥ 0 | ≥ 0 | 💚 Aliados | Green |

### Expandable Detail Rows

Each participant row has a collapsible `<details>` section showing:
- **Edges**: All historical events between Líder ↔ target (both directions), with date, type, weight, direction, event_type, backlash flag
- **Queridômetro timeline**: Last 14 days of daily reactions (Líder→target and target→Líder), color-coded by sentiment weight

### Data Dependencies

- `data/derived/relations_scores.json` — `pairs_daily` + `edges`
- `data/derived/roles_daily.json` — current Líder, Anjo, VIP
- `data/derived/participants_index.json` — active status + avatars
- Daily snapshot matrices (already loaded in `paredao.qmd` setup)

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
