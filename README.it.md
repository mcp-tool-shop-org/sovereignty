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
  <a href="https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://mcp-tool-shop-org.github.io/sovereignty/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

## Gioca stasera

Stampa le carte, prendi un dado e delle monete, siediti con 2-4 persone.
Non sono necessari schermi. Richiede circa 30 minuti.

**[Inizia qui](docs/start_here.md)** | **[Stampa e gioca](docs/print-and-play.md)** | **[Regole complete](docs/rules/campfire_v1.md)** | **[Gioca con sconosciuti](docs/play-with-strangers.md)**

## Oppure usa la console

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

La console tiene traccia del punteggio. Tu mantieni la parola data.

## Come funziona

Inizi con **5 monete** e **3 punti reputazione**. Lancia il dado, muoviti
attorno a un tabellone di 16 caselle e atterra su caselle che ti offrono delle scelte: scambiare, aiutare
qualcuno, correre un rischio o pescare una carta.

**20 carte evento** che raccontano momenti: *"Qualcuno ha visto una piccola sacchetta di pelle?"* (Portafoglio smarrito) o *"Nessuno l'ha vista... vero?"* (Trovato un'scorciatoia).

**20 carte scambio** che stimolano la conversazione: *"Mi presti 2 monete? Te ne restituirò 3."*
o *"Ti copro se tu copri me."*

**La regola della promessa:** Una volta per partita, pronuncia ad alta voce "Prometto..." e
impegnati in qualcosa. Mantieni la promessa: +1 punto reputazione. Rompi la promessa: -2 punti reputazione.
Il tavolo decide.

**Le scuse:** Una volta per partita, se hai rotto una promessa, scusati pubblicamente.
Paga 1 moneta alla persona che hai danneggiato e recupera +1 punto reputazione.

**Scegli il tuo obiettivo** (segreto o pubblico):
- **Prosperità** — raggiungi 20 monete
- **Amato** — raggiungi 10 punti reputazione
- **Costruttore** — completa 4 miglioramenti

Dopo 15 turni, vince chi ha il punteggio combinato più alto.

## Cos'è la modalità diario?

Ogni turno, la console può generare una **prova** — un'impronta digitale dello
stato del gioco. Se qualcuno modifica il punteggio, l'impronta non corrisponderà.

Facoltativamente, questa impronta può essere pubblicata sulla **XRPL Testnet** — un
registro pubblico. Immaginala come scrivere il punteggio su un muro che nessuno
può cancellare.

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

Solo l'host ha bisogno di un portafoglio. Nessun altro tocca uno schermo. Il gioco
funziona perfettamente senza la necessità di un'ancora — è solo il diario che ricorda.

## Tre livelli

| Livello | Nome | Stato | Cosa aggiunge |
|------|------|--------|-------------|
| 1 | **Campfire** | Giocabile | Monete, reputazione, promesse, IOUs |
| 2 | **Town Hall** | Giocabile | Mercato condiviso, scarsità di risorse |
| 3 | **Treaty Table** | Giocabile | Trattati con conseguenze — promesse con valore |

Le regole principali sono stabili nella versione 1.x. Consulta la [roadmap](docs/roadmap.md).

## Pacchetti di scenari

Nessuna nuova regola. Solo atmosfera. Ogni pacchetto imposta un livello, una ricetta e un'atmosfera.

| Scenario | Livello | Ideale per |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | Falò / Festa di paese | Prima partita, gruppi misti |
| [Market Panic](docs/scenarios/market-panic.md) | Assemblea cittadina | Drammi economici |
| [Promises Matter](docs/scenarios/promises-matter.md) | Falò | Fiducia e impegno |
| [Treaty Night](docs/scenarios/treaty-night.md) | Tavolo dei trattati | Accordi ad alto rischio |

Usa il comando `sov scenario list` dalla console per sfogliare.

## Struttura del progetto

```
sovereignty/
  sov_engine/       # Pure game logic (models, rules, serialization, hashing)
  sov_transport/    # Ledger transport (offline + XRPL Testnet)
  sov_cli/          # Typer CLI (the "Round Console")
  tests/            # 143 tests
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

> "Insegna attraverso le conseguenze, non attraverso la terminologia."

I giocatori imparano facendo: emettendo IOUs, rompendo promesse, scambiando a
prezzi variabili. I concetti si collegano ai principi di Web3 — portafogli, token,
linee di credito — ma i giocatori non devono conoscerli per divertirsi.

## Come contribuire

Il modo più semplice per contribuire è [aggiungere una carta](CONTRIBUTING.md).
Non è necessaria alcuna conoscenza del motore — basta un nome, una descrizione e un po' di testo descrittivo.

## Sicurezza

Seed dei portafogli, stato del gioco e file di prova — cosa condividere e cosa no.
Nessuna telemetria, nessuna analisi, nessun "telefono a casa". L'unica chiamata di rete facoltativa è l'ancoraggio su XRPL Testnet.

Consulta [SECURITY.md](SECURITY.md).

## Modello di minaccia

| Minaccia | Mitigazione |
|--------|-----------|
| Fuga di "seed" tramite prove | Le prove contengono solo hash, mai "seed". |
| "Seed" in Git | La cartella `.sov/` è ignorata da Git; il comando `sov wallet` avvisa. |
| Manipolazione dello stato del gioco | Le prove contengono l'hash dello stato completo; `sov verify` rileva eventuali manomissioni. |
| Falsificazione degli anchor di XRPL | L'hash della prova è ancorato sulla blockchain; `sov verify` rileva eventuali discrepanze. |
| Privacy dei nomi dei giocatori | Lo stato del gioco è locale; le prove non includono i nomi. |

## Licenza

MIT

---

Creato da [MCP Tool Shop](https://mcp-tool-shop.github.io/)
