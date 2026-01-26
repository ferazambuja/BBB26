# Review Polish & Growth — BBB26 (Seções 12–14 + bônus)

## 13) SEO & Social — Open Graph, compartilhamento, descobribilidade

### Open Graph + Twitter Card (Quarto)
**Recomendação**: habilitar metadados sociais no `_quarto.yml` com imagem padrão do site + `site-url`. Quarto suporta `open-graph` e `twitter-card`. citeturn0search0turn0search1

**Exemplo de configuração** (ajuste `site-url` e imagem):
```yaml
website:
  site-url: https://<usuario>.github.io/BBB26
  title: "BBB 26 — Painel de Reações"
  description: "Queridômetro diário do BBB26: alianças, rivalidades e risco de paredão."
  open-graph: true
  twitter-card:
    card-style: summary_large_image
  image: assets/og-card.png
  image-alt: "Painel BBB26 com ranking de sentimento e destaques do dia"
```

**Dicas práticas (estático + gratuito)**
- Gere **1 imagem social padrão** (ex.: `assets/og-card.png`) e **1 por página** quando fizer sentido (Painel, Paredão, Arquivo).
- Defina `description` por página (YAML de cada `.qmd`) para previews mais específicos.
- Adicione `favicon` (Quarto suporta) para melhorar percepção de marca. citeturn0search1

### Shareability (viral leve)
- **Botões de compartilhamento** (WhatsApp/Twitter/X) com texto pré‑montado:
  - “Hoje no BBB26: [Destaque do Dia]. Veja o painel → [link]”
- **Cartões compartilháveis**: gerar PNGs dos “Destaques do Dia” via Plotly/Kaleido durante o render.

### Discoverability
- **Sitemap.xml**: Quarto gera automaticamente em sites — revisar se está ativo.
- **Meta description** por página + títulos claros.
- **URLs consistentes** (ex.: `/paredao.html`, `/mudancas.html`).

---

## 14) Testing — o que testar e como (Python, CI, visual)

### O que testar (alto valor / baixo custo)
1. **Parsing de snapshots**: todos os JSONs carregam sem erro
2. **Conferência de dados mínimos**: nº de participantes > 0, reações por par completas
3. **Cálculos críticos**: sentimento, hostilidades, ranking
4. **Render smoke test**: `quarto render` sem erro
5. **Links internos**: navegação e âncoras

### Sugestão de estrutura mínima
```
/tests/
  test_snapshots.py
  test_metrics.py
  test_render_smoke.py
```

### Exemplo (pytest simples)
```python
# tests/test_snapshots.py
import json, glob

def test_snapshots_valid_json():
    for f in glob.glob('data/snapshots/*.json'):
        with open(f, encoding='utf-8') as fp:
            json.load(fp)

# tests/test_metrics.py
from scripts.metrics import calc_sentiment

def test_sentiment_range():
    score = calc_sentiment({"receivedReactions": []})
    assert score <= 100 and score >= -100
```

### Exemplo (CI no GitHub Actions)
```yaml
- name: Run tests
  run: |
    pip install -r requirements.txt
    pip install pytest
    pytest -q

- name: Render smoke test
  run: quarto render
```

### Visual regression (opcional, gratuito)
- Exportar 3–5 gráficos chave como PNGs (Plotly + Kaleido)
- Comparar checksum com baseline (sem depender de serviços pagos)

---

## 15) Competitive Analysis — 2–3 projetos similares e lições

### 1) Survivor Stats DB (dashboard de reality show)
**O que é**: dashboard interativo com dados consolidados de Survivor, baseado no pacote survivoR. citeturn1search3turn1search0
**Lição**: 
- Navegação por perfis e temporadas + foco em lookup rápido.
- Dados consolidados + dashboard leve para consulta.

Links (copiar/colar):
```
https://survivorstatsdb.com/about.html
https://github.com/doehm/survivoR
```

### 2) Big Brother Brasil (Tableau Brasil)
**O que é**: dashboard interativo com histórico de BBB (audiência, prêmios, trajetória). citeturn1search8
**Lição**:
- Experiência guiada (“siga as setas”), foco em interação simples.
- Reforça o valor de “guia de uso” e desktop-first.

Link:
```
https://tableaubrasil.com.br/entretenimento/big-brother-brasil/
```

### 3) survivoR (dataset + dashboard companion)
**O que é**: pacote de dados estruturados + dashboard vinculado. citeturn1search0turn1search3
**Lição**:
- Separação clara entre **dados** e **dashboard**.
- Ajuda a construir features analíticas ao longo do tempo.

Link:
```
https://github.com/doehm/survivoR
```

---

## BÔNUS — Quick wins + “wow factor” + viral

### Quick wins (1–2 dias)
- **Open Graph + Twitter Card** com imagem padrão (aumenta shareability).
- **Destaques do Dia** (texto auto‑gerado).
- **Share CTA** no topo do Painel.

### Wow factor (baixo custo, alto impacto)
- **“Cartão do dia”**: gerar um PNG com ranking e destaque (Pronto para compartilhar).
- **Mini‑timeline animada** (Plotly com slider, só para 3–5 participantes).

### Viral / comunidade
- **“Quem tá na mira?”** (watchlist) com CTA “compartilhe com o grupo do WhatsApp”.
- **“Top 3 da treta”** (hostilidades mútuas do dia), título chamativo.

---

## Observações finais
- Tudo acima funciona em **hosting estático gratuito**, sem login e sem backend.
- Priorize melhorias que **aumentam compartilhamento** (preview social + cartões).

**Fim.**
