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
  <a href="https://pypi.org/project/sovereignty-game/"><img src="https://img.shields.io/pypi/v/sovereignty-game?include_prereleases&style=flat&cacheSeconds=3600" alt="PyPI version"></a>
  <a href="https://pypi.org/project/sovereignty-game/"><img src="https://img.shields.io/pypi/pyversions/sovereignty-game?style=flat&cacheSeconds=3600" alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat&cacheSeconds=86400" alt="License: MIT"></a>
  <a href="https://mcp-tool-shop-org.github.io/sovereignty/"><img src="https://img.shields.io/badge/Landing_Page-live-blue?style=flat&cacheSeconds=86400" alt="Landing Page"></a>
</p>

## Jouez ce soir

Imprimez [l’ensemble complet pour l’impression et le jeu](assets/print/pdf/Sovereignty-Print-Pack.pdf) : plateau, tapis de joueur, aide-mémoire et trois jeux de cartes sur 11 feuilles de papier au format US Letter. Trouvez un dé et quelques pièces. Asseyez-vous avec deux ou trois amis. Vous pourrez commencer à jouer dans vingt minutes.

Si vous souhaitez des feuilles individuelles :

- **[Plateau](assets/print/pdf/board.pdf)** : le plateau de jeu Campfire avec 16 cases, une page.
- **[Tapis de joueur](assets/print/pdf/mat.pdf)** : pièces, réputation, améliorations, promesses. Un par joueur.
- **[Aide-mémoire](assets/print/pdf/quickref.pdf)** : cases du plateau, ordre de tour, règles des promesses.
- **[Cartes d’événements](assets/print/pdf/events.pdf)** : 20 cartes, trois pages, à découper le long des lignes.
- **[Cartes d’échange](assets/print/pdf/deals.pdf)** : 10 cartes, deux pages.
- **[Cartes de caution](assets/print/pdf/vouchers.pdf)** : 10 reconnaissances de dette entre les joueurs, deux pages.
- **[Aide-mémoire sur le traité](assets/print/pdf/treaty.pdf)** : uniquement pour le niveau 3.

Les fichiers PDF sont vectoriels et contiennent des polices intégrées ; ils s’impriment parfaitement sur n’importe quelle imprimante domestique. Le guide d’installation est disponible à l’adresse [Print & Play](docs/print-and-play.md).

## Souhaitez-vous une console pour enregistrer les scores ?

Facultatif. Le jeu fonctionne parfaitement sur papier. Mais si quelqu’un a un ordinateur portable à portée de main, `sov` suit le nombre de pièces, la réputation, les promesses et génère un reçu inviolable à la fin :

```bash
pip install sovereignty-game
sov play campfire_v1
```

`sov play campfire_v1` est la version rapide sans configuration : une personne plus un adversaire par défaut. Pour jouer à plusieurs autour de la table, utilisez `sov new -p Alice -p Bob -p Carol`. Pour un guide étape par étape d’une minute, utilisez `sov tutorial`.

Pas de Python ? Le chemin `npx` télécharge un fichier binaire précompilé :

```bash
npx @mcptoolshop/sovereignty tutorial
```

## Une vraie partie

Une fois que vous et 2 à 3 amis êtes assis autour de la table, la console gère le tour et c’est à vous de parler. Une vraie partie se déroule comme suit :

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

`sov status` affiche un tableau formaté avec les pièces, la réputation, les améliorations, la position et l’objectif de chaque joueur. Pour un aperçu rapide en une seule ligne entre les tours :

```bash
sov status --brief
```

```
R3 |  Alice: 7c 4r 0u | >Bob: 4c 3r 0u |  Carol: 6c 5r 0u
```

(`Nc Nr Nu` = pièces / réputation / améliorations ; `>` indique le joueur actif.)

Répétez l’opération pendant 15 tours. `sov game-end` affiche les scores finaux.

