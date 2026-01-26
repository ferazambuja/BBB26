# BBB26 — Polish & Growth Review

**Baseado em**: `docs/AI_REVIEW_HANDOUT.md` (seções 12–14)  
**Foco**: SEO & Social, Testing, Competitive Analysis + Quick Wins e “wow factor”  
**Restrições**: Audiência em português, hosting estático, free tier, sem login

---

## Resposta rápida: todos os reviews foram salvos como .md?

Sim. Os arquivos de review estão em **`docs/reviews/`** no formato do handout (`{MODEL}_{FOCUS}_{ID}.md`):

| Foco       | Arquivo                      |
|-----------|------------------------------|
| UX (1–6)  | `cursor_ux_2h4j6k.md`        |
| Técnico (7–11) | `cursor_technical_4n8r2t.md` |
| Polish (12–14) | `cursor_polish_7x2k9m.md` (este) |

---

## 13. SEO & Social: Open Graph, Shareability, Discoverability

### Estado atual

- Meta tags básicas do Quarto (título, etc.)
- Sem Open Graph / Twitter Card
- Sem `description` por página
- Sem `site-url` → sem sitemap automático
- Sem imagem de preview para redes

---

### 1. Open Graph e Twitter Card no Quarto

O Quarto gera OG e Twitter Card com `open-graph: true` e `twitter-card: true`. É preciso definir **`site-url`** para que imagens e links fiquem absolutos.

**Exemplo para `_quarto.yml`** (incluir em `website:`):

```yaml
website:
  title: "BBB 26 — Painel de Reações"
  description: "Análise do Queridômetro do BBB 26: reações entre participantes, sentimento, alianças e coerência com os votos. Atualizado 4× ao dia."
  site-url: "https://SEU-USUARIO.github.io/BBB26"   # Ajustar ao seu Pages
  favicon: "assets/favicon.ico"                      # Opcional: criar favicon

  open-graph: true
  open-graph:
    locale: "pt_BR"
    site-name: "BBB 26 — Painel de Reações"
    image: "assets/og-default.png"                   # Imagem padrão (v. seção Shareability)
    image-width: 1200
    image-height: 630

  twitter-card: true
  twitter-card:
    card-style: "summary_large_image"
    image: "assets/og-default.png"
    # creator: "@seu_twitter"   # Se tiver
```

Com isso, o Quarto usa `title` e `description` de cada `.qmd` (ou do `website`) para OG/Twitter. Se uma página tiver `image:` no front matter, ela sobrescreve a imagem padrão.

**Por página** (ex. `index.qmd`):

```yaml
---
title: "BBB 26 — Painel de Reações"
description: "Ranking de sentimento, heatmap de reações e perfis dos participantes do BBB 26. Dados atualizados 4× ao dia."
# image: "assets/og-painel.png"   # Opcional: OG específico por página
lang: pt-BR
---
```

Repetir `description` (e opcionalmente `image`) em `mudancas.qmd`, `trajetoria.qmd`, `paredao.qmd`, `paredoes.qmd` com textos específicos.

---

### 2. Sitemap

O Quarto gera **`sitemap.xml`** em `_site` quando `site-url` está definido. Não é preciso fazer nada além de:

```yaml
website:
  site-url: "https://SEU-USUARIO.github.io/BBB26"
```

Se o site estiver em subpath (ex. `https://usuario.github.io/BBB26/`), pode ser necessário `site-path`:

```yaml
website:
  site-url: "https://SEU-USUARIO.github.io"
  site-path: "BBB26"
```

Após o render, conferir `_site/sitemap.xml`.

---

### 3. Shareability — imagens para redes

**Problema**: WhatsApp, Twitter e Facebook usam uma imagem de preview. Sem `og:image`, o link fica sem thumbnail.

**Opções (estático, free tier):**

| Abordagem | Prós | Contras |
|-----------|------|---------|
| **Imagem estática fixa** | Simples, sempre funciona | Menos “específica” por página |
| **PNG do gráfico no build** | Destaque visual (ranking, heatmap) | Requer kaleido (+ Chrome em alguns CI); precisa de passo extra no render |
| **`preview-image` no 1º gráfico** | Quarto pode usar a 1ª figura com classe `preview-image` | Depende de como o Plotly é inserido; nem sempre vira `og:image` de forma confiável |

**Recomendação imediata**: criar **`assets/og-default.png`** (1200×630):

