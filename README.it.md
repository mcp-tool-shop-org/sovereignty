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

## Installazione in 30 secondi

Il metodo più veloce: per utenti Python:

```bash
pipx install sovereignty-game
sov tutorial
```

Nessun Python? Nessun problema. Il comando `npx` scarica un eseguibile precompilato:

```bash
npx @mcptoolshop/sovereignty tutorial
```

Ecco fatto. `sov tutorial` vi guida attraverso le regole in circa 60 secondi.

## La vostra prima partita

Una volta che voi e 2-3 amici siete seduti al tavolo, la console gestisce il turno e
voi vi occupate di parlare. Una vera partita assomiglia a questo:

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

`sov status` mostra una tabella formattata con le monete, la reputazione, gli aggiornamenti,
la posizione e l'obiettivo di ogni giocatore. Per una rapida occhiata tra un turno e l'altro:

```bash
sov status --brief
```

```
R3 |  Alice: 7c 4r 0u | >Bob: 4c 3r 0u |  Carol: 6c 5r 0u
```

(`Nc Nr Nu` = monete / reputazione / aggiornamenti; `>` indica il giocatore attivo.)

Ripetete per 15 turni. `sov game-end` stampa i punteggi finali.

> Volete prima una guida interattiva? Eseguite `sov tutorial`.
> Volete giocare senza alcun software? Consultate [Print & Play](docs/print-and-play.md).
> Volete una panoramica più approfondita delle regole? Consultate [Iniziate qui](docs/start_here.md) o
> il [manuale completo](https://mcp-tool-shop-org.github.io/sovereignty/handbook/).

> _Un breve GIF o screenshot di esempio dovrebbe essere inserito qui — da tracciare come un follow-up della Fase D
> in modo che il file README possa mostrare come appare effettivamente un turno._

## Giocate senza la console

Stampate le carte, prendete un dado e delle monete, sedetevi con 2-4 persone.
Il gioco funziona completamente al tavolo.

**[Iniziate qui](docs/start_here.md)** | **[Print & Play](docs/print-and-play.md)** | **[Regole complete](docs/rules/campfire_v1.md)** | **[Giocate con sconosciuti](docs/play-with-strangers.md)**

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

La console tiene il punteggio. Voi mantenete la parola data.

## Come funziona

Iniziate con **5 monete** e **3 di reputazione**. Lanciate un dado, muovetevi
attorno a un tabellone di 16 caselle e atterrate su caselle che vi offrono delle scelte: scambiare, aiutare
qualcuno, correre un rischio o pescare una carta.

**28 carte evento** che raccontano dei momenti: *"Qualcuno ha visto una piccola sacchetta di cuoio?"* (Portafoglio smarrito) o *"Nessuno l'ha vista... vero?"* (Trovata una scorciatoia).
Include 8 eventi di cambiamento del mercato per le partite al Municipio.

**22 carte affare e voucher** che stimolano la conversazione: *"Mi presti 2 monete? Ti restituisco 3."* o *"Ti copro se tu mi copri."* Le offerte stabiliscono degli obiettivi con delle scadenze; i voucher sono delle promesse che fate agli altri giocatori.

**La regola della promessa:** Una volta per turno, dite ad alta voce "Prometto..." e
fate una promessa. Mantenetela: +1 reputazione. Non rispettatela: -2 reputazione.
Il tavolo decide.

**Le scuse:** Una volta per partita, se avete rotto una promessa, scusatevi pubblicamente.
Pagate 1 moneta a chi avete offeso e recuperate +1 reputazione.

**Scegliete il vostro obiettivo** (segreto o pubblico):
- **Prosperità** — raggiungete 20 monete
- **Amato** — raggiungete 10 di reputazione
- **Costruttore** — completate 4 aggiornamenti

Dopo 15 turni, vince chi ha il punteggio combinato più alto.

## Cos'è la modalità diario?

Ogni turno, la console può generare una **prova** — un'impronta digitale dello
stato del gioco. Se qualcuno modifica il punteggio, l'impronta digitale non corrisponderà.

Opzionalmente, quell'impronta digitale può essere pubblicata sulla **XRPL Testnet** — un
registro pubblico. Pensateci come a scrivere il punteggio su un muro che nessuno
può cancellare.

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

È necessario solo un portafoglio per l'host. Nessuno tocca uno schermo. Il gioco
funziona perfettamente senza registrazione — è solo il diario che ricorda.

## Tre livelli

| Livello | Nome | Stato | Cosa aggiunge |
|------|------|--------|-------------|
| 1 | **Campfire** | Giocabile | Monete, reputazione, promesse, cambiali |
| 2 | **Town Hall** | Giocabile | Mercato condiviso, scarsità di risorse |
| 3 | **Treaty Table** | Giocabile | Trattati con implicazioni – promesse vincolanti |

Le regole fondamentali sono stabili dalla versione 1.x. Consultare la [roadmap](docs/roadmap.md).

## Pacchetti di scenari

Nessuna nuova regola. Solo atmosfera. Ogni pacchetto definisce un livello, una ricetta e un'atmosfera.

| Scenario | Livello | Ideale per |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | Falò / Giorno di mercato | Prima partita, gruppi misti |
| [Market Panic](docs/scenarios/market-panic.md) | Municipio | Drammi economici |
| [Promises Matter](docs/scenarios/promises-matter.md) | Falò | Fiducia e impegno |
| [Treaty Night](docs/scenarios/treaty-night.md) | Tavolo dei trattati | Accordi con implicazioni importanti |

Utilizzare il comando `sov scenario list` per visualizzare le opzioni dalla console.

## Struttura del progetto

```
sovereignty/
  sov_engine/       # Pure game logic (models, rules, serialization, hashing)
  sov_transport/    # Ledger transport (offline + XRPL Testnet)
  sov_cli/          # Typer CLI (the "Round Console")
  tests/            # Engine, transport, and CLI tests
  docs/             # Rules, cards, print-and-play, play-with-strangers
  assets/print/     # Printable cards, player mat, quick reference
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

> "Insegnare attraverso le conseguenze, non attraverso la terminologia."

I giocatori imparano facendo: emettendo cambiali, infrangendo promesse, commerciando a prezzi variabili. I concetti si riferiscono ai componenti fondamentali di Web3 (portafogli, token, linee di credito), ma i giocatori non devono conoscerli per divertirsi.

## Contributi

Il modo più semplice per contribuire è [aggiungere una carta](CONTRIBUTING.md).
Non è necessaria alcuna conoscenza del motore di gioco: basta un nome, una descrizione e un breve testo descrittivo.

## Sicurezza

Seed dei portafogli, stato del gioco e file di prova: cosa condividere e cosa no.
Nessuna telemetria, nessuna analisi, nessuna trasmissione di dati. L'unica chiamata di rete opzionale è l'ancoraggio alla rete di test XRPL.

Consultare [SECURITY.md](SECURITY.md).

## Modello delle minacce

| Minaccia | Mitigazione |
|--------|-----------|
| Fuga del seed tramite le prove | Le prove contengono solo hash, mai il seed |
| Seed in git | La cartella `.sov/` è ignorata da git; il comando `sov wallet` avvisa |
| Manipolazione dello stato del gioco | Le prove di ogni round contengono l'hash `envelope_hash` che include `game_id`, `round`, `ruleset`, `rng_seed`, `timestamp_utc`, `players` e `state`. Il comando `sov verify` rileva eventuali manomissioni all'interno dell'intero pacchetto. Il formato della prova versione 1 non è più supportato dalla versione 2.0.0. |
| Falsificazione dell'ancora XRPL | L'hash della prova è ancorato sulla blockchain; il controllo di coerenza avviene durante la verifica. |
| Privacy dei nomi dei giocatori | I nomi dei giocatori SONO inclusi nelle prove (elenco principale `players` e all'interno degli snapshot dei giocatori). Per il gioco in privato, non pubblicare `proof.json` né condividere le "cartoline". |

## Licenza

MIT

---

Creato da [MCP Tool Shop](https://mcp-tool-shop.github.io/)
