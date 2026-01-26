# Review UX/Arquitetura de Informacao - BBB26 Dashboard

**Revisor**: Claude Opus 4.5
**Foco**: Secoes 1-6 (Landing Page, Ordenacao de Secoes, Dados Cross-Page, Insights Faltantes, Hierarquia Visual, Layout de Paginas)
**Data**: 2026-01-25

---

## 1. Sumario Executivo

As 5 maiores oportunidades de UX identificadas:

1. **Falta de "Destaques do Dia" na landing page** — O usuario precisa rolar muito para entender o que mudou. Um resumo automatico no topo com 3-5 bullet points captaria atencao imediata e criaria um "gancho" diario.

2. **Trajetoria.qmd esta sobrecarregada (21 secoes!)** — Precisa ser dividida em sub-paginas ou reorganizada com navegacao por abas. E a pagina mais densa do site e usuarios se perdem.

3. **Paredao atual nao esta visivel na landing** — O evento mais importante da semana (quem esta no paredao, quem pode sair) esta escondido em outra pagina. Deveria ter destaque proeminente no Painel.

4. **Narrativa fragmentada entre paginas** — O fluxo "O que esta acontecendo agora? → O que mudou? → Por que importa?" esta quebrado. A historia precisa fluir melhor.

5. **Perfis Individuais no final da landing page** — Sao extremamente uteis mas estao "abaixo da dobra". Deveriam ter acesso rapido ou busca.

---

## 2. Recomendacoes para Landing Page (index.qmd)

### Ordem de Secoes Proposta

```
ACIMA DA DOBRA (primeira tela):
┌─────────────────────────────────────────────────────────────────┐
│  DESTAQUES DO DIA (NOVO)                                        │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ • Jonas (+3.5) lidera ranking pela 3a vez consecutiva       ││
│  │ • Marcelo → Solange: de ❤️ para 🐍 (maior mudanca do dia)   ││
│  │ • Leandro esta no Paredao (indicado por dinamica)           ││
│  │ • 95 reacoes mudaram ontem (21% do total)                   ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  PAREDAO ATUAL (card compacto)           RANKING TOP 5          │
│  ┌────────────────────────────┐    ┌────────────────────────────┐│
│  │ 2o Paredao - Em Formacao   │    │ 1. Jonas       +14.5       ││
│  │ [Leandro] [?] [?]          │    │ 2. Jordana     +10.0       ││
│  │ Ver detalhes →             │    │ 3. Babu        +8.5        ││
│  └────────────────────────────┘    │ 4. Ana Paula   +6.0        ││
│                                     │ 5. Sol         +5.5        ││
│                                     │ Ver ranking completo →     ││
│                                     └────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘

ABAIXO DA DOBRA:
1. Ranking de Sentimento (completo com barra horizontal)
2. Tabela Cruzada de Reacoes (heatmap)
3. Reacoes Recebidas (tabela)
4. Perfis Individuais (com busca/filtro por nome)
5. Cronologia do Jogo (movido para o final - menos urgente)
```

### Secoes Novas a Adicionar

| Secao | Descricao | Complexidade | Impacto |
|-------|-----------|--------------|---------|
| **Destaques do Dia** | 3-5 bullet points auto-gerados: maior subida/queda, mudanca dramatica, status paredao | Media | Alto |
| **Card Paredao Compacto** | Versao resumida do paredao atual na landing | Baixa | Alto |
| **Busca de Participante** | Campo de busca para ir direto ao perfil | Baixa | Medio |
| **Alerta de Risco** | Top 3 participantes mais vulneraveis (falsos amigos) | Baixa | Medio |

### Secoes a Mover/Remover

| Secao | Acao | Motivo |
|-------|------|--------|
| Cronologia do Jogo | Mover para Trajetoria | Nao e urgente; usuarios visitam para ver estado atual |
| Callouts excessivos | Reduzir para 2-3 | 7 callouts de "veja mais" poluem a pagina |

### Conteudo "Acima da Dobra"

