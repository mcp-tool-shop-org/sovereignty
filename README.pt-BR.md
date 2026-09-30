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
  <a href="https://codecov.io/gh/mcp-tool-shop-org/sovereignty"><img src="https://codecov.io/gh/mcp-tool-shop-org/sovereignty/graph/badge.svg" alt="Coverage"></a>
  <a href="https://pypi.org/project/sovereignty-game/"><img src="https://img.shields.io/pypi/v/sovereignty-game?include_prereleases&style=flat&cacheSeconds=3600" alt="PyPI version"></a>
  <a href="https://pypi.org/project/sovereignty-game/"><img src="https://img.shields.io/pypi/pyversions/sovereignty-game?style=flat&cacheSeconds=3600" alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat&cacheSeconds=86400" alt="License: MIT"></a>
  <a href="https://mcp-tool-shop-org.github.io/sovereignty/"><img src="https://img.shields.io/badge/Landing_Page-live-blue?style=flat&cacheSeconds=86400" alt="Landing Page"></a>
</p>

## Jogue hoje à noite

Imprima o pacote completo para impressão e jogo (disponível em assets/print/pdf/Sovereignty-Print-Pack.pdf) — tabuleiro, tapetes para os jogadores, guia de referência rápida, tabuleiro de mercado e três baralhos de cartas em 13 folhas de papel no formato US Letter. Encontre um dado e algumas moedas. Sente-se com dois ou três amigos. Vocês estarão jogando em vinte minutos.

Se você quiser folhas individuais:

- **[Tabuleiro](assets/print/pdf/board.pdf)** — o tabuleiro com 16 espaços, representando a fogueira, em uma página.
- **[Tapete para o jogador](assets/print/pdf/mat.pdf)** — moedas, reputação, melhorias, promessas. Um por jogador.
- **[Guia de referência rápida](assets/print/pdf/quickref.pdf)** — espaços do tabuleiro, ordem das jogadas, regras das promessas.
- **[Cartas de evento](assets/print/pdf/events.pdf)** — 28 cartas, quatro páginas, corte ao longo das linhas.
- **[Cartas de negociação](assets/print/pdf/deals.pdf)** — 12 cartas, duas páginas.
- **[Cartas de vale](assets/print/pdf/vouchers.pdf)** — 10 vales entre os jogadores, duas páginas.
- **[Tabuleiro de mercado](assets/print/pdf/market.pdf)** — Dia de mercado / Câmara Municipal, uma página.
- **[Guia de referência rápida do tratado](assets/print/pdf/treaty.pdf)** — Apenas nível 3.

Os arquivos PDF são vetoriais com fontes incorporadas — eles imprimem de forma nítida em qualquer impressora doméstica. O guia passo a passo para a configuração está disponível em [Print & Play](docs/print-and-play.md).

## Quer um console para controlar a pontuação?

Opcional. O jogo funciona bem no papel. Mas, se alguém tiver um laptop à mão, `sov` rastreia as moedas, a reputação, as promessas e gera um recibo à prova de adulteração no final:

```bash
pip install sovereignty-game
sov play campfire_v1
```

`sov play campfire_v1` é o guia de início rápido sem configuração — um jogador mais um oponente padrão. Para jogos com vários jogadores na mesa, use `sov new -p Alice -p Bob -p Carol`. Para um guia passo a passo de 60 segundos, use `sov tutorial`.

Sem Python? O caminho `npx` baixa um binário pré-compilado:

```bash
npx @mcptoolshop/sovereignty tutorial
```

Ou execute-o no Docker, com seus jogos salvos armazenados em um volume nomeado:

```bash
docker run --rm -it -v sov-data:/data ghcr.io/mcp-tool-shop-org/sovereignty tutorial
```

## Uma sessão real

Depois que você e 2-3 amigos estiverem à mesa, o console executa a rodada e vocês fazem a conversa. Uma sessão real se parece com isto:

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

`sov status` exibe uma tabela formatada em Rich com as moedas, a reputação, as melhorias, a posição e o objetivo de cada jogador. Para uma visualização rápida em uma única linha entre as rodadas:

```bash
sov status --brief
```

```
R3 |  Alice: 7c 4r 0u | >Bob: 4c 3r 0u |  Carol: 6c 5r 0u
```

