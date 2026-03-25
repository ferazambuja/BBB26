# BBB 26 — Painel de Reações

Dashboard interativo de análise do Big Brother Brasil 2026 — reações, relações, votos e dinâmicas de poder.

**Site**: [ferazambuja.github.io/BBB26](https://ferazambuja.github.io/BBB26/)

## Comece por aqui

Para alguém novo no repositório, a ordem mais eficiente é:

1. `README.md` — visão geral, fluxo e mapa rápido do projeto
2. `docs/ARCHITECTURE.md` — responsabilidades por camada, páginas e artefatos derivados
3. `docs/OPERATIONS_GUIDE.md` — runbooks operacionais e receitas por tipo de mudança
4. `docs/MANUAL_EVENTS_GUIDE.md` — contrato real de `data/manual_events.json`
5. `docs/SCORING_AND_INDEXES.md` — fórmulas, pesos e superfícies analíticas
6. `docs/TESTING.md` — o que verificar para cada tipo de alteração

Atalho por objetivo:

- **Mexer em dados manuais**: leia `docs/OPERATIONS_GUIDE.md` + `docs/MANUAL_EVENTS_GUIDE.md`
- **Mexer em cálculo/pipeline**: leia `docs/ARCHITECTURE.md` + `docs/SCORING_AND_INDEXES.md` + `docs/TESTING.md`
- **Mexer em layout/página**: leia `docs/ARCHITECTURE.md` + `docs/TESTING.md`

## O que é

Painel que acompanha diariamente o **queridômetro** (reações entre participantes) via API pública do GloboPlay, complementado com dados manuais de paredões, provas, dinâmicas e eventos de poder.

### Páginas

| Página | Conteúdo |
|--------|----------|
| **Painel** | Visão geral, rankings, heatmap de reações, perfis |
| **Evolução** | Rankings ao longo do tempo, sentimento, impacto, saldo de estalecas |
| **Estalecas VIP/Xepa** | Economia da casa: compras, punições, mesada, VIP/Xepa |
| **Relações** | Alianças, rivalidades, quebras de streak, hostilidade, rede social |
| **Paredão** | Paredão atual — formação, votos, análise de reações vs votos |
| **Cartola** | Pontuação no estilo fantasy (Líder, Anjo, Monstro, etc.) |
| **Provas** | Ranking de desempenho em provas (Líder, Anjo, Bate-Volta) |
| **Paredões** | Arquivo histórico de todos os paredões |
| **Votação** | Análise do sistema 70/30 entre Voto Único e Torcida |

### Páginas utilitárias renderizadas

Além das páginas de navegação principal, `_quarto.yml` também renderiza:

| Arquivo | Uso |
|--------|-----|
| `cronologia_mobile_review.qmd` | Página de revisão focada na cronologia em mobile |
| `_dev/drafts/economia_v2.qmd` | Variante narrativa/mobile da economia (draft) |

## Stack

- **Python 3.10+** — coleta e processamento de dados
- **Quarto** — renderização do site estático
- **Plotly** — visualizações interativas (tema dark customizado)
- **GitHub Actions** — atualização automática multi-captura (slots fixos + probes)
- **GitHub Pages** — hospedagem

## Como funciona

```
API GloboPlay → scripts/fetch_data.py → data/snapshots/*.json
                                                ↓
                                  scripts/build_derived_data.py
                                                ↓
                                   scripts/derived_pipeline.py
                                                ↓
                                  data/derived/*.json (20+ arquivos)
                                                ↓
                         scripts/*_viz.py helpers + thin *.qmd pages
                                                ↓
                                         quarto render
                                                ↓
                                        _site/ → GitHub Pages
```

O GitHub Actions faz polling a cada **15 minutos**. Quando a API muda, o repositório salva um novo snapshot e dispara o pipeline completo de testes, rebuild e render. A janela principal do queridômetro segue em torno de **15:00 BRT**, mas o polling frequente também captura mudanças de saldo, VIP/Xepa e papéis ao longo do dia.

### Camadas de responsabilidade

- `scripts/builders/*` e `scripts/derived_pipeline.py`:
  computação de domínio, validações e geração de artefatos derivados.
- `scripts/*_viz.py`:
  helpers de renderização reutilizáveis, gráficos Plotly e fragmentos HTML.
- `*.qmd`:
  ordem da página, títulos, narrativa, e orquestração final do que renderiza.

### Regra prática para código em QMD

- Categoria A: helper testável de renderização/formatacão.
  Mover para `scripts/*_viz.py`.
- Categoria B: computação cara ou reutilizável.
  Mover para builders + `data/derived/*`.
- Categoria C: orquestração ordenada da página.
  Manter no `.qmd`.

### Onde editar cada tipo de mudança

| Se você quer mudar... | Dono principal |
|-----------------------|----------------|
| Constantes compartilhadas, pesos, helpers de data, loaders, tema Plotly | `scripts/data_utils.py` |
| Cálculo derivado e regras analíticas | `scripts/builders/*` + `scripts/derived_pipeline.py` |
| Cards/HTML/figuras reutilizáveis | `scripts/*_viz.py` |
| Ordem da página, narrativa e composição final | `*.qmd` |
| Dados-fonte manuais | `data/manual_events.json`, `data/paredoes.json`, `data/provas.json`, `data/votalhada/polls.json` |
| Navegação, assets globais e render list | `_quarto.yml` + `assets/*` |

## Desenvolvimento local

```bash
# Dependências
pip install -r requirements.txt
# Quarto: https://quarto.org/docs/get-started/

# Buscar dados da API
python scripts/fetch_data.py

# Reconstruir dados derivados (após edições manuais)
python scripts/build_derived_data.py

# Nota: build_derived_data.py delega para scripts/derived_pipeline.py

# Renderizar o site
quarto render

# Preview com hot reload
quarto preview
```

## Verificação

Guia completo: `docs/TESTING.md`

Loop mínimo recomendado:

```bash
# Rebuild dos artefatos derivados após qualquer edição manual ou mudança de regra
python scripts/build_derived_data.py

# Teste rápido direcionado ou suíte inteira, dependendo do escopo
python -m pytest tests/ -q

# Render local do site quando a mudança afeta páginas/HTML/CSS
quarto render
```

Na CI (`.github/workflows/daily-update.yml`), o caminho completo é:

1. `python -m pytest tests/ -v --tb=short --cov=scripts --cov-report=term-missing`
2. `python scripts/build_derived_data.py`
3. `quarto render`

## Captura de screenshots (desktop + mobile)

Para revisão completa de layout e plots em todas as páginas Quarto:

```bash
./scripts/capture_layout_screenshots.sh
```

O comando acima:
- executa captura **página por página** com logs verbosos (evita parecer travado)
- por padrão faz retake rápido (sem `quarto render` e sem reinstall do browser)
- captura screenshots full-page em `desktop` e `mobile`
- salva em `tmp/page_screenshots/<timestamp>/`
- gera `manifest.json` com sucesso/falhas

Para forçar render completo antes da captura:

```bash
./scripts/capture_layout_screenshots.sh --render
```

Para instalar/atualizar o browser Playwright uma vez:

```bash
./scripts/capture_layout_screenshots.sh --install-browser
```

Uso direto (mais opções):

```bash
python scripts/capture_quarto_screenshots.py --render --profiles desktop,mobile
python scripts/capture_quarto_screenshots.py --page paredao.html --profiles mobile --verbose
```

Alternativa para páginas muito longas no mobile (captura em fatias: topo/meio/fim):

```bash
./scripts/capture_mobile_slices.sh
# ou
python scripts/capture_mobile_slices.py --output-dir tmp/page_screenshots/mobile-slices
```

## Governança de documentação (público vs privado)

Este repositório é público. A documentação é separada em:

- **Pública** (pode ir para GitHub): pilares técnicos e operacionais
- **Privada/local** (não publicar): notas de desenvolvimento, reviews, planos e guias internos de agente

Referências:

- `docs/PUBLIC_PRIVATE_DOCS_POLICY.md` — política oficial de classificação e checklist de push
- `docs/GIT_PUBLIC_PRIVATE_WORKFLOW.md` — fluxo main-first + material privado local via gitignore/denylist
- `docs/ARCHITECTURE.md` — referência técnica pública (substitui dependência pública de docs privados)
- `docs/TESTING.md` — mapa de verificação por tipo de mudança

Hook local recomendado de segurança:

```bash
mkdir -p .git/hooks
cp .githooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

## Aviso

Projeto independente de análise de dados, **sem vínculo com a TV Globo ou o programa BBB**. Os dados são coletados da API pública do GloboPlay e complementados com registros manuais — podem conter erros, atrasos ou imprecisões.

Encontrou um problema? [Abra uma issue](https://github.com/ferazambuja/BBB26/issues).
