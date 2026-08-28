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
  <a href="https://pypi.org/project/sovereignty-game/"><img src="https://img.shields.io/pypi/v/sovereignty-game?include_prereleases&style=flat&cacheSeconds=3600" alt="PyPI version"></a>
  <a href="https://pypi.org/project/sovereignty-game/"><img src="https://img.shields.io/pypi/pyversions/sovereignty-game?style=flat&cacheSeconds=3600" alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat&cacheSeconds=86400" alt="License: MIT"></a>
  <a href="https://mcp-tool-shop-org.github.io/sovereignty/"><img src="https://img.shields.io/badge/Landing_Page-live-blue?style=flat&cacheSeconds=86400" alt="Landing Page"></a>
</p>

## Gioca stasera

Scarica il pacchetto completo per la stampa e il gioco [qui](assets/print/pdf/Sovereignty-Print-Pack.pdf): include il tabellone, i tappetini dei giocatori, un riferimento rapido, il tabellone del mercato e tre mazzi di carte su 13 fogli di carta formato US Letter. Procurati un dado e delle monete. Siediti con due o tre amici. Tra venti minuti inizierete a giocare.

Se desideri i singoli fogli:

- **[Tabellone](assets/print/pdf/board.pdf)**: il percorso "Campfire" con 16 spazi, una pagina.
- **[Tappetino giocatore](assets/print/pdf/mat.pdf)**: monete, reputazione, miglioramenti, promesse. Uno per giocatore.
- **[Riferimento rapido](assets/print/pdf/quickref.pdf)**: spazi del tabellone, ordine di turno, regole delle promesse.
- **[Carte evento](assets/print/pdf/events.pdf)**: 28 carte, quattro pagine, da tagliare lungo le linee.
- **[Carte affare](assets/print/pdf/deals.pdf)**: 12 carte, due pagine.
- **[Carte promessa](assets/print/pdf/vouchers.pdf)**: 10 "IOU" tra i giocatori, due pagine.
- **[Tabellone del mercato](assets/print/pdf/market.pdf)**: Market Day / Town Hall, una pagina.
- **[Riferimento rapido al trattato](assets/print/pdf/treaty.pdf)**: solo livello 3.

I file PDF sono vettoriali con font incorporati: si stampano in modo chiaro su qualsiasi stampante domestica. Le istruzioni per la preparazione del gioco sono disponibili qui: [Stampa e Gioca](docs/print-and-play.md).

## Vuoi una console per tenere il punteggio?

Opzionale. Il gioco funziona bene anche su carta. Ma se qualcuno ha un laptop a portata di mano, `sov` tiene traccia delle monete, della reputazione, delle promesse e produce una ricevuta a prova di manomissione alla fine:

```bash
pip install sovereignty-game
sov play campfire_v1
```

`sov play campfire_v1` è la versione rapida senza configurazioni: un giocatore più un avversario predefinito. Per il gioco con più giocatori al tavolo, usa `sov new -p Alice -p Bob -p Carol`. Per una guida passo-passo di 60 secondi, usa `sov tutorial`.

Non hai Python? Con l'opzione `npx` puoi scaricare un file binario precompilato:

```bash
npx @mcptoolshop/sovereignty tutorial
```

## Una vera sessione di gioco

Quando tu e 2-3 amici siete seduti al tavolo, la console gestisce il turno e voi parlate. Una vera sessione di gioco potrebbe essere così:

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

