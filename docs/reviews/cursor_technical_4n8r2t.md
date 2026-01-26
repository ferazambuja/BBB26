# BBB26 — Technical Implementation Review

**Baseado em**: `docs/AI_REVIEW_HANDOUT.md` (seções 7–11)  
**Foco**: Interatividade, Deployment, Cartola BBB, Data Storage, Mobile & Accessibility  
**Restrições**: Hosting estático, free tier, Quarto + Plotly, ~90 dias de dados

---

## 8. Interatividade: Essencial vs Nice-to-Have? Shiny vs Observable vs JS?

### Veredito: **nice-to-have**, não essencial

O dashboard hoje entrega valor com **pré-render estático**. Date picker e filtros por participante/grupo melhorariam a experiência, mas não são bloqueadores.

---

### Shiny vs Observable vs pure JS

| Opção | Compatível com GitHub Pages? | Complexidade | Recomendação |
|------|------------------------------|--------------|--------------|
| **Shiny (Python)** | ❌ Não — exige servidor | Alta | **Não** — contradiz “static hosting only”. shinyapps.io free tem limites e não integra com o fluxo atual. |
| **Observable / OJS (Quarto)** | ✅ Sim — client-side | Média | **Possível** — dados embarcados na página ou em `data/*.json` estático. Requer reescrever charts em JS ou consumir Plotly já renderizado. |
| **Pure JS (vanilla ou Alpine)** | ✅ Sim | Média | **Melhor custo/benefício** — date picker + filtros em HTML/JS, trocando visibilidade de divs/Plotly. Sem reescrever a pilha. |
| **Pré-render + tabsets** | ✅ Sim | Baixa | **Recomendado primeiro** — ex.: 3–5 comparações “Hoje vs há 7 dias”, “Hoje vs 1º paredão” em abas. Zero JS novo, só Quarto. |

---

### Abordagem recomendada (estático)

**Fase 1 — Pré-render com tabsets (curto prazo)**

Em `mudancas.qmd`, adicionar 2–3 comparações fixas além de “ontem→hoje”:

- **Aba 1**: Ontem → Hoje (atual)
- **Aba 2**: Há 7 dias → Hoje (se houver snapshot de 7 dias atrás)
- **Aba 3**: Data do 1º paredão → Hoje (se aplicável)

Exemplo de estrutura em Quarto:

```yaml
# mudancas.qmd - dentro de uma seção
## Comparação de Períodos

::: {.panel-tabset}
### Ontem → Hoje
(código Python existente: old_snap = daily[-2], new_snap = daily[-1])
...

### Há 7 dias → Hoje
```{python}
#| label: diff-7d
if len(daily_snapshots) >= 8:
    old_7 = daily_snapshots[-8]
    new_7 = daily_snapshots[-1]
    # Calcular ganhadores/perdedores entre old_7 e new_7
    # Gerar mesmo bloco de charts que "ontem→hoje"
else:
    print("Dados de 7 dias atrás não disponíveis.")
```
:::
```

**Fase 2 — Pure JS (opcional, se quiser date picker)**

- Embarque um `data/comparisons_metadata.json` no build, por exemplo:

```json
{"dates": ["2026-01-13", "2026-01-14", ...], "daily_snapshots": ["2026-01-13", "2026-01-15", ...]}
```

- Gere **uma página estática por comparação** (ex.: `mudancas_2026-01-18_2026-01-25.html`) apenas para as N datas mais recentes (ex.: últimas 5 datas “de referência”) para limitar o número de páginas.
- Ou: um único `mudancas_interativo.html` que carrega `data/daily_metrics.json` (pré-computado, ver seção 11) e usa um date picker em JS para filtrar/animar um gráfico já embarcado (Plotly mantém `config` de react em muitos casos; pode-se usar `Plotly.react` com dados filtrados).

**Fase 3 — Observable**  
Só se houver vontade de ter um “explorador” separado (ex.: uma página só para comparar 2 datas任意). Requer duplicar lógica em JS ou chamar uma API — em static, seria tudo embarcado, então o volume de dados (90 dias de métricas resumidas) precisa caber em um JSON razoável (ver Data Storage).

---

### Resumo

| Caso de uso | Essencial? | Solução estática |
|-------------|------------|------------------|
| Comparar ontem→hoje | Sim | Já existe |
| Comparar 2 datas quaisquer | Nice-to-have | Tabsets com 2–3 pares fixos (Fase 1) |
| Filtro por grupo (Pipoca/Camarote/Veterano) | Nice-to-have | Tabs ou `?:grupo=Pipoca` com 3 versões pré-render (uma por grupo) |
| Toggle participantes no line chart | Nice-to-have | Plotly `visible: 'legendonly'` já permite; não precisa de input extra |
| Foco em 1 participante | Nice-to-have | Página estática `perfil_X.html` ou seção colapsável em Perfis |

