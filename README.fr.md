<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.md">English</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

```french
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

## Jouez ce soir

Imprimez [l'ensemble du jeu prêt à jouer](assets/print/pdf/Sovereignty-Print-Pack.pdf) : plateau de jeu, feuilles de joueur, guide rapide et trois paquets de cartes sur 11 feuilles de papier au format US Letter. Trouvez un dé et quelques pièces. Asseyez-vous avec deux ou trois amis. Vous serez en train de jouer dans vingt minutes.

Si vous souhaitez imprimer les feuilles individuellement :

- **[Plateau de jeu](assets/print/pdf/board.pdf)** — le circuit de 16 cases "Campfire", une page.
- **[Feuille de joueur](assets/print/pdf/mat.pdf)** — pièces, réputation, améliorations, promesses. Une par joueur.
- **[Guide rapide](assets/print/pdf/quickref.pdf)** — cases du plateau, ordre des tours, règles des promesses.
- **[Cartes d'événements](assets/print/pdf/events.pdf)** — 20 cartes, trois pages, découpez le long des lignes.
- **[Cartes de contrats](assets/print/pdf/deals.pdf)** — 10 cartes, deux pages.
- **[Cartes de bons d'achat](assets/print/pdf/vouchers.pdf)** — 10 "IOU" entre les joueurs, deux pages.
- **[Guide rapide des traités](assets/print/pdf/treaty.pdf)** — Niveau 3 uniquement.

Les fichiers PDF sont au format vectoriel avec des polices intégrées : ils s'impriment parfaitement sur n'importe quelle imprimante domestique. Le guide d'installation se trouve à [Print & Play](docs/print-and-play.md).

## Vous voulez une interface pour suivre les scores ?

Facultatif. Le jeu fonctionne très bien sur papier. Mais si quelqu'un a un ordinateur portable à portée de main, `sov` permet de suivre les pièces, la réputation, les promesses et génère un reçu infalsifiable à la fin :

```bash
pip install sovereignty-game
sov play campfire_v1
```

`sov play campfire_v1` est le démarrage rapide sans configuration : un joueur humain plus un adversaire par défaut. Pour jouer à plusieurs autour de la table, utilisez `sov new -p Alice -p Bob -p Carol`. Pour un tutoriel guidé de 60 secondes, utilisez `sov tutorial`.

Pas de Python ? La commande `npx` télécharge un exécutable précompilé :

```bash
npx @mcptoolshop/sovereignty tutorial
```

## Une vraie partie

Une fois que vous et 2 à 3 amis êtes assis autour de la table, la console gère le tour et vous vous occupez de la partie. Une vraie partie ressemble à ceci :

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

`sov status` affiche un tableau formaté avec les pièces, la réputation, les améliorations, la position et l'objectif de chaque joueur. Pour un aperçu rapide entre les tours :

```bash
sov status --brief
```

```
R3 |  Alice: 7c 4r 0u | >Bob: 4c 3r 0u |  Carol: 6c 5r 0u
```

(`Nc Nr Nu` = pièces / réputation / améliorations ; `>` indique le joueur actif.)

Répétez l'opération pendant 15 tours. `sov game-end` affiche les scores finaux.

- **Plusieurs parties sauvegardées** (v2.1+) : `sov games` liste les sauvegardes ; `sov resume <game-id>` permet de basculer entre elles.
- **Ancrage groupé** (v2.1+) : `sov anchor` à la fin de la partie regroupe tous les tours en attente dans une seule transaction XRPL : un seul pointeur de chaîne vérifiable par partie. Utilisez `sov anchor --checkpoint` pour une mise à jour intermédiaire.
- **Sélection du réseau** (v2.1+) : `sov anchor --network testnet|mainnet|devnet` (ou la variable d'environnement `SOV_XRPL_NETWORK` ; par défaut `testnet`).
- **Mode démon** (v2.1+, facultatif) : `sov daemon start` lance un serveur HTTP/JSON local pour l'intégration avec le bureau et la surveillance de la chaîne en arrière-plan. Voir [Mode démon](#daemon-mode-optional-v21) ci-dessous.
- **Application de bureau Audit Viewer** (v2.1+, facultatif) : `npm --prefix app run tauri dev`. Voir [Application de bureau](#desktop-app-optional-v21) ci-dessous.

> Voulez-vous un tutoriel guidé dans l'application ? Exécutez `sov tutorial`.
> Voulez-vous une présentation plus approfondie des règles ? Consultez [Commencez ici](docs/start_here.md) ou
> le [guide complet](https://mcp-tool-shop-org.github.io/sovereignty/handbook/).

L'exemple de `sov turn` ci-dessus montre à quoi ressemble un tour dans la console ; pour la visualisation sur le bureau de la version 2.1, voir [Application de bureau](#desktop-app-optional-v21) ci-dessous.
```