O usuario deve ver em 5 segundos:
1. **O que esta quente hoje** (Destaques)
2. **Quem esta em perigo** (Paredao)
3. **Quem lidera** (Top 5 ranking)

---

## 3. Arquitetura Cross-Page

### O Que Deve Aparecer em Multiplas Paginas

| Dado | Painel | Mudancas | Trajetoria | Paredao | Arquivo |
|------|--------|----------|------------|---------|---------|
| Status Paredao (compacto) | SIM (card) | - | - | COMPLETO | HISTORICO |
| Top 5 Ranking | SIM | SIM (delta) | SIM (evolucao) | - | - |
| Destaques do Dia | SIM | SIM (detalhado) | - | - | - |
| Data ultima atualizacao | SIM | SIM | SIM | SIM | SIM |
| Participantes ativos (count) | SIM | - | SIM | - | - |

### O Que Deve Ficar Apenas em Paginas Especializadas

| Dado | Pagina Unica | Motivo |
|------|--------------|--------|
| Heatmap 22x22 completo | Painel | Muito grande para duplicar |
| Perfis Individuais detalhados | Painel | Conteudo extenso |
| Sankey de fluxo | Mudancas | Especifico demais |
| Grafo de relacoes | Trajetoria | Pesado computacionalmente |
| Votacao da casa (tabela) | Paredao | Contexto especifico |
| Analise de coerencia voto/reacao | Paredao + Arquivo | Contexto de eliminacao |

### Fluxo de Navegacao Recomendado

```
USUARIO CASUAL (2 minutos):
  Painel (Destaques + Top 5 + Card Paredao) → FIM

USUARIO REGULAR (5 minutos):
  Painel → Mudancas (se quer ver detalhes das mudancas) → FIM

SUPERFAN (15+ minutos):
  Painel → Perfil individual de interesse → Trajetoria (evolucao) →
  Paredao (se houver) → Arquivo (historico)
```

### Links Entre Paginas - Proposta

Usar callouts mais discretos e contextuais:

```markdown
# Em vez de 7 callouts separados:
::: {.callout-tip title="Explorar Mais" collapse="true"}
- **Mudancas de hoje**: [O Que Mudou](mudancas.html)
- **Evolucao ao longo do tempo**: [Trajetoria](trajetoria.html)
- **Paredao atual**: [Paredao](paredao.html)
:::
```

---

## 4. Novos Recursos/Insights (Rankeados por Impacto)

### Prioridade Alta (Implementar Primeiro)

| # | Recurso | Descricao | Esforco | Impacto |
|---|---------|-----------|---------|---------|
| 1 | **Destaques Automaticos** | Algoritmo que gera 3-5 bullet points: maior delta, maior mudanca, status paredao | Medio | ALTO |
| 2 | **Tendencia (Rising/Falling)** | Seta ou badge indicando se participante subiu/caiu nos ultimos 3 dias | Baixo | ALTO |
| 3 | **Card Paredao na Landing** | Versao compacta com fotos dos indicados | Baixo | ALTO |
| 4 | **Busca de Participante** | Input que filtra perfis ou faz scroll automatico | Baixo | MEDIO |

### Prioridade Media

| # | Recurso | Descricao | Esforco | Impacto |
|---|---------|-----------|---------|---------|
| 5 | **Alerta de Vulnerabilidade** | Top 3 participantes com mais "falsos amigos" destacados | Baixo | MEDIO |
| 6 | **Mini-heatmap por Grupo** | 3 heatmaps pequenos (Pipoca, Camarote, Veterano) separados | Medio | MEDIO |
| 7 | **Comparador de Participantes** | Selecionar 2-3 e ver lado a lado | Alto | MEDIO |

### Prioridade Baixa (Nice to Have)

| # | Recurso | Descricao | Esforco | Impacto |
|---|---------|-----------|---------|---------|
| 8 | **Historico de Participante** | Timeline individual mostrando como relacoes evoluiram | Alto | BAIXO |
| 9 | **Predicao de Votos** | Baseado em hostilidades, quem provavelmente votaria em quem | Alto | MEDIO |
| 10 | **Modo Comparacao de Datas** | Slider ou dropdown para comparar qualquer duas datas | MUITO Alto | MEDIO |