- Fundo escuro (ex. `#222`), título “BBB 26 — Painel de Reações”, subtítulo “Queridômetro: reações, sentimento e votos” e, se possível, um recorte simples do ranking (mesmo que estático). Ferramentas: Canva, Figma, GIMP ou script com PIL.
- Colocar em `assets/` e referenciar em `website.open-graph.image` e `twitter-card.image` como no YAML acima.

**Fase 2 (opcional)**: no job de render, exportar o ranking (ou outro gráfico) para PNG com Plotly + kaleido e usar como `og:image`:

```python
# No final do cell do ranking (index.qmd) ou em script de pos-render
# fig = make_sentiment_ranking(...)
# fig.write_image("assets/og-ranking.png", width=1200, height=630, scale=2)
```

Em `_quarto.yml`:

```yaml
website:
  open-graph:
    image: "assets/og-ranking.png"
```

**Kaleido em CI**: `pip install kaleido`; em alguns runners é preciso `apt` de `chromium` ou equivalente. Se der problema, manter `og-default.png` estática.

---

### 4. “Compartilhar este participante”

Um link do tipo `https://site/ index.html#perfis-X` (âncora para o perfil de “X”) já permite compartilhar “vai direto para o perfil do X”. Não exige login nem backend.

**Melhoria**: garantir que cada perfil em Perfis Individuais tenha `id="perfil-Nome"` (ou slug) para que `index.html#perfil-Jordana` funcione. Se o accordion ou o título já tiver id, basta documentar o padrão (ex. “Compartilhe: [Painel#perfil-Jordana](index.html#perfil-Jordana)”).

Não é necessário botão “Compartilhar no WhatsApp” com `api.whatsapp.com` se o usuário puder copiar a URL; se quiser, um botão “Compartilhar” que abre `https://wa.me/?text=...` com `title` + URL é estático e não exige login.

---

### 5. Discoverability

- **Google**: `site-url` + sitemap + `description` por página ajudam. Enviar o sitemap em [Google Search Console](https://search.google.com/search-console) (free).
- **Bing**: idem, [Bing Webmaster](https://www.bing.com/webmasters).
- **Reddit / fóruns (r/BigBrotherBrasil, etc.)**: postar o link quando fizer sentido (ex.: “Fiz um painel com o Queridômetro da API”). Evitar spam.
- **Twitter/X**: hashtags `#BBB26`, `#BBB26Queridometro` ao divulgar.
- **`robots.txt`**: o Quarto não gera por padrão. Se quiser, criar `robots.txt` na raiz do projeto:

```
User-agent: *
Allow: /
Sitemap: https://SEU-USUARIO.github.io/BBB26/sitemap.xml
```

e garantir que esteja em `resources` ou que seja copiado para `_site` (o Quarto copia `robots.txt` da raiz se existir; ver [Website Tools - Site Resources](https://quarto.org/docs/websites/website-tools.html)).

---

### Checklist SEO & Social

| Item | Ação |
|------|------|
| `site-url` | Definir em `_quarto.yml` (e `site-path` se subpath) |
| `description` | Em `website` e em cada `.qmd` (único por página) |
| `open-graph: true` e `open-graph.locale`, `site-name`, `image` | Ver YAML acima |
| `twitter-card: true` e `card-style: summary_large_image` | Ver YAML acima |
| `assets/og-default.png` 1200×630 | Criar e referenciar em `open-graph.image` e `twitter-card.image` |
| `favicon` | Opcional: `assets/favicon.ico` |
| `sitemap.xml` | Gerado pelo Quarto com `site-url`; checar em `_site` |
| `robots.txt` | Opcional; `Sitemap:` apontando para o sitemap |
| Share “por participante” | Âncoras `#perfil-Nome` e, opcionalmente, botão “Compartilhar” com URL |
| Google/Bing Search Console | Enviar sitemap (free) |

---

## 14. Testing: o que testar e como (Python, CI, regressão visual)

### Estado atual

- Nenhum teste automatizado
- Verificação manual após o render
- Alguns avisos do Pandoc (divs) que não quebram o HTML

---

### 1. O que testar

| Camada | O quê | Prioridade |
|--------|-------|------------|
| **Dados** | Snapshots carregam; `load_snapshot` lida com formato antigo e novo; `get_snapshot_for_date` devolve algo coerente | Alta |
| **Cálculos** | `calc_sentiment`, `build_reaction_matrix`, detecção de ganhadores/perdedores, deltas | Alta |
| **Render** | `quarto render` termina sem erro (exit 0) | Alta |
| **Links** | Nenhum link interno quebrado (`index.html`, `paredao.html`, etc.) | Média |
| **Gráficos** | Plotly gera JSON/HTML sem exceção; opcional: checagem de que o HTML contém elementos do gráfico | Média |
| **Regressão visual** | Screenshots antes/depois de mudanças (Percy, Playwright, etc.) | Baixa (mais custo) |

---

### 2. Testes em Python (pytest)

Extrair funções “puras” (load, matriz, sentimento, deltas) para um módulo `scripts/bbb_utils.py` (ou manter em um `.qmd` e importar; o mais simples é duplicar as funções mínimas em `tests/` só para o pytest) e testar.

**Exemplo de estrutura**:

```
tests/
  __init__.py
  test_load.py      # load_snapshot, get_all_snapshots
  test_calc.py      # calc_sentiment, build_reaction_matrix, SENTIMENT_WEIGHTS
  conftest.py       # fixtures: paths, 1–2 snapshots de exemplo
```

**Exemplo `tests/conftest.py`**:

```python
import json
from pathlib import Path
import pytest

DATA_DIR = Path(__file__).parent.parent / "data" / "snapshots"

@pytest.fixture
def sample_snapshot_path():
    paths = sorted(DATA_DIR.glob("*.json"))
    if not paths:
        pytest.skip("No snapshots in data/snapshots")
    return paths[-1]

@pytest.fixture
def sample_snapshot(sample_snapshot_path):
    with open(sample_snapshot_path, encoding="utf-8") as f:
        data = json.load(f)
    participants = data.get("participants", data) if isinstance(data, dict) else data
    return participants
```

**Exemplo `tests/test_load.py`**:

```python
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
# Ou: from scripts.xxx import load_snapshot, se houver __init__

from pathlib import Path
import json

def load_snapshot(filepath):
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "participants" in data:
        return data["participants"], data.get("_metadata")
    return data, None

def test_load_snapshot_new_format(sample_snapshot_path):
    participants, meta = load_snapshot(sample_snapshot_path)
    assert isinstance(participants, list)
    assert len(participants) >= 1
    assert "name" in participants[0]
    assert "characteristics" in participants[0]

def test_load_snapshot_old_format():
    # Se tiver um snapshot antigo em tests/fixtures/: array puro
    old = Path(__file__).parent / "fixtures" / "old_format.json"
    if not old.exists():
        pytest.skip("No old format fixture")
    participants, meta = load_snapshot(old)
    assert isinstance(participants, list)
    assert meta is None
```

**Exemplo `tests/test_calc.py`** (usando a mesma assinatura de `calc_sentiment` e `build_reaction_matrix` do projeto):

```python
# Copiar SENTIMENT_WEIGHTS e assinaturas de calc_sentiment e build_reaction_matrix
# do index.qmd ou de um bbb_utils.py

def test_calc_sentiment_positive_only(sample_snapshot):
    # Montar um participante só com Coração; importar calc_sentiment de bbb_utils (ou do módulo onde estiver)
    # from bbb_utils import calc_sentiment
    p = {"characteristics": {"receivedReactions": [
        {"label": "Coração", "amount": 10, "participants": []}
    ]}}
    s = calc_sentiment(p)
    assert s == 10.0

def test_build_reaction_matrix_has_correct_keys(sample_snapshot):
    # from bbb_utils import build_reaction_matrix
    matrix = build_reaction_matrix(sample_snapshot)
    names = {p["name"] for p in sample_snapshot}
    for (g, r), v in matrix.items():
        assert g in names and r in names
        assert v in {"Coração", "Planta", "Mala", "Biscoito", "Cobra", "Alvo", "Vômito", "Mentiroso", "Coração partido", ""} or True  # ajustar ao seu conjunto
```

Na prática, o mais útil é ter `bbb_utils.py` (ou equivalente) com `load_snapshot`, `calc_sentiment`, `build_reaction_matrix` e importar em `tests/`. Os exemplos acima mostram o tipo de assertivas.

---

### 3. CI (GitHub Actions)

**Job 1: testes Python** (sempre, em push/PR):

```yaml
# .github/workflows/test.yml (novo) ou adicionar job em daily-update
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      - run: pip install -r requirements.txt pytest
      - run: pytest tests/ -v
```

**Job 2: quarto render (smoke)**  
Para garantir que nenhum `.qmd` quebra o build, rodar `quarto render` em PRs que alteram `*.qmd`, `_quarto.yml` ou `scripts/`. Pode ser pesado com 90+ snapshots; uma opção é ter 2–3 snapshots de fixture em `tests/fixtures/snapshots/` e um `QUARTO_DATA_DIR=tests/fixtures` (ou script que temporariamente troca `DATA_DIR`) só no job de teste. Mais simples: rodar o render completo no CI 1x por PR; se demorar, deixar só no `schedule` e aceitar que quebras em .qmd podem ser descobertas lá.

**Job 3: checagem de links**  
Ferramenta: [lychee](https://github.com/lycheeverse/lychee) ou [linkcheckmd](https://github.com/nicoddemus/linkcheckmd). Exemplo com lychee (binário ou `cargo install lychee`; em Actions, `lychee/lychee-action`):

```yaml
- name: Check links
  uses: lycheeverse/lychee-action@v1
  with:
    args: '_site/**/*.html'
    # fail: true  # se quiser falhar o job em link quebrado
```

Como o `_site` só existe depois do `quarto render`, esse passo deve depender do job de render. Alternativa: rodar lychee só no `schedule` (depois do deploy), ou em um job que faz `quarto render` e depois `lychee`.

---

### 4. Regressão visual

- **Percy, Playwright, BackstopJS** etc. tiram screenshot e comparam. Para estático em free tier, o custo é sobretudo de tempo e manutenção.
- **Recomendação**: deixar para uma fase posterior. Se fizer, usar **uma** página (ex. `index.html`) e um viewport fixo (ex. 1280×720) para não explodir o número de screenshots.
- **Substituto leve**: um teste que garante que o HTML do ranking (ou da heatmap) contém strings esperadas, por exemplo `"Ranking de Sentimento"` e a classe do container do Plotly. Não substitui regressão visual, mas evita que um refactor quebre o bloco inteiro.

---

### 5. Tratamento de erros nos dados

- **API fora**: `fetch_data.py` já faz `raise_for_status`; o job quebra. Retry e notificação estão no review técnico.
- **Snapshot corrompido**: `load_snapshot` pode envolver `try/except` e, em caso de `json.JSONDecodeError`, registrar e pular o arquivo (ou falhar). Em contexto de render, “pular” pode deixar um dia sem dados; para um painel crítico, **falhar** pode ser preferível. O importante é **não travar sem mensagem**.
- **Formato inesperado** (ex. `participants` vazio ou sem `name`): `calc_sentiment` e `build_reaction_matrix` devem tolerar dados incompletos (ex. `get(..., [])`). Testes com fixtures “quebradas” ajudam.

---

### Checklist Testing

| Item | Ação |
|------|------|
| `pytest` | `tests/test_load.py`, `tests/test_calc.py` (e `conftest.py`) |
| `bbb_utils.py` | Extrair `load_snapshot`, `calc_sentiment`, `build_reaction_matrix` (ou copiar para `tests` só para pytest) |
| CI `pytest` | Job em `test.yml` ou no workflow de PR |
| CI `quarto render` | Job que roda `quarto render` em PRs que tocam `.qmd`/`_quarto.yml` (ou só no schedule) |
| Lychee (ou similar) | Job que roda sobre `_site` após o render |
| Regressão visual | Opcional; em caso de fazer, 1 página e 1 viewport |
| `load_snapshot` com JSON quebrado | `try/except` + log claro ou falha controlada |

---

## 15. Competitive Analysis: 2–3 projetos parecidos e o que aproveitar

### 1. BBBstatistics (Matt-Fontes) — BBB 2021

- **Link**: [github.com/Matt-Fontes/BBBstatistics](https://github.com/Matt-Fontes/BBBstatistics)  
- **Site (quando existia)**: [tiny.cc/bbbstats](https://tiny.cc/bbbstats)  
- **O que é**: site estático com estatísticas em “tempo real” (seguidores e “outras coisinhas”), páginas `index`, `paredoes`, `queridometro`, `sobre`. HTML/CSS/JS, sem framework pesado.

**O que aproveitar**

- Estrutura de páginas parecida: índice, paredões, queridômetro, sobre. O BBB26 já tem Painel, Paredão, Arquivo e O Que Mudou; faz sentido uma **“Sobre”** (metodologia, fontes, atualização, link para a API/Globo).
- **Queridômetro em página dedicada**: no BBB26 o ranking/heatmap estão no Painel; dá para manter, mas a ideia de ter uma “página do Queridômetro” (ou seção de destaque) alinha com o que o público de BBB espera.
- **Simplicidade**: HTML estático e leve. O BBB26 com Quarto + Plotly é mais pesado; vale manter só o necessário (evitar JS extra) e otimizar carregamento (lazy, pré-computação).
- **Divulgação**: o `tiny.cc/bbbstats` sugere uso de link curto para compartilhar; um link curto para a home ou para “Queridômetro” pode ajudar em redes e fóruns.

---

### 2. Survivor Stats e ecossistema (Survivor EUA)

- **Survivor Stats (Zak Laughton)**: [github.com/ZakLaughton/survivor-stats](https://github.com/ZakLaughton/survivor-stats) — React + Node + PostgreSQL; status por episódio, tribes, advantages.  
- **survivor-stats-website (mollyjewel)**: [github.com/mollyjewel/survivor-stats-website](https://github.com/mollyjewel/survivor-stats-website) — React + MUI, edição e análise de dados.  
- **Outwit Outplay Outlast (caievelyn)**: [github.com/caievelyn/outwit_outplay_outlast](https://github.com/caievelyn/outwit_outplay_outlast) — R Shiny, 37 temporadas.  
- **survivor-data (davekwiatkowski)**: [github.com/davekwiatkowski/survivor-data](https://github.com/davekwiatkowski/survivor-data) — repositório de dados em JSON.

**O que aproveitar**

- **Dados bem definidos e versionados** (survivor-data): JSON por temporada/episódio. No BBB26, os snapshots já cumprem papel parecido; o `daily_metrics.json` (pré-computado) segue a ideia de “resumo estável” para consumo rápido.
- **Seleção por temporada/episódio**: em Survivor, a ideia de “escolher época” é central. No BBB26 estático, isso se traduz em **tabsets ou links** “Hoje”, “Há 7 dias”, “1º Paredão” (já sugerido no review técnico), em vez de backend.
- **Comunidade e fontes**: Survivor tem wiki e fãs que citam fontes. No BBB26, a **página Sobre** com metodologia, `manual_events` com `fontes` e menção a GShow/API deixa o projeto mais “citável” e confiável.
- **Shiny vs estático**: Outwit Outplay Outlast é Shiny (requer servidor). Para BBB26, o que importa é a **organização das análises** (evolução, comparações, paredões), não a stack; dá para replicar a lógica em estático com tabs e filtros pré-render.

---

### 3. Parrot Analytics (Big Brother Brasil)

- **Link**: [tv.parrotanalytics.com/BR/big-brother-brasil-tv-globo](https://tv.parrotanalytics.com/BR/big-brother-brasil-tv-globo)  
- **O que é**: demanda de audiência, não painel de participantes. Mostra “37.7× a média” etc.

**O que aproveitar**

- **Linguagem de “métricas” e comparação**: mesmo que o BBB26 não calcule demanda, usar **números simples e comparáveis** (ex. “X é o que mais subiu na semana”, “Y tem o maior número de reações negativas”) torna o painel mais “analítico” e compartilhável.
- **Apresentação**: gráficos claros e títulos que contam uma história. No BBB26, **Destaques do Dia** e **frases de insight** (como no review de UX) vão nessa direção.

---

### Síntese comparativa

| Projeto | Tipo | Stack | Lição principal |
|---------|------|-------|------------------|
| BBBstatistics | BBB (BR), queridômetro/paredões | HTML/CSS/JS | Página Sobre, queridômetro em destaque, link curto para divulgação |
| Survivor Stats / survivor-data | Survivor (EUA) | React, Node, R Shiny, JSON | Dados versionados, “escolher época” (tabs/links), documentação e fontes |
| Parrot (BBB) | Audiência | SaaS | Linguagem de métricas e comparação, narrativa com números |

---

## BÔNUS: Quick Wins, “Wow Factor” e Recursos Mais Visíveis

### Quick wins (pouco esforço, alto impacto)

1. **`site-url` + `description` + `open-graph: true` e `twitter-card: true`** em `_quarto.yml` — melhora SEO e preview em redes.  
2. **`assets/og-default.png`** 1200×630 — share com imagem em vez de link “vazio”.  
3. **`description` por página** em cada `.qmd` — 1 frase por arquivo.  
4. **Página “Sobre”** (`sobre.qmd`): o que é o painel, fonte dos dados (API Globo + manual), atualização 4×/dia, link para o repo e, se houver, `fontes` em `manual_events`. Incluir no `navbar` em `_quarto.yml`.  
5. **Texto “Dados de: …”** no rodapé ou no Painel (a partir de `latest.json` → `_metadata.captured_at`), como no review técnico.  
6. **Âncoras nos perfis** (`id="perfil-Nome"`) e exemplo de link “Compartilhe o perfil de X” na seção de Perfis.  
7. **`pytest` para `load_snapshot` e `calc_sentiment`** com 1–2 fixtures — evita quebras silenciosas ao mudar dados ou funções.

---

### “Wow factor” (destaque visual e de conteúdo)

1. **Destaques do Dia** (já no review de UX): 3–5 tópicos no topo do Painel (quem subiu/desceu, hostilidade nova, status do paredão). Dá impressão de “site vivo” e diferente do GShow.  
2. **Card do Paredão** no topo do Painel com link para a página do Paredão — reforça o evento semanal.  
3. **Um “insight do dia” em texto** (ex.: “Hoje, quem mais ganhou reações positivas foi X; quem mais perdeu foi Y”) mesmo que curto. Pode ser gerado a partir das mesmas métricas de “O Que Mudou”.  
4. **Gráfico “Reações preveem votos?”** na página do Paredão já é diferencial; destacar isso no Sobre e no texto de divulgação (“analisamos se o Queridômetro antecipa o voto da casa”).  
5. **Exportar o ranking como PNG** (Plotly + kaleido) e usar como `og:image` (ou alternar com `og-default.png`) — o card nas redes mostra o ranking de verdade, não só um título.

---

### Recursos “virais” / comunidade (sem login, estático)

1. **URLs compartilháveis por contexto**  
   - `index.html#ranking`  
   - `index.html#perfil-Jordana`  
   - `paredao.html`  
   - `trajetoria.html#evolucao`  
   Documentar no Sobre: “Links para compartilhar”.

2. **Texto pronto para Ctrl+C**  
   Na Sobre ou em um callout: “Ao divulgar, pode usar: *Painel de reações do BBB 26: ranking de sentimento, heatmap e coerência com os votos. Atualizado 4× ao dia. [link]*”.

3. **Hashtags sugeridas**  
   No rodapé ou Sobre: “#BBB26 #BBB26Queridometro” para quem divulga no Twitter/Instagram.

4. **Link curto**  
   Se houver domínio ou short link (bit.ly, tiny.cc, etc.), usar na navbar ou no Sobre para posts e stories.

5. **Botão “Compartilhar” (opcional)**  
   Abrir `https://wa.me/?text=` ou `https://twitter.com/intent/tweet?text=` com `title` + URL. Pode ser um ícone no navbar ou ao lado do título. 100% client-side.

6. **RSS (opcional)**  
   Se no futuro houver “posts” ou “atualizações” (ex. uma listing de “O que mudou na última semana”), o Quarto permite `feed` em listings. Para um site só com dashboards, RSS é secundário; fica como melhoria futura.

---

### Exemplo de “Sobre” (`sobre.qmd`)

```yaml
---
title: "Sobre"
description: "Metodologia, fontes e atualização do Painel de Reações do BBB 26."
---
```

Conteúdo sugerido (resumo):

- **O que é**: painel que usa a API do GloboPlay e dados manuais para analisar o Queridômetro, o voto da casa e a coerência entre reações e votos.
- **Fontes**: API GloboPlay (reações, saldo, papéis); `manual_events.json` (Líder, Anjo, Paredão, Big Fone, etc.) e `paredoes` (votos e resultados) com links para GShow e notícias quando existirem.
- **Atualização**: 4× ao dia via GitHub Actions; “Dados de: …” no Painel.
- **Como citar / compartilhar**: link do site, hashtags #BBB26 e #BBB26Queridometro, e o texto sugerido acima.
- **Código**: link para o repositório (e licença, se aplicável).

Incluir no `_quarto.yml`:

```yaml
website:
  navbar:
    left:
      - href: index.qmd
        text: "📊 Painel"
      # ... itens atuais ...
      - href: paredoes.qmd
        text: "📚 Arquivo"
      - href: sobre.qmd
        text: "Sobre"
```

Em `_quarto.yml`, adicionar `- sobre.qmd` à lista `project.render`.

---

*Documento gerado a partir do AI_REVIEW_HANDOUT.md, foco em Polish & Growth (seções 12–14) e bônus de quick wins e fatores de crescimento.*
