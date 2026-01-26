# Review UX & IA — BBB26 (Seções 1–7)

## 1) Executive Summary
- **Transformar o Painel em “glanceable”**: topo com KPIs + Destaques do Dia + status do Paredão antes de qualquer gráfico grande.
- **Narrativa clara por páginas**: Painel = hoje; Mudanças = o que virou; Trajetória = padrões; Paredão = voto; Arquivo = histórico.
- **Duplicar só resumos** (teasers), sempre com CTA para a análise completa.
- **Priorizar 3 features de alto impacto e baixo custo**: Destaques automáticos, Watchlist de risco, comparador de datas pré-renderizado.
- **Adotar Quarto Dashboards** apenas em Painel e Paredão; manter formato artigo em Mudanças/Trajetória/Arquivo.

---

## 2) Landing Page (Painel): ordem proposta + adicionar/remover

### Ordem proposta (do topo ao fundo)
1. **Barra de contexto** (linha única)
   - “Último dado: AAAA-MM-DD • 22 participantes • 462 reações • 12 dias”
2. **KPIs (cards)**
   - ❤️ recebidos (total), negativas (total), hostilidades mútuas, mudanças do dia
3. **Destaques do Dia (novo)**
   - 3–5 bullets auto-gerados (ex.: “Maior queda: Matheus -4,5”, “Nova hostilidade: X→Y”)
4. **Status do Paredão (novo, curto)**
   - “Em votação: Leandro + …” + CTA para `paredao.qmd`
5. **Ranking de Sentimento (resumo)**
   - Top 5 e Bottom 5 + botão “Ranking completo”
6. **Mapa Rápido de Relações (novo)**
   - Mini-matriz ❤️ vs negativas (sem emojis detalhados) OU mini-network simplificado
7. **Hostilidades do Dia (resumo)**
   - Top 5 mútuas + Top 5 blind spots
8. **Tabela Cruzada (compacta)**
   - Versão resumida + botão “Mapa completo”
9. **Perfis Individuais (accordion)**
   - Colapsado por padrão
10. **Navegação (cards grandes)**
   - Mudanças / Trajetória / Paredão / Arquivo

### Adicionar
- **Destaques do Dia** (auto-gerado)
- **Watchlist de risco** (Top 5 vulneráveis)
- **CTA de Paredão** em destaque

### Remover do Painel
- Cronologia do Jogo (ir para Trajetória)
- Seções longas acumuladas (clusters, saldos, etc.)

### ASCII mockup (topo)
```
[Último dado: 2026-01-24 | 22 participantes | 462 reações | 12 dias]

[❤️ 280] [Negativas 182] [Hostilidades mútuas 38] [Mudanças hoje 95]

Destaques do Dia:
- Maior alta: Babu +3.0
- Maior queda: Matheus -4.5
- Nova hostilidade: X → Y
- Top vulnerável: Gabriela

PAREDÃO AGORA: Leandro + ?? (Em votação) [Ver Paredão]

Ranking (Top 5 / Bottom 5) [Ver completo]
Mapa rápido ❤️/neg [Abrir mapa completo]
Hostilidades do dia (Top 5) [Detalhes]
Perfis (accordion) [Abrir]
[Navegação: Mudanças | Trajetória | Paredão | Arquivo]
```

---

## 3) Cross-Page Architecture: duplicar vs linkar

### Duplicar (apenas resumo curto)
- **Destaques do Dia**: Painel + Mudanças
- **Status do Paredão**: Painel + Paredão
- **Top 5 Sentimento**: Painel + Paredão (apenas indicados)

### Linkar (não duplicar)
- **Sankey/Volatilidade/Mudanças dramáticas**: só Mudanças
- **Clusters/Hostilidades persistentes/Saldos históricos**: só Trajetória
- **Voto vs Reações detalhado**: só Paredão + Arquivo

**Regra prática**: Painel mostra “teaser + CTA”, páginas especializadas guardam a profundidade.

---

