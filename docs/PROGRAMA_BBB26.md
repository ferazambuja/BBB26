# Big Brother Brasil 26 — Guia do Programa

Este documento reúne **informações do programa** (formato, dinâmica, seleção e regras gerais) para **uso interno** do projeto.
Ele é separado do `CLAUDE.md`, que foca em **análise de dados** e decisões técnicas.
**Não é conteúdo para o site** — serve apenas para contextualizar agentes e análises internas.

> Aviso: trata-se de um reality em exibição; informações podem mudar com frequência.

## Resumo da edição
- 26ª temporada do Big Brother Brasil, **no ar desde 12 de janeiro de 2026**.
- Apresentação: **Tadeu Schmidt**.
- Direção de gênero: **Rodrigo Dourado**; direção geral: **Angélica Campos** e **Mário Marcondes**.
- Música‑tema: **“Vida Real” (Paulo Ricardo)**.
- Temporada com **100 dias** e **100 episódios**.
- Elenco com três grupos: **Pipoca (anônimos)**, **Camarote (famosos)** e **Veteranos (ex‑BBB)**.

## Exibição
- Exibição diária na **TV Globo** (sinal aberto) e no **Multishow** (TV paga).
- **Globoplay** oferece transmissão contínua via PPV (câmeras 24h).

## Formato e dinâmica do jogo (resumo de alto nível)

### Seleção de participantes
As inscrições foram abertas em **17 de abril de 2025**, com vagas divididas por regiões do Brasil e retorno da inscrição individual.

### Laboratório (Seleção BBB)
O **Laboratório BBB** previa participantes não escolhidos nas Casas de Vidro isolados na casa, com chance de substituição por voto do público.  
A dinâmica ficou em suspenso com o **Quarto Branco** e o aumento de vagas, mas voltou a ser citada em **26/01/2026**, mantendo a ideia de substituição e estreia em fevereiro.

### Seleção BBB / Casas de Vidro
Foram **cinco Casas de Vidro** (uma por região do país).  
Vinte candidatos do Pipoca disputaram vagas e o público escolheu **um homem e uma mulher por região**, totalizando **10 Pipocas**.

### Quarto Branco
Na estreia, os candidatos não escolhidos ficaram no **Quarto Branco**, em prova de resistência.
Quem desistisse deveria apertar o **botão vermelho**; os últimos resistentes garantiriam vagas extras no elenco.
Em **15/01/2026** foi aberta uma **terceira vaga** por saída com recomendação médica; em **17/01/2026**, uma **quarta vaga**.

### Sistema de votação
O paredão é decidido por dois sistemas:
- **Voto da Torcida** (ilimitado).
- **Voto Único** (1 voto por CPF), com voto também via Globoplay.  
O resultado combina **30% Voto da Torcida + 70% Voto Único**.

### Prêmio
O prêmio foi estimado em **R$ 5,44 milhões**, sem o “Modo Stone”.

### Sincerão
Exibido ao vivo nas **segundas‑feiras**, com foco nos **protagonistas** da semana (Líder, Anjo e indicados ao Paredão).  
Os demais assistem pelo telão; há direito de **réplica** se o alvo também for protagonista.  
Nesta edição, há participação de **plateia convidada**.

**Exemplos de formatos (BBB 26):**
- **1º Sincerão (19/01)**: todos montaram **pódio** e indicaram **“quem não ganha”**.  
  Destaques do resumo: Marciele foi a mais citada no pódio; Leandro não foi citado.  
- **2º Sincerão (26/01)**: distribuição de **bombas** com temas escolhidos pelo público;  
  plateia escolheu a **“planta”** da casa.

### Big Fone
Há **três Big Fones** na casa; o público decide qual deles tocará e qual mensagem será lida pelo Big Boss.  
Exemplo registrado: **15/01/2026** — Marcelo atendeu, ficou imune e indicou Aline ao Paredão.

### Prova do Anjo e Monstro
O Anjo pode **autoimunizar‑se** ou imunizar outro participante.  
O Anjo também escolhe quem recebe o **Castigo do Monstro**, que **perde 300 estalecas** e vai para a **Xepa** se estiver no VIP.  
O castigo dura **até o dia da eliminação** (e não apenas até a formação do Paredão).  
A prova do Anjo ocorre **no dia seguinte** à Prova do Líder (sexta ou sábado), com exceções por veto do Líder.