**[Commencer ici](docs/start_here.md)** | **[Imprimable](docs/print-and-play.md)** | **[Règles complètes](docs/rules/campfire_v1.md)** | **[Jouer avec des inconnus](docs/play-with-strangers.md)**

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

La console enregistre les scores. Vous respectez votre parole.

## Mode démon (optionnel, v2.1+)

Pour l'intégration au bureau (Audit Viewer, shell Tauri) ou pour la surveillance en arrière-plan de la chaîne de blocs, exécutez sovereignty en tant que démon HTTP local :

```bash
pip install 'sovereignty-game[daemon]'
sov daemon start --readonly        # audit-only, no wallet seed
sov daemon start                   # full daemon with anchor endpoints (loads XRPL_SEED)
sov daemon status                  # running | stale | none
sov daemon stop
```

Le démon se connecte à `127.0.0.1` sur un port aléatoire ; les détails de la connexion (port + jeton d'authentification) se trouvent dans `.sov/daemon.json`. Un seul démon par répertoire de projet. Consultez [docs/v2.1-daemon-ipc.md](docs/v2.1-daemon-ipc.md) pour le contrat IPC complet.

## Application de bureau (optionnelle, v2.1+)

L'Audit Viewer est l'application de bureau v2.1 : un shell Tauri (Rust + webview) qui exécute le visualiseur d'audit et une vue de jeu en lecture seule, au-dessus du démon.

### Installation (binaires)

La version 2.1.0 est livrée avec des binaires précompilés sur la [page des versions GitHub](https://github.com/mcp-tool-shop-org/sovereignty/releases/latest) :

- **macOS (universel) :** `sovereignty-app-2.1.0-darwin-universal.dmg` — Intel + Apple Silicon
- **Windows (x64) :** `sovereignty-app-2.1.0-win-x64.msi`
- **Linux (x64, .deb) :** `sovereignty-app-2.1.0-linux-x64.deb` — Debian / Ubuntu / dérivés. Installez avec `sudo dpkg -i sovereignty-app-2.1.0-linux-x64.deb`. Le support AppImage est reporté à la version 2.2 (interaction `linuxdeploy` / Ubuntu 24.04 FUSE en amont).

Vous avez également besoin du démon Python qui prend en charge l'application : `pip install 'sovereignty-game[daemon]'==2.1.0`.

> **Un avertissement lors du premier lancement est attendu.** macOS affichera "développeur non identifié" : cliquez avec le bouton droit sur le fichier .app, choisissez Ouvrir, puis confirmez. Windows SmartScreen affichera "éditeur non reconnu" : cliquez sur "Plus d'informations", puis sur "Exécuter quand même". Ces deux avertissements indiquent que la version 2.1 est livrée avec une attestation de provenance de la construction uniquement (vérifiez avec `gh attestation verify`), et non avec une signature de code au niveau du système d'exploitation. L'infrastructure de signature au niveau de l'espace de travail est disponible dans la version 2.2.

### Vérifier la provenance

Chaque artefact de version contient une attestation de provenance de construction SLSA. Vérifiez avant de l'exécuter :

```bash
gh attestation verify \
  --repo mcp-tool-shop-org/sovereignty \
  ./sovereignty-app-2.1.0-darwin-universal.dmg
```

Une vérification réussie prouve que le binaire a été créé à partir d'un commit spécifique, par le processus de publication, dans ce dépôt. C'est un niveau de confiance différent de la signature de code au niveau du système d'exploitation : le binaire déclenche toujours l'avertissement du système d'exploitation, mais sa provenance de la chaîne d'approvisionnement est cryptographiquement vérifiée.

### Exécuter à partir du code source

Si vous préférez compiler à partir du code source (ou si le binaire ne s'exécute pas sur votre plateforme) :

```bash
# 1. Install Python + daemon deps
pip install -e '.[xrpl,daemon]'

# 2. Install frontend + Rust deps (one-time)
cd app && npm install && cd ..
cargo build --manifest-path app/src-tauri/Cargo.toml

# 3. Start the dev shell (auto-starts the daemon in readonly mode)
npm --prefix app run tauri dev
```

Le shell Tauri démarre automatiquement un démon en lecture seule au lancement et l'arrête automatiquement à la fermeture. Les démons démarrés manuellement (`sov daemon start`) restent actifs même après les redémarrages du shell.

Consultez [docs/v2.1-tauri-shell.md](docs/v2.1-tauri-shell.md) pour le contrat complet.

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

L'Audit Viewer est fourni avec trois vues :

- **`/audit`** — Visualiseur de preuve ancré à XRPL. Liste des jeux, état de l'ancre par tour, "Vérifier tous les tours" effectue un recalcul local de la preuve + une recherche dans la chaîne de blocs. La vue de l'auditeur : confirmer qu'un jeu s'est déroulé honnêtement sans lire le JSON brut.
- **`/game`** — Affichage en temps réel passif de l'état du jeu actif. Cartes de ressources des joueurs, chronologie des tours, journal des 20 derniers événements SSE. En lecture seule ; jouez dans l'interface en ligne de commande dans un autre terminal.
- **`/settings`** — Affichage de la configuration du démon + commutateur réseau (testnet / mainnet / devnet) avec une protection pour la confirmation du mainnet.

Spécifications complètes de la vue à [docs/v2.1-views.md](docs/v2.1-views.md).

## Comment ça marche

Vous commencez avec **5 pièces** et **3 réputations**. Lancez un dé, déplacez-vous sur un plateau de 16 cases et atterrissez sur des cases qui vous offrent des choix : échanger, aider quelqu'un, prendre un risque ou tirer une carte.

**20 cartes d'événements** qui ressemblent à des moments : *"Est-ce que quelqu'un a vu un petit sac en cuir ?"* (Portefeuille perdu) ou *"Personne n'a rien vu... n'est-ce pas ?"* (Un raccourci trouvé). Inclut des événements de fluctuation du marché pour les jeux de type "Town Hall".

**10 cartes de transaction + 10 cartes de chèque** qui encouragent la conversation : *"Tu me avances 2 pièces ? Je te rembourse 3."* ou *"Je te couvre si tu me couvres."*. Les transactions fixent des objectifs avec des délais ; les chèques sont des promesses que vous faites à d'autres joueurs.

**La règle de la promesse :** Une fois par tour, dites à voix haute "Je promets..." et engagez-vous sur quelque chose. Si vous respectez votre promesse : +1 de réputation. Si vous la rompez : -2 de réputation. Le groupe décide.

**Les excuses :** Une fois par partie, si vous avez rompu une promesse, présentez publiquement vos excuses. Payez 1 pièce à la personne que vous avez lésée et regagnez +1 de réputation.

**Choisissez votre objectif** (secret ou public) :
- **Prosperité** — atteindre 20 pièces
- **Bien-aimé** — atteindre 10 de réputation
- **Constructeur** — compléter 4 améliorations

Après 15 tours, le joueur avec le score combiné le plus élevé gagne.

## Qu'est-ce que le mode "Journal" ?

Chaque tour, la console peut générer une **preuve** — une empreinte de l'état du jeu. Si quelqu'un modifie le score, l'empreinte ne correspondra pas.

Facultativement, cette empreinte peut être publiée sur le **Testnet XRPL** — un registre public. Considérez cela comme écrire le score sur un mur que personne ne peut effacer.

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

Seul l'hôte a besoin d'un portefeuille. Personne d'autre n'interagit avec un écran. Le jeu fonctionne parfaitement sans ancrage ; c'est simplement le "journal" qui se souvient.

## Trois niveaux

| Niveau | Nom | Statut | Ce qu'il ajoute |
|------|------|--------|-------------|
| 1 | **Campfire** | Jouable | Pièces, réputation, promesses, chèques |
| 2 | **Town Hall** | Jouable | Marché partagé, rareté des ressources |
| 3 | **Treaty Table** | Jouable | Traités avec des enjeux — promesses avec des garanties |

Les règles de base sont stables dans la version 1.x. Consultez la [feuille de route](docs/roadmap.md).

## Packs de scénarios

Aucune nouvelle règle. Juste l'ambiance. Chaque pack définit un niveau, une recette et une ambiance.

| Scénario | Niveau | Idéal pour |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | Coin de feu / Journée au marché | Première partie, groupes mixtes |
| [Market Panic](docs/scenarios/market-panic.md) | Town Hall | Drame économique |
| [Promises Matter](docs/scenarios/promises-matter.md) | Coin de feu | Confiance et engagement |
| [Treaty Night](docs/scenarios/treaty-night.md) | Table des traités | Accords à enjeux élevés |

Utilisez `sov scenario list` pour parcourir les options depuis la console.

## Structure du projet

```
sovereignty/
  sov_engine/       # Pure game logic (models, rules, serialization, hashing)
  sov_transport/    # Ledger transport (offline + XRPL Testnet)
  sov_cli/          # Typer CLI (the "Round Console")
  tests/            # Engine, transport, and CLI tests
  docs/             # Rules, cards, print-and-play, play-with-strangers
  assets/print/     # Print pack — markdown sources, rendered PDFs, JSX render sources
```

## Développement

```bash
git clone https://github.com/mcp-tool-shop-org/sovereignty.git
cd sovereignty
uv sync --dev
uv run pytest tests/ -v
uv run ruff check .
```

## Principe de conception

> "Apprendre par les conséquences, pas par la terminologie."

Les joueurs apprennent en faisant : en émettant des chèques, en rompant des promesses, en échangeant à des prix fluctuants. Les concepts correspondent aux primitives Web3 — portefeuilles, jetons, lignes de confiance — mais les joueurs n'ont pas besoin de le savoir pour s'amuser.

## Contribution

La façon la plus simple de contribuer est d'[ajouter une carte](CONTRIBUTING.md). Aucune connaissance du moteur n'est nécessaire — juste un nom, une description et un texte descriptif.

## Sécurité

Clés de portefeuille, état du jeu et fichiers de preuve — ce qu'il faut partager et ce qu'il ne faut pas. Pas de télémétrie, pas d'analyse, pas de "retour à la maison". L'unique appel réseau facultatif est l'ancrage sur le Testnet XRPL.

Consultez [SECURITY.md](SECURITY.md).

## Modèle de menace

| Menace | Atténuation |
|--------|-----------|
| Fuite de la clé de portefeuille via les preuves | Les preuves contiennent uniquement des hachages, jamais de clés. |
| Clé de portefeuille dans Git | `.sov/` est ignoré par Git ; `sov wallet` avertit. |
| Manipulation de l'état du jeu | Les preuves de chaque tour, le `envelope_hash`, couvre l'`game_id`, le `round`, le `ruleset`, le `rng_seed`, le `timestamp_utc`, les `players` et l'`state`. `sov verify` détecte toute modification sur l'ensemble de l'enveloppe. Le format de preuve v1 n'est plus pris en charge dans la version 2.0.0+. |
| Falsification de l'ancrage XRPL. | La somme de contrôle (hash) est ancrée sur la chaîne de blocs ; détection des incohérences lors de la vérification. |
| Confidentialité des noms de joueurs. | Les noms de joueurs sont inclus dans les preuves (liste `players` de niveau supérieur et dans les instantanés des joueurs). Pour une partie privée, ne publiez pas le fichier `proof.json` et ne partagez pas les cartes postales. |

## Licence

MIT

---

Développé par [MCP Tool Shop](https://mcp-tool-shop.github.io/)
