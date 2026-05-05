<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.md">English</a>
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

## Jogue hoje à noite

Imprima [todo o pacote para impressão e jogo](assets/print/pdf/Sovereignty-Print-Pack.pdf) — tabuleiro, tapetes para os jogadores, guia rápido e três baralhos de cartas em 11 folhas de papel no formato US Letter. Encontre um dado e algumas moedas. Sente-se com dois ou três amigos. Você estará jogando em vinte minutos.

Se você quiser as folhas individualmente:

- **[Tabuleiro](assets/print/pdf/board.pdf)** — o circuito de 16 espaços da fogueira, uma página.
- **[Tapete do jogador](assets/print/pdf/mat.pdf)** — moedas, reputação, melhorias, promessas. Um para cada jogador.
- **[Guia rápido](assets/print/pdf/quickref.pdf)** — espaços do tabuleiro, ordem de turno, regras das promessas.
- **[Cartas de evento](assets/print/pdf/events.pdf)** — 20 cartas, três páginas, corte ao longo das linhas.
- **[Cartas de acordo](assets/print/pdf/deals.pdf)** — 10 cartas, duas páginas.
- **[Cartas de vale](assets/print/pdf/vouchers.pdf)** — 10 títulos de dívida entre os jogadores, duas páginas.
- **[Guia rápido de tratados](assets/print/pdf/treaty.pdf)** — apenas para o Nível 3.

Os arquivos PDF são vetoriais e possuem fontes incorporadas — eles imprimem com boa qualidade em qualquer impressora doméstica. O guia de instalação está disponível em [Print & Play](docs/print-and-play.md).

## Quer um console para registrar a pontuação?

Opcional. O jogo funciona bem no papel. Mas, se alguém tiver um laptop por perto, o programa `sov` registra moedas, reputação, promessas e gera um recibo inviolável no final:

```bash
pip install sovereignty-game
sov play campfire_v1
```

`sov play campfire_v1` é a forma rápida de começar, sem configurações: um jogador humano contra um oponente padrão, usando as regras do "Campfire". Para jogar com vários jogadores, use `sov new -p Alice -p Bob -p Carol`. Para um tutorial guiado de 60 segundos, use `sov tutorial`.

Não tem Python? O comando `npx` baixa um binário pré-compilado:

```bash
npx @mcptoolshop/sovereignty tutorial
```

## Uma sessão real

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

