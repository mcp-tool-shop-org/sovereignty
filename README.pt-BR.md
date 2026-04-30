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
  Sit down with 2-4 friends, roll a die, move around a board, and try to
  end up with more coins or more goodwill than anyone else. Make promises
  out loud — keep them and people trust you, break them and they don't.
  No prior games like this needed. No screens at the table.
</p>

<!--
Badge style policy (Stage D / W7CIDOCS-001): all badges use shields.io
default `flat` style for visual consistency. Each shields.io URL pins
`cacheSeconds=3600` so cold-cache renders fall back to the last known
value rather than going blank when the upstream registry is slow. The
CI badge is GitHub's first-party SVG and is exempt — GitHub serves it
from camo with its own cache.
-->
<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/sovereignty-game/"><img src="https://img.shields.io/pypi/v/sovereignty-game?include_prereleases&style=flat&cacheSeconds=3600" alt="PyPI version"></a>
  <a href="https://pypi.org/project/sovereignty-game/"><img src="https://img.shields.io/pypi/pyversions/sovereignty-game?style=flat&cacheSeconds=3600" alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat&cacheSeconds=86400" alt="License: MIT"></a>
  <a href="https://mcp-tool-shop-org.github.io/sovereignty/"><img src="https://img.shields.io/badge/Landing_Page-live-blue?style=flat&cacheSeconds=86400" alt="Landing Page"></a>
</p>

## Instale em 30 segundos

A maneira mais rápida — para usuários de Python:

```bash
pipx install sovereignty-game
sov tutorial
```

Não usa Python? Sem problemas. O comando `npx` baixa um binário pré-compilado:

```bash
npx @mcptoolshop/sovereignty tutorial
```

Pronto. O comando `sov tutorial` te guiará pelas regras em cerca de 60 segundos.

## Sua primeira partida

Depois que você e 2-3 amigos estiverem à mesa, o console conduz a rodada e você faz a parte de conversar. Uma partida real acontece assim:

```bash
# Start a game with three players
sov new -p Alice -p Bob -p Carol

# Each player takes a turn — roll, land, resolve
sov turn

# Check where everyone stands
sov status

# When everyone has gone, close the round
sov end-round
```

O comando `sov status` mostra uma tabela formatada com as moedas, reputação, melhorias, posição e objetivo de cada jogador. Para uma visão rápida de uma linha entre as rodadas:

```bash
sov status --brief
```

```
R3 |  Alice: 7c 4r 0u | >Bob: 4c 3r 0u |  Carol: 6c 5r 0u
```

(`Nc Nr Nu` = moedas / reputação / melhorias; `>` indica o jogador ativo.)

Repita por 15 rodadas. O comando `sov game-end` exibe as pontuações finais.

