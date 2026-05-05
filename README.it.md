<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

```text
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

## Gioca stasera

Stampa [l'intero pacchetto "stampa e gioca"](assets/print/pdf/Sovereignty-Print-Pack.pdf) — tabellone, schede giocatore, guida rapida e tre mazzi di carte su 11 fogli di carta in formato US Letter. Trova un dado e alcune monete. Siediti con due o tre amici. Inizia a giocare in venti minuti.

Se desideri i fogli singoli:

- **[Tabellone](assets/print/pdf/board.pdf)** — il circuito di 16 caselle "Campfire", una pagina.
- **[Scheda giocatore](assets/print/pdf/mat.pdf)** — monete, reputazione, potenziamenti, promesse. Una per giocatore.
- **[Guida rapida](assets/print/pdf/quickref.pdf)** — caselle del tabellone, ordine di turno, regole delle promesse.
- **[Carte evento](assets/print/pdf/events.pdf)** — 20 carte, tre pagine, ritaglia lungo le linee.
- **[Carte offerta](assets/print/pdf/deals.pdf)** — 10 carte, due pagine.
- **[Carte voucher](assets/print/pdf/vouchers.pdf)** — 10 "I.O.U." tra i giocatori, due pagine.
- **[Guida rapida sui trattati](assets/print/pdf/treaty.pdf)** — solo per il livello 3.

I file PDF sono vettoriali e contengono font incorporati: si stampano perfettamente con qualsiasi stampante domestica. Le istruzioni per la stampa sono disponibili a [Stampa e gioca](docs/print-and-play.md).

## Vuoi un'interfaccia per tenere il punteggio?

Opzionale. Il gioco funziona bene anche sulla carta. Ma se qualcuno ha un laptop a disposizione, `sov` tiene traccia di monete, reputazione, promesse e genera una ricevuta non modificabile alla fine:

```bash
pip install sovereignty-game
sov play campfire_v1
```

`sov play campfire_v1` è l'avvio rapido senza configurazione: un giocatore umano più un avversario predefinito. Per il gioco in multiplayer, usa `sov new -p Alice -p Bob -p Carol`. Per una guida passo passo di 60 secondi, usa `sov tutorial`.

Non hai Python? Il comando `npx` scarica un eseguibile precompilato:

```bash
npx @mcptoolshop/sovereignty tutorial
```

## Una vera partita

Una volta che tu e 2-3 amici siete seduti al tavolo, la console gestisce il turno e voi vi occupate di interagire. Una vera partita assomiglia a questo:

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

`sov status` mostra una tabella formattata con le monete, la reputazione, i potenziamenti, la posizione e l'obiettivo di ogni giocatore. Per una rapida occhiata tra un turno e l'altro:

```bash
sov status --brief
```

```
R3 |  Alice: 7c 4r 0u | >Bob: 4c 3r 0u |  Carol: 6c 5r 0u
```

(`Nc Nr Nu` = monete / reputazione / potenziamenti; `>` indica il giocatore attivo.)

Ripeti per 15 turni. `sov game-end` stampa i punteggi finali.

- **Giochi salvati (v2.1+):** `sov games` elenca i salvataggi; `sov resume <id_gioco>` permette di alternare tra di essi.
- **Ancoraggio in batch (v2.1+):** `sov anchor` alla fine della partita raggruppa tutti i turni in sospeso in un'unica transazione XRPL: un singolo puntatore alla catena verificabile per ogni partita. Usa `sov anchor --checkpoint` per un aggiornamento intermedio.
- **Selezione della rete (v2.1+):** `sov anchor --network testnet|mainnet|devnet` (o variabile d'ambiente `SOV_XRPL_NETWORK`; predefinito `testnet`).
- **Modalità demone (v2.1+, opzionale):** `sov daemon start` avvia un server HTTP/JSON locale per l'integrazione con il desktop e il monitoraggio della catena in background. Vedi [Modalità demone](#daemon-mode-optional-v21) qui sotto.
- **App desktop Audit Viewer (v2.1+, opzionale):** `npm --prefix app run tauri dev`. Vedi [App desktop](#desktop-app-optional-v21) qui sotto.

> Vuoi una guida interattiva all'interno dell'app? Esegui `sov tutorial`.
> Vuoi una panoramica più approfondita delle regole? Consulta [Inizia qui](docs/start_here.md) o
> il [manuale completo](https://mcp-tool-shop-org.github.io/sovereignty/handbook/).

L'esempio inline di `sov turn` mostrato sopra illustra come appare un turno nella console; per la visualizzazione desktop della versione 2.1, consulta [App desktop](#desktop-app-optional-v21) qui sotto.
```