- **Plusieurs parties sauvegardées** (v2.1 et versions ultérieures) : `sov games` liste les parties sauvegardées ; `sov resume <game-id>` permet de passer d’une partie à l’autre.
- **Ancrage par lots** (v2.1 et versions ultérieures) : `sov anchor`, à la fin de la partie, vide les tours en attente dans un petit nombre constant de transactions AccountSet XRPL (≤8 mémos chacune ; une partie Campfire typique de 16 tours → 2 txs) — pas une seule transaction / un seul pointeur de chaîne. Utilisez `sov anchor --checkpoint` pour un flush en cours de partie.
- **Sélection du réseau** (v2.1 et versions ultérieures) : `sov anchor --network testnet|mainnet|devnet` (ou variable d’environnement `SOV_XRPL_NETWORK` ; valeur par défaut : `testnet`).
- **Mode démon** (v2.1 et versions ultérieures, facultatif) : `sov daemon start` exécute un serveur HTTP/JSON sur localhost pour l’intégration avec le bureau et la surveillance de la chaîne en arrière-plan. Voir [Mode démon](#mode-demon-facultatif-v21) ci-dessous.
- **Application de bureau Audit Viewer** (v2.1 et versions ultérieures, facultative) : `npm --prefix app run tauri dev`. Voir [Application de bureau](#application-de-bureau-facultative-v21) ci-dessous.

> Souhaitez-vous d’abord suivre un guide intégré à l’application ? Exécutez `sov tutorial`.
> Souhaitez-vous en savoir plus sur les règles ? Consultez [Commencer ici](docs/start_here.md) ou le [manuel complet](https://mcp-tool-shop-org.github.io/sovereignty/handbook/).

L’exemple `sov turn` ci-dessus montre à quoi ressemble un tour dans la console ; pour la visualisation de bureau de la version 2.1, consultez [Application de bureau](#application-de-bureau-facultative-v21) ci-dessous.

**[Commencer ici](docs/start_here.md)** | **[Print & Play](docs/print-and-play.md)** | **[Règles complètes](docs/rules/campfire_v1.md)** | **[Jouer avec des inconnus](docs/play-with-strangers.md)**

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

La console enregistre les scores. Vous tenez vos promesses.

## Mode démon (facultatif, v2.1+)

Pour l’intégration avec le bureau (Audit Viewer, Tauri shell) ou la surveillance de la chaîne en arrière-plan, exécutez Sovereignty en tant que démon HTTP sur localhost :

```bash
pip install 'sovereignty-game[daemon]'
sov daemon start --readonly        # audit-only, no wallet seed
sov daemon start                   # full daemon with anchor endpoints (loads XRPL_SEED)
sov daemon status                  # running | stale | none
sov daemon stop
```

Le démon se lie à `127.0.0.1` sur un port aléatoire ; les détails de connexion (port + jeton d’authentification) sont disponibles dans `.sov/daemon.json`. Un seul démon par répertoire du projet. Consultez [docs/v2.1-daemon-ipc.md](docs/v2.1-daemon-ipc.md) pour connaître l’ensemble complet du contrat IPC.

## Application de bureau (facultative, v2.1+)

Audit Viewer est l’application de bureau v2.1 : un Tauri shell (Rust + webview) qui exécute la visionneuse d’audit et une vue de jeu en lecture seule au-dessus du démon.

### Installation (fichiers binaires)

La version 2.3.0 est étiquetée dans git mais **n’a publié ni roues PyPI ni binaires de bureau.** L’exécution 33118253060 de `publish.yml` a échoué : PyPI n’a pas de distribution 2.3.0, et GitHub Release v2.3.0 a des assets vides. Les noms `sovereignty-app-2.3.0-{darwin-universal.dmg,win-x64.msi,linux-x64.deb,linux-x64.AppImage}` renvoient 404. Ne pas épingler `pip install …==2.3.0`.

Jusqu’à ce qu’une étiquette suivante (2.3.1 ou un 2.3.x réparé) joigne des fichiers :

- **Python / démon :** `pip install 'sovereignty-game[daemon]'` (la ligne PyPI actuelle est **2.2.1** ; `pipx` / `npx @mcptoolshop/sovereignty` sans pin résolvent aussi vers 2.2.1).
- **Application de bureau :** exécutez depuis les sources (ci-dessous). N’utilisez pas [GitHub Releases latest](https://github.com/mcp-tool-shop-org/sovereignty/releases/latest) pour les binaires tant que cette page n’a pas de fichiers correspondants.

> **L’avertissement au premier lancement est normal** lorsque des binaires attestés seront réellement publiés. Ces builds portent uniquement une attestation SLSA de provenance — pas de signature Apple Developer ID / Authenticode. macOS : clic droit sur le .app → Ouvrir. Windows SmartScreen : Plus d’informations → Exécuter quand même.

### Vérifier la provenance

Lorsqu’une version joint réellement des artefacts de bureau, vérifiez le fichier téléchargé :

```bash
gh attestation verify \
  --repo mcp-tool-shop-org/sovereignty \
  ./<downloaded-artifact>
```

Une vérification réussie prouve que le fichier binaire a été créé à partir d’un commit spécifique, par le workflow de publication, dans ce dépôt. Il s’agit d’une couche de confiance différente de la signature de code au niveau du système d’exploitation ; le fichier binaire déclenche toujours l’avertissement du système d’exploitation, mais sa provenance de chaîne d’approvisionnement est cryptographiquement verrouillée.

### Exécuter à partir du code source

Si vous préférez créer le fichier à partir du code source (ou si le fichier binaire ne s’exécute pas sur votre plateforme) :

```bash
# 1. Install Python + daemon deps
pip install -e '.[xrpl,daemon]'

# 2. Install frontend + Rust deps (one-time)
cd app && npm install && cd ..
cargo build --manifest-path app/src-tauri/Cargo.toml

# 3. Start the dev shell (auto-starts the daemon in readonly mode)
npm --prefix app run tauri dev
```

Le Tauri shell démarre automatiquement un démon en lecture seule au lancement et l’arrête automatiquement à la fermeture. Les démons démarrés de manière externe (`sov daemon start`) restent actifs lors des redémarrages du shell.

Consultez [docs/v2.1-tauri-shell.md](docs/v2.1-tauri-shell.md) pour connaître l’ensemble complet du contrat.

Audit Viewer est livré avec trois vues :

- **`/audit`** — Visualiseur de preuves ancré sur XRPL. Liste par jeu pouvant être réduite, statut d’ancrage par tour, l’option « Vérifier tous les tours » exécute un recalcul local des preuves et une recherche dans la chaîne en série. Vue pour l’auditeur : confirmer qu’un jeu s’est déroulé honnêtement sans lire le JSON brut.
- **`/game`** — Affichage passif de l’état en temps réel pour le jeu actif. Cartes des ressources des joueurs, chronologie du tour, journal des 20 derniers événements SSE. En lecture seule ; exécution dans la ligne de commande (CLI) dans un autre terminal.
- **`/settings`** — Affichage de la configuration du démon + commutateur de réseau (testnet / mainnet / devnet) avec une protection pour le mainnet.

Spécifications complètes disponibles sur [docs/v2.1-views.md](docs/v2.1-views.md).

## Comment cela fonctionne

Vous commencez avec **5 pièces** et **3 points de réputation**. Lancez un dé, déplacez-vous sur un plateau de 16 cases, et atterrissez sur des cases qui vous offrent des choix : échanger, aider quelqu’un, prendre un risque ou piocher une carte.

**20 cartes d’événements** ressemblent à des moments : « Quelqu’un a-t-il vu une petite bourse en cuir ? » (Portefeuille perdu) ou « Personne n’a rien vu… pas vrai ? » (Raccourci trouvé). Inclut des événements de changement de marché pour les jeux Town Hall.

**10 cartes d’échange + 10 cartes de bons** obligent à la conversation : « Vous me prêtez 2 pièces ? Je vous en rembourserai 3. » ou « Je vous soutiens si vous me soutenez. ». Les échanges fixent des objectifs avec des échéances ; les bons sont des reconnaissances de dette que vous émettez à d’autres joueurs.

**La règle de la promesse :** Une fois par tour, dites à voix haute « Je promets… » et engagez-vous sur quelque chose. Tenez votre promesse : +1 point de réputation. Rompez votre promesse : -2 points de réputation. C’est au groupe de décider.

**Les excuses :** Une fois par jeu, si vous avez rompu une promesse, présentez publiquement vos excuses. Payez 1 pièce à la personne que vous avez lésée et regagnez +1 point de réputation.

**Choisissez votre objectif** (secret ou public) :
- **Prospérité** — atteignez 20 pièces
- **Bien-aimé** — atteignez 10 points de réputation
- **Constructeur** — effectuez 4 améliorations

Après 15 tours, le joueur avec le score combiné le plus élevé gagne.

## Qu’est-ce que le mode Journal ?

À chaque tour, la console peut générer une **preuve** — une empreinte de l’état du jeu. Si quelqu’un modifie le score, l’empreinte ne correspondra pas.

Facultativement, cette empreinte peut être publiée sur le **XRPL Testnet** — un registre public. Considérez cela comme si vous écriviez le score sur un mur que personne ne peut effacer.

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

Seul l’hôte a besoin d’un portefeuille. Personne d’autre n’a besoin de toucher un écran. Le jeu fonctionne parfaitement sans ancrage — c’est simplement le journal qui se souvient.

## Trois niveaux

| Niveau | Nom | Statut | Ce que cela ajoute |
|------|------|--------|-------------|
| 1 | **Campfire** | Jouable | Pièces, réputation, promesses, reconnaissances de dette |
| 2 | **Town Hall** | Jouable | Marché partagé, rareté des ressources |
| 3 | **Treaty Table** | Jouable | Traités avec enjeux — promesses contraignantes |

Les règles de base sont stables jusqu’à la version 1.x. Voir [roadmap](docs/roadmap.md).

## Packs de scénarios

Aucune nouvelle règle. Juste une ambiance. Chaque pack définit un niveau, une recette et une humeur.

| Scénario | Niveau | Idéal pour |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | Campfire / Journée du marché | Premier jeu, groupes mixtes |
| [Market Panic](docs/scenarios/market-panic.md) | Town Hall | Drame économique |
| [Promises Matter](docs/scenarios/promises-matter.md) | Campfire | Confiance et engagement |
| [Treaty Night](docs/scenarios/treaty-night.md) | Table des traités | Accords à enjeux élevés |

`sov scenario list` pour naviguer depuis la console.

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

> « Enseignez par les conséquences, et non par la terminologie. »

Les joueurs apprennent en faisant : en émettant des reconnaissances de dette, en rompant des promesses, en échangeant à des prix fluctuants. Les concepts correspondent aux primitives Web3 — portefeuilles, jetons, lignes de confiance —, mais les joueurs n’ont pas besoin de le savoir pour s’amuser.

## Contribution

Le moyen le plus simple de contribuer est d’[ajouter une carte](CONTRIBUTING.md). Aucune connaissance du moteur n’est nécessaire — juste un nom, une description et quelques éléments de texte pour l’ambiance.

## Sécurité

Clés de portefeuille, état du jeu et fichiers de preuve : ce qu’il faut partager et ce qu’il ne faut pas. Pas de télémétrie, pas d’analyses, pas de communication vers un serveur distant. La seule option de réseau est l’ancrage sur le XRPL Testnet.

Voir [SECURITY.md](SECURITY.md).

## Modèle de menace

| Menace | Atténuation |
|--------|-----------|
| Fuite de clé via les preuves | Les preuves ne contiennent que des hachages, jamais de clés. |
| Clé dans git | `.sov/` ignoré par git ; `sov wallet` avertit |
| Manipulation de l’état du jeu | Les preuves de tour `envelope_hash` couvrent `game_id`, `round`, `ruleset`, `rng_seed`, `timestamp_utc`, `players` et `state`. `sov verify` détecte la falsification sur l’ensemble de l’enveloppe. Le format de preuve v1 n’est plus pris en charge dans la version 2.0.0+. |
| Falsification de l’ancrage XRPL | Hachage de la preuve ancré sur la chaîne ; détection des incohérences lors de la vérification |
| Confidentialité du nom du joueur | Les noms des joueurs SONT inclus dans les preuves (liste de niveau supérieur `players` et à l’intérieur des instantanés des joueurs). Pour une partie privée, ne publiez pas `proof.json` et ne partagez pas les cartes postales. |

## Licence

MIT

---

Créé par [MCP Tool Shop](https://mcp-tool-shop.github.io/)
