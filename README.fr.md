<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.md">English</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

## Jouez ce soir

Imprimez [l’ensemble complet pour imprimer et jouer](assets/print/pdf/Sovereignty-Print-Pack.pdf) : le plateau, les tapis de joueur, la fiche de référence rapide, le tableau du marché et trois jeux de cartes sur 13 feuilles de papier au format US Letter. Trouvez un dé et quelques pièces de monnaie. Asseyez-vous avec deux ou trois amis. Vous pourrez commencer à jouer dans vingt minutes.

Si vous souhaitez des feuilles individuelles :

- **[Plateau](assets/print/pdf/board.pdf)** : la boucle du campement avec 16 cases, une page.
- **[Tapis de joueur](assets/print/pdf/mat.pdf)** : pièces de monnaie, réputation, améliorations, promesses. Un par joueur.
- **[Fiche de référence rapide](assets/print/pdf/quickref.pdf)** : cases du plateau, ordre de tour, règles des promesses.
- **[Cartes d’événements](assets/print/pdf/events.pdf)** : 28 cartes, quatre pages, à découper le long des lignes.
- **[Cartes d’échange](assets/print/pdf/deals.pdf)** : 12 cartes, deux pages.
- **[Cartes de bons](assets/print/pdf/vouchers.pdf)** : 10 promesses entre les joueurs, deux pages.
- **[Tableau du marché](assets/print/pdf/market.pdf)** : Jour du marché / Hôtel de ville, une page.
- **[Fiche de référence rapide du traité](assets/print/pdf/treaty.pdf)** : uniquement pour le niveau 3.

Les fichiers PDF sont vectoriels et contiennent des polices intégrées ; ils s’impriment parfaitement sur n’importe quelle imprimante domestique. Le guide d’installation est disponible à l’adresse [Print & Play](docs/print-and-play.md).

## Souhaitez-vous une console pour enregistrer les scores ?

Facultatif. Le jeu fonctionne bien sur papier. Mais si quelqu’un a un ordinateur portable à portée de main, `sov` suit les pièces de monnaie, la réputation, les promesses et génère un reçu inviolable à la fin :

```bash
pip install sovereignty-game
sov play campfire_v1
```

`sov play campfire_v1` est le démarrage rapide sans configuration : un joueur plus un adversaire par défaut. Pour une partie à plusieurs joueurs, utilisez `sov new -p Alice -p Bob -p Carol`. Pour un guide étape par étape de 60 secondes, utilisez `sov tutorial`.

Pas de Python ? Le chemin `npx` télécharge un binaire précompilé :

```bash
npx @mcptoolshop/sovereignty tutorial
```

Ou exécutez-le dans Docker, en conservant vos données dans un volume nommé :

```bash
docker run --rm -it -v sov-data:/data ghcr.io/mcp-tool-shop-org/sovereignty tutorial
```

## Une vraie partie

Une fois que vous et 2 à 3 amis êtes assis à la table, la console gère le tour et vous vous chargez de la conversation. Une vraie partie ressemble à ceci :

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

`sov status` affiche un tableau formaté avec les pièces de monnaie, la réputation, les améliorations, la position et l’objectif de chaque joueur. Pour un aperçu rapide en une seule ligne entre les tours :

```bash
sov status --brief
```

```
R3 |  Alice: 7c 4r 0u | >Bob: 4c 3r 0u |  Carol: 6c 5r 0u
```

(`Nc Nr Nu` = pièces de monnaie / réputation / améliorations ; `>` indique le joueur actif.)

Répétez l’opération pendant 15 tours. `sov game-end` affiche les scores finaux.