**[Inizia qui](docs/start_here.md)** | **[Stampa e gioca](docs/print-and-play.md)** | **[Regole complete](docs/rules/campfire_v1.md)** | **[Gioca con sconosciuti](docs/play-with-strangers.md)**

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

La console tiene traccia del punteggio. Tu mantieni la tua parola.

## Modalità daemon (opzionale, v2.1+)

Per l'integrazione con il desktop (Audit Viewer, shell Tauri) o per il monitoraggio in background della blockchain, esegui sovereignty come un demone HTTP locale:

```bash
pip install 'sovereignty-game[daemon]'
sov daemon start --readonly        # audit-only, no wallet seed
sov daemon start                   # full daemon with anchor endpoints (loads XRPL_SEED)
sov daemon status                  # running | stale | none
sov daemon stop
```

Il demone si connette a `127.0.0.1` su una porta casuale; i dettagli della connessione (porta + token di autorizzazione) si trovano in `.sov/daemon.json`. Un solo demone per cartella del progetto. Consulta [docs/v2.1-daemon-ipc.md](docs/v2.1-daemon-ipc.md) per il contratto IPC completo.

## Applicazione desktop (opzionale, v2.1+)

L'Audit Viewer è l'applicazione desktop v2.1: una shell Tauri (Rust + webview) che esegue l'audit viewer e una visualizzazione di gioco in sola lettura, sovrapposti al demone.

### Installazione (binari)