**Conclusão**: Manter **100% estático**; priorizar **tabsets com comparações pré-render**. Evitar Shiny. Considerar pure JS + `daily_metrics.json` somente se o date picker for priorizado depois.

---

## 9. Deployment: GitHub Pages + Actions — Suficiente? Que Salvaguardas?

### Veredito: **sim, é suficiente** para o cenário (estático, 4x/dia, free tier), com **salvaguardas adicionais**.

---

### Pontos fortes atuais

- `fetch_data.py` só grava quando o hash muda → evita commits e renders desnecessários.
- `concurrency: group: "pages", cancel-in-progress: false` → evita deploy concorrente.
- `workflow_dispatch` permite re-run manual.
- Uso de `actions/configure-pages` + `deploy-pages` é o fluxo recomendado para Pages.

---

### Gaps e melhorias

#### 1. **Render incondicional**

Hoje o Quarto roda **sempre**, mesmo quando `data_changed=false`. Com 90+ snapshots, 2–3 min por run × 4 runs/dia desperdiça tempo e torna o job mais sujeito a timeout.

**Proposta**: Só rodar `quarto render` quando houver mudança em `data/` ou em `*.qmd`/`_quarto.yml`/assets. Exemplo de adaptação no workflow:

```yaml
      - name: Fetch latest data
        id: fetch
        run: |
          python scripts/fetch_data.py
          if git status --porcelain | grep -q "data/"; then
            echo "data_changed=true" >> $GITHUB_OUTPUT
          else
            echo "data_changed=false" >> $GITHUB_OUTPUT
          fi

      - name: Check for render-triggering changes
        id: should_render
        run: |
          # Render if data changed, or if source/design changed
          if [ "${{ steps.fetch.outputs.data_changed }}" = "true" ]; then
            echo "render=true" >> $GITHUB_OUTPUT
            echo "reason=data" >> $GITHUB_OUTPUT
            exit 0
          fi
          git diff --name-only ${{ github.event.before }} ${{ github.sha }} 2>/dev/null || git diff --name-only HEAD~1 -- . ':(exclude)data/' ':(exclude).git'
          if git diff --name-only ${{ github.event.before }} ${{ github.sha }} 2>/dev/null | grep -qE '\.(qmd|yml)$|^_quarto\.yml|^assets/'; then
            echo "render=true" >> $GITHUB_OUTPUT
            echo "reason=source" >> $GITHUB_OUTPUT
          else
            echo "render=false" >> $GITHUB_OUTPUT
          fi
```

Problema: em `schedule`, `github.event.before` pode não existir. Alternativa mais simples: **só checar `data_changed`** e aceitar que mudanças só em `.qmd` disparem render manual ou no próximo run com `data_changed=true`:

```yaml
      - name: Render Quarto site
        if: steps.fetch.outputs.data_changed == 'true'
        run: quarto render
```

Risco: se alterar só `index.qmd` e não houver novo snapshot, o deploy não reflete a mudança. Mitigação: em PRs que tocam `*.qmd`/`_quarto.yml`, um job de CI (ver item 5) roda `quarto render` para quebrar se houver erro; o deploy em si continua condicionado a `data_changed` no `schedule`. Para `workflow_dispatch` pode-se forçar `render=true` com um `input` ou sempre rodar no manual.

**Recomendação pragmática**:  
- Em **schedule**: `if: steps.fetch.outputs.data_changed == 'true'` no passo “Render Quarto site”.  
- Em **workflow_dispatch**: sempre rodar render (ou um `input: force_render`).

---

#### 2. **API fora do ar**

Se a API Globo falhar, `response.raise_for_status()` derruba o script e o job quebra. O push de `data/` e o deploy dependem do fetch.

**Proposta**: em `fetch_data.py`, em caso de `requests.RequestException` ou 5xx, **não fazer exit(1)**; retornar um código que o Actions interprete como “não há dados novos, pular commit e deploy de dados, mas ainda assim rodar deploy se já houver `_site`” é mais complicado. Mais simples:

- **Fetch**: em falha de rede/API, `exit(1)` (como hoje) para o job falhar.
- **Actions**: **não** fazer `git push` em `data/` se o fetch falhou (já é o caso: o step de fetch falha e os seguintes não rodam).
- **Deploy**: hoje o “Upload artifact” e “Deploy” rodam só se o fetch e o render passaram. Ou seja, em falha de API **não há deploy** — o site continua na versão anterior. Isso é aceitável.