### Detalhamento: Destaques Automaticos

Algoritmo proposto para gerar destaques:

```python
def gerar_destaques(snapshot_hoje, snapshot_ontem, paredao_atual):
    destaques = []

    # 1. Maior subida de sentimento
    deltas = calcular_deltas(snapshot_hoje, snapshot_ontem)
    maior_subida = max(deltas, key=lambda x: x['delta'])
    if maior_subida['delta'] > 1.5:
        destaques.append(f"{maior_subida['nome']} subiu {maior_subida['delta']:+.1f} pontos")

    # 2. Maior queda
    maior_queda = min(deltas, key=lambda x: x['delta'])
    if maior_queda['delta'] < -1.5:
        destaques.append(f"{maior_queda['nome']} caiu {abs(maior_queda['delta']):.1f} pontos")

    # 3. Mudanca dramatica (❤️ → 🐍 ou vice-versa)
    for mudanca in mudancas_dramaticas(snapshot_hoje, snapshot_ontem):
        destaques.append(f"{mudanca['de']} → {mudanca['para']}: {mudanca['emoji_antes']} para {mudanca['emoji_depois']}")

    # 4. Status paredao
    if paredao_atual:
        nomes = [p['nome'] for p in paredao_atual['participantes']]
        destaques.append(f"No paredao: {', '.join(nomes)}")

    # 5. Contagem de mudancas
    n_mudancas = contar_mudancas(snapshot_hoje, snapshot_ontem)
    pct = n_mudancas * 100 / total_relacoes
    destaques.append(f"{n_mudancas} reacoes mudaram ({pct:.0f}% do total)")

    return destaques[:5]  # Maximo 5
```

---

## 5. Ordenacao de Secoes por Pagina

### index.qmd (Painel) - Proposta

| # | Secao Atual | Acao | Secao Nova |
|---|-------------|------|------------|
| 1 | (novo) | ADICIONAR | **Destaques do Dia** |
| 2 | (novo) | ADICIONAR | **Card Paredao + Top 5** (lado a lado) |
| 3 | Visao Geral | SIMPLIFICAR | Mover stats para footer, manter apenas count |
| 4 | Ranking de Sentimento | MANTER | Adicionar badges de tendencia |
| 5 | Tabela Cruzada | MANTER | - |
| 6 | Reacoes Recebidas | MANTER | - |
| 7 | Perfis Individuais | MELHORAR | Adicionar busca, ordenar por vulnerabilidade |
| 8 | Cronologia do Jogo | MOVER | → Trajetoria |

**Racional**: Lead with action (o que esta acontecendo), then data (rankings), then details (perfis).

### mudancas.qmd (O Que Mudou) - Proposta

| # | Secao Atual | Acao | Racional |
|---|-------------|------|----------|
| 1 | Date comparison alert | MANTER | Contexto essencial |
| 2 | Summary stats | EXPANDIR | Adicionar destaques em bullets |
| 3 | Quem Ganhou e Quem Perdeu | SUBIR | Mais importante que volatilidade |
| 4 | Mudancas Dramaticas | SUBIR | Alto interesse |
| 5 | Mapa de Diferencas | MANTER | - |
| 6 | Fluxo de Reacoes (Sankey) | MANTER | - |
| 7 | Volatilidade | DESCER | Menos urgente |
| 8 | Centro do Drama | MANTER | - |
| 9 | Hostilidades (evolucao + detalhes) | MANTER | - |

**Racional**: "Quem ganhou/perdeu" e "mudancas dramaticas" sao o que usuarios querem saber primeiro.

### trajetoria.qmd - Proposta de Reorganizacao

**Problema**: 21 secoes e demais. Usuarios se perdem.

**Solucao**: Agrupar em 4-5 "capitulos" com navegacao clara.

