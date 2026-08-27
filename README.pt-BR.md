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

## Joguem hoje à noite

Imprima [todo o pacote para imprimir e jogar](assets/print/pdf/Sovereignty-Print-Pack.pdf) — tabuleiro, tapetes dos jogadores, guia de referência rápida e três baralhos de cartas em 11 folhas de papel US Letter. Encontre um dado e algumas moedas. Sente-se com dois ou três amigos. Vocês começarão a jogar em vinte minutos.

Se você quiser folhas individuais:

- **[Tabuleiro](assets/print/pdf/board.pdf)** — o circuito Campfire de 16 espaços, uma página.
- **[Tapete do jogador](assets/print/pdf/mat.pdf)** — moedas, reputação, melhorias, promessas. Um por jogador.
- **[Guia de referência rápida](assets/print/pdf/quickref.pdf)** — espaços do tabuleiro, ordem das jogadas, regras das promessas.
- **[Cartas de evento](assets/print/pdf/events.pdf)** — 20 cartas, três páginas, corte ao longo das linhas.
- **[Cartas de acordo](assets/print/pdf/deals.pdf)** — 10 cartas, duas páginas.
- **[Cartas de vale](assets/print/pdf/vouchers.pdf)** — 10 vales entre os jogadores, duas páginas.
- **[Guia de referência rápida do tratado](assets/print/pdf/treaty.pdf)** — apenas Nível 3.

Os arquivos PDF são vetoriais com fontes incorporadas — eles imprimem bem em qualquer impressora doméstica. O guia passo a passo para configurar o jogo está disponível em [Print & Play](docs/print-and-play.md).

## Quer um console para controlar a pontuação?

Opcional. O jogo funciona bem no papel. Mas, se alguém tiver um laptop à mão, `sov` rastreia as moedas, a reputação, as promessas e gera um recibo inviolável no final:

```bash
pip install sovereignty-game
sov play campfire_v1
```

`sov play campfire_v1` é o guia de início rápido sem configuração — um jogador mais um oponente padrão. Para jogos com vários jogadores na mesa, use `sov new -p Alice -p Bob -p Carol`. Para um guia passo a passo de 60 segundos, use `sov tutorial`.

Não tem Python? O caminho `npx` baixa um binário pré-compilado:

```bash
npx @mcptoolshop/sovereignty tutorial
```

## Uma sessão real

Depois que você e 2 a 3 amigos estiverem à mesa, o console executa a rodada e vocês fazem as conversas. Uma sessão real se parece com isto:

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

`sov status` mostra uma tabela formatada em Rich com as moedas, a reputação, as melhorias, a posição e o objetivo de cada jogador. Para uma visualização rápida em uma única linha entre as rodadas:

```bash
sov status --brief
```

```
R3 |  Alice: 7c 4r 0u | >Bob: 4c 3r 0u |  Carol: 6c 5r 0u
```

(`Nc Nr Nu` = moedas / reputação / melhorias; `>` marca o jogador ativo.)

Repita por 15 rodadas. `sov game-end` imprime a pontuação final.

