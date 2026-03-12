# BBB 26 — Painel de Reações

Dashboard interativo de análise do Big Brother Brasil 2026 — reações, relações, votos e dinâmicas de poder.

**Site**: [ferazambuja.github.io/BBB26](https://ferazambuja.github.io/BBB26/)

## O que é

Painel que acompanha diariamente o **queridômetro** (reações entre participantes) via API pública do GloboPlay, complementado com dados manuais de paredões, provas, dinâmicas e eventos de poder.

### Páginas

| Página | Conteúdo |
|--------|----------|
| **Painel** | Visão geral, rankings, heatmap de reações, perfis |
| **Evolução** | Rankings ao longo do tempo, sentimento, impacto, saldo de estalecas |
| **Relações** | Alianças, rivalidades, quebras de streak, hostilidade, rede social |
| **Paredão** | Paredão atual — formação, votos, análise de reações vs votos |
| **Paredões** | Arquivo histórico de todos os paredões |
| **Cartola** | Pontuação no estilo fantasy (Líder, Anjo, Monstro, etc.) |
| **Provas** | Ranking de desempenho em provas (Líder, Anjo, Bate-Volta) |

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

O GitHub Actions roda com slots permanentes em **00:00, 06:00, 15:00 e 18:00 BRT**, extras aos sábados (**17:00** e **20:00 BRT**) e probes temporários entre **09:30–16:00 BRT** para validar a janela real de atualização do queridômetro (revisão de fechamento prevista para **2026-03-08**).

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
- `docs/GIT_PUBLIC_PRIVATE_WORKFLOW.md` — fluxo de branch local privada + branch pública
- `docs/ARCHITECTURE.md` — referência técnica pública (substitui dependência pública de docs privados)

Hook opcional de segurança:

```bash
mkdir -p .git/hooks
cp .githooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

## Aviso

Projeto independente de análise de dados, **sem vínculo com a TV Globo ou o programa BBB**. Os dados são coletados da API pública do GloboPlay e complementados com registros manuais — podem conter erros, atrasos ou imprecisões.

Encontrou um problema? [Abra uma issue](https://github.com/ferazambuja/BBB26/issues).