```
TRAJETORIA REORGANIZADA:

# Capitulo 1: Evolucao de Popularidade
  - Evolucao do Sentimento (line chart)
  - Vira-Casacas (quem muda mais)
  - Saldo Over Time

# Capitulo 2: Aliacas e Rivalidades
  - Aliancas Mais Consistentes
  - Rivalidades Mais Persistentes
  - Rivalidades Mais Longas
  - Hostilidades Unilaterais

# Capitulo 3: Dinamicas de Grupo
  - Dinamica VIP vs Xepa
  - Clusters de Afinidade
  - Grafo de Relacoes

# Capitulo 4: Analise de Hostilidades
  - Hostilidades do Dia
  - Quem Ataca Quem Lhe Da ❤️
  - Quem Da ❤️ a Inimigos
  - Quem Tem Mais Inimigos

# Capitulo 5: Insights
  - Saldo vs Sentimento
  - Quem Da Mais Negatividade
  - Insights do Jogo
```

**Implementacao**: Usar headers H1 para capitulos e H2 para secoes. TOC mostrara estrutura hierarquica.

### paredao.qmd - Proposta

| # | Secao | Acao | Racional |
|---|-------|------|----------|
| 1 | Status header + Nominee cards | MANTER NO TOPO | Primeira coisa que usuario quer ver |
| 2 | API status alert | MOVER PARA BAIXO | Tecnico demais para o topo |
| 3 | Formation narrative | MANTER | - |
| 4 | Result bar chart | MANTER | - |
| 5 | Vote vs Reaction coherence | MANTER | - |
| 6 | Scatter + Pie | MANTER | - |
| 7 | "O Caso X" | MANTER | - |
| 8 | Leader nomination analysis | MANTER | - |

### paredoes.qmd - Proposta

Estrutura atual esta boa. Sugestoes menores:
- Adicionar filtro por resultado (eliminado vs salvo)
- Adicionar grafico de tendencia de votos ao longo dos paredoes

---

## 6. Narrativa de Storytelling

### Que Historia o Dashboard Deve Contar?

**Arco Narrativo Principal**:

```
ATO 1: ESTADO ATUAL (Painel)
"Hoje, Jonas lidera o queridometro enquanto Brigido e o mais rejeitado.
Leandro esta no paredao apos ser indicado por dinamica.
O que vai acontecer?"

        ↓

ATO 2: O QUE MUDOU (Mudancas)
"Ontem, 95 reacoes mudaram. Marcelo virou as costas para Solange
(foi de ❤️ para 🐍). Ana Paula continua brigando com Brigido.
A casa esta dividida."

        ↓

ATO 3: PADROES E TENDENCIAS (Trajetoria)
"Ao longo dos ultimos 12 dias, Jonas tem sido consistentemente popular.
Brigido acumula inimigos. Gabriela e a mais vulneravel -
tem 9 'falsos amigos' que podem votar contra ela."

        ↓

ATO 4: ELIMINACAO (Paredao)
"No 1o Paredao, Aline foi eliminada com 45% dos votos.
Dos 11 votos da casa contra ela, 6 vieram de pessoas
que ela considerava aliadas. Seu ponto cego foi fatal."

        ↓

ATO 5: HISTORICO (Arquivo)
"Padroes se repetem: quem tem mais 'falsos amigos'
tende a ser eliminado. O queridometro nao mente."
```

### Como Usuarios Devem Progredir

```
JORNADA DO USUARIO CASUAL:
┌──────────┐    "Legal, entendi    ┌──────────┐
│  Painel  │ ─────────────────────>│   FIM    │
│(2 min)   │    o basico"          │          │
└──────────┘                       └──────────┘

JORNADA DO USUARIO ENGAJADO:
┌──────────┐    "Quero saber      ┌──────────┐    "Interessante!"   ┌──────────┐
│  Painel  │ ───────────────────> │ Mudancas │ ──────────────────> │   FIM    │
│(2 min)   │    mais detalhes"    │ (3 min)  │                     │          │
└──────────┘                      └──────────┘                     └──────────┘

JORNADA DO SUPERFAN:
┌──────────┐         ┌──────────┐         ┌───────────┐         ┌──────────┐
│  Painel  │ ──────> │ Mudancas │ ──────> │ Trajetoria│ ──────> │ Paredao  │
│          │         │          │         │           │         │          │
└──────────┘         └──────────┘         └───────────┘         └──────────┘
     │                                                                │
     │ "Quem e esse                                                   │
     │  participante?"                                                │
     ▼                                                                ▼
┌──────────┐                                                    ┌──────────┐
│  Perfil  │                                                    │ Arquivo  │
│Individual│                                                    │(historico)│
└──────────┘                                                    └──────────┘
```