Para **evitar** que um deploy antigo seja “esquecido” (ex.: primeiro run do repo, sem `_site` ainda), garantir que o `Upload artifact` use `_site` de um render anterior. No primeiro deploy, é necessário que ao menos um run completo (fetch OK + render) tenha sucedido. Nada a mudar para o cenário recorrente.

**Opcional**: retry no fetch:

```python
# fetch_data.py
for attempt in range(3):
    try:
        response = requests.get(API_URL, timeout=30)
        response.raise_for_status()
        break
    except requests.RequestException as e:
        if attempt == 2:
            raise
        time.sleep(10 * (attempt + 1))
```

---

#### 3. **Indicação de “última atualização”**

Os usuários não sabem se os dados são de ontem ou de 1h atrás.

**Proposta**: gravar em `data/latest.json` (ou em `_metadata` de cada snapshot) o `captured_at`; no Quarto, ler e exibir no rodapé ou no topo do Painel:

```python
# Em index.qmd (e opcionalmente em outras páginas)
with open("data/latest.json", encoding="utf-8") as f:
    data = json.load(f)
ts = data.get("_metadata", {}).get("captured_at", "")
# Parse e formata em pt-BR, ex.: "25 jan 2026, 13:47 UTC"
```

```html
<!-- No final do body ou no layout -->
<p class="text-muted small">Dados atualizados: 25 jan 2026, 13:47 UTC. Atualização automática 4×/dia.</p>
```

---

#### 4. **Notificação em caso de falha**

Em free tier, o que é viável sem servidor:

- **GitHub**: em “Actions” → “BBB26 Daily Update” → “...” → “Create status badge” e, se quiser, inscrever-se em “Watch” no repositório para receber e-mails de falha de workflow (depende das notificações do usuário).
- **Não recomendado** para esse projeto: webhooks externos, Slack, etc., pois exigem secrets e um mínimo de integração; para um dashboard de nicho, o badge + eventual e-mail do GitHub costumam bastar.

Sugestão: **badge no README**:

```markdown
[![BBB26 Daily Update](https://github.com/USER/BBB26/actions/workflows/daily-update.yml/badge.svg)](https://github.com/USER/BBB26/actions/workflows/daily-update.yml)
```

---

#### 5. **Performance com 90+ snapshots e timeout**

- **Render**: 2–3 min com ~15 snapshots; com 90+ pode chegar a 8–12 min. O limite de jobs no GitHub Actions (6h para jobs default) é suficiente.
- **Mitigação**: pré-computar `data/daily_metrics.json` (ver seção 11) e fazer as páginas “leves” (ex.: Painel, O Que Mudou) lerem esse JSON em vez de carregar todos os snapshots. Trajetória e Arquivo podem continuar carregando os snapshots necessários (ou um subconjunto por data). Isso reduz tempo e memória.

---

### Exemplo de blocos YAML (trechos a integrar no workflow atual)

**Condicionar render no schedule (só quando `data_changed`):**

```yaml
      - name: Render Quarto site
        if: always() && (steps.fetch.outputs.data_changed == 'true' || github.event_name == 'workflow_dispatch')
        run: quarto render
```

(Nota: `always()` faz o step ser avaliado mesmo se fetch tiver falhado; a condição interna evita render quando não há dados novos no schedule. Ajustar conforme a preferência: em falha de fetch, provavelmente não faz sentido rodar render.)

Versão mais simples, apenas para “só render quando dados mudaram no schedule”:

```yaml
      - name: Render Quarto site
        if: steps.fetch.outputs.data_changed == 'true' || github.event_name == 'workflow_dispatch'
        run: quarto render
```

E, para evitar “Upload/Deploy” sem `_site` em caso de skip do render, seria necessário um `_site` pré-existente no repo ou um render “vazio” em outro job. Na prática, se `data_changed` for false no schedule, faz sentido **não** fazer deploy: o `_site` não foi regenerado. O artifact seria o `_site` da última run bem-sucedida — o “Upload artifact” e “Deploy” não têm acesso a runs anteriores. Conclusão: quando `render` é omitido, `_site` pode estar desatualizado ou vazio. Por isso, a opção mais segura é:

- **Sempre** rodar `quarto render` (como hoje), para que `_site` exista.
- **Otimização**: usar `daily_metrics.json` e menos snapshots carregados nas páginas leves para **reduzir tempo** de render, em vez de pular o render.

Se quiser mesmo pular o render quando `data_changed==false`:

- O “Upload artifact” deve usar `path: _site` apenas se `_site` existir; caso contrário, o job precisaria “reusar” o artifact da última run, o que o Actions não suporta nativamente.  
- Alternativa: manter um branch `gh-pages` com o `_site` e, quando `data_changed==false`, fazer `git checkout gh-pages` e usar essa pasta como artifact. Isso exige mudar o fluxo de deploy (deploy-pages vs push em `gh-pages`).  
- **Recomendação**: **manter render sempre**; investir em **pré-computação e menos I/O** para diminuir o tempo de render.

---

### Checklist de salvaguardas

| Salvaguarda | Status | Ação |
|-------------|--------|------|
| Retry no fetch (3× com backoff) | Opcional | Adicionar em `fetch_data.py` |
| Exibir “Dados de: …” no site | Não existe | Ler `_metadata.captured_at` de `latest.json` e mostrar no layout |
| Badge do workflow no README | Não existe | Adicionar badge |
| Render condicional (data_changed) | Não existe | Avaliar: ou sempre render + otimizar, ou condicionar e tratar falta de `_site` |
| Concurrency `pages` | Existe | Manter |
| `workflow_dispatch` | Existe | Manter |

---

## 10. Cartola BBB: Visualizações, Auto vs Manual, Estrutura

### Fontes de dados

- **API (snapshots)**: `roles` (Líder, Anjo, Monstro, Paredão), `memberOf` (VIP/Xepa), participante some da lista quando eliminado.
- **manual_events.json**: `participants` (saídas: desistente, eliminada, desclassificado), `weekly_events` (Líder, Anjo, Monstro, Big Fone, Quarto Secreto, imunidade, VIP, caixas/dinâmicas), `special_events`, `cartola_points_log`.

---

### O que pode ser **auto** vs **manual**

| Evento Cartola | Fonte | Auto? | Observação |
|----------------|-------|-------|------------|
| Líder | API `roles` ou `weekly_events.lider` | Auto (se `weekly_events` estiver preenchido) | API só diz “quem é Líder hoje”; para semana N, `weekly_events` é a autoridade. |
| Anjo | Idem | Auto | Idem. |
| Monstro | `weekly_events.monstro` ou API | Híbrido | API tem “Monstro” no `roles`; para histórico semanal, `weekly_events`. |
| Enviado Quarto Secreto | Só `weekly_events.quarto_secreto` | Manual | |
| Imunizado / Imunizado por | `weekly_events.imunizado` / `imunizado_por` | Manual | |
| Atendeu Big Fone | `weekly_events.big_fone.atendeu` | Manual | |
| Salvo do paredão | Lógica a partir de `paredoes` + `participants` do paredão | Manual / semi | Quem foi salvo pelo Anjo; depende de `manual` ou de `paredao` em `paredao.qmd`. |
| Não eliminado no paredão | Saber quem estava no paredão e quem saiu | Semi | Dados em `paredoes`; quem não tem `resultado: 'ELIMINADA/O'` e estava em `participantes` = +20. |
| Não emparedado | Quem não está em `participantes` do paredão da semana | Semi | Cruzar `weekly_events` (semana) com `paredoes` (participantes do paredão daquela semana). |
| VIP | API `memberOf: VIP` ou `weekly_events.vip_members` | Auto | Para “quem era VIP na semana N”, `vip_members` é melhor. |
| Não recebeu votos | `votos_casa` em `paredao`/`paredoes` | Manual | Já está em `votos_casa`; precisa de lógica “quem não apareceu como alvo”. |
| Monstro retirado do VIP | `weekly_events` ou nota | Manual | |
| Monstro | `weekly_events.monstro` ou API | Manual para histórico | |
| Emparedado | `paredoes[].participantes` (quem não tem `resultado`) | Semi | Quem está no paredão e não foi eliminado ainda = -15 na semana da formação. Cuidado: o -15 é na semana em que foi emparedado. |
| Eliminado | `participants.exit_status` ou `paredoes` | Semi | `manual_events.participants` ou `paredoes` com `resultado: 'ELIMINADA/O'`. |
| Desclassificado | `manual_events.participants` | Manual | |
| Desistente | `manual_events.participants` | Manual | |

---

### Estratégia de cálculo

- **Manter `cartola_points_log`** como registro **por semana e por participante**, podendo ser:
  - **100% manual**: como hoje, preenche-se à mão após cada semana.
  - **Híbrido**: script `scripts/calc_cartola.py` que:
    - Lê `manual_events.json`, snapshots (ou um `daily_metrics.json` que já tenha “última semana”), e `paredoes` (do `paredao.qmd` ou de uma exportação em JSON).
    - Gera eventos que **consegue** inferir (Líder, Anjo, Monstro, VIP da semana, Não emparedado, Emparedado, Eliminado, Desistente, etc.).
    - **Não sobrescreve** o que já existe em `cartola_points_log`; apenas **sugere** ou preenche lacunas, ou gera um `cartola_points_suggested.json` para o humano conferir e copiar para `manual_events.cartola_points_log`.