> Quer um tutorial interativo primeiro? Execute o comando `sov tutorial`.
> Quer jogar sem nenhum software? Veja [Jogar em papel](docs/print-and-play.md).
> Quer uma visão mais detalhada das regras? Veja [Comece aqui](docs/start_here.md) ou
> o [manual completo](https://mcp-tool-shop-org.github.io/sovereignty/handbook/).

> _Um pequeno GIF ou captura de tela demonstrativa deve ser colocado aqui — será rastreado como uma tarefa de acompanhamento da Fase D para que o README possa mostrar como uma rodada realmente acontece._

## Jogue sem o console

Imprima as cartas, pegue um dado e algumas moedas, sente-se com 2-4 pessoas.
O jogo funciona completamente na mesa.

**[Comece aqui](docs/start_here.md)** | **[Jogar em papel](docs/print-and-play.md)** | **[Regras completas](docs/rules/campfire_v1.md)** | **[Jogue com estranhos](docs/play-with-strangers.md)**

<details>
<summary>Full command reference</summary>

```bash
sov new --recipe cozy -p ...         # curated vibe (cozy/spicy/market/promise)
sov new --tier treaty-table -p ...   # pick a tier
sov new --code "SOV|..." -p ...      # play from a share code
sov tutorial                         # learn in 60 seconds
sov turn                             # roll, land, resolve
sov status                           # show current game state
sov board                            # show the board layout
sov recap                            # what happened this round
sov promise make "I'll help Bob"     # say it out loud
sov promise keep "I'll help Bob"     # kept it: +1 Rep
sov promise break "text"             # broke it: -2 Rep
sov apologize Bob                    # once per game, pay 1 coin, +1 Rep
sov offer "2 coins for 1 wood" --to Bob  # make a trade offer
sov treaty make "pact" --with Bob --stake "2 coins"  # binding treaty
sov treaty list                      # show your treaties
sov market                           # show market prices + supply
sov market buy food                  # buy a resource (Town Hall+)
sov market sell wood                 # sell a resource (Town Hall+)
sov vote mvp Alice                   # table votes: mvp/chaos/promise
sov toast Alice                      # +1 Rep, once per player per game
sov end-round                        # generate round proof
sov game-end                         # final scores + Story Points
sov postcard                         # shareable summary
sov season-postcard                  # season standings across games
sov feedback                         # issue-ready play report
sov scenario list                    # browse scenario packs
sov scenario code cozy-night -s 42   # generate a share code
sov scenario lint                    # validate scenario files
sov doctor                           # pre-flight check before play night
sov self-check                       # diagnose your environment
sov support-bundle                   # diagnostic zip for bug reports
```

</details>

O console registra a pontuação. Você cumpre sua palavra.

## Como funciona

Você começa com **5 moedas** e **3 de reputação**. Lance um dado, mova-se
em um tabuleiro de 16 espaços e pare em espaços que oferecem opções: trocar, ajudar
alguém, correr um risco ou comprar uma carta.

**28 cartas de evento** parecem momentos: *"Alguém viu uma pequena bolsa de couro?"* (Carteira perdida) ou *"Ninguém viu... certo?"* (Encontrou um atalho).
Inclui 8 eventos de mudança de mercado para jogos na prefeitura.

**22 cartas de acordo e vale:** forçam a conversa: *"Me empresta 2 moedas? Eu te devolvo 3 depois."* ou *"Eu te protejo se você me proteger."* Os acordos estabelecem metas com prazos; os vales são promessas que você faz a outros jogadores.

**A regra da promessa:** Uma vez por rodada, diga "Eu prometo..." em voz alta e
comprometa-se com algo. Cumpra: +1 de reputação. Quebre: -2 de reputação.
A mesa decide.

**O pedido de desculpas:** Uma vez por jogo, se você quebrou uma promessa, peça desculpas publicamente.
Pague 1 moeda para quem você prejudicou e recupere +1 de reputação.

**Escolha seu objetivo** (secreto ou público):
- **Prosperidade** — alcance 20 moedas
- **Amado** — alcance 10 de reputação
- **Construtor** — complete 4 melhorias

Após 15 rodadas, quem tiver a maior pontuação total vence.

## O que é o Modo Diário?

A cada rodada, o console pode gerar uma **prova** — uma impressão digital do
estado do jogo. Se alguém alterar a pontuação, a impressão digital não corresponderá.

Opcionalmente, essa impressão digital pode ser postada na **XRPL Testnet** — um
registro público. Pense nisso como escrever a pontuação em uma parede que ninguém
pode apagar.

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

Apenas o anfitrião precisa de uma carteira. Ninguém mais toca na tela. O jogo
funciona perfeitamente sem necessidade de registro — é apenas o diário que registra.

## Três níveis

| Nível | Nome | Status | O que ele adiciona |
|------|------|--------|-------------|
| 1 | **Campfire** | Jogável | Moedas, reputação, promessas, dívidas. |
| 2 | **Town Hall** | Jogável | Mercado compartilhado, escassez de recursos. |
| 3 | **Treaty Table** | Jogável | Tratados com consequências — promessas com peso. |

As regras principais são estáveis na versão 1.x. Consulte o [roteiro](docs/roadmap.md).

## Pacotes de cenários

Nenhuma nova regra. Apenas a atmosfera. Cada pacote define um nível, uma receita e um clima.

| Cenário | Nível | Ideal para |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | Fogueira / Dia de Mercado | Primeira partida, grupos mistos. |
| [Market Panic](docs/scenarios/market-panic.md) | Prefeitura | Dramas econômicos. |
| [Promises Matter](docs/scenarios/promises-matter.md) | Fogueira | Confiança e compromisso. |
| [Treaty Night](docs/scenarios/treaty-night.md) | Mesa de Tratados | Acordos de alto risco. |

Use `sov scenario list` para navegar pelo console.

## Estrutura do projeto

```
sovereignty/
  sov_engine/       # Pure game logic (models, rules, serialization, hashing)
  sov_transport/    # Ledger transport (offline + XRPL Testnet)
  sov_cli/          # Typer CLI (the "Round Console")
  tests/            # Engine, transport, and CLI tests
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

Os jogadores aprendem fazendo: emitindo dívidas, quebrando promessas, negociando a preços variáveis. Os conceitos correspondem aos elementos básicos do Web3 — carteiras, tokens, linhas de crédito — mas os jogadores não precisam saber disso para se divertir.

## Contribuições

A maneira mais fácil de contribuir é [adicionar um cartão](CONTRIBUTING.md).
Não é necessário conhecimento do motor — basta um nome, uma descrição e um texto descritivo.

## Segurança

Chaves de carteira, estado do jogo e arquivos de prova — o que compartilhar e o que não compartilhar.
Sem telemetria, sem análise, sem envio de dados. A única chamada de rede opcional é a ancoragem no Testnet XRPL.

Consulte [SECURITY.md](SECURITY.md).

## Modelo de Ameaças

| Ameaça | Mitigação |
|--------|-----------|
| Vazamento de chaves através de provas | As provas contêm apenas hashes, nunca chaves. |
| Chave no Git | `.sov/` ignorado pelo Git; `sov wallet` avisa. |
| Manipulação do estado do jogo | As provas de rodada (`envelope_hash`) cobrem `game_id`, `round`, `ruleset`, `rng_seed`, `timestamp_utc`, `players` e `state`. `sov verify` detecta adulterações em todo o envelope. O formato de prova v1 não é mais suportado na versão 2.0.0+. |
| Falsificação da âncora XRPL | O hash da prova é ancorado na blockchain; detecção de incompatibilidades na verificação. |
| Privacidade do nome do jogador | Os nomes dos jogadores ESTÃO incluídos nas provas (lista de nível superior `players` e dentro dos snapshots dos jogadores). Para jogos privados, não publique `proof.json` nem compartilhe cartões postais. |

## Licença

MIT

---

Criado por [MCP Tool Shop](https://mcp-tool-shop.github.io/)
