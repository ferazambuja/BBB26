# BBB26 — UX & Information Architecture Review

**Baseado em**: `docs/AI_REVIEW_HANDOUT.md` (seções 1–6)  
**Foco**: Arquitetura de informação, landing page, ordenação de seções, cross-page, storytelling, layout  
**Restrições**: Português, GitHub Pages estático, free tier, Quarto + Plotly

---

## 1. Executive Summary

- **Destaques no topo da landing page**: A Painel hoje abre com estatísticas frias; o gancho deve ser **Destaques do Dia** (3–5 bullets: quem subiu/caiu, nova hostilidade, paredão em formação) para dar motivo de voltar todo dia.
- **Paredão como âncora de navegação**: O paredão é o evento semanal mais aguardado; no Painel, colocar **card/link do Paredão Atual** acima da dobra (após Destaques), em vez de callout no meio da página.
- **Trajetória fragmentada**: 21 seções num único scroll prejudicam superfans e mobile; dividir em **3–4 subpáginas ou tabsets** (Evolução | Alianças e Hostilidades | Grafo e Clusters | Saldo e Economia) mantendo um único `.qmd` ou via `_quarto.yml`.
- **Duplicação vs link**: Reduzir duplicação: **Ranking de Sentimento** só no Painel (com link para Trajetória#evolucao); **coerência voto×reação** só em Paredão/Arquivo; **Destaques** só no Painel, linkando O Que Mudou.
- **Layout híbrido**: Manter **article** (page-layout: full) nas páginas longas; usar **Quarto Dashboard** apenas no **Painel** (value boxes + cards em linhas/colunas) para um “resumo executivo” estático que funciona em mobile.

---

## 2. Landing Page (Painel) — Ordem e Conteúdo

### Proposta de ordem de seções

| # | Seção | Ação | Motivo |
|---|--------|------|--------|
| 1 | **Destaques do Dia** | **NOVO** | Gancho diário: 3–5 bullets (quem ganhou/perdeu, hostilidade nova, status do paredão). Acima da dobra. |
| 2 | **Paredão Atual (card)** | **MOVER para cima** | Card compacto: status (em formação / em votação / resultado), nomes, link "Ver análise →". |
| 3 | **Visão Geral** | Manter (enxugar) | Manter: participantes, reações, dias, última coleta. Reduzir Cronologia a 1 frase + link "Ver cronologia → Trajetória". |
| 4 | **Ranking de Sentimento** | Manter | Principal chart do Queridômetro. Manter 1 callout para O Que Mudou + 1 para Trajetória. |
| 5 | **Tabela Cruzada** | Manter | Heatmap; importante para superfans. Manter callouts para Trajetória (grafo, clusters). |
| 6 | **Reações Recebidas** | Manter (como hoje, dentro da Tabela Cruzada) | Tabela de breakdown por emoji. |
| 7 | **Perfis Individuais** | Manter | Accordion por participante. Pode ir para o final. |
| — | **Cronologia do Jogo** | **MOVER para Trajetória** | A Cronologia completa (entradas, saídas, Líder, etc.) vive melhor em Trajetória; no Painel: 1 linha tipo “13 jan–25 jan, 3 saídas, 4 entradas. [Cronologia completa →](trajetoria.html#visao-geral)” |

### O que adicionar

- **Destaques do Dia (novo bloco)**  
  - Conteúdo (regras simples, 100% com dados existentes):
    - Top 1–2 “ganhadores” e 1–2 “perdedores” de sentimento (ontem→hoje), com Δ.
    - 1–2 “mudanças dramáticas” (ex.: X passou a dar 🐍 para Y).
    - Se existir paredão `em_andamento`: “Paredão em votação: A, B, C”.
    - Se existir nova hostilidade unilateral relevante (ex.: primeira vez que X dá negativa a Y): 1 linha.
  - Fonte de dados: `mudancas.qmd` já calcula ganhadores/perdedores e mudanças dramáticas; extrair no `index.qmd` ou via função compartilhada. Estático, sem Shiny.

- **Card “Paredão Atual”**  
  - 1 card horizontal: ícone 🗳️, status, 3 nomes (ou “em formação”), botão “Ver análise →” para `paredao.html`.

### O que remover / deslocar

- **Cronologia do Jogo (tabela completa)** → Remover do Painel; deixar só 1 frase + link para Trajetória. A tabela fica em `trajetoria.qmd`.
- **Callouts em excesso** → Manter 1 callout por “próxima página” (Paredão, O Que Mudou, Trajetória) nas seções mais relevantes; eliminar chamadas repetidas (ex.: vários para Grafo/Clusters/Saldo na Tabela Cruzada).

### Acima da dobra (mobile/desktop)

Objetivo: sem scroll, o usuário vê **Destaques** + **Card Paredão** + **Visão Geral (1 linha)** + **Ranking (chart)**.

```
+------------------------------------------------------------------+
|  Destaques do Dia                                                |
|  • X subiu / Y caiu no sentimento  • Paredão: A, B, C em votação |
|  • Nova: João passou a dar 🐍 a Maria                             |
+------------------------------------------------------------------+
|  Paredão Atual          [Ver análise →]                           |
|  Em votação: Ana, Bruno, Carla                                    |
+------------------------------------------------------------------+
|  Visão Geral: 22 ativos | 462 reações | 13–25 jan  [Cronologia →] |
+------------------------------------------------------------------+
|  Ranking de Sentimento (chart)                                    |
+------------------------------------------------------------------+
```

---

## 3. Cross-Page: O Que Duplicar vs O Que Só Linkar

### Duplicar (resumo pequeno) em mais de uma página

| Conteúdo | Onde duplicar | Formato |
|----------|----------------|---------|
| **Status do Paredão** | Painel + Paredão | Painel: card 1 linha + link. Paredão: bloco completo. |
| **Ranking de Sentimento (só o chart)** | Apenas Painel | Painel: chart do dia. Trajetória: só evolução temporal; Arquivo: ranking por data do paredão (já existe). |
| **Destaques / “O que mudou”** | Apenas Painel (Destaques) e O Que Mudou | Painel: 3–5 bullets. O Que Mudou: seções completas (ganhadores, mapa, Sankey, etc.). |

### Só em uma página, com link nas outras

| Conteúdo | Onde fica | De onde linkar |
|----------|-----------|----------------|
| **Evolução do Sentimento (linha no tempo)** | Trajetória | Painel (callout no Ranking), O Que Mudou (1 linha no topo). |
| **Coerência Voto × Reação** | Paredão (em andamento/finalizado) e Arquivo (por paredão) | Painel: não duplicar; no card Paredão: “Ver coerência voto×reação →”. |
| **Grafo de Relações** | Trajetória | Painel (callout na Tabela Cruzada), Paredão (opcional: “Grafo do dia” só se fizer sentido no futuro). |
| **Clusters de Afinidade** | Trajetória | Painel (callout na Tabela Cruzada). |
| **Hostilidades (listas, unilateral/mútua)** | Trajetória | Painel: em Perfis há resumo por pessoa; link “Hostilidades do dia → Trajetória”. |
| **Cronologia (tabela de eventos)** | Trajetória | Painel: 1 frase + link. |
| **Saldo vs Sentimento, Quem Dá Mais Negatividade** | Trajetória | Painel: não duplicar; callout na Tabela ou em Visão Geral. |
| **Fluxo Sankey, Mapa de Diferenças, Centro do Drama** | O Que Mudou | Painel: Destaques apontam para O Que Mudou; sem Sankey/Mapa no Painel. |

### Fluxo de navegação sugerido

```
                    +-------------+
                    |   Painel    |
                    | (Destaques, |
                    |  Paredão,   |
                    |  Ranking,   |
                    |  Heatmap,   |
                    |  Perfis)    |
                    +------+------+
                           |
         +-----------------+-----------------+
         |                 |                 |
         v                 v                 v
+-------------+   +-------------+   +-------------+
| O Que Mudou |   |  Paredão    |   | Trajetória  |
| (detalhe    |   | (status,    |   | (evolução,  |
|  dia a dia) |   |  votos,     |   |  alianças,  |
|             |   |  coerência) |   |  grafo,     |
+-------------+   +------+------+   |  clusters)  |
                    |     |           +------+------+
                    v     v                  |
              +-------------+                 v
              |  Arquivo    | <--------------+
              | (paredões   |
              |  finalizados)|
              +-------------+
```

- **Painel** = hub: Destaques + Paredão + Ranking + Heatmap + Perfis; links para as outras 4 páginas.
- **O Que Mudou** ↔ **Painel**: Destaques no Painel linkam para O Que Mudou; O Que Mudou pode ter 1 linha “Ver ranking e heatmap de hoje → Painel”.
- **Paredão** ↔ **Arquivo**: Paredão linka “Histórico → Arquivo”; Arquivo linka “Paredão atual → Paredão”.
- **Trajetória** recebe links do Painel (evolução, grafo, clusters, cronologia) e do Paredão/Arquivo (“Reações e sentimento na data do paredão” já está no Arquivo; Trajetória é a visão temporal completa).

---

## 4. Novas Funcionalidades — Ranqueadas por Impacto

Critério: impacto para **casual + superfans** vs esforço (dados + código estático, sem backend).

| # | Funcionalidade | Impacto | Esforço | Descrição |
|---|----------------|---------|---------|-----------|
| 1 | **Destaques do Dia** | Alto | Baixo | 3–5 bullets no topo do Painel: quem subiu/desceu, 1–2 mudanças dramáticas, status do paredão, 1 hostilidade nova. Dados já existem em mudancas.qmd; replicar lógica no index ou fatorar. |
| 2 | **Card Paredão no Painel** | Alto | Baixo | Card compacto acima da dobra com status e link; dados vêm de `paredoes`/API já usados em paredao.qmd. |
| 3 | **“Quem pode estar em risco?” (Watch list)** | Alto | Médio | Lista: alta vulnerabilidade (muitos “falsos amigos”) + no Paredão ou próximo (ex.: mais votado na casa na última semana). Texto explícito: “Análise de posição no jogo, não previsão de eliminação.” Dados: Perfis + manual. |
| 4 | **Tendência (subindo/caindo em N dias)** | Médio | Baixo | No Ranking ou nos Perfis: seta ↑/↓ + “subiu X pts em 5 dias”. Requer sentimento por dia já calculado em trajetoria. |
| 5 | **Resumo “O Que Mudou” em 1 frase no topo de O Que Mudou** | Médio | Baixo | Ex.: “De ontem para hoje: 12 relações mudaram; maiores ganhos: X e Y; maiores perdas: Z.” Reduz necessidade de scroll para pegar o contexto. |
| 6 | **Modo “foco em 1 participante”** | Médio | Médio | Página ou tab: linha de sentimento, quem dá ❤️/neg a ele, hostilidades, participação em paredões. Pode ser um `?participante=Nome` ou seção colapsável em Perfis que expande. |
| 7 | **Comparação de 2 datas (qualquer)** | Médio | Médio | Sem Shiny: pre-render 2–3 comparações (ex.: “Hoje vs há 7 dias”) em tabs ou abas em O Que Mudou. Aumenta valor sem quebrar estático. |
| 8 | **Cartola BBB (pontos)** | Médio | Alto | Nova página ou seção: tabela de pontos por evento, por semana. Depende de manual_events + regras; handout já descreve. Útil para Cartola players; prioridade após Destaques/Paredão/Watch list. |
| 9 | **Índice/âncoras na Trajetória** | Médio | Baixo | Se Trajetória continuar como 1 página: TOC fixo ou âncoras “Evolução | Alianças | Grafo | Clusters | Saldo” no topo para pular seções. |
| 10 | **Share/SEO: imagem OG por página** | Baixo | Baixo | Uma imagem estática (ex.: ranking ou grafo) por página para Open Graph; meta description por página. Aumenta CTR em redes. |

Prioridade sugerida para as 3 próximas: **1 (Destaques)**, **2 (Card Paredão)**, **3 (Watch list)** ou **4 (Tendência)**.

---

## 5. Ordenação de Seções por Página

### Painel (index.qmd)

| Ordem | Seção | Observação |
|-------|--------|------------|
| 1 | Destaques do Dia | **NOVO** — 3–5 bullets |
| 2 | Paredão Atual (card) | **NOVO** — 1 card + link |
| 3 | Visão Geral | Enxuta: 1 parágrafo + 1 linha de Cronologia + link |
| 4 | Ranking de Sentimento | Idem, 1 callout O Que Mudou, 1 Trajetória |
| 5 | Tabela Cruzada de Reações | Idem |
| 6 | Reações Recebidas | Dentro ou imediatamente após Tabela Cruzada |
| 7 | Perfis Individuais | Fim; accordion |
| — | ~~Cronologia do Jogo (tabela)~~ | **REMOVER** → Trajetória |

### O Que Mudou (mudancas.qmd)

| Ordem | Seção | Observação |
|-------|--------|------------|
| 1 | **Resumo em 1 frase** | **NOVO** — “Ontem→Hoje: X mudanças; principais: …” |
| 2 | O Que Mudou Hoje? (alerta de datas) | Manter |
| 3 | Quem Ganhou e Quem Perdeu | Manter |
| 4 | Mapa de Diferenças | Manter |
| 5 | Quem Mais Mudou de Opinião? (Volatilidade) | Manter |
| 6 | Fluxo de Reações (Sankey) | Manter |
| 7 | Quem Está no Centro do Drama? | Manter |
| 8 | Evolução das Hostilidades | Manter; colapsável para detalhes |
| 9 | (opcional) Callout | “Ver ranking e heatmap de hoje → [Painel](index.html)” |

### Trajetória (trajetoria.qmd)

Proposta: **agrupar em 4 blocos** (com âncoras ou, no futuro, subpáginas/tabs). A ordem dos blocos segue a narrativa: contexto → evolução → relações → estrutura.

| Bloco | Seções no bloco | Ordem interna |
|-------|------------------|---------------|
| **A. Contexto** | Visão Geral, **Cronologia do Jogo** (migrada do Painel) | 1. Visão 2. Cronologia |
| **B. Evolução** | Evolução do Sentimento, Mudanças Entre Dias, Vira-Casacas, Dinâmica Vip vs Xepa, Saldo Over Time | 1. Evolução 2. Mudanças 3. Vira-Casacas 4. Vip vs Xepa 5. Saldo |
| **C. Alianças e Hostilidades** | Alianças Mais Consistentes, Rivalidades Mais Persistentes, Rivalidades Mais Longas, Hostilidades Unilaterais Mais Longas, Hostilidades do Dia, Quem Ataca Quem Lhe Dá ❤️, Quem Dá ❤️ a Inimigos, Quem Tem Mais Inimigos, Listas de Hostilidades, **Insights do Jogo** | 1. Alianças 2. Rivalidades (todas) 3. Hostilidades do Dia 4. Ataca/Dá ❤️/Inimigos 5. Listas 6. Insights |
| **D. Grafo e Clusters** | Grafo de Relações, Clusters de Afinidade, Cluster Heatmap, Saldo vs Sentimento, Quem Dá Mais Negatividade | 1. Grafo 2. Clusters 3. Cluster Heatmap 4. Saldo vs Sentimento 5. Emissores |

Ordenação final das seções (sequência única, para manter 1 .qmd):

1. Visão Geral  
2. **Cronologia do Jogo** (nova, vinda do Painel)  
3. Evolução do Sentimento  
4. Alianças Mais Consistentes  
5. Rivalidades Mais Persistentes  
6. Mudanças Entre Dias  
7. Vira-Casacas  
8. Dinâmica Vip vs Xepa  
9. Rivalidades Mais Longas  
10. Hostilidades Unilaterais Mais Longas  
11. Saldo Over Time  
12. Grafo de Relações  
13. Hostilidades do Dia  
14. Quem Ataca Quem Lhe Dá ❤️ / Quem Dá ❤️ a Inimigos / Quem Tem Mais Inimigos  
15. Listas de Hostilidades  
16. Insights do Jogo  
17. Clusters de Afinidade  
18. Cluster Heatmap  
19. Saldo vs Sentimento  
20. Quem Dá Mais Negatividade  

Ou: manter a ordem atual e apenas **inserir Cronologia** após Visão Geral e **adicionar um mini-índice no topo** com links para os 4 blocos (Contexto, Evolução, Alianças e Hostilidades, Grafo e Clusters).

### Paredão (paredao.qmd)

| Ordem | Seção | Observação |
|-------|--------|------------|
| 1 | Alerta de status/API (quem tem role Paredão) | Manter |
| 2 | Status (em formação / em votação / resultado) | Manter |
| 3 | Cards dos nomes + formação | Manter |
| 4 | Formação (narrativa), Líder, imunidade | Manter |
| 5 | Votação da casa (tabela) | Manter |
| 6 | Resultado (barras) — se finalizado | Manter |
| 7 | Voto da Casa vs Queridômetro | Manter |
| 8 | Reações Preveem Votos? | Manter |
| 9 | Votaram no que mais detestam? / O Caso X / Indicação do Líder | Manter |
| 10 | Navegação (Arquivo, Painel) | Manter |

Sem mudança de ordem; no Painel, o **card Paredão** faz a ponte.

### Arquivo (paredoes.qmd)

| Ordem | Seção | Observação |
|-------|--------|------------|
| 1 | Resumo das Eliminações (tabela) | Manter |
| 2 | Por paredão (finalizado): Resultado, Formação, Votação, Voto×Reação, Reações preveem votos?, O Caso X, Indicação Líder, Ranking de Sentimento na data, Reações Recebidas | Manter |

Sem alteração de ordem; apenas garantir links “Paredão atual” e “Painel” no topo ou no rodapé.

---

## 6. Storytelling — Qual História o Dashboard Conta?

### Arco narrativo sugerido

1. **“O que importa hoje?”**  
   Destaques + Paredão + 1 linha de contexto. O usuário entende em 10 segundos: clima da casa e se há paredão.

2. **“Quem está em alta e em baixa?”**  
   Ranking de Sentimento + (opcional) tendência em N dias. Responde: quem a casa prefere hoje.

3. **“Quem se relaciona com quem?”**  
   Tabela Cruzada + Perfis. Mostra o grafo em formato tabela e, nos Perfis, pontos cegos (falsos amigos) e vulnerabilidade.

4. **“O que mudou de ontem para hoje?”**  
   O Que Mudou. Para quem volta todo dia: ganhadores, perdedores, fluxo, drama.

5. **“Como chegamos aqui?”**  
   Trajetória: evolução, alianças, rivalidades, grafo, clusters. Para quem quer深度.

6. **“O voto da casa faz sentido com as reações?”**  
   Paredão e Arquivo. Conexão direta com o jogo: reações preveem votos? Quem foi “O caso”?

### Princípios

- **Lead with “now”**: Painel responde “hoje” e “esta semana” (paredão). O Que Mudou responde “ontem→hoje”. Trajetória responde “desde o início”.
- **Progressão**: do resumo (Destaques, card, ranking) para o detalhe (heatmap, perfis, depois O Que Mudou e Trajetória).
- **Um gancho por página**:  
  - Painel: Destaques + Paredão  
  - O Que Mudou: “X mudanças; maiores: …”  
  - Trajetória: Evolução do Sentimento ou Insights  
  - Paredão: Status e “Reações preveem votos?”  
  - Arquivo: Resumo das eliminações e “O Caso X” por paredão.
- **Sem spoiler de “quem vai sair”**: Watch list e vulnerabilidade são “posição no jogo”, com aviso explícito de que não é previsão.

### Frase de efeito (para fixar no topo ou no about)

> “O Queridômetro mostra o que a casa pensa **hoje**. Aqui você vê quem subiu, quem caiu, quem se alinha e quem se ataca — e se isso se reflete no voto.”

---

## 7. Layout: Quarto Dashboards vs Formato Article

### Recomendação: **híbrido**

- **Manter `page-layout: full` (article)** em: **O Que Mudou**, **Trajetória**, **Paredão**, **Arquivo**.  
  - Motivo: muito conteúdo em scroll, narrativa longa; dashboards com muitas rows/cols e cards podem piorar a navegação em mobile (muitos cards pequenos). O article com TOC e bons H2/H3 já organiza.

- **Converter só o Painel** para **`format: dashboard`** (Quarto Dashboard estático), com:
  - **Value boxes** na primeira row: Participantes, Reações, Dias de dados, (opcional) Paredão: Em votação / Finalizado / Em formação.
  - **Row 2**: Destaques do Dia (card de texto) | Card Paredão (card com link).
  - **Row 3**: Ranking de Sentimento (1 coluna, height ~50%).
  - **Row 4**: Tabela Cruzada (heatmap) | ou heatmap em 1 coluna.
  - **Row 5** (ou nova page “Detalhes”): Reações Recebidas (tabela) + Perfis (accordion ou cards).

Isso exige:
- `index.qmd` com `format: dashboard` e `layout` em rows/columns.
- Garantir que `theme: darkly` e `bbb_dark` (Plotly) continuem; Dashboards permitem theme.
- Testar no GitHub Pages: Dashboards estáticos geram HTML/JS; sem Shiny, funciona em free tier.

### Alternativa mais conservadora

- **Manter todas as páginas em article.**  
- No Painel, **simular “dashboard” com estrutura Bootstrap**:
  - 1 row com `col-md-3` para 4 “value boxes” (participantes, reações, dias, status paredão) em `<div>` estilizados.
  - 1 row: Destaques (card) | Card Paredão (card).
  - Depois: Ranking, Tabela Cruzada, Reações, Perfis como hoje.

Vantagem: zero mudança de format; apenas reordenação e novos blocos em HTML/Markdown.  
Desvantagem: value boxes não são nativos; parecem um pouco menos “dashboard”.

### Resumo

| Página    | Formato recomendado | Motivo |
|-----------|----------------------|--------|
| **Painel** | Dashboard **ou** article com “fake” value boxes | Painel é “resumo executivo”; cards/boxes ajudam. Dashboard nativo é melhor se a equipa quiser investir. |
| **O Que Mudou** | Article | Muitas seções, leitura sequencial. |
| **Trajetória** | Article | Muito longo; TOC/âncoras resolvem. Dashboard fragmentaria demais. |
| **Paredão** | Article | Fluxo linear: status → formação → votos → análise. |
| **Arquivo** | Article | Lista de paredões; cada um é um “artigo” em si. |

### ASCII — Painel como Dashboard (formato Quarto)

```
+------------------------------------------------------------------+
|  NAVBAR:  Painel | O Que Mudou | Trajetória | Paredão | Arquivo   |
+------------------------------------------------------------------+
|  Row {height=12%}                                                |
|  +----------+  +----------+  +----------+  +----------------------+ |
|  | 22       |  | 462      |  | 13 dias  |  | Paredão: Em votação  | |
|  | ativos   |  | reações  |  | de dados |  | (value boxes)        | |
|  +----------+  +----------+  +----------+  +----------------------+ |
+------------------------------------------------------------------+
|  Row {height=18%}                                                |
|  +--------------------------------+  +--------------------------+ |
|  | Destaques do Dia                |  | Paredão Atual             | |
|  | • X subiu, Y caiu              |  | Em votação: A, B, C       | |
|  | • Nova: João→Maria 🐍          |  | [Ver análise →]          | |
|  | • Paredão: A, B, C             |  |                          | |
|  +--------------------------------+  +--------------------------+ |
+------------------------------------------------------------------+
|  Row {height=45%}                                                |
|  +----------------------------------------------------------------+|
|  | Ranking de Sentimento (Plotly)                                  ||
|  +----------------------------------------------------------------+|
+------------------------------------------------------------------+
|  Row {height=25%}                                                |
|  +----------------------------------------------------------------+|
|  | Tabela Cruzada (heatmap) ou [Tabela | Perfis em 2 cols]        |
|  +----------------------------------------------------------------+|
+------------------------------------------------------------------+
|  Footer / link Cronologia → Trajetória                            |
+------------------------------------------------------------------+
```

### ASCII — Painel como Article (alternativa conservadora)

```
+------------------------------------------------------------------+
|  # Painel                                                        |
+------------------------------------------------------------------+
|  [4 divs em Bootstrap row: 22 ativos | 462 reações | 13 dias |   |
|   Paredão: Em votação]                                            |
+------------------------------------------------------------------+
|  ## Destaques do Dia                                             |
|  • ...  (texto)                                                  |
+------------------------------------------------------------------+
|  ## Paredão Atual   [Ver análise →]                              |
|  Em votação: A, B, C                                              |
+------------------------------------------------------------------+
|  ## Visão Geral  |  Cronologia: 13–25 jan [link → Trajetória]   |
+------------------------------------------------------------------+
|  ## Ranking de Sentimento   [chart]                              |
+------------------------------------------------------------------+
|  ## Tabela Cruzada  [heatmap]  |  Reações Recebidas [tabela]    |
+------------------------------------------------------------------+
|  ## Perfis Individuais  [accordion]                               |
+------------------------------------------------------------------+
```

---

## Checklist de Ações (priorizado)

1. **Painel**
   - [ ] Criar bloco **Destaques do Dia** (reuso de lógica de mudancas.qmd).
   - [ ] Criar **Card Paredão Atual** com link para paredao.html.
   - [ ] Enxugar Visão Geral; mover **Cronologia** para Trajetória (1 linha + link no Painel).
   - [ ] Reduzir callouts repetidos; manter 1 por destino (Paredão, O Que Mudou, Trajetória).
   - [ ] (Opcional) Converter para `format: dashboard` ou simular value boxes em article.

2. **Trajetória**
   - [ ] Inserir **Cronologia do Jogo** após Visão Geral.
   - [ ] Adicionar **mini-índice** no topo com âncoras (Contexto | Evolução | Alianças e Hostilidades | Grafo e Clusters).
   - [ ] (Opcional) Reordenar seções conforme o bloco D (Grafo e Clusters) proposto.

3. **O Que Mudou**
   - [ ] Adicionar **resumo em 1 frase** no topo.
   - [ ] (Opcional) Callout “Ver ranking e heatmap de hoje → Painel”.

4. **Paredão e Arquivo**
   - [ ] Garantir links para Arquivo (no Paredão) e para Paredão (no Arquivo); sem mudança de ordem.

5. **Cross-page**
   - [ ] Não duplicar Ranking em Trajetória (só Evolução); não duplicar Sankey/Mapa no Painel.
   - [ ] Coerência voto×reação apenas em Paredão e Arquivo.

6. **Novas features (curto prazo)**
   - [ ] Destaques do Dia.
   - [ ] Card Paredão no Painel.
   - [ ] Tendência (↑/↓ em N dias) no Ranking ou Perfis.
   - [ ] (Depois) Watch list “Quem pode estar em risco?”.

---

*Documento gerado a partir do AI_REVIEW_HANDOUT.md, foco em UX e Arquitetura de Informação (seções 1–6).*
