# BBB26 — Data Visualization Expert Review

**Baseado em**: `docs/AI_REVIEW_HANDOUT.md`  
**Foco**: Tipos de gráficos, design visual, acessibilidade, alternativas mobile  
**Restrições**: Plotly (Python), tema escuro (bg #222 / #303030)

---

## 1. Horizontal Bar (Ranking de Sentimento)

**Onde**: `index.qmd` (`make_sentiment_ranking`), `trajetoria.qmd`, `paredoes.qmd`  
**Implementação**: `go.Bar(orientation='h')`, y = nome, x = score; cor por grupo; `text` fora com `+X.X`; linha vertical em 0; opção de avatares à esquerda.

### Tipo correto?

Sim. Barra horizontal é a escolha certa para ranking com muitos itens (nomes longos, 20+ linhas): o nome à esquerda lê bem e a magnitude à direita permite comparar scores.

### O que ajustar

| Problema | Ajuste |
|----------|--------|
| Linha em 0 em **vermelho** (`color='red'`) | Em fundo #303030, vermelho puro cansa e compete com Camarote (#E6194B). Usar `#666` ou `#888` com `dash='dash'`. |
| `textposition='outside'` | Em scores muito negativos, o texto pode sair do papel. Usar `textposition='auto'` ou `'outside'` só quando `abs(x) < xaxis.range[1]*0.3`; senão `'inside'` com cor do texto clara. |
| `height=max(500, len(df_sent)*32)` | Com 22 pessoas fica ~700px; em mobile o scroll é grande. Manter, mas garantir `responsive=True` e `autosize` no layout. |
| Legenda de grupo via `go.Scatter(x=[None], y=[None])` | Funciona, mas polui a legenda em telas pequenas. Considerar caixa de legenda compacta acima do gráfico ou `legend.orientation='h'` e `yanchor='bottom', y=1.02`. |

### Alternativa

- **Cleveland dot plot** (`go.Scatter` com `mode='markers'`, x=score, y=nome): mesma informação, menos “peso” visual. Para “ranking” explícito, barra horizontal continua melhor.
- Em mobile: **top 10 + “Ver todos”** que expande ou link para tabela; o gráfico completo em `overflow-x: auto` se a barra horizontal for “invertida” (nome embaixo) não é ideal.

---

## 2. Heatmap 22×22 com Emoji

**Onde**: `index.qmd` (`make_cross_table_heatmap`), `mudancas.qmd` (diferenças), `trajetoria.qmd` (cluster).  
**Implementação**: `go.Heatmap` com `z` = peso de sentimento; `text` = emoji; `colorscale` RdYlGn; diagonal `nan` com "—".

### Tipo correto?

Sim. Heatmap é o padrão para matriz de relações (emissor × receptor). O emoji no `text` transmite a reação de forma direta.

### O que ajustar

| Problema | Ajuste |
|----------|--------|
| **Cores RdYlGn** (`#d73027` → `#ffffbf` → `#1a9850`) | O amarelo `#ffffbf` no centro em fundo #303030 tem pouco contraste e “brilha” demais. Trocar o passo central para `[0.5, '#7f7f7f']` ou `'#888'` (neutro escuro). Ex.: `[0,'#d73027'], [0.25,'#fc8d59'], [0.5,'#888'], [0.75,'#91cf60'], [1,'#1a9850']`. |
| **22×22 em mobile** | Células ~15–20px; emojis 14px ficam ilegíveis. Oferecer **visão agregada**: heatmap 10×10 (top 5 positivo + top 5 negativo por sentimento) ou só a **tríade do paredão** (3×N) quando houver paredão. Manter 22×22 em desktop com `overflow-x: auto` e `min-width` no container. |
| **Diagonais "—"** | Ok. Garantir que `hovertemplate` em células vazias ou `nan` não quebre; Plotly costuma omitir. |
| **`textfont=dict(size=14)`** | Em 22×22, 12px às vezes lê melhor sem sobrepor. Testar 12; se a célula for grande (desktop), 14 segue ok. |

### Alternativa

- **Treemap** de pares (emissor→receptor) apenas para relações negativas: destaca “quem ataca quem” sem a matriz inteira. Complementar, não substituir.
- **Tabela ordenável** com as 50 piores relações (A→B, emoji, peso): mais acessível para leitores de tela e mobile.

---

## 3. Diverging Bar (Ganhos/Perdas)

**Onde**: `mudancas.qmd` — “Quem Ganhou e Quem Perdeu”.  
**Implementação**: `go.Bar(orientation='h')`, x=delta, cores `#1a9850` / `#d73027` por sinal; `add_vline(x=0)`.

### Tipo correto?

Sim. Barra divergente com eixo em zero é o padrão para “melhorou vs piorou” (delta de sentimento).

### O que ajustar

| Problema | Ajuste |
|----------|--------|
| **`add_vline` branca** | Em #303030, branco funciona, mas uma linha `#555` ou `#666` com `dash='dash'` alinha melhor ao tema e reduz ruído. |
| **Só quem teve delta ≠ 0** | Correto; evita barras de tamanho zero. Se a lista for longa (15+), considerar ordenar por `abs(delta)` e mostrar top 12; o restante em “Outros” ou tabela. |
| **Falta de referência de escala** | Se os deltas forem sempre pequenos (ex. -2 a +2), o eixo implícito ajuda. Se um dia houver um outlier (ex. +5), fixar `xaxis.range=[-max_abs, max_abs]` simétrico para não distorcer. |

### Alternativa

- **Slopegraph** (dois tempos, um eixo): bom para “quem subiu/desceu” em 2 datas, mas com 20+ nomes fica confuso. Barra divergente continua melhor.
- **Bullet ou gauge por pessoa**: excessivo para o objetivo; manter barra.

---

## 4. Difference Heatmap

**Onde**: `mudancas.qmd` — “Mapa de Diferenças” (Antes→Depois).  
**Implementação**: `go.Heatmap` com `z=Delta`; `text` = "Antes→Depois" (emoji); anotações ⭐ para `|Δ| ≥ 1.5`.

### Tipo correto?

Sim. Heatmap de diferença é adequada para “quais pares mudaram e em que direção”. O `text` com transição (ex. ❤️→🐍) é informativo.

### O que ajustar

| Problema | Ajuste |
|----------|--------|
| **Muitas células vazias (nan)** | Células sem mudança ficam vazias; a escala vai de -2 a +2. O `colorscale` com neutro no 0.5 (`#888`) evita “furo” visual; garantir que `zmin`/`zmax` não escondam a cor do zero. |
| **⭐ como anotação** | `annotations` com ⭐ em cada célula dramática pode sobrepor o emoji. Avaliar: (a) manter ⭐ com `font.size=10` e `xshift`/`yshift` para não tapar, ou (b) borda grossa (`line.width`) na célula em vez de ⭐. |
| **`height=850`** | Mesmo problema de mobile que o heatmap 22×22; mesma estratégia: versão reduzida ou rolável. |

### Alternativa

- **Lista ordenada por |Δ|** (top 15 mudanças) com badge de cor (verde/vermelho) e emoji Antes→Depois: mais legível em mobile e para screen readers.
- **Sankey** já cobre “fluxo de tipo de reação”; o heatmap de diferença cobre “qual par”. Os dois se complementam.

---

## 5. Sankey (Fluxo de Reações)

**Onde**: `mudancas.qmd` — “Fluxo de Reações”.  
**Implementação**: `go.Sankey`: nós = “reação antes” e “reação depois”; links = contagem de transições; cor do link por melhora/piora/lateral.

### Tipo correto?

Em geral sim. Sankey mostra bem fluxo entre categorias (de qual reação para qual as pessoas mudaram). Os nós “Coração antes/depois” etc. são coerentes.

### O que ajustar

| Problema | Ajuste |
|----------|--------|
| **Muitos nós** (9×2 = 18) | Com poucas transições, vários nós ficam vazios ou finos. Agrupar: **Positivo** (Coração), **Leve neg** (Planta, Mala, Biscoito, Coração partido), **Forte neg** (Cobra, Alvo, Vômito, Mentiroso). Ficam 3×2 = 6 nós, fluxo mais legível. |
| **`line=dict(color='black', width=0.5)` nos nós** | Preto em #303030 gera borda dura. Usar `#444` ou `#555`. |
| **`height=500`** | Em mobile, 500px pode cortar nós. `autosize=True` e `height` mínimo (ex. 400) com `margin` ajustado ajudam; em telas muito pequenas, oferecer **tabela de transições** (De → Para, N, %). |
| **`font_size=10`** | Em nós pequenos, 10px pode ser pouco. Subir para 11–12 se o espaço permitir. |

### Alternativa

- **Alluvial** (estilo alluvial/Parallel Sets): mesma ideia, às vezes mais estável em Plotly; o Sankey é suficiente.
- **Tabela “Top transições”** (ex. Coração→Cobra: 8; Cobra→Coração: 2): como resumo textual ou substituição em mobile.

---

## 6. Scatter Plots

**Onde**:
- **Trajetoria**: Saldo vs Sentimento (`px.scatter` + linha de tendência).
- **Paredao / Paredoes**: Reações negativas recebidas vs votos recebidos (`px.scatter` + tendência).
- **Mudancas**: “Centro do Drama” — dado vs recebido (bubble, `go.Scatter(mode='markers+text')`).

### Tipo correto?

Sim em todos. Scatter para correlação (Saldo×Sentimento, Neg×Votos) e para “dado vs recebido” (Drama) é adequado.

### O que ajustar

| Uso | Problema | Ajuste |
|-----|----------|--------|
| **Saldo vs Sentimento, Reações vs Votos** | `px.scatter` com `text='Participante'` e `textposition='top center'`: nomes podem sobrepor. | Aumentar ligeiramente `marker.size` e usar `textposition='top center'` só quando poucos pontos; para 15+, `textposition='none'` e `hovertemplate` rico. Ou `mode='markers'` e anotações só para top 3 e bottom 3. |
| **Linha de tendência** | `go.Scatter(mode='lines', line=dict(dash='dash', color='gray'))`. | Em #303030, `#888` ou `#999` lega melhor que `gray`. Manter `dash`. |
| **Centro do Drama** | `markers+text` com `text=name.split()[0]` e `textfont=dict(color='white')`: em marcadores pequenos o texto some. | Garantir `marker.size` mínimo (ex. 20) e `textfont.size=9`. Se sobrepor, `textposition='top center'` ou `'outside'`. |
| **Cor por grupo** | `color_discrete_map=GROUP_COLORS` em px e `GROUP_COLORS` em go. | Consistente; verificar contraste no #303030 (Camarote #E6194B, Veterano #3CB44B, Pipoca #4363D8). |

### Alternativa

- **Hexbin** ou densidade: com ~20 pontos, scatter simples é melhor.
- **Centro do Drama**: **quadrantes explícitos** (2×2) com contagem por quadrante; o scatter atual já tem anotações “Volátil”/“Alvo”; manter e só refinar posição.

---

## 7. Line Charts

**Onde**: `trajetoria.qmd` — Evolução do Sentimento, Evolução do Saldo (e análogos).  
**Implementação**: `go.Scatter(mode='lines+markers')`, uma série por participante; top 3 e bottom 3 `visible=True`, restante `'legendonly'`; linha em zero; `hovermode='x unified'`.

### Tipo correto?

Sim. Linha no tempo é o padrão para evolução de métrica (sentimento, saldo).

### O que ajustar

| Problema | Ajuste |
|----------|--------|
| **Muitas séries (20+)** | `legendonly` para a maioria é bom; em mobile a legenda pode ficar enorme. | `legend=dict(itemsizing='constant')` já existe. Adicionar `legend.groupclick='toggle'` (Plotly) se disponível; ou **dropdown/tabs** “Top/Bottom” vs “Todos” (ex. 2 figuras: uma com 6, outra com todos). |
| **Cores** | `Plotly + D3 + Set2 + Bold`: algumas cores (amarelo, bege) em #303030 têm baixo contraste. | Restringir a uma paleta com bom contraste: ex. `['#3498db','#e74c3c','#2ecc71','#9b59b6','#f39c12','#1abc9c']` e repetir se precisar. Ou usar `GROUP_COLORS` quando a série for “por grupo” agregado. |
| **Linha em zero** | `color='red', dash='dash'`. | Mesmo que ranking: `#666` ou `#888` em vez de vermelho. |
| **`hovermode='x unified'`** | Bom para comparar muitos no mesmo x. | Manter. |

### Alternativa

- **Área empilhada** (sentimento total por “positivo” vs “negativo”): útil para visão agregada; não substitui a evolução por pessoa.
- **Small multiples** (um mini-line por participante): mais espaço; para 20+ seria outra página. Manter line único com legenda.

---

## 8. Network Graph (Grafo de Relações)

**Onde**: `trajetoria.qmd` — “Grafo de Relações”.  
**Implementação**: `networkx.spring_layout`; arestas como `go.Scatter(mode='lines')` (verde aliança, vermelho tracejado rivalidade); nós como `go.Scatter(mode='markers+text')`; tamanho do nó por sentimento; cor por grupo.

### Tipo correto?

Sim. Grafo é natural para alianças e rivalidades. Spring é razoável; o risco é sobreposição e arestas cruzando.

### O que ajustar

| Problema | Ajuste |
|----------|--------|
| **`spring_layout` com k=2.5** | Pode gerar nós muito juntos ou um “bolo” em grafos densos. | Aumentar `k` (ex. 3.5–4) ou testar `nx.kamada_kawai_layout` para menos cruzamentos. `iterations=80` é ok; 100–120 se o grafo for grande. |
| **Arestas `hoverinfo='none'`** | O usuário não sabe quem é quem na aresta. | Em Plotly é difícil hover em arestas; em troca, `hovertemplate` nos **nós** pode listar “Alianças: X, Y; Rivalidades: Z” se essa informação for pré-calculada e passada em `hovertext`. |
| **Texto no nó** | `text=name.split()[0]`, `textposition='top center'`. | Em nós pequenos, “top” pode cortar. `textposition='middle center'` com `textfont.size=8` e contorno (`textfont.color='white'` com `outline`) se a lib suportar; senão manter e só garantir `marker.size` mínimo. |
| **`xaxis/yaxis showticklabels=False`** | Correto para grafo. | Garantir `showgrid=False, zeroline=False` para não aparecer linhas. |
| **Performance** | Com 22 nós e dezenas de arestas, Plotly aguenta; com 90 dias e muitas arestas, pode travar em mobile. | Manter só alianças e rivalidades (como hoje); não desenhar “tudo”. |

### Alternativa

- **Circular/ Hierarchy**: para “clusters” o layout circular pode ajudar; para “quem se alia a quem”, spring segue bom.
- **Matrix de adjacência** (heatmap 22×22 só com 0/1 “há aresta”): redundante com o heatmap de sentimento; o grafo continua sendo a visão de rede.

---

## 9. Stacked Bars

**Onde**:
- **index/trajetoria**: “Quem Dá Mais Negatividade” — `barmode='stack'`, ❤️ dados (verde) + Negativos dados (vermelho).
- **mudancas**: “Volatilidade” — melhora (verde) + piora (vermelho) + lateral (cinza).

### Tipo correto?

Sim. Empilhamento é adequado para “composição” (❤️ vs neg) ou “tipos de mudança” (melhora/piora/lateral).

### O que ajustar

| Uso | Problema | Ajuste |
|-----|----------|--------|
| **Negatividade** | Ordenação por `% Negativo` ascendente: quem dá menos negatividade no topo. | Boa escolha. Deixar explícito no título ou eixo: “Ordenado por % de reações negativas (menor no topo)”. |
| **Volatilidade** | Três segmentos (melhora/piora/lateral). | Cores ok. Ordenar por “total” de mudanças (já feito). Em mobile, 20+ barras empilhadas ficam altas; considerar top 12. |
| **Cores** | Verde `#1a9850`, vermelho `#d73027`, cinza `#888`. | Em #303030 funcionam. Para daltonismo, evitar verde/vermelho como única distinção: adicionar padrão (listras) é complexo em Plotly; usar **labels no segmento** (“❤️” / “Neg”) e garantir que a legenda e o hover sejam claros. |

### Alternativa

- **Proporção (100% stacked)**: para “% do que cada um deu” (❤️ vs neg), 100% stacked é uma opção; a versão em quantidade absoluta também é válida. Manter absoluto e, se quiser, um segundo gráfico em %.
- **Grouped bar** (❤️ ao lado de Neg, não empilhado): facilita comparar “quanto de cada” por pessoa; para “composição”, stacked segue mais direto.

---

## 10. Pie Charts

**Onde**: `paredao.qmd`, `paredoes.qmd` — “Votaram no que mais detestam?” / coerência (Deu ❤️ mas votou contra / Coerente leve / forte).  
**Implementação**: `go.Pie` com `hole=0.4`, 3–4 fatias, `textinfo='label+percent+value'`, anotação central com total.

### Tipo correto?

Discutível. Pie com 3–4 categorias é aceitável para “proporção de um todo” (ex. X% incoerentes). O donut (`hole=0.4`) reduz um pouco o problema de ângulos difíceis de comparar.

### O que ajustar

| Problema | Ajuste |
|----------|--------|
| **Comparação de fatias** | Em pie, ângulos são ruins para comparar. | Para 3 categorias, **barra horizontal** (uma barra por categoria, comprimento = count ou %) ou **barra de 100%** é mais fácil de ler. Ex.: `go.Bar(y=['Deu ❤️ mas votou contra','Coerente leve','Coerente forte'], x=[n1,n2,n3], orientation='h')` com `barmode='stack'` ou 3 barras lado a lado. |
| **Cores** | `#E6194B`, `#FF9800`, `#3CB44B`, `#999`. | Ok para tema escuro. |
| **`textinfo='label+percent+value'`** | Em fatias pequenas o texto pode sobrepor. | `textinfo='percent+value'` e `labels` na legenda, ou `textposition='outside'` se Plotly permitir por fatia. |

### Alternativa recomendada

- **Substituir por barra horizontal** (count ou %) para as 3–4 categorias de coerência. Pie pode permanecer como vista “resumo” em um segundo plano, mas a principal passa a ser barra.
- Se manter pie: donut está ok; evitar mais de 4 fatias.

---

## 11. Outros (Grouped Bars, etc.)

**Paredão – Resultado (Voto Único, Torcida, Média)**  
`barmode='group'` com 3 barras por nome: adequado para comparar as três métricas. Cores (azul, laranja, verde/vermelho por resultado) são distintas. Ajuste: garantir que, quando `voto_torcida` ou `voto_unico` faltar, o trace não quebre e a legenda reflita “quando disponível”.

**Mudanças entre dias (Trajetoria)**  
`go.Bar` agrupado: ❤️→Neg vs Neg→❤️ por transição. Tipo e cores apropriados. Manter.

**Evolução de Hostilidades (Mudancas)**  
`go.Bar` vertical com 4 categorias (Novas Mútuas, Resolvidas Mútuas, etc.). Ok; em mobile, `tickangle` ou categorias abreviadas se o texto cortar.

---

## 12. Três Novas Visualizações

### 1. **Radar (spider) por participante**

**O que**: para 1 pessoa, eixos = Coração, Planta, Mala, Biscoito, Cobra, etc. (quantidade **recebida** ou **dada**).  
**Por quê**: resume o “perfil” de reações em um formato comparável entre participantes.  
**Implementação**: `go.Scatterpolar` com `fill='toself'`. Um radar por seção ou um **dropdown/tabs** “Selecione o participante” (em estático: um radar por pessoa em accordion ou uma página “Perfil” com 1 gráfico que recebe o nome por âncora/parâmetro).  
**Onde**: em Perfis Individuais ou numa página “Perfil” dedicada.

### 2. **Timeline de relações (Lollipop ou Segment)**

**O que**: para um par (A, B), linha do tempo com segmentos coloridos por “reação de A→B” em cada dia (❤️=verde, neg=vermelho, etc.).  
**Por quê**: responde “como a relação A–B mudou ao longo do tempo”.  
**Implementação**: `go.Scatter` com `mode='lines+markers'` ou `go.Bar` com barra fina por dia; cor por tipo de reação. Um gráfico por par; acessível via “Clique em um par na tabela de alianças/rivalidades”. Em estático: pre-render para top 5–10 pares.  
**Onde**: na seção Alianças/Rivalidades de Trajetória, como “detalhe” ao clicar num par.

### 3. **Mapa de calor por “emissor” (quem dá o quê)**

**O que**: linhas = participantes; colunas = tipos de reação (❤️, 🌱, 💼, …); célula = quantas vezes o emissor deu aquela reação.  
**Por quê**: mostra “quem é coração, quem é cobra” em uma vista; complementa o “Quem Dá Mais Negatividade”.  
**Implementação**: `go.Heatmap` com `z` = contagem, `text` = valor ou emoji; `colorscale` sequencial (ex. branco→vermelho para negativos, branco→verde para ❤️ na coluna Coração).  
**Onde**: Trajetória (perto de “Quem Dá Mais Negatividade”) ou Painel.

---

## 13. Tipos que Estamos Exagerando

| Tipo | Onde aparece em excesso | Sugestão |
|------|--------------------------|----------|
| **Horizontal bar** | Ranking, Ganhos/Perdas, Alianças, Rivalidades, Volatilidade, Negatividade, Mudanças entre dias (parcial), … | Não remover; é o mais versátil para rankings e “valor por categoria”. Onde fizer sentido, **tabelas ordenáveis** (ex. coerência voto×reação) ou **top N + link “ver todos”** para reduzir número de barras. |
| **Heatmap** | Cruzada 22×22, Diferenças, Cluster. | 3 heatmaps é aceitável (objetos diferentes: estado, delta, clusters). O abuso maior é o **tamanho** (22×22) em todas as telas; mitigar com versões reduzidas em mobile. |
| **Bar (geral)** | Agrupada, empilhada, divergente, horizontal. | Barras são o cavalo de carga do dashboard. Para “contagem” e “ranking”, não há substituto melhor. Alternar com **números destacados** (KPI) ou **tabelas** em seções secundárias. |

Não há “excesso” de scatter, line ou pie; o pie está subutilizado e, onde está, barra seria preferível.

---

## 14. Esquema de Cores para Tema Escuro (#222 / #303030)

### Regras

- **Fundo**: `paper_bgcolor` e `plot_bgcolor` = `#303030`; página `#222` (darkly). Manter.
- **Texto**: `#fff` ou `#e0e0e0` para títulos e eixos; `#aaa` para secundário.
- **Grid / linhas de referência**: `#444` ou `#555`; zero em `#666` ou `#888`, evitar vermelho puro.
- **Dados**: evitar amarelo puro e bege claro; preferir cores com contraste suficiente no #303030.

### Paleta sugerida (por uso)

| Uso | Cor | Hex | Nota |
|-----|-----|-----|------|
| Positivo / melhora / ❤️ | Verde | `#2ecc71` ou `#1a9850` | Manter. |
| Negativo / piora / forte neg | Vermelho | `#e74c3c` ou `#d73027` | Manter; não usar como única pista (label+ hover). |
| Neutro / lateral / zero | Cinza | `#888` ou `#7f7f7f` | Preferir ao amarelo no centro de escalas. |
| Leve neg / tensão | Laranja | `#f39c12` ou `#fc8d59` | Ok. |
| Grupos: Camarote | Vermelho-rosa | `#E6194B` | Manter. |
| Grupos: Veterano | Verde | `#3CB44B` | Manter. |
| Grupos: Pipoca | Azul | `#4363D8` | Manter. |
| Linhas de série (múltiplas) | Paleta | `#3498db`, `#e74c3c`, `#2ecc71`, `#9b59b6`, `#f39c12`, `#1abc9c` | Evitar amarelo puro e tons pastel fracos. |

### Ajustes em escalas (heatmaps)

- **Sentimento ( -1 a +1 )**:  
  `[0,'#d73027'], [0.25,'#fc8d59'], [0.5,'#7f7f7f'], [0.75,'#91cf60'], [1,'#1a9850']`  
  (evitar `#ffffbf` no meio).
- **Delta ( -2 a +2 )**: mesma lógica; o 0 no 0.5 do gradiente.

---

## 15. Alternativas Amigáveis a Mobile

| Gráfico | Problema em mobile | Alternativa |
|---------|---------------------|-------------|
| **Heatmap 22×22** | Células e emojis ilegíveis | (a) Heatmap “top 10” (mais/menos sentimento); (b) Tabela “Top 20 relações negativas” com emoji e peso; (c) Container com `overflow-x: auto` e `min-width` para o 22×22. |
| **Ranking horizontal (20+)** | Altura e scroll | (a) Top 10 no gráfico + “Ver ranking completo” que expande ou abre tabela; (b) `height` dinâmico com `max` (ex. 400px) e scroll interno. |
| **Line com 20+ séries** | Legenda enorme | (a) Aba “Top/Bottom 6” e “Todos” (2 figuras); (b) Dropdown “Participante” que destaca 1 série (exige JS simples ou pré-render de N figuras). |
| **Grafo** | Nós e arestas pequenos, toque | (a) Manter; Plotly já tem zoom/pan; (b) Tabela “Alianças” e “Rivalidades” (listas de pares) como alternativa. |
| **Sankey** | Nós e fluxos finos | (a) Tabela “Top transições”; (b) Sankey com 3×2 nós (Positivo/Leve neg/Forte neg) em vez de 9×2. |
| **Scatter com muitos pontos** | Sobreposição de labels | (a) Só `markers`, sem `text`; (b) Anotar só 3–5 pontos; (c) `textposition='none'` e hover rico. |

Implementação em estático: **duas versões** (ex. `fig_desktop` e `fig_mobile`) e exibir via classe CSS `d-none d-md-block` e `d-md-none` (Bootstrap) conforme o viewport, ou uma única figura com `responsive=True` e `autosize=True` e, no pior caso, `overflow` no container.

---

## 16. Melhorias de Acessibilidade

| Aspecto | Situação | Ajuste |
|---------|----------|--------|
| **Contraste** | Cores em #303030; amarelo/bege e alguns verdes leves podem falhar WCAG AA. | Trocar amarelo do heatmap por cinza; verificar `#91cf60`, `#d9ef8b` em fundo escuro (ferramenta de contraste). |
| **Cor como única informação** | Positivo=verde, Negativo=vermelho em vários gráficos. | Sempre **label ou ícone** (❤️, 🐍) + **hover/texto** com o valor. Evitar “verde = bom” sozinho. |
| **Gráficos (screen readers)** | Plotly gera SVG/canvas; legenda e título ajudam. | Em cada bloco de `fig.show()`, **`fig.update_layout(title=dict(...))`** com descrição breve; no markdown, parágrafo **antes** do gráfico descrevendo: “O gráfico X mostra…”. Usar `fig-cap` no Quarto. |
| **Emojis** | ❤️🐍 etc. | Na primeira menção da página, texto entre parênteses: “❤️ (Coração)”, “🐍 (Cobra)”. Em `hovertemplate`, incluir o nome: “Coração”, “Cobra”. |
| **Foco e teclado** | Plotly: foco em botões (Expandir, etc.) e legenda. | Garantir que a legenda e os botões da barra de modo sejam acionáveis por teclado; não depender de hover para informação essencial. |
| **Título e eixos** | `xaxis_title`, `yaxis_title`, `title`. | Manter; evitar títulos vazios. Em barra horizontal, `yaxis_title=""` é ok. |

---

## Checklist Resumido

| Item | Ação |
|------|------|
| Linha em zero (ranking, diverging, line) | Trocar vermelho por `#666`/`#888`. |
| Heatmap: centro da escala | Trocar `#ffffbf` por `#7f7f7f`/`#888`. |
| Heatmap 22×22 em mobile | Versão 10×10 ou tabela top 20; ou `overflow-x: auto` + `min-width`. |
| Sankey | Agrupar nós em 3×2 (Positivo / Leve neg / Forte neg). |
| Pie coerência | Preferir barra horizontal; se manter pie, donut e no máx. 4 fatias. |
| Scatter: labels | Reduzir `text` a 3–5 pontos ou só hover. |
| Line: muitas séries | Top/Bottom 6 em uma vista; “Todos” em aba ou figura separada. |
| Cores de linha (evolução) | Paleta com bom contraste; evitar amarelo/bege. |
| Grafo: nós e arestas | Aumentar `k` no spring; `hovertext` nos nós com “Alianças/Rivalidades”. |
| Radar, Timeline de par, Heatmap por emissor | Considerar como 3 novas visões. |
| A11y | Descrição em prosa + `fig-cap`; emoji com texto; contraste. |

---

*Documento gerado a partir do AI_REVIEW_HANDOUT.md, com foco em dataviz (chart types, design, acessibilidade, mobile).*