(`Nc Nr Nu` = moedas / reputação / melhorias; `>` marca o jogador ativo.)

Repita por 15 rodadas. `sov game-end` imprime as pontuações finais.

- **Múltiplos jogos salvos** (v2.1+): `sov games` lista os jogos salvos; `sov resume <game-id>` alterna entre eles.
- **Ancoragem em lote** (v2.1+): `sov anchor` no final do jogo armazena as rodadas pendentes em uma pequena constante de transações XRPL AccountSet (≤8 memorandos cada; um jogo típico de 16 rodadas → 2 transações) — não uma única transação / único ponteiro de cadeia. Use `sov anchor --checkpoint` para ancoragem no meio do jogo.
- **Seleção de rede** (v2.1+): `sov anchor --network testnet|mainnet|devnet` (ou variável de ambiente `SOV_XRPL_NETWORK`; padrão `testnet`).
- **Modo daemon** (v2.1+, opcional): `sov daemon start` executa um servidor HTTP/JSON em localhost para integração com o desktop e polling de cadeia em segundo plano. Consulte [Modo daemon](#daemon-mode-optional-v21) abaixo.
- **Aplicativo de desktop Audit Viewer** (v2.1+, opcional): `npm --prefix app run tauri dev`. Consulte [Aplicativo de desktop](#desktop-app-optional-v21) abaixo.

> Quer um guia passo a passo no aplicativo primeiro? Execute `sov tutorial`.
> Quer um guia mais detalhado das regras? Consulte [Comece aqui](docs/start_here.md) ou
> o [manual completo](https://mcp-tool-shop-org.github.io/sovereignty/handbook/).

O exemplo `sov turn` acima mostra como uma rodada se parece no console; para a visualização do desktop v2.1, consulte [Aplicativo de desktop](#desktop-app-optional-v21) abaixo.

**[Comece aqui](docs/start_here.md)** | **[Print & Play](docs/print-and-play.md)** | **[Regras completas](docs/rules/campfire_v1.md)** | **[Jogue com estranhos](docs/play-with-strangers.md)**

<details>
<summary>Full command reference</summary>

```bash
sov play campfire_v1                 # no-config quickstart (v2.1+) — alias for sov new
sov new --recipe cozy -p ...         # curated vibe (cozy/spicy/market/promise)
sov new --tier treaty-table -p ...   # pick a tier
sov new --code "SOV|..." -p ...      # play from a share code
sov games                            # list saved games (multi-save, v2.1+)
sov games --json                     # machine-readable saves list (v2.1+)
sov resume <game-id>                 # switch to a saved game (v2.1+)
sov tutorial                         # learn in 60 seconds
sov turn                             # roll, land, resolve
sov undo                             # last-turn only (cleared by end-round)
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
sov anchor                           # batch pending rounds to XRPL (v2.1+)
sov anchor --checkpoint              # mid-game flush (v2.1+)
sov anchor --network mainnet         # network selection (v2.1+)
sov verify <proof.json> --tx <txid>  # confirm a proof is anchored on chain
sov daemon start [--readonly]        # localhost HTTP/JSON daemon (v2.1+)
sov daemon status                    # running | stale | none
sov daemon stop                      # SIGTERM + cleanup
sov postcard                         # shareable summary
sov season-postcard                  # season standings / printable recap
sov feedback                         # issue-ready play report
sov scenario list                    # browse scenario packs
sov scenario code cozy-night -s 42   # generate a share code
sov scenario lint                    # validate scenario files
sov doctor                           # pre-flight check before play night
sov self-check                       # diagnose your environment
sov support-bundle                   # diagnostic zip for bug reports
```

</details>

O console controla a pontuação. Você cumpre sua palavra.

## Modo daemon (opcional, v2.1+)

Para integração com o desktop (Audit Viewer, Tauri shell) ou polling de cadeia em segundo plano, execute o Sovereignty como um daemon HTTP em localhost:

```bash
pip install 'sovereignty-game[daemon]'
sov daemon start --readonly        # audit-only, no wallet seed
sov daemon start                   # full daemon with anchor endpoints (loads XRPL_SEED)
sov daemon status                  # running | stale | none
sov daemon stop
```

O daemon é vinculado a `127.0.0.1` em uma porta aleatória; os detalhes da conexão (porta + token de portador) estão em `.sov/daemon.json`. Um daemon por raiz do projeto. Consulte [docs/v2.1-daemon-ipc.md](docs/v2.1-daemon-ipc.md) para o contrato IPC completo.

> O extra `[daemon]` precisa de **2.3.2 ou posterior**. As versões até 2.3.1 deixaram o pacote `sov_daemon` de fora, então `sov daemon start` falhou na instalação do PyPI.

## Docker (opcional, v2.3.2+)

A imagem em `ghcr.io/mcp-tool-shop-org/sovereignty` contém a CLI `sov` e o daemon, para `linux/amd64` e `linux/arm64`. Tudo o que o jogo lembra está em `/data/.sov`: jogos, provas de rodada, `anchors.json`, o registro da temporada, a semente da carteira e o handshake do daemon. Monte um volume em `/data` ou o contêiner esquece tudo.

Execute o daemon com o [`compose.yaml`](compose.yaml) incluído:

```bash
docker compose up -d                  # readonly audit daemon on 127.0.0.1:47823
docker compose run --rm sov doctor    # any sov command, same saves
docker compose run --rm sov play campfire_v1
docker compose logs -f
```

O contêiner tem como padrão um daemon **somente leitura** na **testnet**. A porta é publicada apenas para o loopback do host (`127.0.0.1:47823`), e cada solicitação ainda precisa do token de portador de `.sov/daemon.json`.

| Configuração | Padrão | O que faz |
|---|---|---|
| `SOV_DATA` | `sov-data` (volume nomeado) | De onde `/data` vem. Defina-o para uma pasta (`SOV_DATA=./`) para manter os jogos salvos no host. |
| `SOV_DAEMON_PORT` | `47823` | Porta do daemon, dentro e no host. Os dois devem corresponder. |
| `SOV_DAEMON_NETWORK` | `testnet` | `testnet`, `devnet` ou `mainnet`. |
| `SOV_DAEMON_READONLY` | `1` | `0` habilita os endpoints de ancoragem. |
| `SOV_DAEMON_TOKEN` | aleatório a cada início | Corrija para que os clientes permaneçam conectados entre as reinicializações. |
| `SOV_DAEMON_LOG_FORMAT` | `human` | `json` para linhas de log estruturadas. |

**Anexe o aplicativo de desktop.** Aponte `SOV_DATA` para a pasta do projeto que o aplicativo abre. O daemon grava seu handshake lá, e o aplicativo disca `127.0.0.1:47823` com o token dele:

```bash
SOV_DATA=./ docker compose up -d
```

Enquanto o contêiner possui o daemon, gerencie-o com `docker compose`, não `sov daemon start|stop|status` no host. A CLI do host não consegue ver o processo de um contêiner, então ela relata o handshake como obsoleto, e `sov daemon start` o limparia.

**Ancore a partir do contêiner.** Crie uma carteira testnet no volume e, em seguida, desative a proteção contra gravação:

```bash
docker compose run --rm sov wallet
SOV_DAEMON_READONLY=0 docker compose up -d
```

Para evitar que a semente seja incluída no volume, forneça-a como um segredo do Docker. O bloco comentado `secrets` em `compose.yaml` mostra como.

## Aplicativo para desktop (opcional, v2.1+)

O Audit Viewer é o aplicativo para desktop v2.1 — um shell Tauri (Rust + webview) que executa o visualizador de auditoria e uma visualização de jogo somente leitura sobre o daemon.

### Instalação (binários)

**v2.3.4** é a versão atual. A versão **v2.3.0** lançada no GitHub não incluía pacotes pré-compilados (wheels) nem recursos para aplicações de ambiente de trabalho, portanto, não fixe a versão em `pip install …==2.3.0`.

- **Python / daemon:** `pip install 'sovereignty-game[daemon]'` (2.3.2 ou posterior para o daemon).
- **Aplicativo para desktop:** [a versão mais recente do GitHub Release](https://github.com/mcp-tool-shop-org/sovereignty/releases/latest) quando o CI tiver anexado os arquivos da plataforma. Se uma tarefa da plataforma falhar, execute a partir do código-fonte (abaixo).

> **O aviso do sistema operacional no primeiro lançamento é esperado** quando os binários autenticados forem disponibilizados. Essas versões contêm apenas a atestação de proveniência da construção SLSA — não a assinatura do Apple Developer ID / Authenticode no nível do sistema operacional. macOS: clique com o botão direito no .app → Abrir. Windows SmartScreen: Mais informações → Executar de qualquer forma.

### Verificar a proveniência

Quando uma versão realmente anexar artefatos para desktop, verifique o arquivo que você baixou:

```bash
gh attestation verify \
  --repo mcp-tool-shop-org/sovereignty \
  ./<downloaded-artifact>
```

Uma verificação limpa prova que o binário foi construído a partir de um commit específico, pelo fluxo de trabalho da versão, neste repositório. Uma camada diferente de confiança em relação à assinatura de código no nível do sistema operacional — o binário ainda aciona o aviso do sistema operacional, mas sua proveniência da cadeia de suprimentos é criptograficamente fixada.

### Executar a partir do código-fonte

Se você preferir construir a partir do código-fonte (ou o binário não for executado em sua plataforma):

```bash
# 1. Install Python + daemon deps
pip install -e '.[xrpl,daemon]'

# 2. Install frontend + Rust deps (one-time)
cd app && npm install && cd ..
cargo build --manifest-path app/src-tauri/Cargo.toml

# 3. Start the dev shell (auto-starts the daemon in readonly mode)
npm --prefix app run tauri dev
```

O shell Tauri inicia automaticamente um daemon somente leitura no lançamento e o interrompe automaticamente no encerramento. Os daemons iniciados externamente (`sov daemon start`) permanecem ativos durante as reinicializações do shell.

Consulte [docs/v2.1-tauri-shell.md](docs/v2.1-tauri-shell.md) para obter o contrato completo.

O Audit Viewer é fornecido com três visualizações:

- **`/audit`** — visualizador de prova ancorada ao XRPL. Lista por jogo expansível, status do âncora por rodada, "Verificar todas as rodadas" executa a recomputação local da prova + pesquisa na cadeia em série. A visualização do auditor: confirma que um jogo foi executado de forma honesta sem ler o JSON bruto.
- **`/game`** — exibição passiva do estado em tempo real para o jogo ativo. Cartões de recursos do jogador, linha do tempo da rodada, registro dos últimos 20 eventos SSE. Somente leitura; jogue no CLI em outro terminal.
- **`/settings`** — exibição da configuração do daemon + alternador de rede (testnet / mainnet / devnet) com proteção de confirmação da mainnet.

Especificação completa da visualização em [docs/v2.1-views.md](docs/v2.1-views.md).

## Como funciona

Você começa com **5 moedas** e **3 reputações**. Jogue um dado, mova-se em um tabuleiro de 16 espaços e pare em espaços que lhe dão opções: negociar, ajudar alguém, correr um risco ou comprar uma carta.

**28 cartas de evento** são como momentos: *"Alguém viu uma pequena bolsa de couro?"* (Carteira perdida) ou *"Ninguém viu... certo?"* (Encontrou um atalho). Inclui eventos de mudança de mercado para jogos da Câmara Municipal.

**12 cartas de acordo + 10 cartas de vale** forçam a conversa: *"Me empresta 2 moedas? Eu te pago 3 de volta."* ou *"Eu te apoio se você me apoiar."* Os acordos definem metas com prazos; os vales são promissórias que você emite para outros jogadores.

**A regra da Promessa:** Uma vez por rodada, diga "Eu prometo..." em voz alta e se comprometa com algo. Cumpra: +1 reputação. Quebre: -2 reputação. A mesa decide.

**O Pedido de Desculpas:** Uma vez por jogo, se você quebrou uma promessa, peça desculpas publicamente. Pague 1 moeda para quem você prejudicou, recupere +1 reputação.

**Escolha seu objetivo** (secreto ou público):
- **Prosperidade** — alcance 20 moedas
- **Amado** — alcance 10 reputações
- **Construtor** — complete 4 atualizações

Após 15 rodadas, a pontuação combinada mais alta vence.

## O que é o Modo Diário?

A cada rodada, o console pode produzir uma **prova** — uma impressão digital do estado do jogo. Se alguém alterar a pontuação, a impressão digital não corresponderá.

Opcionalmente, essa impressão digital pode ser postada no **XRPL Testnet** — um livro-razão público. Pense nisso como escrever a pontuação em uma parede que ninguém pode apagar.

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

Apenas o host precisa de uma carteira. Ninguém mais toca em uma tela. O jogo funciona perfeitamente sem ancoragem — é apenas o diário que se lembra.

## Três níveis

| Nível | Nome | Status | O que ele adiciona |
|------|------|--------|-------------|
| 1 | **Campfire** | Jogável | Moedas, reputação, promessas, promissórias |
| 2 | **Town Hall** | Jogável | Mercado compartilhado, escassez de recursos |
| 3 | **Treaty Table** | Jogável | Tratados com apostas — promessas com consequências |

As regras básicas são estáveis até a v1.x. Consulte [roteiro](docs/roadmap.md).

## Pacotes de cenário

Nenhuma nova regra. Apenas vibrações. Cada pacote define um nível, receita e humor.

| Cenário | Nível | Melhor para |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | Fogueira / Dia de mercado | Primeiro jogo, grupos mistos |
| [Market Panic](docs/scenarios/market-panic.md) | Câmara Municipal | Drama econômico |
| [Promises Matter](docs/scenarios/promises-matter.md) | Fogueira | Confiança e compromisso |
| [Treaty Night](docs/scenarios/treaty-night.md) | Mesa de Tratados | Acordos de alto risco |

`sov scenario list` para navegar a partir do console.

## Estrutura do projeto

```
sovereignty/
  sov_engine/       # Pure game logic (models, rules, serialization, hashing)
  sov_transport/    # Ledger transport (offline + XRPL Testnet)
  sov_cli/          # Typer CLI (the "Round Console")
  sov_daemon/       # Localhost HTTP/SSE daemon for the desktop app
  app/              # Tauri desktop app (Audit Viewer)
  docker/           # Container entrypoint + healthcheck
  site/             # Landing page + handbook
  tests/            # Engine, transport, daemon, and CLI tests
  docs/             # Rules, cards, print-and-play, play-with-strangers
  assets/print/     # Print pack — markdown sources, rendered PDFs, JSX render sources
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

Os jogadores aprendem fazendo: emitindo promissórias, quebrando promessas, negociando a preços variáveis. Os conceitos se relacionam com os primitivos da Web3 — carteiras, tokens, linhas de confiança — mas os jogadores não precisam saber disso para se divertir.

## Contribuindo

A maneira mais fácil de contribuir é [adicionar uma carta](CONTRIBUTING.md). Não é necessário conhecimento do mecanismo — apenas um nome, uma descrição e algum texto de sabor.

## Segurança

Sementes da carteira, estado do jogo e arquivos de prova — o que compartilhar e o que não. Sem telemetria, sem análise de dados, sem comunicação com servidores externos. A única chamada de rede opcional é a ancoragem na XRPL Testnet.

Consulte [SECURITY.md](SECURITY.md).

## Modelo de ameaças

| Ameaça | Mitigação |
|--------|-----------|
| Vazamento de sementes por meio de provas | As provas contêm apenas hashes, nunca sementes |
| Semente no Git | `.sov/` ignorado no Git; `sov wallet` emite um aviso |
| Manipulação do estado do jogo | As provas da rodada `envelope_hash` abrangem `game_id`, `round`, `ruleset`, `rng_seed`, `timestamp_utc`, `players` e `state`. `sov verify` detecta adulterações em todo o envelope. O formato de prova v1 não é mais suportado na v2.0.0+. |
| Falsificação da âncora XRPL | Hash da prova ancorado na cadeia; detecção de incompatibilidade na verificação |
| Exposição do contêiner | A imagem do daemon é publicada apenas para o host `127.0.0.1`; token de portador em cada solicitação; somente leitura por padrão; executa como um usuário não root com um sistema de arquivos raiz somente leitura e sem privilégios |
| Privacidade do nome do jogador | Os nomes dos jogadores SÃO incluídos nas provas (lista de nível superior `players` e dentro dos snapshots dos jogadores). Para jogos privados, não publique `proof.json` nem compartilhe cartões postais. |

## Licença

MIT

---

Criado por [MCP Tool Shop](https://mcp-tool-shop.github.io/)