Exemplo de assinatura:

```python
# scripts/calc_cartola.py (proposta)
def compute_week(week: int, weekly: dict, paredoes_that_week: list, 
                 participants_exits: dict) -> dict[str, list[dict]]:
    """Returns {"participant": [{"event": "...", "points": N}, ...], ...}."""
    # Líder, Anjo, Monstro, VIP, Quarto Secreto, Big Fone, Imunizado, etc.
    # Emparedado: quem está em paredoes_that_week sem resultado
    # Eliminado: quem tem resultado naquela semana em paredoes
    # Desistente: exit_date naquela semana em participants
    ...
```

---

### Estrutura da página Cartola (página nova: `cartola.qmd`)

**Seções sugeridas (ordem):**

1. **Tabela de pontuação (ranking)**  
   - Por semana: colunas = Semana 1, 2, 3, …; linhas = participante; célula = total da semana.  
   - Última coluna: **Acumulado**.  
   - Fonte: `cartola_points_log` (+ sugestão do `calc_cartola` se houver).

2. **Timeline acumulada (linha)**  
   - Eixo X: semana (ou data fim da semana); Eixo Y: pontos acumulados.  
   - Uma série por participante (ou top 10 + “Outros”). Plotly `go.Scatter` com `mode='lines'`.

3. **Distribuição por tipo de evento (barras empilhadas ou treemap)**  
   - Por participante (ou top 15): quantos pontos vieram de Líder, Anjo, VIP, Emparedado, Eliminado, etc.  
   - Ajuda a ver “quem vive de Líder/Anjo” vs “quem acumula -15/-20”.

4. **Tabela de eventos por semana**  
   - Para cada semana: Líder, Anjo, Monstro, Big Fone, Quarto Secreto, Imunizado, VIP, paredão (nomes), eliminado.  
   - Fonte: `weekly_events` + `special_events` + `paredoes`. Pode ser uma tabela estática em Markdown gerada por Python.

5. **Link para Painel / Paredão**  
   - “Ver reações e sentimento → Painel”; “Ver paredão atual → Paredão”.

---

### Esboço de `cartola.qmd`

```yaml
---
title: "BBB 26 — Cartola BBB"
subtitle: "Pontuação e eventos do jogo Cartola BBB"
format:
  html:
    code-fold: true
---
```

```python
# Carregar manual_events.json
# Se existir scripts/calc_cartola, opcionalmente mesclar sugestões
# Construir:
#   - df_weekly: (participant, week, total, events_breakdown)
#   - df_cum: (participant, week, cumsum)
#   - events_by_week: (week, lider, anjo, monstro, big_fone, quarto_secreto, imunizado, vip, paredao_nomes, eliminado)
```

```python
# Tabela ranking (estilo pandas .style ou Plotly table)
# fig = go.Figure(data=[go.Table(header=..., cells=...)])
```

```python
# Timeline acumulada: go.Scatter(x=semana, y=acum, line_shape='hv', ...)
```

```python
# Barras ou treemap por tipo de evento (opcional)
```

---

### O que precisa ficar em `manual_events.json`

- `weekly_events`: `lider`, `anjo`, `monstro`, `big_fone`, `quarto_secreto`, `imunizado`, `imunizado_por`, `vip_members`, `caixas_surpresa` (ou equivalente), e `fontes`.
- `participants`: para desistente, eliminada, desclassificado, com `exit_date` e `cartola_penalty` (ou derivar do tipo).
- `cartola_points_log`: pelo menos um registro por participante que tenha tido algum evento. O script de sugestão pode preencher o que for inferível; o restante (Quarto Secreto, Imunizado, Não recebeu votos, Monstro retirado do VIP) fica manual.

---

## 11. Data Storage: JSON por Snapshot para 90 Dias? Pré-computação?

### JSON por snapshot: **adequado** para 90 dias, com **pré-computação** para escalar

- **~120 arquivos × ~270 KB ≈ 32 MB** é aceitável em disco e em git.
- O gargalo é **tempo de render** e **memória**: carregar 120 JSON e construir 120 matrizes de reação em cada `.qmd` vai pesar.

---

### Manter

- **Um JSON por snapshot** em `data/snapshots/`: bom para auditoria, diff e debug; permite “mostrar reações da data X” carregando só aquele arquivo.
- **`data/manual_events.json`** separado: faz sentido; Cartola e eventos de jogo são outro domínio.
- **`data/latest.json`** como cópia do último snapshot: útil para Painel e scripts.

