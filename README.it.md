<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.md">English</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

## Gioca stasera

Stampa [l'intero pacchetto di gioco](assets/print/pdf/Sovereignty-Print-Pack.pdf): il tabellone, i tappetini per i giocatori, un riferimento rapido, il tabellone del mercato e tre mazzi di carte su 13 fogli di carta formato US Letter. Procurati un dado e delle monete. Siediti con due o tre amici. In venti minuti inizierete a giocare.

Se desideri fogli singoli:

- **[Tabellone](assets/print/pdf/board.pdf)**: il percorso del falò con 16 spazi, una pagina.
- **[Tappetino giocatore](assets/print/pdf/mat.pdf)**: monete, reputazione, miglioramenti, promesse. Uno per giocatore.
- **[Riferimento rapido](assets/print/pdf/quickref.pdf)**: spazi del tabellone, ordine di turno, regole delle promesse.
- **[Carte evento](assets/print/pdf/events.pdf)**: 28 carte, quattro pagine, da tagliare lungo le linee.
- **[Carte affare](assets/print/pdf/deals.pdf)**: 12 carte, due pagine.
- **[Carte buono](assets/print/pdf/vouchers.pdf)**: 10 promesse tra i giocatori, due pagine.
- **[Tabellone del mercato](assets/print/pdf/market.pdf)**: Giorno del mercato / Municipio, una pagina.
- **[Riferimento rapido al trattato](assets/print/pdf/treaty.pdf)**: solo livello 3.

I file PDF sono vettoriali con font incorporati: si stampano in modo chiaro su qualsiasi stampante domestica. Le istruzioni per la preparazione sono disponibili qui: [Stampa e gioca](docs/print-and-play.md).

## Vuoi una console per tenere il punteggio?

Opzionale. Il gioco funziona bene anche su carta. Ma se qualcuno ha un laptop a portata di mano, `sov` tiene traccia delle monete, della reputazione, delle promesse e produce una ricevuta a prova di manomissione alla fine:

```bash
pip install sovereignty-game
sov play campfire_v1
```

`sov play campfire_v1` è la versione rapida, senza configurazione: un giocatore più un avversario predefinito. Per il gioco con più giocatori, usa `sov new -p Alice -p Bob -p Carol`. Per una guida passo passo di 60 secondi, usa `sov tutorial`.

Non hai Python? Il percorso `npx` scarica un file binario precompilato:

```bash
npx @mcptoolshop/sovereignty tutorial
```

Oppure eseguilo in Docker, con i tuoi salvataggi conservati in un volume denominato:

```bash
docker run --rm -it -v sov-data:/data ghcr.io/mcp-tool-shop-org/sovereignty tutorial
```

## Una vera sessione

Una volta che tu e 2-3 amici siete seduti al tavolo, la console gestisce il turno e voi parlate. Una vera sessione potrebbe essere così:

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

`sov status` mostra una tabella formattata con le monete, la reputazione, i miglioramenti, la posizione e l'obiettivo di ciascun giocatore. Per una rapida occhiata tra un turno e l'altro:

```bash
sov status --brief
```

```
R3 |  Alice: 7c 4r 0u | >Bob: 4c 3r 0u |  Carol: 6c 5r 0u
```

(`Nc Nr Nu` = monete / reputazione / miglioramenti; `>` indica il giocatore attivo.)

Ripeti per 15 turni. `sov game-end` stampa i punteggi finali.

- **Più giochi salvati** (v2.1+): `sov games` elenca i salvataggi; `sov resume <game-id>` passa da uno all'altro.
- **Ancoraggio in batch** (v2.1+): `sov anchor` alla fine del gioco memorizza i turni in sospeso in una piccola costante di transazioni XRPL AccountSet (≤8 memo ciascuna; un tipico gioco Campfire di 16 turni → 2 transazioni) — non una singola transazione / un singolo puntatore alla catena. Usa `sov anchor --checkpoint` per la memorizzazione a metà gioco.
- **Selezione della rete** (v2.1+): `sov anchor --network testnet|mainnet|devnet` (o variabile d'ambiente `SOV_XRPL_NETWORK`; predefinito `testnet`).
- **Modalità daemon** (v2.1+, opzionale): `sov daemon start` esegue un server HTTP/JSON su localhost per l'integrazione con il desktop e il polling di background della catena. Vedi [Modalità daemon](#daemon-mode-optional-v21) qui sotto.
- **App desktop Audit Viewer** (v2.1+, opzionale): `npm --prefix app run tauri dev`. Vedi [App desktop](#desktop-app-optional-v21) qui sotto.

> Vuoi prima una guida passo passo all'interno dell'app? Esegui `sov tutorial`.
> Vuoi una panoramica più approfondita delle regole? Vedi [Inizia qui](docs/start_here.md) o
> il [manuale completo](https://mcp-tool-shop-org.github.io/sovereignty/handbook/).

L'esempio `sov turn` mostrato sopra illustra come appare un turno nella console; per la visualizzazione desktop della versione 2.1, vedi [App desktop](#desktop-app-optional-v21) qui sotto.

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

La console tiene il punteggio. Tu mantieni la tua parola.

## Modalità daemon (opzionale, v2.1+)

Per l'integrazione con il desktop (Audit Viewer, shell Tauri) o il polling di background della catena, esegui Sovereignty come daemon HTTP su localhost:

```bash
pip install 'sovereignty-game[daemon]'
sov daemon start --readonly        # audit-only, no wallet seed
sov daemon start                   # full daemon with anchor endpoints (loads XRPL_SEED)
sov daemon status                  # running | stale | none
sov daemon stop
```

Il daemon si connette a `127.0.0.1` su una porta casuale; i dettagli della connessione (porta + token di autenticazione) sono disponibili in `.sov/daemon.json`. Un daemon per ogni cartella di progetto. Vedi [docs/v2.1-daemon-ipc.md](docs/v2.1-daemon-ipc.md) per il contratto IPC completo.

> L'extra `[daemon]` richiede la **versione 2.3.2 o successiva**. Le versioni fino alla 2.3.1 escludevano il pacchetto `sov_daemon`, quindi `sov daemon start` falliva durante l'installazione da PyPI.

## Docker (opzionale, v2.3.2+)

L'immagine all'indirizzo `ghcr.io/mcp-tool-shop-org/sovereignty` contiene la CLI `sov` e il daemon, per `linux/amd64` e `linux/arm64`. Tutto ciò che il gioco memorizza si trova in `/data/.sov`: giochi, prove dei turni, `anchors.json`, la cronologia della stagione, il seed del portafoglio e l'handshake del daemon. Monta un volume su `/data`, altrimenti il container dimentica tutto.

Esegui il daemon con il file [`compose.yaml`](compose.yaml) incluso:

```bash
docker compose up -d                  # readonly audit daemon on 127.0.0.1:47823
docker compose run --rm sov doctor    # any sov command, same saves
docker compose run --rm sov play campfire_v1
docker compose logs -f
```

Il container per impostazione predefinita esegue un daemon in modalità **sola lettura** su **testnet**. La porta è pubblicata solo sul loopback dell'host (`127.0.0.1:47823`) e ogni richiesta richiede comunque il token di autenticazione da `.sov/daemon.json`.

| Impostazione | Predefinita | Cosa fa |
|---|---|---|
| `SOV_DATA` | `sov-data` (volume denominato) | Da dove proviene `/data`. Impostalo su una cartella (`SOV_DATA=./`) per conservare i salvataggi sull'host. |
| `SOV_DAEMON_PORT` | `47823` | Porta del daemon, all'interno e sull'host. Le due devono corrispondere. |
| `SOV_DAEMON_NETWORK` | `testnet` | `testnet`, `devnet` o `mainnet`. |
| `SOV_DAEMON_READONLY` | `1` | `0` abilita gli endpoint di ancoraggio. |
| `SOV_DAEMON_TOKEN` | casuale all'avvio | Impostalo in modo che i client rimangano connessi anche dopo i riavvii. |
| `SOV_DAEMON_LOG_FORMAT` | `human` | `json` per le linee di log strutturate. |

**Collega l'app desktop.** Punta `SOV_DATA` alla cartella del progetto che l'app apre. Il daemon scrive lì l'handshake e l'app si connette a `127.0.0.1:47823` con il token da esso:

```bash
SOV_DATA=./ docker compose up -d
```

Mentre il container possiede il daemon, gestiscilo con `docker compose`, non con `sov daemon start|stop|status` sull'host. La CLI dell'host non può vedere il processo di un container, quindi segnala l'handshake come obsoleto e `sov daemon start` lo cancellerebbe.

**Ancora dal container.** Crea un portafoglio testnet nel volume, quindi disattiva la modalità sola lettura:

```bash
docker compose run --rm sov wallet
SOV_DAEMON_READONLY=0 docker compose up -d
```

Per evitare che il seme venga incluso nel volume, forniscilo come segreto Docker. Il blocco commentato `secrets` in `compose.yaml` mostra come fare.

## Applicazione desktop (opzionale, v2.1+)

Audit Viewer è l'applicazione desktop v2.1: un'interfaccia Tauri (Rust + webview) che esegue l'Audit Viewer e una visualizzazione di gioco in sola lettura sopra il daemon.

### Installazione (binari)

**v2.3.4** è la versione corrente. La versione **v2.3.0** pubblicata su GitHub non includeva i pacchetti precompilati (wheel) né le risorse per le applicazioni desktop, quindi non è necessario specificare `pip install …==2.3.0`.

- **Python / daemon:** `pip install 'sovereignty-game[daemon]'` (2.3.2 o successivo per il daemon).
- **Applicazione desktop:** [l'ultima versione su GitHub](https://github.com/mcp-tool-shop-org/sovereignty/releases/latest) quando il processo CI ha allegato i file specifici per la piattaforma. Se un processo per una piattaforma è fallito, esegui il codice sorgente (vedi sotto).

> **È previsto un avviso del sistema operativo al primo avvio** quando vengono forniti i binari verificati. Queste build includono solo l'attestazione della provenienza della build SLSA, non la firma a livello di sistema operativo Apple Developer ID / Authenticode. macOS: fai clic con il tasto di controllo sull'applicazione .app → Apri. Windows SmartScreen: Altre informazioni → Esegui comunque.

### Verifica della provenienza

Quando un rilascio include effettivamente gli artefatti per desktop, verifica il file che hai scaricato:

```bash
gh attestation verify \
  --repo mcp-tool-shop-org/sovereignty \
  ./<downloaded-artifact>
```

Una verifica corretta dimostra che il binario è stato creato da un commit specifico, tramite il flusso di lavoro del rilascio, in questo repository. Si tratta di un livello di fiducia diverso dalla firma del codice a livello di sistema operativo: il binario attiva comunque l'avviso del sistema operativo, ma la sua provenienza della catena di fornitura è crittograficamente verificata.

### Esecuzione dal codice sorgente

Se preferisci compilare dal codice sorgente (o se il binario non funziona sulla tua piattaforma):

```bash
# 1. Install Python + daemon deps
pip install -e '.[xrpl,daemon]'

# 2. Install frontend + Rust deps (one-time)
cd app && npm install && cd ..
cargo build --manifest-path app/src-tauri/Cargo.toml

# 3. Start the dev shell (auto-starts the daemon in readonly mode)
npm --prefix app run tauri dev
```

L'interfaccia Tauri avvia automaticamente un daemon in sola lettura all'avvio e lo arresta automaticamente all'uscita. I daemon avviati esternamente (`sov daemon start`) rimangono attivi anche dopo il riavvio dell'interfaccia.

Consulta [docs/v2.1-tauri-shell.md](docs/v2.1-tauri-shell.md) per la specifica completa.

Audit Viewer viene fornito con tre visualizzazioni:

- **`/audit`** — Visualizzatore di prove ancorate a XRPL. Elenco di giochi espandibile, stato dell'ancoraggio per ogni round, "Verifica tutti i round" esegue il ricalcolo locale delle prove + la ricerca nella catena in sequenza. La visualizzazione dell'auditor: conferma che un gioco è stato eseguito in modo corretto senza leggere il JSON grezzo.
- **`/game`** — Visualizzazione passiva dello stato in tempo reale per il gioco attivo. Schede delle risorse del giocatore, cronologia dei round, registro degli ultimi 20 eventi SSE. In sola lettura; gioca nella CLI in un'altra finestra del terminale.
- **`/settings`** — Visualizzazione della configurazione del daemon + selettore di rete (testnet / mainnet / devnet) con protezione di conferma della mainnet.

La specifica completa delle visualizzazioni è disponibile all'indirizzo [docs/v2.1-views.md](docs/v2.1-views.md).

## Come funziona

Inizi con **5 monete** e **3 punti reputazione**. Lancia un dado, muoviti su una scacchiera di 16 caselle e atterra su caselle che ti offrono delle scelte: commercia, aiuta qualcuno, corri un rischio o pesca una carta.

**28 carte Evento** sono formulate come momenti: *"Qualcuno ha visto una piccola borsa di cuoio?"* (Portafoglio smarrito) o *"Nessuno ha visto... giusto?"* (Trovato un passaggio segreto). Include eventi di cambiamento del mercato per i giochi di Town Hall.

**12 carte Affare + 10 carte Voucher** forzano la conversazione: *"Mi presti 2 monete? Te ne restituirò 3."* o *"Ti copro le spalle se mi copri le spalle."* Gli affari stabiliscono obiettivi con scadenze; i voucher sono cambiali che emetti ad altri giocatori.

**La regola della Promessa:** Una volta per round, dì ad alta voce "Prometto..." e impegnati a fare qualcosa. Mantienila: +1 punto reputazione. Infrangila: -2 punti reputazione. La decisione spetta al tavolo.

**Le Scuse:** Una volta per partita, se hai infranto una promessa, scusati pubblicamente. Paga 1 moneta a chi hai danneggiato e riacquista +1 punto reputazione.

**Scegli il tuo obiettivo** (segreto o pubblico):
- **Prosperità** — raggiungi 20 monete
- **Amato** — raggiungi 10 punti reputazione
- **Costruttore** — completa 4 miglioramenti

Dopo 15 round, vince chi ha il punteggio combinato più alto.

## Cos'è la modalità Diario?

Ogni round, la console può generare una **prova**, un'impronta digitale dello stato del gioco. Se qualcuno modifica il punteggio, l'impronta digitale non corrisponderà.

Facoltativamente, tale impronta digitale può essere pubblicata sulla **XRPL Testnet**, un registro pubblico. Consideralo come scrivere il punteggio su un muro che nessuno può cancellare.

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

Solo l'host ha bisogno di un portafoglio. Nessun altro tocca uno schermo. Il gioco funziona perfettamente anche senza l'ancoraggio: è solo il diario che ricorda.

## Tre livelli

| Livello | Nome | Stato | Cosa aggiunge |
|------|------|--------|-------------|
| 1 | **Campfire** | Giocabile | Monete, reputazione, promesse, cambiali |
| 2 | **Town Hall** | Giocabile | Mercato condiviso, scarsità di risorse |
| 3 | **Treaty Table** | Giocabile | Trattati con posta in gioco: promesse con conseguenze |

Le regole principali sono stabili fino alla versione 1.x. Consulta la [roadmap](docs/roadmap.md).

## Pacchetti di scenari

Nessuna nuova regola. Solo atmosfera. Ogni pacchetto imposta un livello, una ricetta e un'atmosfera.

| Scenario | Livello | Ideale per |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | Falò / Giornata di mercato | Prima partita, gruppi misti |
| [Market Panic](docs/scenarios/market-panic.md) | Town Hall | Dramma economico |
| [Promises Matter](docs/scenarios/promises-matter.md) | Falò | Fiducia e impegno |
| [Treaty Night](docs/scenarios/treaty-night.md) | Tavolo dei trattati | Accordi ad alto rischio |

`sov scenario list` per sfogliare i contenuti dalla console.

## Struttura del progetto

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

I giocatori imparano facendo: emettono cambiali, infrangono promesse, commerciano a prezzi variabili. I concetti si riferiscono ai primitivi Web3: portafogli, token, linee di credito, ma i giocatori non devono conoscerli per divertirsi.

## Contributi

Il modo più semplice per contribuire è [aggiungere una carta](CONTRIBUTING.md). Non è necessaria alcuna conoscenza del motore: basta un nome, una descrizione e un testo descrittivo.

## Sicurezza

Chiavi private del portafoglio, stato del gioco e file di verifica: cosa condividere e cosa no. Nessun telemetria, nessuna analisi, nessun collegamento a server esterni. L'unica chiamata di rete opzionale è l'ancoraggio alla XRPL Testnet.

Consultare [SECURITY.md](SECURITY.md).

## Modello delle minacce

| Minaccia | Mitigazione |
|--------|-----------|
| Perdita delle chiavi private tramite le prove | Le prove contengono solo hash, mai le chiavi private |
| Chiavi private in Git | `.sov/` ignorato da Git; `sov wallet` avvisa |
| Manipolazione dello stato del gioco | Le prove del round `envelope_hash` coprono `game_id`, `round`, `ruleset`, `rng_seed`, `timestamp_utc`, `players` e `state`. `sov verify` rileva eventuali manomissioni sull'intero pacchetto. Il formato della prova v1 non è più supportato nella versione v2.0.0+. |
| Spoofing dell'ancoraggio XRPL | Hash della prova ancorato sulla blockchain; rilevamento di incongruenze durante la verifica |
| Esposizione del container | L'immagine del daemon viene pubblicata sull'host `127.0.0.1`; token di autenticazione su ogni richiesta; in sola lettura per impostazione predefinita; viene eseguito come utente non root con un file system root di sola lettura e senza privilegi |
| Privacy del nome del giocatore | I nomi dei giocatori SONO inclusi nelle prove (elenco di livello superiore `players` e all'interno degli snapshot dei giocatori). Per giocare in privato, non pubblicare `proof.json` o condividere le cartoline. |

## Licenza

MIT

---

Realizzato da [MCP Tool Shop](https://mcp-tool-shop.github.io/)