## 4) Novas Features (rank por impacto)
1. **Destaques do Dia** (alto impacto, baixo esforço) — 3–5 frases auto-geradas
2. **Watchlist de Risco** — ranking de vulneráveis por “blind spot” + negativas recebidas
3. **Comparador de Datas (pré-renderizado)** — dropdown com últimos 7 dias
4. **Filtro por grupo (Pipoca/Camarote/Veterano)** — versões pré-calculadas
5. **Resumo semanal** — bloco “Mudanças da Semana” em Mudanças

---

## 5) Ordenação das Seções (5 páginas)

### Painel (index.qmd)
1) Barra de contexto
2) KPIs
3) Destaques do Dia
4) Status do Paredão
5) Ranking (Top/Bottom)
6) Mapa rápido
7) Hostilidades do Dia (resumo)
8) Tabela Cruzada (compacta)
9) Perfis Individuais (accordion)
10) Navegação

### O Que Mudou (mudancas.qmd)
1) Contexto de datas
2) Destaques do Dia (duplicado)
3) Quem ganhou/perdeu
4) Mapa de diferenças
5) Volatilidade
6) Sankey
7) Centro do drama
8) Mudanças em hostilidades
9) Lista de mudanças dramáticas
10) CTA “Ver estado atual”

### Trajetória (trajetoria.qmd)
1) Contexto histórico
2) Evolução do Sentimento
3) Alianças consistentes
4) Rivalidades persistentes
5) Hostilidades persistentes
6) Clusters de afinidade
7) Saldo ao longo do tempo
8) Saldo vs Sentimento
9) Dinâmica VIP vs Xepa
10) Insights do jogo
11) CTA “Voltar ao Hoje”

### Paredão (paredao.qmd)
1) Status do Paredão
2) Cards de indicados
3) Formação narrativa
4) Votos da casa
5) Coerência voto vs reação
6) Reações preveem votos? (scatter)
7) O caso do mais votado
8) CTA “Ver Arquivo”

### Arquivo (paredoes.qmd)
1) Tabela resumo
2) Paredão N: resultado + cards
3) Formação
4) Votos da casa
5) Coerência votos vs reações
6) Ranking de sentimento da data
7) Reações recebidas

---

## 6) Storytelling: narrativa do dashboard
**Narrativa principal**: “O Queridômetro revela o clima de hoje, as viradas do dia e os padrões de longo prazo — tudo converge para o Paredão.”

**Fluxo ideal do usuário**:
- **Painel**: entende o estado do dia em 30 segundos
- **Mudanças**: descobre o que virou e por quê
- **Trajetória**: entende padrões e consistência
- **Paredão**: conecta reação e voto
- **Arquivo**: valida padrões históricos

---

## 7) Layout: Quarto Dashboards vs artigo

### Recomendação
- **Painel e Paredão**: migrar para **format: dashboard**
  - Benefício: KPIs, alertas e CTAs acima da dobra
  - Melhor para mobile e “glanceable”
- **Mudanças, Trajetória e Arquivo**: manter **formato artigo**
  - Páginas longas e analíticas precisam de narrativa

### Exemplo de grid (Painel)
```
Row 1: [Contexto] [❤️] [Negativas] [Hostilidades] [Mudanças]
Row 2: [Destaques do Dia] [Paredão + CTA]
Row 3: [Ranking Top/Bottom] [Mapa rápido]
Row 4: [Hostilidades do dia] [Tabela compacta]
Row 5: [Perfis (accordion)] [Navegação]
```

### Trade-offs (estático GH Pages)
- **Pró**: melhor hierarquia visual, KPIs claros, boa responsividade
- **Contra**: reformatar conteúdo e ajustar quebras de linha

---

## Observações finais (constrangimentos respeitados)
- Tudo acima é compatível com **Quarto + Plotly + GitHub Pages**.
- Sem backend, sem custos, sem dependência externa paga.
- Interatividade limitada a pré-renderização + JS leve.

**Fim.**