---

### Pré-computação: `data/daily_metrics.json`

Objetivo: ter um **único JSON** com métricas agregadas **por dia** (uma linha por `(date, participant)` ou por `date`), para que:

- As páginas “leves” (Painel, O Que Mudou) **não** carreguem todos os snapshots.
- Trajetória e Arquivo continuem a acessar snapshots quando precisarem da matriz bruta (heatmap de um dia, reações de um paredão).

**Conteúdo sugerido de `daily_metrics.json`:**

```json
{
  "_metadata": {"generated_at": "2026-01-25T15:00:00Z", "schema": "1.0"},
  "dates": ["2026-01-13", "2026-01-14", ...],
  "by_date": {
    "2026-01-13": {
      "participants": ["Alberto Cowboy", ...],
      "sentiment": {"Alberto Cowboy": 12.5, ...},
      "reaction_counts": {"Alberto Cowboy": {"❤️": 15, "🐍": 2, ...}, ...}
    }
  },
  "deltas": {
    "2026-01-14": {
      "prev": "2026-01-13",
      "winners": [{"name": "X", "delta": 2.5}],
      "losers": [{"name": "Y", "delta": -1.5}],
      "change_count": 12,
      "dramatic": [{"giver": "A", "target": "B", "from": "Coração", "to": "Cobra"}]
    }
  }
}
```

- `by_date`: uma entrada por **data** (usar a data do último snapshot do dia, ou a lógica de `daily_snapshots` já existente).
- `deltas`: opcional; permite “O Que Mudou” sem abrir os dois snapshots. Pode ser gerado por um script que roda **após** `fetch_data.py` (no mesmo job) e antes do `quarto render`.

---

### Script de geração

`scripts/build_daily_metrics.py`:

- Lista `data/snapshots/*.json`, agrupa por data (prefixo `YYYY-MM-DD`).
- Para cada data, pega o último snapshot do dia; calcula `sentiment` por participante, `reaction_counts` (resumo por emoji por pessoa).
- Para cada par (dia anterior, dia atual), calcula `winners`, `losers`, `change_count`, `dramatic` (quem mudou de ❤️ para 🐍 ou equivalente).
- Grava `data/daily_metrics.json`.

**Uso no Actions:**

```yaml
      - name: Fetch latest data
        id: fetch
        run: python scripts/fetch_data.py
        # ... data_changed ...

      - name: Build daily metrics
        if: steps.fetch.outputs.data_changed == 'true'
        run: python scripts/build_daily_metrics.py

      - name: Commit data changes
        if: steps.fetch.outputs.data_changed == 'true'
        run: |
          git add data/
          git diff --staged --quiet || git commit -m "data: snapshot and daily_metrics $(date -u +%Y-%m-%d_%H-%M) UTC"
          git push
```

Em `build_daily_metrics.py`, incluir `daily_metrics.json` no `git add data/` (o commit já adiciona `data/` inteiro).

---

### Uso nas páginas

- **Painel (index.qmd)**:  
  - Para Ranking e Destaques: ler `daily_metrics.json` → `by_date[ultima_data]` e `deltas[hoje]` (se existir).  
  - Para Tabela Cruzada e Perfis: continuar a usar o **último snapshot** (ou `latest.json`), pois precisam da matriz completa. Assim, o Painel só carrega 1 snapshot grande + 1 JSON de métricas.

- **O Que Mudou (mudancas.qmd)**:  
  - Se `deltas` existir para “ontem→hoje”, usar para ganhadores/perdedores e mudanças dramáticas.  
  - Para Mapa de Diferenças e Sankey: ainda é necessário carregar os 2 snapshots. Opcional: no futuro, guardar em `deltas` um “diff compacto” (lista de (giver, target, from, to)); pode aumentar o tamanho do JSON — para ~90 dias e ~500 arestas/dia, é viável.

- **Trajetória (trajetoria.qmd)**:  
  - Evolução do Sentimento: `by_date[*].sentiment` basta; não precisa dos snapshots completos.  
  - Alianças, rivalidades, grafo, clusters: seguir com snapshots (ou um subconjunto: 1 por semana + últimos 7 dias, por exemplo) para não reimplementar a lógica.

- **Arquivo (paredoes.qmd)**:  
  - Por paredão: `get_snapshot_for_date(paredao_date)` como hoje; o snapshot continua necessário para a matriz daquela data.

---

### Formato de arquivo e git

- **Manter 1 JSON por snapshot**: não migrar para SQLite/Parquet agora; o benefício em static + Quarto é pequeno.
- **Git**: 32 MB de JSON ao final da temporada é ok. Evitar LFS a menos que o repositório precise ficar enxuto (por exemplo, para clone em máquinas lentas). Se um dia migrar, `.gitattributes`:

