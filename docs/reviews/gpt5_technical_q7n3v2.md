# Review Técnico — BBB26 (Seções 7–11)

## 8) Interatividade — essencial vs nice‑to‑have? Shiny vs Observable vs JS

### Essencial (baixo custo, alto valor, compatível com estático)
1. **Comparador de datas pré‑renderizado**
   - Dropdown com últimas 7 datas (ou 10) e conteúdo pré‑computado no HTML.
   - Zero backend, sem Shiny.
2. **Filtros de grupo (Pipoca/Camarote/Veterano)**
   - Renderizar 3 versões das tabelas/gráficos e alternar via JS simples (mostrar/ocultar).
3. **Modo foco (participante)**
   - Selector que mostra blocos já renderizados por participante (colapsados por padrão).

### Nice‑to‑have (se houver tempo)
- **Mini‑tabs por período** (Últimos 3 dias / 7 dias / Total)
- **Ordenação dinâmica** (ex.: ranking por sentimento vs vulnerabilidade) com JS que alterna colunas já calculadas.

### Não recomendado (custo alto + estático)
- **Shiny**: precisa servidor (ou shinyapps.io pago), não compatível com GitHub Pages.
- **Observable JS**: possível, mas aumenta complexidade, exige OJS e carregamento de dados no cliente.

### Recomendação
- **Priorizar JS leve** (show/hide) + pré‑render no Quarto.
- **Evitar Shiny** (incompatível com hospedagem estática gratuita).

#### Exemplo (JS simples para alternar blocos)
```html
<div class="btn-group" role="group">
  <button class="btn btn-sm btn-outline-light" data-target="#view-all">Todos</button>
  <button class="btn btn-sm btn-outline-light" data-target="#view-pipoca">Pipoca</button>
  <button class="btn btn-sm btn-outline-light" data-target="#view-camarote">Camarote</button>
  <button class="btn btn-sm btn-outline-light" data-target="#view-veterano">Veterano</button>
</div>

<div id="view-all">...plot/table full...</div>
<div id="view-pipoca" style="display:none">...plot/table pipoca...</div>
<div id="view-camarote" style="display:none">...</div>
<div id="view-veterano" style="display:none">...</div>

<script>
document.querySelectorAll('[data-target]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('[id^="view-"]').forEach(el => el.style.display = 'none');
    document.querySelector(btn.dataset.target).style.display = 'block';
  });
});
</script>
```

---

## 9) Deploy — GitHub Pages + Actions é robusto? Safeguards

**Sim, é suficiente** para 90 dias de dados e render 4x/dia. Mas faltam salvaguardas:

### Safeguards recomendados
1. **Fail fast no render**
   - Se `quarto render` falhar, **não** faz deploy.
2. **Validação de snapshots**
   - Checar JSON malformado ou vazio antes de render.
3. **Checagem de links internos**
   - `quarto render` + script simples de verificação de links.
4. **Logs claros**
   - Salvar `stderr` e anexar em artifact do GitHub Actions.

### Exemplo (workflow com salvaguardas)
```yaml
- name: Validate snapshots
  run: |
    python - <<'PY'
    import json, sys, glob
    for f in glob.glob('data/snapshots/*.json'):
        try:
            json.load(open(f, encoding='utf-8'))
        except Exception as e:
            print(f"Invalid JSON: {f}: {e}")
            sys.exit(1)
    print("Snapshots OK")
    PY

- name: Render Quarto
  run: quarto render

- name: Link check (light)
  run: |
    python - <<'PY'
    import re
    html = open('_site/index.html', encoding='utf-8').read()
    if '404' in html:
        print('Potential broken references')
    PY
```

### Deploy robusto
- Manter `fetch_data.py` com hash (já existe)
- Commit apenas quando houve mudança
- Usar cache de pip

---

## 10) Página Cartola BBB — estrutura + auto‑calc vs manual

### Objetivo
Atender “cartoleiros” com métricas de risco, destaque e regularidade.