La versione 2.1.0 include binari precompilati nella [pagina delle release di GitHub](https://github.com/mcp-tool-shop-org/sovereignty/releases/latest):

- **macOS (universal):** `sovereignty-app-2.1.0-darwin-universal.dmg` — Intel + Apple Silicon
- **Windows (x64):** `sovereignty-app-2.1.0-win-x64.msi`
- **Linux (x64, .deb):** `sovereignty-app-2.1.0-linux-x64.deb` — Debian / Ubuntu / derivati. Installa con `sudo dpkg -i sovereignty-app-2.1.0-linux-x64.deb`. Il supporto AppImage è previsto per la versione 2.2 (upstream `linuxdeploy` / Ubuntu 24.04 FUSE interaction).

È necessario anche il demone Python che supporta l'applicazione: `pip install 'sovereignty-game[daemon]'==2.1.0`.

> **È previsto un avviso al primo avvio.** Su macOS, verrà visualizzato "sviluppatore non identificato": fai clic con il pulsante destro del mouse sul file .app, scegli Apri e conferma. Su Windows, SmartScreen visualizzerà "editore non riconosciuto": fai clic su "Altre informazioni" e quindi su "Esegui comunque". Entrambi gli avvisi indicano che la versione 2.1 viene fornita con l'attestazione della provenienza della build (verifica con `gh attestation verify`), e non con la firma del codice a livello di sistema operativo. L'infrastruttura di firma a livello di workspace è disponibile nella versione 2.2.

### Verifica della provenienza

Ogni artefatto della release include un'attestazione della provenienza della build SLSA. Verifica prima di eseguire:

```bash
gh attestation verify \
  --repo mcp-tool-shop-org/sovereignty \
  ./sovereignty-app-2.1.0-darwin-universal.dmg
```

Una verifica corretta dimostra che il binario è stato creato da un commit specifico, tramite il workflow di release, in questo repository. Questo livello di fiducia è diverso dalla firma del codice a livello di sistema operativo: il binario continua a generare l'avviso del sistema operativo, ma la sua provenienza della catena di fornitura è fissata crittograficamente.

### Esecuzione dal codice sorgente

Se preferisci compilare dal codice sorgente (o se il binario non viene eseguito sulla tua piattaforma):

```bash
# 1. Install Python + daemon deps
pip install -e '.[xrpl,daemon]'

# 2. Install frontend + Rust deps (one-time)
cd app && npm install && cd ..
cargo build --manifest-path app/src-tauri/Cargo.toml

# 3. Start the dev shell (auto-starts the daemon in readonly mode)
npm --prefix app run tauri dev
```

La shell Tauri avvia automaticamente un demone in sola lettura all'avvio e lo interrompe automaticamente all'uscita. I demoni avviati esternamente (`sov daemon start`) rimangono attivi anche dopo i riavvii della shell.

Consulta [docs/v2.1-tauri-shell.md](docs/v2.1-tauri-shell.md) per il contratto completo.

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

L'Audit Viewer include tre visualizzazioni:

- **`/audit`** — Visualizzatore di prove ancorate a XRPL. Elenco dei giochi collassabile, stato dell'ancora per ogni round, "Verifica tutti i round" esegue un calcolo locale delle prove + ricerca nella blockchain. La visualizzazione dell'auditore: conferma che un gioco è stato eseguito onestamente senza leggere il JSON grezzo.
- **`/game`** — Visualizzazione passiva in tempo reale dello stato del gioco attivo. Carte delle risorse dei giocatori, timeline dei round, log degli ultimi 20 eventi SSE. Sola lettura; gioca nella CLI in un'altra finestra del terminale.
- **`/settings`** — Visualizzazione della configurazione del demone + interruttore di rete (testnet / mainnet / devnet) con protezione di conferma mainnet.

Specifiche complete della visualizzazione in [docs/v2.1-views.md](docs/v2.1-views.md).

## Come funziona

Inizi con **5 monete** e **3 reputazioni**. Lancia un dado, muoviti su un tabellone di 16 caselle e atterra su caselle che ti offrono delle scelte: scambia, aiuta qualcuno, corri un rischio o pesca una carta.

**20 carte evento** che richiamano momenti specifici: *"Qualcuno ha visto un piccolo sacchetto di pelle?"* (Portafoglio smarrito) oppure *"Nessuno l'ha visto... giusto?"* (Si è trovato un'scorciatoia). Include eventi che modificano il mercato, adatti alle partite con il Municipio.

**10 carte scambio + 10 carte voucher** che stimolano la conversazione: *"Mi presti 2 monete? Te ne restituirò 3."* oppure *"Ti copro le spalle se anche tu mi copri le mie."*. Le carte scambio stabiliscono obiettivi con scadenze; i voucher sono promesse che rilasci ad altri giocatori.

**La regola della Promessa:** Una volta per turno, pronuncia ad alta voce "Prometto..." e impegnati in qualcosa. Se mantieni la promessa: +1 reputazione. Se la rompi: -2 reputazione. La decisione spetta al tavolo.

**Le Scuse:** Una volta durante la partita, se hai rotto una promessa, scusati pubblicamente. Paga 1 moneta alla persona che hai danneggiato e recupera +1 reputazione.

**Scegli il tuo obiettivo** (segreto o pubblico):
- **Prosperità** — raggiungere 20 monete
- **Amato** — raggiungere 10 reputazione
- **Costruttore** — completare 4 miglioramenti

Dopo 15 turni, vince chi ha il punteggio combinato più alto.

## Cos'è la Modalità Diario?

Ogni turno, la console può generare una **prova** — un'impronta dello stato del gioco. Se qualcuno modifica il punteggio, l'impronta non corrisponderà.

Facoltativamente, questa impronta può essere pubblicata sulla **XRPL Testnet** — un registro pubblico. Immaginala come scrivere il punteggio su un muro che nessuno può cancellare.

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

È necessario solo un portafoglio per l'host. Nessun altro tocca uno schermo. Il gioco funziona perfettamente senza essere ancorato a una blockchain; è solo il diario che memorizza le informazioni.

## Tre livelli

| Livello | Nome | Stato | Cosa aggiunge |
|------|------|--------|-------------|
| 1 | **Campfire** | Giocabile | Monete, reputazione, promesse, voucher |
| 2 | **Town Hall** | Giocabile | Mercato condiviso, scarsità di risorse |
| 3 | **Treaty Table** | Giocabile | Trattati con conseguenze — promesse vincolanti |

Le regole principali sono stabili dalla versione 1.x. Consulta la [roadmap](docs/roadmap.md).

## Pacchetti di scenari

Nessuna nuova regola. Solo atmosfera. Ogni pacchetto definisce un livello, una ricetta e un'atmosfera.

| Scenario | Livello | Ideale per |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | Falò / Festa del mercato | Prima partita, gruppi misti |
| [Market Panic](docs/scenarios/market-panic.md) | Municipio | Drammi economici |
| [Promises Matter](docs/scenarios/promises-matter.md) | Falò | Fiducia e impegno |
| [Treaty Night](docs/scenarios/treaty-night.md) | Tavolo dei trattati | Accordi ad alto rischio |

Usa `sov scenario list` per sfogliare dalla console.

## Struttura del progetto

```
sovereignty/
  sov_engine/       # Pure game logic (models, rules, serialization, hashing)
  sov_transport/    # Ledger transport (offline + XRPL Testnet)
  sov_cli/          # Typer CLI (the "Round Console")
  tests/            # Engine, transport, and CLI tests
  docs/             # Rules, cards, print-and-play, play-with-strangers
  assets/print/     # Print pack — markdown sources, rendered PDFs, JSX render sources
```

## Sviluppo

```bash
git clone https://github.com/mcp-tool-shop-org/sovereignty.git
cd sovereignty
uv sync --dev
uv run pytest tests/ -v
uv run ruff check .
```

## Principio di progettazione

> "Insegna attraverso le conseguenze, non attraverso la terminologia."

I giocatori imparano facendo: rilasciando voucher, rompendo promesse, scambiando a prezzi variabili. I concetti si collegano ai principi di Web3 — portafogli, token, linee di credito — ma i giocatori non devono conoscerli per divertirsi.

## Contributi

Il modo più semplice per contribuire è [aggiungere una carta](CONTRIBUTING.md). Non è necessaria alcuna conoscenza del motore — basta un nome, una descrizione e un breve testo descrittivo.

## Sicurezza

Seed dei portafogli, stato del gioco e file di prova — cosa condividere e cosa non condividere. Nessuna telemetria, nessuna analisi, nessun "telefono a casa". L'unica chiamata di rete facoltativa è l'ancoraggio alla XRPL Testnet.

Consulta [SECURITY.md](SECURITY.md).

## Modello delle minacce

| Minaccia | Mitigazione |
|--------|-----------|
| Perdita del seed tramite le prove | Le prove contengono solo hash, mai i seed |
| Seed in git | `.sov/` ignorato da git; `sov wallet` avverte |
| Manipolazione dello stato del gioco | Le prove di ogni turno coprono l' `envelope_hash` che include `game_id`, `round`, `ruleset`, `rng_seed`, `timestamp_utc`, `players` e `state`. `sov verify` rileva eventuali manomissioni all'interno dell'intero pacchetto. Il formato della prova v1 non è più supportato dalla versione 2.0.0+. |
| Spoofing dell'ancoraggio XRPL | L'hash di verifica è ancorato alla blockchain; rilevamento di incongruenze durante la verifica. |
| Privacy dei nomi dei giocatori. | I nomi dei giocatori sono inclusi nelle prove (nella lista `players` di livello superiore e all'interno degli snapshot dei giocatori). Per le partite private, non pubblicare il file `proof.json` e non condividere le "cartoline". |

## Licenza

MIT.

---

Creato da [MCP Tool Shop](https://mcp-tool-shop.github.io/).
