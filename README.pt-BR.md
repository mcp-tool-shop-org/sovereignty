<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.md">English</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/sovereignty/readme.png" width="400" alt="Sovereignty">
</p>

<p align="center">
  A board game about trust, trade, and keeping your word.
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://mcp-tool-shop-org.github.io/sovereignty/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

## Jogue hoje à noite

Imprima as cartas, pegue um dado e algumas moedas, sente-se com 2 a 4 pessoas.
Não são necessárias telas. Leva cerca de 30 minutos.

**[Comece aqui](docs/start_here.md)** | **[Imprimir e jogar](docs/print-and-play.md)** | **[Regras completas](docs/rules/campfire_v1.md)** | **[Jogue com estranhos](docs/play-with-strangers.md)**

## Ou use o console

```bash
pipx install sovereignty-game       # one-time install (or: uv tool install sovereignty-game)
sov tutorial                         # learn in 60 seconds
sov new -p Alice -p Bob -p Carol     # start a game
```

<details>
<summary>Full command reference</summary>

```bash
sov new --recipe cozy -p ...         # curated vibe (cozy/spicy/market/promise)
sov new --tier treaty-table -p ...   # pick a tier
sov turn                             # roll, land, resolve
sov promise make "I'll help Bob"     # say it out loud
sov treaty make "pact" --with Bob --stake "2 coins"  # stakes
sov scenario list                    # browse scenario packs
sov scenario code cozy-night -s 42   # generate a share code
sov scenario lint                    # validate scenario files
sov new --code "SOV|..." -p ...      # play from a share code
sov doctor                           # pre-flight check before play night
sov recap                            # what happened this round
sov game-end                         # final scores + Story Points
sov postcard                         # shareable summary
sov feedback                         # issue-ready play report
sov season-postcard                  # season standings across games
```

</details>

O console registra a pontuação. Você cumpre sua palavra.

## Como funciona

Você começa com **5 moedas** e **3 pontos de reputação**. Lance o dado, mova-se
por um tabuleiro de 16 espaços e pare em espaços que oferecem opções: trocar, ajudar
alguém, correr um risco ou comprar uma carta.

**20 cartas de evento** parecem momentos: *"Alguém viu uma pequena bolsa de couro?"* (Carteira perdida) ou *"Ninguém viu... certo?"* (Encontrou um atalho).

**20 cartas de acordo** incentivam a conversa: *"Me empresta 2 moedas? Eu te devolvo 3 depois."*
ou *"Eu te protejo se você me proteger."*

**A regra da promessa:** Uma vez por rodada, diga "Eu prometo..." em voz alta e
comprometa-se com algo. Cumpra: +1 ponto de reputação. Quebre: -2 pontos de reputação.
A mesa decide.

**O pedido de desculpas:** Uma vez por partida, se você quebrou uma promessa, peça desculpas publicamente.
Pague 1 moeda para quem você prejudicou e recupere +1 ponto de reputação.

**Escolha seu objetivo** (secreto ou público):
- **Prosperidade** — alcance 20 moedas
- **Amado** — alcance 10 pontos de reputação
- **Construtor** — complete 4 melhorias

Após 15 rodadas, o jogador com a maior pontuação total vence.

## O que é o Modo Diário?

A cada rodada, o console pode gerar uma **prova** — uma impressão digital do
estado do jogo. Se alguém alterar a pontuação, a impressão digital não corresponderá.

Opcionalmente, essa impressão digital pode ser enviada para a **XRPL Testnet** — um
registro público. Pense nisso como escrever a pontuação em uma parede que ninguém
pode apagar.

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

Apenas o anfitrião precisa de uma carteira. Ninguém mais usa uma tela. O jogo
funciona perfeitamente sem a necessidade de "ancoragem" — é apenas o diário que registra.

## Três níveis

| Nível | Nome | Status | O que ele adiciona |
|------|------|--------|-------------|
| 1 | **Campfire** | Jogável | Moedas, reputação, promessas, dívidas |
| 2 | **Town Hall** | Jogável | Mercado compartilhado, escassez de recursos |
| 3 | **Treaty Table** | Jogável | Tratados com consequências — promessas com peso |

As regras básicas são estáveis na versão 1.x. Veja o [roteiro](docs/roadmap.md).

## Pacotes de cenários

Nenhuma nova regra. Apenas a atmosfera. Cada pacote define um nível, uma receita e um clima.

| Cenário | Nível | Ideal para |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | Fogueira / Dia de Mercado | Primeira partida, grupos mistos |
| [Market Panic](docs/scenarios/market-panic.md) | Assembleia | Drama econômico |
| [Promises Matter](docs/scenarios/promises-matter.md) | Fogueira | Confiança e compromisso |
| [Treaty Night](docs/scenarios/treaty-night.md) | Mesa de Tratados | Acordos de alto risco |

Use o comando `sov scenario list` para navegar pelo console.

## Estrutura do projeto

```
sovereignty/
  sov_engine/       # Pure game logic (models, rules, serialization, hashing)
  sov_transport/    # Ledger transport (offline + XRPL Testnet)
  sov_cli/          # Typer CLI (the "Round Console")
  tests/            # 143 tests
  docs/             # Rules, cards, print-and-play, play-with-strangers
  assets/print/     # Printable cards, player mat, quick reference
```

## Desenvolvimento

```bash
git clone https://github.com/mcp-tool-shop-org/sovereignty.git
cd sovereignty
uv sync --dev
uv run pytest tests/ -v
uv run ruff check .
```

## Princípio de design

> "Ensine através das consequências, não da terminologia."

Os jogadores aprendem fazendo: emitindo dívidas, quebrando promessas, negociando a
preços variáveis. Os conceitos se relacionam com os elementos básicos do Web3 — carteiras, tokens,
linhas de crédito — mas os jogadores não precisam saber disso para se divertir.

## Contribuição

A maneira mais fácil de contribuir é [adicionar uma carta](CONTRIBUTING.md).
Não é necessário conhecimento do motor — basta um nome, uma descrição e um texto descritivo.

## Segurança

Chaves de carteira, estado do jogo e arquivos de prova — o que compartilhar e o que não.
Sem telemetria, sem análise, sem envio de dados. A única chamada de rede opcional é a ancoragem na XRPL Testnet.

Consulte [SECURITY.md](SECURITY.md).

## Modelo de ameaças

| Ameaças | Mitigação |
|--------|-----------|
| Vazamento de "seeds" através de provas | As provas contêm apenas "hashes", nunca "seeds". |
| "Seed" no Git | `.sov/` ignorado pelo Git; o comando `sov wallet` emite um aviso. |
| Manipulação do estado do jogo | As provas "hash" o estado completo; o comando `sov verify` detecta adulterações. |
| Falsificação de "âncoras" do XRPL | O "hash" da prova é ancorado na blockchain; a detecção de inconsistências ocorre durante a verificação. |
| Privacidade dos nomes dos jogadores | O estado do jogo é local; as provas não incluem nomes. |

## Licença

MIT

---

Desenvolvido por [MCP Tool Shop](https://mcp-tool-shop.github.io/)