- **Plusieurs parties enregistrées** (v2.1+) : `sov games` affiche la liste des parties enregistrées ; `sov resume <game-id>` permet de passer de l’une à l’autre.
- **Ancrage par lots** (v2.1+) : `sov anchor`, à la fin de la partie, regroupe les tours en attente dans une petite constante de transactions XRPL AccountSet (≤ 8 mémos par transaction ; une partie typique de Campfire de 16 tours → 2 transactions) ; il ne s’agit pas d’une seule transaction / d’un seul pointeur de chaîne. Utilisez `sov anchor --checkpoint` pour un regroupement en cours de partie.
- **Sélection du réseau** (v2.1+) : `sov anchor --network testnet|mainnet|devnet` (ou variable d’environnement `SOV_XRPL_NETWORK` ; par défaut `testnet`).
- **Mode démon** (v2.1+, facultatif) : `sov daemon start` exécute un serveur HTTP/JSON sur localhost pour l’intégration avec le bureau et la surveillance de la chaîne en arrière-plan. Voir [Mode démon](#mode-démon-facultatif-v21) ci-dessous.
- **Application de bureau Audit Viewer** (v2.1+, facultatif) : `npm --prefix app run tauri dev`. Voir [Application de bureau](#application-de-bureau-facultatif-v21) ci-dessous.

> Souhaitez-vous d’abord un guide intégré à l’application ? Exécutez `sov tutorial`.
> Souhaitez-vous une présentation plus approfondie des règles ? Consultez [Commencer ici](docs/start_here.md) ou
> le [manuel complet](https://mcp-tool-shop-org.github.io/sovereignty/handbook/).

L’exemple `sov turn` intégré ci-dessus montre à quoi ressemble un tour dans la console ; pour la visualisation de bureau v2.1, consultez [Application de bureau](#application-de-bureau-facultatif-v21) ci-dessous.

**[Commencer ici](docs/start_here.md)** | **[Imprimer et jouer](docs/print-and-play.md)** | **[Règles complètes](docs/rules/campfire_v1.md)** | **[Jouer avec des inconnus](docs/play-with-strangers.md)**

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
sov anchor --reanchor                # after a test network reset: anchor lost rounds again (v2.4+)
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

La console enregistre les scores. Vous tenez vos promesses.

## Mode démon (facultatif, v2.1+)

Pour l’intégration avec le bureau (Audit Viewer, shell Tauri) ou la surveillance de la chaîne en arrière-plan, exécutez sovereignty en tant que démon HTTP sur localhost :

```bash
pip install 'sovereignty-game[daemon]'
sov daemon start --readonly        # audit-only, no wallet seed
sov daemon start                   # full daemon with anchor endpoints (loads XRPL_SEED)
sov daemon status                  # running | stale | none
sov daemon stop
```

Le démon se lie à `127.0.0.1` sur un port aléatoire ; les détails de la connexion (port + jeton) sont disponibles dans `.sov/daemon.json`. Un démon par répertoire de projet. Consultez [docs/v2.1-daemon-ipc.md](docs/v2.1-daemon-ipc.md) pour l’ensemble du contrat IPC.

> Les éléments supplémentaires `[daemon]` nécessitent **la version 2.3.2 ou ultérieure**. Les versions jusqu’à 2.3.1 n’incluaient pas le package `sov_daemon`, ce qui a entraîné l’échec de `sov daemon start` lors de l’installation de PyPI.

## Docker (facultatif, v2.3.2+)

L’image à l’adresse `ghcr.io/mcp-tool-shop-org/sovereignty` contient la CLI `sov` et le démon, pour `linux/amd64` et `linux/arm64`. Tout ce dont le jeu a besoin pour se souvenir est stocké dans `/data/.sov` : parties, preuves de tour, `anchors.json`, le classement de la saison, la clé du portefeuille et la poignée de main du démon. Montez un volume sur `/data`, sinon le conteneur oubliera tout.

Exécutez le démon avec le [`compose.yaml`](compose.yaml) fourni :

```bash
docker compose up -d                  # readonly audit daemon on 127.0.0.1:47823
docker compose run --rm sov doctor    # any sov command, same saves
docker compose run --rm sov play campfire_v1
docker compose logs -f
```

Par défaut, le conteneur exécute un démon en **lecture seule** sur le **testnet**. Le port est publié uniquement sur la boucle locale de l’hôte (`127.0.0.1:47823`), et chaque requête nécessite toujours le jeton d’authentification de `.sov/daemon.json`.

| Paramètre | Valeur par défaut | Fonction |
|---|---|---|
| `SOV_DATA` | `sov-data` (volume nommé) | D’où provient `/data`. Définissez-le sur un dossier (`SOV_DATA=./`) pour conserver les parties enregistrées sur l’hôte. |
| `SOV_DAEMON_PORT` | `47823` | Port du démon, à l’intérieur et sur l’hôte. Les deux doivent correspondre. |
| `SOV_DAEMON_NETWORK` | `testnet` | `testnet`, `devnet` ou `mainnet`. |
| `SOV_DAEMON_READONLY` | `1` | `0` active les points de terminaison d’ancrage. |
| `SOV_DAEMON_TOKEN` | aléatoire au démarrage | Configurez-le pour que les clients restent connectés après les redémarrages. |
| `SOV_DAEMON_LOG_FORMAT` | `human` | `json` pour les lignes de journal structurées. |

**Attachez l’application de bureau.** Indiquez à `SOV_DATA` le dossier du projet que l’application ouvre. Le démon y écrit sa poignée de main, et l’application appelle `127.0.0.1:47823` avec le jeton qu’elle contient :

```bash
SOV_DATA=./ docker compose up -d
```

Bien que le conteneur héberge le démon, gérez-le avec `docker compose`, et non avec `sov daemon start|stop|status` sur l’hôte. La CLI de l’hôte ne peut pas voir le processus d’un conteneur, elle signale donc la poignée de main comme étant obsolète, et `sov daemon start` la supprimerait.

**Ancrez à partir du conteneur.** Créez un portefeuille testnet dans le volume, puis désactivez la lecture seule :

```bash
docker compose run --rm sov wallet
SOV_DAEMON_READONLY=0 docker compose up -d
```

Pour éviter de stocker la clé dans le volume, fournissez-la plutôt sous forme de secret Docker. Le bloc `secrets` commenté dans `compose.yaml` montre comment faire.

## Application de bureau (facultatif, v2.1+)

Audit Viewer est l’application de bureau v2.1 : un shell Tauri (Rust + webview) qui exécute l’audit viewer et une vue de jeu en lecture seule au-dessus du démon.

### Installation (binaires)

**v2.4.1** est la version actuelle. La version **v2.3.0** de GitHub n’a pas fourni de binaires ou d’éléments de bureau, ne fixez donc pas `pip install …==2.3.0`.

- **Python / daemon :** `pip install 'sovereignty-game[daemon]'` (version 2.3.2 ou ultérieure pour le daemon).
- **Application de bureau :** [la dernière version GitHub](https://github.com/mcp-tool-shop-org/sovereignty/releases/latest) lorsque CI a ajouté les fichiers de la plateforme. Si une tâche de la plateforme a échoué, exécutez à partir du code source (ci-dessous).

> **Un avertissement du système d’exploitation au premier lancement est attendu** lorsque des binaires certifiés sont fournis. Ces versions ne contiennent que l’attestation de provenance de la build SLSA, et non la signature Apple Developer ID / Authenticode au niveau du système d’exploitation. macOS : cliquez avec le bouton droit sur le fichier .app → Ouvrir. Windows SmartScreen : Plus d’informations → Exécuter de toute façon.

### Vérifier la provenance

Lorsque une version inclut effectivement des artefacts de bureau, vérifiez le fichier que vous avez téléchargé :

```bash
gh attestation verify \
  --repo mcp-tool-shop-org/sovereignty \
  ./<downloaded-artifact>
```

Une vérification réussie prouve que le binaire a été créé à partir d’un commit spécifique, par le processus de build de la version, dans ce dépôt. Il s’agit d’un niveau de confiance différent de la signature de code au niveau du système d’exploitation ; le binaire déclenche toujours l’avertissement du système d’exploitation, mais sa provenance de la chaîne d’approvisionnement est cryptographiquement ancrée.

### Exécuter à partir du code source

Si vous préférez créer à partir du code source (ou si le binaire ne s’exécute pas sur votre plateforme) :

```bash
# 1. Install Python + daemon deps
pip install -e '.[xrpl,daemon]'

# 2. Install frontend + Rust deps (one-time)
cd app && npm install && cd ..
cargo build --manifest-path app/src-tauri/Cargo.toml

# 3. Start the dev shell (auto-starts the daemon in readonly mode)
npm --prefix app run tauri dev
```

Le shell Tauri démarre automatiquement un daemon en lecture seule au lancement et l’arrête automatiquement à la fermeture. Les daemons démarrés en externe (`sov daemon start`) restent actifs lors des redémarrages du shell.

Consultez [docs/v2.1-tauri-shell.md](docs/v2.1-tauri-shell.md) pour connaître l’intégralité du contrat.

L’outil Audit Viewer est fourni avec trois vues :

- **`/audit`** — Visualiseur de preuves ancrées sur XRPL. Liste par jeu, par tour, avec l’état de l’ancre, « Vérifier toutes les tours » exécute localement le recalcul des preuves + la recherche dans la chaîne en série. La vue de l’auditeur : confirmer qu’un jeu s’est déroulé honnêtement sans lire le JSON brut.
- **`/game`** — Affichage passif de l’état en temps réel pour le jeu actif. Cartes des ressources des joueurs, chronologie des tours, journal des 20 derniers événements SSE. En lecture seule ; jouez dans la ligne de commande dans un autre terminal.
- **`/settings`** — Affichage de la configuration du daemon + commutateur de réseau (testnet / mainnet / devnet) avec protection de confirmation du mainnet.

Spécifications complètes de la vue à [docs/v2.1-views.md](docs/v2.1-views.md).

## Comment cela fonctionne

Vous commencez avec **5 pièces** et **3 points de réputation**. Lancez un dé, déplacez-vous sur un plateau de 16 cases et atterrissez sur des cases qui vous donnent des choix : échanger, aider quelqu’un, prendre un risque ou piocher une carte.

**28 cartes Événement** ressemblent à des moments : « Quelqu’un a-t-il vu une petite bourse en cuir ? » (Portefeuille perdu) ou « Personne n’a vu… n’est-ce pas ? » (Trouvé un raccourci). Inclut des événements de changement de marché pour les jeux Town Hall.

**12 cartes Accord + 10 cartes Bon** obligent à la conversation : « Vous me prêtez 2 pièces ? Je vous en rembourserai 3. » ou « Je vous soutiens si vous me soutenez. » Les accords fixent des objectifs avec des échéances ; les bons sont des reconnaissances de dette que vous émettez à d’autres joueurs.

**La règle de la promesse :** Une fois par tour, dites à voix haute « Je promets… » et engagez-vous sur quelque chose. Tenez-vous-y : +1 point de réputation. Ne vous y tenez pas : -2 points de réputation. C’est le groupe qui décide.

**Les excuses :** Une fois par partie, si vous avez rompu une promesse, présentez publiquement vos excuses. Payez 1 pièce à la personne que vous avez lésée et regagnez +1 point de réputation.

**Choisissez votre objectif** (secret ou public) :
- **Prospérité** — atteignez 20 pièces
- **Bien-aimé** — atteignez 10 points de réputation
- **Constructeur** — effectuez 4 améliorations

Après 15 tours, le joueur avec le score combiné le plus élevé gagne.

## Qu’est-ce que le mode Journal ?

À chaque tour, la console peut produire une **preuve** — une empreinte de l’état du jeu. Si quelqu’un modifie le score, l’empreinte ne correspondra pas.

Facultativement, cette empreinte peut être publiée sur le **XRPL Testnet** — un registre public. Considérez cela comme l’écriture du score sur un mur que personne ne peut effacer.

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

Seul l’hôte a besoin d’un portefeuille. Personne d’autre ne touche un écran. Le jeu fonctionne parfaitement sans ancrage ; c’est simplement le journal qui se souvient.

Le testnet et le devnet sont effacés de temps en temps (prochainement le 2026-11-25), et une ancre créée avant un effacement disparaît ensuite. `sov verify --tx` indique alors que l’ancre ne peut plus être vérifiée (code de sortie 3), et non qu’elle a réussi. Exécutez `sov wallet` et `sov anchor --reanchor` pour remettre les tours du jeu dans le registre. Consultez [le manuel](https://mcp-tool-shop-org.github.io/sovereignty/handbook/diary-mode/).

## Trois niveaux

| Niveau | Nom | État | Ce qu’il ajoute |
|------|------|--------|-------------|
| 1 | **Campfire** | Jouable | Pièces, réputation, promesses, reconnaissances de dette |
| 2 | **Town Hall** | Jouable | Marché partagé, rareté des ressources |
| 3 | **Treaty Table** | Jouable | Traités avec enjeux — promesses contraignantes |

Les règles de base sont stables jusqu’à v1.x. Consultez [la feuille de route](docs/roadmap.md).

## Packs de scénarios

Aucune nouvelle règle. Juste une ambiance. Chaque pack définit un niveau, une recette et une ambiance.

| Scénario | Niveau | Idéal pour |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | Feu de camp / Journée du marché | Première partie, groupes mixtes |
| [Market Panic](docs/scenarios/market-panic.md) | Hôtel de ville | Drame économique |
| [Promises Matter](docs/scenarios/promises-matter.md) | Feu de camp | Confiance et engagement |
| [Treaty Night](docs/scenarios/treaty-night.md) | Table des traités | Accords à enjeux élevés |

`sov scenario list` pour parcourir depuis la console.

## Structure du projet

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

## Développement

```bash
git clone https://github.com/mcp-tool-shop-org/sovereignty.git
cd sovereignty
uv sync --dev
uv run pytest tests/ -v
uv run ruff check .
```

## Principe de conception

> « Enseignez par les conséquences, et non par la terminologie. »

Les joueurs apprennent en faisant : en émettant des reconnaissances de dette, en rompant des promesses, en échangeant à des prix fluctuants. Les concepts correspondent aux primitives Web3 — portefeuilles, jetons, lignes de confiance — mais les joueurs n’ont pas besoin de le savoir pour s’amuser.

## Contribution

Le moyen le plus simple de contribuer est d’[ajouter une carte](CONTRIBUTING.md). Aucune connaissance du moteur n’est requise : il suffit d’un nom, d’une description et de quelques éléments de style.

## Sécurité

Clés de portefeuille, état du jeu et fichiers de preuve : ce qu’il faut partager et ce qu’il ne faut pas partager. Pas de télémétrie, pas d’analyses, pas de communication vers le domicile. La seule communication réseau facultative est l’ancrage sur le XRPL Testnet.

Consultez [SECURITY.md](SECURITY.md).

## Modèle de menace

| Menace | Atténuation |
|--------|-----------|
| Fuite de la clé du portefeuille via les preuves | Les preuves ne contiennent que des hachages, jamais de clés. |
| Initialisation dans Git | `.sov/` est ignoré par Git ; `sov wallet` affiche un avertissement |
| Manipulation de l’état du jeu | Les preuves de tour `envelope_hash` couvrent `game_id`, `round`, `ruleset`, `rng_seed`, `timestamp_utc`, `players` et `state`. `sov verify` détecte toute falsification dans l’ensemble des données. Le format de preuve v1 n’est plus pris en charge dans v2.0.0+. |
| Usurpation d’identité d’un point d’ancrage XRPL | Hachage de preuve ancré sur la chaîne ; détection de divergence lors de la vérification |
| Exposition du conteneur | L’image du démon est publiée uniquement sur l’hôte `127.0.0.1` ; jeton d’authentification requis pour chaque requête ; en lecture seule par défaut ; s’exécute en tant qu’utilisateur non root avec un système de fichiers racine en lecture seule et sans privilèges |
| Confidentialité du nom du joueur | Les noms des joueurs SONT inclus dans les preuves (liste de niveau supérieur `players` et dans les instantanés des joueurs). Pour une partie privée, ne publiez pas `proof.json` et ne partagez pas de cartes postales. |

## Licence

MIT

---

Créé par [MCP Tool Shop](https://mcp-tool-shop.github.io/)
