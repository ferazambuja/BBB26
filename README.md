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
- **GitHub Actions** — atualização automática 4x/dia
- **GitHub Pages** — hospedagem

## Como funciona

```
API GloboPlay → fetch_data.py → data/snapshots/*.json
                                        ↓
                              build_derived_data.py
                                        ↓
                              data/derived/*.json (20+ arquivos)
                                        ↓
                                  quarto render
                                        ↓
                                _site/ → GitHub Pages
```

O GitHub Actions roda automaticamente nos horários **06:00, 15:00, 18:00 e 00:00 BRT**, buscando dados novos, reconstruindo os índices e publicando o site.

## Desenvolvimento local

```bash
# Dependências
pip install -r requirements.txt
# Quarto: https://quarto.org/docs/get-started/

# Buscar dados da API
python scripts/fetch_data.py

# Reconstruir dados derivados (após edições manuais)
python scripts/build_derived_data.py

# Renderizar o site
quarto render

# Preview com hot reload
quarto preview
```

## Aviso

Projeto independente de análise de dados, **sem vínculo com a TV Globo ou o programa BBB**. Os dados são coletados da API pública do GloboPlay e complementados com registros manuais — podem conter erros, atrasos ou imprecisões.

Encontrou um problema? [Abra uma issue](https://github.com/ferazambuja/BBB26/issues).