- **Vários jogos salvos** (v2.1+): `sov games` lista os jogos salvos; `sov resume <game-id>` alterna entre eles.
- **Ancoragem em lote** (v2.1+): `sov anchor`, no final do jogo, agrupa todas as rodadas pendentes em uma única transação XRPL — um ponteiro de cadeia verificável por jogo. Use `sov anchor --checkpoint` para atualizar durante o jogo.
- **Seleção de rede** (v2.1+): `sov anchor --network testnet|mainnet|devnet` (ou a variável de ambiente `SOV_XRPL_NETWORK`; padrão `testnet`).
- **Modo daemon** (v2.1+, opcional): `sov daemon start` executa um servidor HTTP/JSON localhost para integração com o desktop e coleta de dados da cadeia em segundo plano. Consulte [Modo daemon](#daemon-mode-optional-v21) abaixo.
- **Aplicativo de desktop Audit Viewer** (v2.1+, opcional): `npm --prefix app run tauri dev`. Consulte [Aplicativo de desktop](#desktop-app-optional-v21) abaixo.

> Quer um guia passo a passo no aplicativo primeiro? Execute `sov tutorial`.
> Quer uma visão geral mais detalhada das regras? Consulte [Comece aqui](docs/start_here.md) ou o [manual completo](https://mcp-tool-shop-org.github.io/sovereignty/handbook/).

O exemplo `sov turn` acima mostra como uma rodada se parece no console; para a visualização do desktop v2.1, consulte [Aplicativo de desktop](#desktop-app-optional-v21) abaixo.

**[Comece aqui](docs/start_here.md)** | **[Imprima e jogue](docs/print-and-play.md)** | **[Regras completas](docs/rules/campfire_v1.md)** | **[Jogue com estranhos](docs/play-with-strangers.md)**

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

Para integração com o desktop (Audit Viewer, Tauri shell) ou coleta de dados da cadeia em segundo plano, execute Sovereignty como um daemon HTTP localhost:

```bash
pip install 'sovereignty-game[daemon]'
sov daemon start --readonly        # audit-only, no wallet seed
sov daemon start                   # full daemon with anchor endpoints (loads XRPL_SEED)
sov daemon status                  # running | stale | none
sov daemon stop
```

O daemon é vinculado a `127.0.0.1` em uma porta aleatória; os detalhes da conexão (porta + token de portador) estão em `.sov/daemon.json`. Um daemon por raiz do projeto. Consulte [docs/v2.1-daemon-ipc.md](docs/v2.1-daemon-ipc.md) para o contrato IPC completo.

## Aplicativo de desktop (opcional, v2.1+)

O Audit Viewer é o aplicativo de desktop v2.1 — um Tauri shell (Rust + webview) que executa o visualizador de auditoria e uma visualização de jogo somente leitura sobre o daemon.

### Instale (binários)

A v2.3.0 é enviada com binários pré-compilados na [página de lançamentos do GitHub](https://github.com/mcp-tool-shop-org/sovereignty/releases/latest):

- **macOS (universal):** `sovereignty-app-2.3.0-darwin-universal.dmg` — Intel + Apple Silicon
- **Windows (x64):** `sovereignty-app-2.3.0-win-x64.msi`
- **Linux (x64, .deb):** `sovereignty-app-2.3.0-linux-x64.deb` — Debian / Ubuntu / derivados. Instale com `sudo dpkg -i sovereignty-app-2.3.0-linux-x64.deb`.
- **Linux (x64, AppImage):** `sovereignty-app-2.3.0-linux-x64.AppImage` — `chmod +x` e execute.

Você também precisa do daemon Python que suporta o aplicativo: `pip install 'sovereignty-game[daemon]'==2.3.0`.

> **O aviso de primeiro lançamento é esperado.** O macOS exibirá "desenvolvedor não identificado" — clique com o botão direito no .app, escolha Abrir e confirme. O SmartScreen do Windows dirá "editor desconhecido" — clique em "Mais informações" e depois em "Executar de qualquer forma". Ambos os avisos refletem que as versões atuais são enviadas apenas com a atestação de proveniência da compilação (verifique com `gh attestation verify`), não com a assinatura de código no nível do sistema operacional.

### Verificar a proveniência

Cada artefato de lançamento carrega uma atestação de proveniência da compilação SLSA. Verifique antes de executar:

```bash
gh attestation verify \
  --repo mcp-tool-shop-org/sovereignty \
  ./sovereignty-app-2.3.0-darwin-universal.dmg
```

Uma verificação limpa prova que o binário foi construído a partir de um commit específico, pelo fluxo de trabalho de lançamento, neste repositório. Uma camada diferente de confiança em relação à assinatura de código no nível do sistema operacional — o binário ainda aciona o aviso do sistema operacional, mas sua proveniência da cadeia de suprimentos é criptograficamente fixada.

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

O Tauri shell inicia automaticamente um daemon somente leitura ao iniciar e o interrompe automaticamente ao sair. Os daemons iniciados externamente (`sov daemon start`) permanecem ativos entre as reinicializações do shell.

Consulte [docs/v2.1-tauri-shell.md](docs/v2.1-tauri-shell.md) para o contrato completo.

O Audit Viewer é enviado com três visualizações:

- **`/audit`** — Visualizador de provas ancorado ao XRPL. Lista expansível por jogo, status do ponto de referência por rodada e a opção "Verificar todas as rodadas" executa o recálculo local da prova + pesquisa na cadeia em série. A visão do auditor: confirmar que um jogo foi executado honestamente sem ler o JSON bruto.
- **`/game`** — Exibição passiva do estado em tempo real para o jogo ativo. Cartas de recursos dos jogadores, linha do tempo da rodada e registro das últimas 20 ocorrências SSE. Somente leitura; jogue no terminal CLI em outro terminal.
- **`/settings`** — Exibição da configuração do daemon + alternador de rede (testnet / mainnet / devnet) com proteção para confirmação na mainnet.

Especificação completa em [docs/v2.1-views.md](docs/v2.1-views.md).

## Como funciona

Você começa com **5 moedas** e **3 pontos de reputação**. Jogue um dado, mova-se em um tabuleiro de 16 espaços e pare nos espaços que oferecem opções: trocar, ajudar alguém, correr riscos ou comprar uma carta.

**20 cartas de evento** são como momentos: *"Alguém viu uma pequena bolsa de couro?"* (Carteira perdida) ou *"Ninguém viu... certo?"* (Achou um atalho). Inclui eventos de mudança de mercado para jogos na Câmara Municipal.

**10 cartas de acordo + 10 cartas de vale** forçam a conversa: *"Me empresta 2 moedas? Eu te pago 3 depois."* ou *"Eu estou aqui para você, se você estiver aqui para mim."* Os acordos definem metas com prazos; os vales são promissas que você faz para outros jogadores.

**A regra da Promessa:** Uma vez por rodada, diga em voz alta "Eu prometo..." e comprometa-se com algo. Cumpra: +1 ponto de reputação. Quebre: -2 pontos de reputação. A mesa decide.

**O Pedido de Desculpas:** Uma vez por jogo, se você quebrou uma promessa, peça desculpas publicamente. Pague 1 moeda para quem você prejudicou e recupere +1 ponto de reputação.

**Escolha seu objetivo** (secreto ou público):
- **Prosperidade** — alcance 20 moedas
- **Amado** — alcance 10 pontos de reputação
- **Construtor** — complete 4 atualizações

Após 15 rodadas, a maior pontuação combinada vence.

## O que é o Modo Diário?

A cada rodada, o console pode produzir uma **prova** — uma impressão digital do estado do jogo. Se alguém alterar a pontuação, a impressão digital não corresponderá.

Opcionalmente, essa impressão digital pode ser postada no **XRPL Testnet** — um livro-razão público. Pense nisso como escrever a pontuação em uma parede que ninguém pode apagar.

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

Apenas o anfitrião precisa de uma carteira. Ninguém mais toca na tela. O jogo funciona perfeitamente sem ancoragem — é apenas o diário que se lembra.

## Três níveis

| Nível | Nome | Status | O que ele adiciona |
|------|------|--------|-------------|
| 1 | **Campfire** | Jogável | Moedas, reputação, promessas, vales |
| 2 | **Town Hall** | Jogável | Mercado compartilhado, escassez de recursos |
| 3 | **Treaty Table** | Jogável | Tratados com apostas — promessas com consequências |

As regras básicas são estáveis até a versão 1.x. Veja [roadmap](docs/roadmap.md).

## Pacotes de cenário

Nenhuma nova regra. Apenas vibrações. Cada pacote define um nível, receita e humor.

| Cenário | Nível | Melhor para |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | Fogueira / Dia de Mercado | Primeiro jogo, grupos mistos |
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

Os jogadores aprendem fazendo: emitindo vales, quebrando promessas, negociando em preços variáveis. Os conceitos se relacionam com os primitivos Web3 — carteiras, tokens, linhas de confiança —, mas os jogadores não precisam saber disso para se divertirem.

## Contribuindo

A maneira mais fácil de contribuir é [adicionar uma carta](CONTRIBUTING.md). Não é necessário conhecimento do motor — apenas um nome, uma descrição e algum texto adicional.

## Segurança

Sementes da carteira, estado do jogo e arquivos de prova — o que compartilhar e o que não compartilhar. Sem telemetria, sem análise, sem comunicação com servidores externos. A única chamada de rede opcional é a ancoragem no XRPL Testnet.

Veja [SECURITY.md](SECURITY.md).

## Modelo de ameaças

| Ameaça | Mitigação |
|--------|-----------|
| Vazamento de sementes através das provas | As provas contêm apenas hashes, nunca sementes |
| Semente no git | `.sov/` ignorado pelo git; `sov wallet` alerta |
| Manipulação do estado do jogo | As provas de rodada `envelope_hash` cobrem `game_id`, `round`, `ruleset`, `rng_seed`, `timestamp_utc`, `players` e `state`. `sov verify` detecta adulteração em todo o envelope. O formato da prova v1 não é mais suportado na v2.0.0+. |
| Falsificação da âncora XRPL | Hash da prova ancorado na cadeia; detecção de incompatibilidade na verificação |
| Privacidade do nome do jogador | Os nomes dos jogadores SÃO incluídos nas provas (lista de nível superior `players` e dentro dos snapshots dos jogadores). Para jogos privados, não publique `proof.json` nem compartilhe cartões postais. |

## Licença

MIT

---

Criado por [MCP Tool Shop](https://mcp-tool-shop.github.io/)