### Titulos e Subtitulos Narrativos

Em vez de titulos tecnicos, usar titulos que contam uma historia:

| Titulo Atual | Titulo Proposto |
|--------------|-----------------|
| "Ranking de Sentimento" | "Quem Esta Ganhando o Coracao da Casa?" |
| "Tabela Cruzada de Reacoes" | "Quem Ama Quem? Quem Odeia Quem?" |
| "Volatilidade" | "Quem Esta Mudando de Opiniao?" |
| "Hostilidades Unilaterais" | "Pontos Cegos: Quem Nao Sabe Que E Alvo?" |
| "Perfis Individuais" | "Conheca Cada Jogador" |

---

## 7. Recomendacao de Formato de Layout

### Quarto Dashboards vs Articles - Analise

| Aspecto | Articles (Atual) | Dashboards |
|---------|------------------|------------|
| **Scroll longo** | Sim (problema em Trajetoria) | Nao - cards em grid |
| **Navegacao** | TOC lateral | Tabs, navegacao estruturada |
| **Value boxes** | Nao disponivel | Sim - otimo para KPIs |
| **Mobile** | OK (scroll vertical) | Mais compacto mas pode ser denso |
| **Flexibilidade** | Alta | Media (estrutura mais rigida) |
| **Aprendizado** | Ja dominado | Curva de aprendizado |

### Recomendacao Hibrida

**Manter como Article**:
- `trajetoria.qmd` - Conteudo extenso, precisa de scroll
- `paredoes.qmd` - Formato de arquivo/historico

**Converter para Dashboard**:
- `index.qmd` - Landing page se beneficiaria muito de value boxes e layout em grid
- `mudancas.qmd` - Comparacao dia-a-dia funciona bem com cards
- `paredao.qmd` - Status atual e ideal para dashboard

### Mock Layout: index.qmd como Dashboard

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        BBB 26 — Painel de Reacoes                           │
│                        Atualizado: 25 Jan 2026, 16:47                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │     22       │ │     462      │ │      12      │ │   PAREDAO    │       │
│  │ Participantes│ │   Reacoes    │ │  Dias Dados  │ │  EM VOTACAO  │       │
│  │    Ativos    │ │  Registradas │ │              │ │   Leandro    │       │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
│                                                                              │
├────────────────────────────────────┬────────────────────────────────────────┤
│  DESTAQUES DO DIA                  │  TOP 5 SENTIMENTO                      │
│  ┌────────────────────────────────┐│  ┌────────────────────────────────────┐│
│  │ • Jonas lidera (+14.5)         ││  │ 1. Jonas ████████████████ +14.5   ││
│  │ • Marcelo → Solange: ❤️ → 🐍   ││  │ 2. Jordana ██████████████ +10.0   ││
│  │ • 95 reacoes mudaram (21%)     ││  │ 3. Babu █████████████ +8.5        ││
│  │ • Brigido mais rejeitado (-8.0)││  │ 4. Ana Paula ██████████ +6.0      ││
│  └────────────────────────────────┘│  │ 5. Sol █████████ +5.5             ││
│                                    │  └────────────────────────────────────┘│
├────────────────────────────────────┴────────────────────────────────────────┤
│                                                                              │
│  [Ranking Completo]  [Tabela Cruzada]  [Perfis]  (tabs)                     │
│  ┌──────────────────────────────────────────────────────────────────────────┐
│  │                                                                          │
│  │                     (conteudo da tab selecionada)                        │
│  │                                                                          │
│  └──────────────────────────────────────────────────────────────────────────┘
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Implementacao Gradual