### Estrutura recomendada
1. **Resumo da rodada** (cards)
   - Top pontuador da semana
   - Maior queda
   - Melhor custo/benefício
2. **Ranking Cartola (tabela)**
   - Pontos semanais + acumulados
3. **Watchlist de risco**
   - Quem tem alta hostilidade e baixa popularidade
4. **Gráfico de tendência (sparklines)**
   - Evolução de 5 principais nomes
5. **Histórico por participante**
   - tabela com pontos semanais

### Auto‑calc vs manual
**Auto‑calc possível**:
- Sentimento, hostilidade, vulnerabilidade (a partir do API)
- Métricas de consistência (variação diária)

**Manual necessário**:
- Eventos de jogo (Líder, Anjo, Monstro, Big Fone)
- Pontuação Cartola se não existir API oficial

### Exemplo de entrada manual (JSON)
```json
{
  "week": 2,
  "leader": "Babu Santana",
  "anjo": "Jonas Sulzbach",
  "monstro": ["Chaiany"],
  "cartola_points": {
    "Babu Santana": 95,
    "Jonas Sulzbach": 82
  }
}
```

---

## 11) Data Storage — JSON por snapshot é bom para 90 dias?

### Avaliação
- **Sim**. 90 dias × 4 capturas/dia → ~120 snapshots (~30–40 MB) é aceitável em Git.
- O gargalo será **tempo de render**, não tamanho.

### Recomendações
1. **Pré‑computar métricas diárias**
   - Criar `data/daily_metrics.json` com:
     - sentimento por participante/dia
     - mudanças diárias
     - hostilidades
2. **Pré‑computar comparações recentes**
   - Últimos 7 dias já renderizados → melhora UX sem backend.
3. **Cache de parsing**
   - Em cada `.qmd`, carregar `daily_metrics.json` primeiro; só carregar snapshots completos quando necessário.

### Exemplo de pré‑cálculo (script)
```python
# scripts/build_daily_metrics.py
import json, glob
from datetime import datetime

metrics = {}
for f in glob.glob('data/snapshots/*.json'):
    data = json.load(open(f, encoding='utf-8'))
    participants = data.get('participants', data)
    date = f.split('/')[-1].split('_')[0]
    # ... calcular sentimento etc.
    metrics.setdefault(date, {})['sentiment'] = {...}

with open('data/daily_metrics.json', 'w', encoding='utf-8') as f:
    json.dump(metrics, f, ensure_ascii=False)
```

### Estrutura sugerida
```
/data/
  snapshots/           # bruto
  daily_metrics.json   # métricas prontas
  manual_events.json   # eventos manuais
```

---

## 12) Mobile & Accessibility — problemas e correções

### Problemas críticos (mobile)
- Heatmaps 22×22 ilegíveis
- Network graph pesado no celular
- Scroll longo sem “resumo”

### Correções viáveis
1. **Versão compacta para mobile**
   - CSS media query: esconder heatmap completo e mostrar mini‑tabela resumida
2. **Lazy load de charts abaixo da dobra**
   - Renderizar imagens estáticas ou placeholders
3. **Botão “Abrir gráfico completo”**
   - Força usuário a abrir modal full‑screen

### Acessibilidade
- Contraste do tema darkly precisa validação
- Emojis como único canal de informação → adicionar legendas textuais

#### Exemplo CSS (mobile)
```css
@media (max-width: 768px) {
  .heatmap-full { display: none; }
  .heatmap-compact { display: block; }
}
```

#### Exemplo (legendas textuais)
```
❤️ = apoio | 🐍 = traição | 💔 = decepção
```

---

## Conclusão técnica
- **Interatividade mínima + pré‑render** é a estratégia ideal no static.
- **GitHub Pages + Actions** é suficiente, com validações extras.
- **JSON por snapshot** é aceitável; pré‑computação reduz render e melhora UX.
- **Mobile** precisa fallback compacto e lazy‑load.

**Fim.**