```
data/snapshots/*.json filter=lfs diff=lfs merge=lfs -text
```

- **Backward compatibility**: o código já lida com `[{...}]` e `{_metadata, participants}`. Manter; não reescrever snapshots antigos.

---

### Resumo Data Storage

| Decisão | Recomendação |
|---------|--------------|
| Manter JSON por snapshot? | Sim |
| Adicionar `daily_metrics.json`? | Sim; gerar em `build_daily_metrics.py` após o fetch |
| Migrar para SQLite/Parquet? | Não no horizonte atual |
| LFS para snapshots? | Só se o tamanho do repo se tornar problema |
| Carregar menos snapshots em Trajetória? | Opcional: 1/dia ou 1/semana + últimos 7 dias para gráficos de evolução; snapshots completos só onde for preciso (grafo, heatmap por data) |

---

## 12. Mobile & Accessibility: Problemas e Correções

### Mobile

#### Heatmap 22×22

- Em ~360–400 px de largura, 22 colunas ficam ilegíveis.
- **Sugestões**:
  1. **Scroll horizontal** no container do Plotly: `config={'scrollZoom': False}` e a div com `overflow-x: auto` e `min-width` compatível com a largura nativa do heatmap (ex.: 700–800 px). O Plotly já é responsivo; o ponto é não espremer o gráfico.
  2. **Aba “Resumido” no mobile**: por exemplo, só os 10 mais e 10 menos no sentimento, heatmap 10×10 ou 10×22. Detectar viewport com JS ou, de forma estática, uma **segunda figura** “Top/Bottom 10” exibida via classe CSS `d-md-none`; a heatmap completa em `d-none d-md-block`.
  3. **Tooltip rico**: garantir que, ao toque, o tooltip mostre “Emissor → Receptor: reação”. Plotly já suporta; revisar `hovertemplate`.

Exemplo de div com scroll horizontal:

```html
<div style="overflow-x: auto; -webkit-overflow-scrolling: touch;">
  <div id="heatmap-container" style="min-width: 720px;">
    <!-- Plotly chart -->
  </div>
</div>
```

Em Quarto, se o Plotly for gerado em um `div` com `id`, pode-se colocar esse `div` dentro de um `::: {.overflow-x-auto}` ou usar estilo custom.

#### Navbar e TOC

- Bootstrap + Quarto: navbar colapsa em hamburger. Garantir `lang=pt-BR` e que os itens sejam focáveis e ativáveis por toque.
- TOC (offcanvas ou sidebar): em mobile, o TOC pode cobrir o conteúdo; assegurar `aria-label` e fechar ao escolher um item.

#### Plotly: toque e zoom

- `config` para evitar zoom acidental em mobile:

```python
fig.show(config={'scrollZoom': False, 'responsive': True})
```

- Em `pio.templates['bbb_dark']` ou no `layout` global, não é obrigatório; o importante é que, ao chamar `fig.show()` ou `quarto-render`, o `config` seja passado. Em Quarto, isso costuma ser via `fig.show()`; pode ser centralizado em um helper.

---

### Acessibilidade

#### Gráficos (alt text / aria)

- Plotly gera `<img>` ou `<svg>` com `role="img"`; o `layout.title` não vira `aria-label` automaticamente de forma confiável.
- **Correção**: definir `layout.annotations` ou, melhor, configurar no **layout** um título descritivo e, no HTML, um `<figure>` com `<figcaption>` que o Quarto/Quarto gera. Alternativa: **`fig.update_layout(annotations=[], title=...)`** e, no markdown, um parágrafo imediatamente antes/depois com a descrição, envolvendo o output em `<figure aria-labelledby="...">` exigiria customização.
- Solução pragmática: para cada chart, adicionar um **parágrafo em markdown** antes ou depois, com `aria-describedby` ou que descreva em texto o que o gráfico mostra. Ex.:

```markdown
::: {#desc-ranking aria-hidden="false"}
O *Ranking de Sentimento* mostra, da esquerda para a direita, os participantes 
ordenados pelo score (soma de reações positivas e negativas recebidas). 
Coração soma +1; cobra, alvo, vômito e mentiroso somam -1; planta, mala, 
biscoito e coração partido somam -0,5.
:::

```{python}
#| fig-cap: "Ranking de Sentimento"
fig = make_sentiment_ranking(...)
fig.show()
```
```

- Para **leitura por leitores de tela**: o `fig-cap` do Quarto vira legenda; o bloco de texto acima funciona como descrição longa. Para WCAG 2.1, um `fig-cap` bem escrito já ajuda; o bloco em prosa melhora.