**Fase 1** (Baixo Risco):
- Adicionar value boxes no topo da landing page atual
- Adicionar secao "Destaques do Dia"
- Nao precisa mudar para `format: dashboard`

**Fase 2** (Medio Risco):
- Converter `paredao.qmd` para dashboard
- Testar responsividade mobile

**Fase 3** (Se Fase 2 der certo):
- Converter `index.qmd` para dashboard
- Converter `mudancas.qmd` para dashboard

---

## Respostas as Perguntas Abertas

### 1. Landing page deve liderar com "o que mudou" ou "estado atual"?

**Resposta**: **Hibrido** — Liderar com "Destaques do Dia" que INCLUI o que mudou.

**Racional**:
- Usuarios recorrentes querem saber o que mudou
- Usuarios novos precisam de contexto
- Destaques auto-gerados resolvem ambos: "Jonas lidera (+3.5 desde ontem)"

### 2. 5 paginas e muito ou pouco?

**Resposta**: **5 paginas e adequado**, mas Trajetoria precisa ser reorganizada internamente.

**Racional**:
- Cada pagina tem proposito claro
- O problema nao e quantidade de paginas, e a densidade de Trajetoria
- Nao fundir Paredao + Arquivo (contextos diferentes)
- Cartola seria uma 6a pagina valida SE houver demanda

### 3. Interatividade e essencial?

**Resposta**: **Nice-to-have, nao essencial** para o foco UX deste review.

**Racional**:
- O maior problema atual e organizacao de informacao, nao falta de interatividade
- Pre-render com tabs por data pode resolver 80% da necessidade
- Interatividade verdadeira (Shiny/Observable) deve ser Fase 2 apos arrumar UX

### 4. Balanco para mobile?

**Resposta**: **Desktop-first com fallback mobile aceitavel**.

**Racional**:
- Heatmap 22x22 nunca sera bom em mobile
- Superfans (publico principal) usam desktop
- Investir em mobile-first nao vale o custo/beneficio
- Garantir que mobile nao QUEBRE, mas nao otimizar

### 5. Cartola BBB?

**Resposta**: **Adiar** — fora do escopo UX atual.

**Racional**:
- Requer muito input manual
- Publico diferente do queridometro
- Se implementar, seria pagina separada, nao integrada

### 6. Quanta predicao/especulacao incluir?

**Resposta**: **Incluir analise de vulnerabilidade, evitar predicoes explicitas**.

**Racional**:
- "Gabriela tem 9 falsos amigos" = fato, baseado em dados
- "Gabriela sera eliminada" = especulacao, pode estar errada
- Mostrar os dados que permitem o usuario tirar conclusoes
- Badge de vulnerabilidade e analise, nao predicao

---

## Proximos Passos Recomendados

### Curto Prazo (1-2 semanas)

1. [ ] Criar funcao `gerar_destaques()` e adicionar ao topo de index.qmd
2. [ ] Adicionar card compacto de paredao na landing
3. [ ] Adicionar badges de tendencia (seta up/down) no ranking
4. [ ] Consolidar callouts em um unico bloco colapsavel
5. [ ] Mover Cronologia para Trajetoria

### Medio Prazo (3-4 semanas)

6. [ ] Reorganizar Trajetoria em "capitulos" com headers hierarquicos
7. [ ] Adicionar busca de participante em Perfis
8. [ ] Testar conversao de paredao.qmd para dashboard format
9. [ ] Adicionar mini-heatmaps por grupo (experimental)

### Longo Prazo (apos temporada)

10. [ ] Avaliar metricas de uso para priorizar melhorias
11. [ ] Considerar interatividade se houver demanda comprovada
12. [ ] Documentar aprendizados para BBB 27

---

*Review gerado por Claude Opus 4.5 em 2026-01-25*
*Foco: Secoes 1-6 do AI_REVIEW_HANDOUT.md (UX/Arquitetura de Informacao)*