### Cartola BBB
Extensão do **Cartola FC**: usuários escalam participantes e pontuam por eventos do programa.  
Inclui “mini‑games” para palpites e perguntas sobre o reality.

### Ganha‑Ganha
Dinâmica em duas etapas: participantes são sorteados, escolhem **envelopes** (um deles é veto), e o vencedor escolhe entre **dinheiro + informação** ou **o dobro do dinheiro**.  
Registro: **20/01/2026** — Maxiane ganhou **R$ 10 mil** e a informação “não haverá Prova Bate e Volta após a votação”.

### Caixas‑Surpresa
Dinâmica anunciada em **22/01/2026** (sexta), com **caixas** que trazem efeitos imprevisíveis.  
Efeitos registrados na semana 2 incluem:  
- **Indicação em consenso** (Alberto + Brigido → Leandro)  
- **Perda de voto** (Jonas)  
- **Poder de veto** do voto no Paredão (Sarah → Ana Paula)  
- **Voto 2x** aparece **riscado** na tabela da Wikipédia (verificar antes de registrar)

## Cronograma semanal (auto)
Esta tabela é **gerada automaticamente** a partir de `data/manual_events.json`.
Atualize os eventos e rode:

```
python scripts/update_programa_doc.py
```

<!-- AUTO:WEEKLY_TIMELINE_START -->
| Semana | Datas (aprox.) | Dinâmicas/ocorrências | Observações |
|-------:|----------------|-----------------------|-------------|
| 1 | 2026-01-13 – 2026-01-19 | Big Fone: 2026-01-15 — Marcelo — Indicou Aline ao paredão e ficou imune<br>Sincerão: 2026-01-19 — pódio + quem não ganha — todos | Primeira semana. Henri saiu por orientação médica dia 15. |
| 2 | 2026-01-20 – 2026-01-26 | Caixas‑Surpresa: 2026-01-24 — Leandro indicado ao paredão. Jonas perdeu direito de votar. Sarah vetou o voto de Ana Paula. Ana Paula tinha voto duplo, mas foi vetada.<br>Anjo: Jonas (Anjo pela 2ª vez) escolheu vídeo da família ao invés de imunizar alguém<br>Sincerão: 2026-01-26 — bombas com temas do público + plateia define planta — protagonistas da semana + plateia | Pedro desistiu dia 19. Aline eliminada dia 21 (1º paredão). 2º paredão formado dia 25: Leandro (caixas), Matheus (líder), Brigido (casa com 6 votos). Sem Bate e Volta. |
<!-- AUTO:WEEKLY_TIMELINE_END -->

## Checklist semanal (junto com o Paredão)
Ao registrar manualmente o Paredão da semana:
1. **Conferir Wikipédia** (seções “O jogo”, Big Fones, Ganha‑Ganha, Caixas‑Surpresa, Prova do Anjo).  
2. **Atualizar este guia** (`docs/PROGRAMA_BBB26.md`) com novos eventos e datas.  
3. **Atualizar `data/manual_events.json`** (power_events, dedo‑duro, veto, perda de voto, etc.).  
4. **Registrar fontes** (`fontes`) sempre que houver evento novo.  
5. **Rodar `python scripts/build_derived_data.py`** após mudanças.
6. **Rodar `python scripts/update_programa_doc.py`** para atualizar o cronograma automático.

## Observações importantes para o projeto
- Este documento **não** deve ser usado como base de inferência de dados.
- Para análise, **use sempre** as fontes de dados do projeto:
  - `data/snapshots/*` (queridômetro / reações)
  - `data/manual_events.json` (eventos manuais)
  - `data/paredoes.json` (formação + resultados)
  - `data/derived/*` (dados consolidados)

## Fontes
- Wikipédia: página oficial do **Big Brother Brasil 26** (consultada em 27/01/2026).
- GShow (Sincerão): 1º Sincerão (pódio + quem não ganha) e 2º Sincerão (bombas/temas).