- **Plotly**: em `fig.update_layout`:

```python
fig.update_layout(
    title=dict(text="Ranking de Sentimento — 25 jan 2026"),
    # Plotly não expõe aria-label nativamente; o title aparece no SVG.
    # Garantir que não haja title vazio.
)
```

#### Emojis

- ❤️🐍 etc. podem ser lidos como “emoji coração” ou “cobra”; o significado (Coração, Cobra) nem sempre é óbvio.
- **Correção**: nas tabelas e tooltips, usar **texto entre parênteses** na primeira ocorrência da página (ex.: “❤️ (Coração)”, “🐍 (Cobra)”). Em tooltips do Plotly: `hovertemplate="%{y} → %{x}: %{z} (Coração)"` etc.
- **`aria-label` em células**: em tabelas HTML, `scope` em header e descrição na célula; para heatmap Plotly, o tooltip é o canal principal; a legenda de emojis no topo da página em texto (❤️ Coração, 🐍 Cobra, …) já existe no handout; replicar no site.

#### Contraste (darkly)

- `#375a7f` (azul) e `#00bc8c` (verde) em `#222` costumam passar em AA para texto normal; para gráficos, verificar ratios de linhas/pontos.
- **Correção**: usar [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/). Se algum par falhar, clarear linha (ex.: `#5bc0de`) ou aumentar `line.width` do Plotly. O template `bbb_dark` já usa cores claras; validar ao menos o ranking e a heatmap.

#### Navegação por teclado

- Links e botões (navbar, TOC, Expandir no Plotly): devem ser focáveis e ativáveis por Enter/Space. O Bootstrap e o Quarto já cuidam na maior parte.
- **Plotly**: o foco não entra “dentro” do gráfico de forma útil; o esperado é que o foco vá para o botão “Expandir” e para os links ao redor. Garantir que o `layout.margin` e os botões de modo barra não capturem o foco de forma que impeçam sair do gráfico com Tab.

---

### Performance em dispositivos fracos

- **Vários Plotly na mesma página**: cada um carrega a lib e desenha o DOM. Em Trajetória (muitos charts), consider lazy-load: em `_quarto.yml` não há suporte nativo; uma opção é **dividir Trajetória em subpáginas** (menos charts por página) ou **colapsar seções** com `<details>` e que o primeiro `render` do Plotly ocorra quando o `details` for aberto (o Quarto costuma renderizar tudo; isso pode precisar de JS custom).
- Alternativa simples: **reduzir o número de séries** em gráficos de evolução (ex.: top 10 + “Outros”) em mobile via uma variável `n_track = 10` quando a página detectar viewport pequeno — em estático é mais fácil fazer 2 versões (uma “completa” e uma “reduzida”) e mostrar uma com `d-none d-md-block` e outra com `d-md-none` do que detectar no servidor.

---

### Checklist Mobile & A11y

| Item | Ação |
|------|------|
| Heatmap em mobile | `overflow-x: auto` no container; `min-width` no gráfico; ou heatmap “top/bottom 10” em `d-md-none` |
| Plotly: zoom em mobile | `config={'scrollZoom': False, 'responsive': True}` |
| Descrição de gráficos | `fig-cap` + parágrafo em prosa antes/depois; título em `layout.title` |
| Emojis | Texto “❤️ (Coração)” na legenda e em tooltips; tabela de emojis no início |
| Contraste | Revisar cores do `bbb_dark` em [WebAIM](https://webaim.org/resources/contrastchecker/) |
| Navbar/TOC | Conferir foco e ativação por teclado; `aria-label` em TOC se for custom |
| Performance | Menos séries em gráficos longos em mobile (duas versões) ou menos charts por página (subpáginas em Trajetória) |

---

### Exemplo: `config` e `layout` centralizados (trecho)

```python
# Em um módulo ou no setup do .qmd
PLOTLY_CONFIG = {
    "scrollZoom": False,
    "responsive": True,
    "displayModeBar": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
}

def show_fig(fig):
    return fig.show(config=PLOTLY_CONFIG)
```

E, ao invés de `fig.show()`, usar `show_fig(fig)` ou definir `import plotly.io as pio; pio.kaleido.scope.plotlyjs = None` e usar `pio.write_html(..., config=PLOTLY_CONFIG)` se o output for HTML estático. Em Quarto, `fig.show()` geralmente aceita `config` por parâmetro em versões recentes; verificar a doc do Quarto para o engine em uso.

---

*Documento gerado a partir do AI_REVIEW_HANDOUT.md, foco em implementação técnica (seções 7–11).*