- **Più partite salvate** (v2.1+): `sov games` elenca le partite salvate; `sov resume <game-id>` permette di passare da una all'altra.
- **Ancoraggio in batch** (v2.1+): `sov anchor`, alla fine della partita, svuota i round in sospeso in un piccolo numero costante di transazioni AccountSet XRPL (≤8 memo ciascuna; una partita Campfire tipica da 16 round → 2 tx) — non una singola transazione / un singolo puntatore di catena. Usa `sov anchor --checkpoint` per lo svuotamento a metà partita.
- **Selezione della rete** (v2.1+): `sov anchor --network testnet|mainnet|devnet` (o variabile d'ambiente `SOV_XRPL_NETWORK`; predefinito `testnet`).
- **Modalità daemon** (v2.1+, opzionale): `sov daemon start` esegue un server HTTP/JSON su localhost per l'integrazione con il desktop e il polling della catena in background. Consulta [Modalità daemon](#daemon-mode-optional-v21) qui sotto.
- **App desktop Audit Viewer** (v2.1+, opzionale): `npm --prefix app run tauri dev`. Consulta [App desktop](#desktop-app-optional-v21) qui sotto.

> Vuoi prima una guida interattiva all'interno dell'app? Esegui `sov tutorial`.
> Vuoi un approfondimento delle regole? Consulta [Inizia da qui](docs/start_here.md) o
> il [manuale completo](https://mcp-tool-shop-org.github.io/sovereignty/handbook/).

L'esempio `sov turn` mostrato sopra illustra come appare un turno nella console; per la visualizzazione desktop della versione v2.1, consulta [App desktop](#desktop-app-optional-v21) qui sotto.

**[Inizia da qui](docs/start_here.md)** | **[Stampa e Gioca](docs/print-and-play.md)** | **[Regole complete](docs/rules/campfire_v1.md)** | **[Gioca con sconosciuti](docs/play-with-strangers.md)**

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

Per l'integrazione con il desktop (Audit Viewer, shell Tauri) o il polling della catena in background, esegui Sovereignty come un daemon HTTP su localhost:

```bash
pip install 'sovereignty-game[daemon]'
sov daemon start --readonly        # audit-only, no wallet seed
sov daemon start                   # full daemon with anchor endpoints (loads XRPL_SEED)
sov daemon status                  # running | stale | none
sov daemon stop
```

Il daemon si collega a `127.0.0.1` su una porta casuale; i dettagli della connessione (porta + token bearer) sono disponibili in `.sov/daemon.json`. Un solo daemon per ogni cartella di progetto. Consulta [docs/v2.1-daemon-ipc.md](docs/v2.1-daemon-ipc.md) per il contratto IPC completo.

## App desktop (opzionale, v2.1+)

L'Audit Viewer è l'app desktop v2.1: una shell Tauri (Rust + webview) che esegue l'audit viewer e una visualizzazione di gioco in sola lettura sopra il daemon.

### Installa (file binari)

**v2.3.1** è la linea viva pubblicata da questo tag. GitHub Release **v2.3.0** non ha pubblicato wheel né asset desktop (`publish.yml` esecuzione 33118253060; asset vuoti). Non fissare `pip install …==2.3.0`. I nomi `sovereignty-app-2.3.0-*` restano 404.

- **Python / daemon:** `pip install 'sovereignty-game[daemon]'` (questo tag è **2.3.1**).
- **App desktop:** [GitHub Release v2.3.1](https://github.com/mcp-tool-shop-org/sovereignty/releases/tag/v2.3.1) quando CI ha allegato i file di piattaforma. Se un job di piattaforma è fallito, esegui dal codice sorgente (sotto).

> **È previsto un avviso all'avvio** quando i binari attestati verranno effettivamente pubblicati. Quelle build portano solo l'attestazione SLSA di provenienza — non la firma Apple Developer ID / Authenticode. macOS: clic destro sul .app → Apri. Windows SmartScreen: Ulteriori informazioni → Esegui comunque.

### Verifica la provenienza

Quando una release allega realmente artefatti desktop, verifica il file scaricato:

```bash
gh attestation verify \
  --repo mcp-tool-shop-org/sovereignty \
  ./<downloaded-artifact>
```

Una verifica corretta dimostra che il file binario è stato creato da uno specifico commit, dal flusso di lavoro della release, in questo repository. Si tratta di un livello di fiducia diverso dalla firma del codice a livello di sistema operativo: il file binario attiverà comunque l'avviso del sistema operativo, ma la sua provenienza nella catena di fornitura sarà crittograficamente ancorata.

### Esegui dal codice sorgente

Se preferisci compilare dal codice sorgente (o se il file binario non funziona sulla tua piattaforma):

```bash
# 1. Install Python + daemon deps
pip install -e '.[xrpl,daemon]'

# 2. Install frontend + Rust deps (one-time)
cd app && npm install && cd ..
cargo build --manifest-path app/src-tauri/Cargo.toml

# 3. Start the dev shell (auto-starts the daemon in readonly mode)
npm --prefix app run tauri dev
```

La shell Tauri avvia automaticamente un daemon in sola lettura all'avvio e lo arresta automaticamente all'uscita. I daemon avviati esternamente (`sov daemon start`) rimangono attivi anche dopo i riavvii della shell.

Consulta [docs/v2.1-tauri-shell.md](docs/v2.1-tauri-shell.md) per il contratto completo.

L'Audit Viewer include tre visualizzazioni:

- **`/audit`** — Visualizzatore di prove ancorato a XRPL. Elenco per gioco espandibile/comprimibile, stato dell'ancoraggio per ogni turno, "Verifica tutti i turni" esegue il ricalcolo locale delle prove + la ricerca nella blockchain in sequenza. La vista per l'auditor: conferma che una partita si è svolta correttamente senza leggere il JSON grezzo.
- **`/game`** — Visualizzazione passiva dello stato in tempo reale per la partita in corso. Carte delle risorse dei giocatori, cronologia dei turni, registro degli ultimi 20 eventi SSE. Solo lettura; gioca nella CLI in un altro terminale.
- **`/settings`** — Visualizzazione della configurazione del daemon + selettore di rete (testnet / mainnet / devnet) con protezione per la conferma sulla mainnet.

La specifica completa è disponibile all'indirizzo [docs/v2.1-views.md](docs/v2.1-views.md).

## Come funziona

Inizi con **5 monete** e **3 punti reputazione**. Lancia un dado, muoviti su una scacchiera di 16 caselle e atterra su caselle che ti offrono delle scelte: commercia, aiuta qualcuno, corri un rischio o pesca una carta.

**28 carte Evento** sono formulate come momenti: *"Qualcuno ha visto una piccola borsa di cuoio?"* (Portafoglio smarrito) oppure *"Nessuno l'ha vista... vero?"* (Trovata una scorciatoia). Include eventi che modificano il mercato per le partite in Town Hall.

**12 carte Affare + 10 carte Voucher** forzano la conversazione: *"Mi presti 2 monete? Te ne restituirò 3."* oppure *"Ti copro le spalle se tu fai lo stesso per me."* Gli affari stabiliscono obiettivi con scadenze; i voucher sono promesse di pagamento che emetti ad altri giocatori.

**La regola della Promessa:** Una volta per turno, dì ad alta voce "Prometto..." e impegnati a fare qualcosa. Mantienila: +1 punto reputazione. Infrangila: -2 punti reputazione. La decisione spetta al tavolo.

**Le Scuse:** Una volta per partita, se hai infranto una promessa, scusati pubblicamente. Paga 1 moneta a chi hai danneggiato e recupera +1 punto reputazione.

**Scegli il tuo obiettivo** (segreto o pubblico):
- **Prosperità:** raggiungi 20 monete
- **Amato:** raggiungi 10 punti reputazione
- **Costruttore:** completa 4 miglioramenti

Dopo 15 turni, vince chi ha il punteggio combinato più alto.

## Cos'è la modalità Diario?

Ogni turno, la console può generare una **prova**, un'impronta digitale dello stato del gioco. Se qualcuno modifica il punteggio, l'impronta non corrisponderà.

Facoltativamente, questa impronta può essere pubblicata sulla **XRPL Testnet** — un registro pubblico. Consideralo come scrivere il punteggio su un muro che nessuno può cancellare.

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

Solo l'host ha bisogno di un portafoglio. Nessun altro tocca uno schermo. Il gioco funziona perfettamente anche senza ancoraggio; è solo il diario che ricorda.

## Tre livelli

| Livello | Nome | Stato | Cosa aggiunge |
|------|------|--------|-------------|
| 1 | **Campfire** | Giocabile | Monete, reputazione, promesse, promesse di pagamento |
| 2 | **Town Hall** | Giocabile | Mercato condiviso, scarsità di risorse |
| 3 | **Treaty Table** | Giocabile | Trattati con posta in gioco: promesse vincolanti |

Le regole principali sono stabili fino alla versione 1.x. Vedi [roadmap](docs/roadmap.md).

## Pacchetti di scenari

Nessuna nuova regola. Solo atmosfera. Ogni pacchetto definisce un livello, una ricetta e un'atmosfera.

| Scenario | Livello | Ideale per |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | Falò / Giornata al mercato | Prima partita, gruppi misti |
| [Market Panic](docs/scenarios/market-panic.md) | Town Hall | Dramma economico |
| [Promises Matter](docs/scenarios/promises-matter.md) | Falò | Fiducia e impegno |
| [Treaty Night](docs/scenarios/treaty-night.md) | Tavolo dei trattati | Accordi ad alto rischio |

`sov scenario list` per navigare dalla console.

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

I giocatori imparano facendo: emettendo promesse di pagamento, infrangendo promesse, scambiando a prezzi variabili. I concetti si collegano ai primitivi Web3 — portafogli, token, linee di fiducia — ma i giocatori non devono conoscerli per divertirsi.

## Contributi

Il modo più semplice per contribuire è [aggiungere una carta](CONTRIBUTING.md). Non sono necessarie conoscenze del motore; basta un nome, una descrizione e qualche testo descrittivo.

## Sicurezza

Seed dei portafogli, stato del gioco e file di prova: cosa condividere e cosa no. Nessun telemetria, nessuna analisi, nessun "chiamata a casa". L'unica chiamata di rete opzionale è l'ancoraggio alla XRPL Testnet.

Vedi [SECURITY.md](SECURITY.md).

## Modello di minaccia

| Minaccia | Mitigazione |
|--------|-----------|
| Perdita del seed tramite le prove | Le prove contengono solo hash, mai i seed |
| Seed in git | `.sov/` ignorato da git; `sov wallet` avvisa |
| Manipolazione dello stato del gioco | Le prove di fine turno `envelope_hash` coprono `game_id`, `round`, `ruleset`, `rng_seed`, `timestamp_utc`, `players` e `state`. `sov verify` rileva manomissioni sull'intero pacchetto. Il formato della prova v1 non è più supportato nella versione 2.0.0+. |
| Spoofing dell'ancoraggio XRPL | Hash della prova ancorato sulla blockchain; rilevamento di incongruenze durante la verifica |
| Privacy del nome del giocatore | I nomi dei giocatori SONO inclusi nelle prove (elenco di livello superiore `players` e all'interno degli snapshot dei giocatori). Per un gioco privato, non pubblicare `proof.json` o condividere cartoline. |

## Licenza

MIT

---

Creato da [MCP Tool Shop](https://mcp-tool-shop.github.io/)