- **Múltiplos jogos salvos** (v2.1+): `sov games` lista os jogos salvos; `sov resume <id-do-jogo>` alterna entre eles.
- **Agrupamento de transações** (v2.1+): `sov anchor` no final do jogo agrupa todas as rodadas pendentes em uma única transação XRPL — um ponteiro de cadeia verificável por jogo. Use `sov anchor --checkpoint` para "flush" durante o jogo.
- **Seleção de rede** (v2.1+): `sov anchor --network testnet|mainnet|devnet` (ou variável de ambiente `SOV_XRPL_NETWORK`; padrão: `testnet`).
- **Modo daemon** (v2.1+, opcional): `sov daemon start` executa um servidor HTTP/JSON local para integração com a área de trabalho e monitoramento da cadeia em segundo plano. Veja [Modo daemon](#daemon-mode-optional-v21) abaixo.
- **Aplicativo de desktop "Audit Viewer"** (v2.1+, opcional): `npm --prefix app run tauri dev`. Veja [Aplicativo de desktop](#desktop-app-optional-v21) abaixo.

> Quer um tutorial guiado dentro do aplicativo primeiro? Execute `sov tutorial`.
> Quer uma visão geral mais detalhada das regras? Consulte [Comece aqui](docs/start_here.md) ou
> o [manual completo](https://mcp-tool-shop-org.github.io/sovereignty/handbook/).

O exemplo de `sov turn` acima mostra como uma rodada se parece no console; para a visualização de desktop da v2.1, veja [Aplicativo de desktop](#desktop-app-optional-v21) abaixo.

**[Comece aqui](docs/start_here.md)** | **[Jogar em papel](docs/print-and-play.md)** | **[Regras completas](docs/rules/campfire_v1.md)** | **[Jogue com estranhos](docs/play-with-strangers.md)**

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
sov verify --tx <txid>               # confirm a proof is anchored on chain
sov daemon start [--readonly]        # localhost HTTP/JSON daemon (v2.1+)
sov daemon status                    # running | stale | none
sov daemon stop                      # SIGTERM + cleanup
sov postcard                         # shareable summary
sov season                           # season standings across games (v2.1+)
sov season-postcard                  # printable season recap
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

## Modo daemon (opcional, v2.1+)

Para integração com a área de trabalho (Audit Viewer, shell Tauri) ou monitoramento da cadeia em segundo plano, execute o "sovereignty" como um daemon HTTP local:

```bash
pip install 'sovereignty-game[daemon]'
sov daemon start --readonly        # audit-only, no wallet seed
sov daemon start                   # full daemon with anchor endpoints (loads XRPL_SEED)
sov daemon status                  # running | stale | none
sov daemon stop
```

O daemon se conecta a `127.0.0.1` em uma porta aleatória; os detalhes da conexão (porta + token de autenticação) estão em `.sov/daemon.json`. Um daemon por diretório do projeto. Veja [docs/v2.1-daemon-ipc.md](docs/v2.1-daemon-ipc.md) para o contrato completo de IPC.

## Aplicativo de desktop (opcional, v2.1+)

O "Audit Viewer" é o aplicativo de desktop da v2.1 — um shell Tauri (Rust + webview) que executa o visualizador de auditoria e uma visualização de jogo somente leitura, sobre o daemon.

### Instalação (binários)

A v2.1.0 inclui binários pré-compilados na [página de lançamentos do GitHub](https://github.com/mcp-tool-shop-org/sovereignty/releases/latest):

- **macOS (universal):** `sovereignty-app-2.1.0-darwin-universal.dmg` — Intel + Apple Silicon
- **Windows (x64):** `sovereignty-app-2.1.0-win-x64.msi`
- **Linux (x64, .deb):** `sovereignty-app-2.1.0-linux-x64.deb` — Debian / Ubuntu / derivados. Instale com `sudo dpkg -i sovereignty-app-2.1.0-linux-x64.deb`. O suporte para AppImage será implementado na versão 2.2 (upstream `linuxdeploy` / interação Ubuntu 24.04 FUSE).

Você também precisa do daemon Python que suporta o aplicativo: `pip install 'sovereignty-game[daemon]'==2.1.0`.

> **Aviso de primeiro lançamento é esperado.** No macOS, aparecerá "desenvolvedor não identificado" — clique com o botão direito no arquivo .app, escolha "Abrir", confirme. No Windows, o SmartScreen exibirá "editor desconhecido" — clique em "Mais informações" e depois em "Executar mesmo assim". Ambos os avisos indicam que a v2.1 é fornecida com apenas a atestação de origem da compilação (verifique com `gh attestation verify`), e não com a assinatura de código no nível do sistema operacional. A infraestrutura de assinatura no nível do workspace será incluída na v2.2.

### Verificar a origem

Cada artefato de lançamento possui uma atestação de origem de compilação SLSA. Verifique antes de executar:

```bash
gh attestation verify \
  --repo mcp-tool-shop-org/sovereignty \
  ./sovereignty-app-2.1.0-darwin-universal.dmg
```

Uma verificação bem-sucedida comprova que o binário foi construído a partir de um commit específico, pelo fluxo de trabalho de lançamento, neste repositório. É um nível de confiança diferente da assinatura de código no nível do sistema operacional — o binário ainda aciona o aviso do sistema operacional, mas sua origem na cadeia de suprimentos é fixada criptograficamente.

### Executar a partir do código-fonte

Se você preferir compilar a partir do código-fonte (ou se o binário não for executado em sua plataforma):

```bash
# 1. Install Python + daemon deps
pip install -e '.[xrpl,daemon]'

# 2. Install frontend + Rust deps (one-time)
cd app && npm install && cd ..
cargo build --manifest-path app/src-tauri/Cargo.toml

# 3. Start the dev shell (auto-starts the daemon in readonly mode)
npm --prefix app run tauri dev
```

O shell Tauri inicia automaticamente um daemon somente leitura na inicialização e o interrompe automaticamente na saída. Os daemons iniciados externamente (`sov daemon start`) permanecem ativos mesmo após a reinicialização do shell.

Veja [docs/v2.1-tauri-shell.md](docs/v2.1-tauri-shell.md) para o contrato completo.

<p align="center">
  <img src="site/public/screenshots/audit-viewer.png" alt="Audit Viewer — XRPL-anchored proofs visualized as a collapsible per-game list with per-round verify status" width="640">
  <br>
  <em>Audit Viewer — XRPL-anchored proofs verifiable per round.</em>
</p>

<p align="center">
  <img src="site/public/screenshots/game-shell.png" alt="Game Shell — passive real-time display of the active game with player resource cards and round timeline" width="640">
  <br>
  <em>Game Shell — passive real-time display of the active game.</em>
</p>

<p align="center">
  <img src="site/public/screenshots/settings.png" alt="Settings — daemon network selector (testnet / mainnet / devnet) with daemon connection status" width="640">
  <br>
  <em>Settings — daemon network selection and configuration.</em>
</p>

O "Audit Viewer" é fornecido com três visualizações:

- **`/audit`** — Visualizador de provas ancoradas no XRPL. Lista de jogos com opção de recolhimento, status da âncora por rodada, "Verificar todas as rodadas" executa um recálculo local da prova e uma consulta na cadeia. A visão do auditor: confirmar que um jogo foi executado de forma honesta sem ler o JSON bruto.
- **`/game`** — Exibição em tempo real do estado do jogo ativo. Cartas de recursos dos jogadores, linha do tempo das rodadas, registro dos últimos 20 eventos SSE. Apenas para leitura; para jogar, use a interface de linha de comando em outro terminal.
- **`/settings`** — Exibição da configuração do daemon + chaveadora de rede (testnet / mainnet / devnet) com proteção para a rede principal.

Especificação completa da interface em [docs/v2.1-views.md](docs/v2.1-views.md).

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
