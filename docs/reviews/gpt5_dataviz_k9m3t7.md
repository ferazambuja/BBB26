# Review DataViz — BBB26 (Plotly, dark theme)

## 1) Horizontal bar (ranking de sentimento)
**Tipo certo?** Sim, ótimo para ranking.  
**Ajustes:**
- Fixar Top 5 / Bottom 5 com cor forte; resto em cinza.
- Adicionar linha vertical em 0 (neutro) para leitura imediata.
**Alternativa:** Lollipop chart (mais leve visualmente) se quiser reduzir densidade.

## 2) Heatmap 22×22 com emoji
**Tipo certo?** Para detalhe profundo, sim. Para visão rápida, não.  
**Ajustes:**
- Adicionar modo compacto (apenas ❤️ vs negativo).
- Incluir tooltips com texto (emoji + label).
**Alternativas:**
- Matriz binária (❤️ vs negativo) para mobile.
- Tabela ordenável com filtros (grupo/participante).

## 3) Diverging bar (ganhadores/perdedores)
**Tipo certo?** Sim, perfeito para delta diário.  
**Ajustes:**
- Ordenar do maior ganho → maior perda.
- Usar uma cor para ganho e outra para perda (alto contraste).
**Alternativa:** Slopegraph para mostrar mudança ontem→hoje (mas mais complexo).

## 4) Difference heatmap (mudanças)
**Tipo certo?** Sim, mas pesado.  
**Ajustes:**
- Mostrar apenas células que mudaram (sparse view).
- Tooltip explicando reação anterior → nova.
**Alternativa:** Tabela de mudanças top 20 (mais legível no mobile).

## 5) Sankey diagram
**Tipo certo?** Útil para mostrar migração de reações, mas difícil de ler.  
**Ajustes:**
- Filtrar só mudanças acima de N.
- Agrupar negativos em “Negativo”.
**Alternativa:** Matriz de transição (counts) ou stacked bars por tipo.

## 6) Scatter plots
**Tipo certo?** Sim para correlações (saldo vs sentimento).  
**Ajustes:**
- Labels só nos outliers (evitar poluição).
- Linha de tendência + r.
**Alternativa:** Bubble chart com tamanho=saldo, cor=grupo.

## 7) Line charts
**Tipo certo?** Sim para evolução temporal.  
**Ajustes:**
- Mostrar só top/bottom 5 por padrão.
- Toggle para selecionar participante.
**Alternativa:** Small multiples por grupo.

## 8) Network graph
**Tipo certo?** Legal para “wow”, mas pesado e pouco legível.  
**Ajustes:**
- Filtrar apenas arestas fortes (❤️ mútuo + rivalidades mútuas).
- Fixar layout para consistência entre dias.
**Alternativa:** Matriz de afinidade + clusters (mais clara).

## 9) Stacked bars
**Tipo certo?** Sim para composição (❤️ vs negativos).  
**Ajustes:**
- Empilhar apenas 2 categorias (positivo vs negativo) para leitura rápida.
**Alternativa:** 100% stacked bar para comparar proporções.

## 10) Pie charts
**Tipo certo?** Fraco em precisão; só serve para 2–3 categorias.  
**Ajustes:**
- Se manter, limitar a 2–3 fatias.
**Alternativa:** Bar chart horizontal (mais comparável).

---

## 3 novas visualizações
1) **Ridgeline de sentimento** (por grupo, ao longo do tempo).  
2) **Heat rank chart**: posição no ranking por dia (tipo “bump chart”).  
3) **Vulnerability ladder**: ranking de “blind spots” com barras.

## Tipos de gráfico em excesso
- Heatmaps (2 grandes) e gráficos longos com muito texto.  
- Network graph se torna redundante com heatmaps.

## Esquema de cores (dark theme #222)
- Fundo: `#222` (page) e `#303030` (plots).  
- Texto: `#E0E0E0`  
- Positivo: `#1DB954`  
- Negativo forte: `#E74C3C`  
- Negativo leve: `#F39C12`  
- Neutro/linha de base: `#AAAAAA`

## Mobile‑friendly alternatives
- Mini‑matriz (❤️ vs negativo) em vez do 22×22.  
- Tabelas ordenáveis (top 10).  
- Gráficos com “show more” progressivo.

## Acessibilidade
- Não depender só de cor: usar ícones/texto.  
- Tooltips com descrição textual do emoji.  
- Linha de base e rótulos claros.  
- Contraste mínimo AA para texto e linhas.

**Fim.**
