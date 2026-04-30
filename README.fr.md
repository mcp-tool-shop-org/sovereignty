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

## Installation en 30 secondes

La méthode la plus rapide — Pour les utilisateurs de Python :

```bash
pipx install sovereignty-game
sov tutorial
```

Pas de Python ? Pas de problème. La commande `npx` télécharge un exécutable précompilé :

```bash
npx @mcptoolshop/sovereignty tutorial
```

C'est tout. `sov tutorial` vous guide à travers les règles en environ 60 secondes.

## Votre premier jeu

Une fois que vous et 2 à 3 amis êtes assis autour de la table, la console gère le déroulement des tours et vous vous occupez de la partie verbale. Une partie réelle ressemble à ceci :

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

`sov status` affiche un tableau formaté avec les pièces, la réputation, les améliorations,
la position et l'objectif de chaque joueur. Pour un aperçu rapide entre les tours :

```bash
sov status --brief
```

```
R3 |  Alice: 7c 4r 0u | >Bob: 4c 3r 0u |  Carol: 6c 5r 0u
```

(`Nc Nr Nu` = pièces / réputation / améliorations ; `>` indique le joueur actif.)

Répétez l'opération pendant 15 tours. `sov game-end` affiche les scores finaux.

> Vous souhaitez d'abord un tutoriel intégré ? Exécutez `sov tutorial`.
> Vous souhaitez jouer sans aucun logiciel ? Consultez [Print & Play](docs/print-and-play.md).
> Vous souhaitez une présentation plus approfondie des règles ? Consultez [Commencez ici](docs/start_here.md) ou
> le [manuel complet](https://mcp-tool-shop-org.github.io/sovereignty/handbook/).

> _Une courte animation GIF ou une capture d'écran devrait être placée ici — suivie d'un suivi de la phase D afin que le fichier README puisse montrer à quoi ressemble réellement un tour._

## Jouer sans la console

Imprimez les cartes, prenez un dé et quelques pièces, asseyez-vous avec 2 à 4 personnes.
Le jeu fonctionne entièrement à la table.

**[Commencez ici](docs/start_here.md)** | **[Print & Play](docs/print-and-play.md)** | **[Règles complètes](docs/rules/campfire_v1.md)** | **[Jouez avec des inconnus](docs/play-with-strangers.md)**

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

La console garde les scores. Vous tenez parole.

## Comment ça marche

Vous commencez avec **5 pièces** et **3 de réputation**. Lancez un dé, déplacez-vous
sur un plateau de 16 cases et atterrissez sur des cases qui vous offrent des choix : échanger, aider
quelqu'un, prendre un risque ou piocher une carte.

**28 cartes d'événements** ressemblent à des moments : *"Est-ce que quelqu'un a vu un petit
pochette en cuir ?"* (Portefeuille perdu) ou *"Personne n'a rien vu... n'est-ce pas ?"* (Un raccourci
trouvé). Inclut 8 événements de changement de marché pour les parties au conseil municipal.

**22 cartes de transactions et de bons** encouragent la conversation : *"Tu me avances 2 pièces ? Je
te rembourse 3."* ou *"Je te couvre si tu me couvres."* Les transactions fixent des objectifs avec des
délais ; les bons sont des promesses que vous faites à d'autres joueurs.

**La règle de la promesse :** Une fois par tour, dites à voix haute "Je promets..." et
engagez-vous sur quelque chose. Respectez votre engagement : +1 de réputation. Rompez votre
engagement : -2 de réputation. La table décide.

**Les excuses :** Une fois par partie, si vous avez rompu une promesse, présentez publiquement
vos excuses. Payez 1 pièce à la personne que vous avez lésée et regagnez +1 de réputation.

**Choisissez votre objectif** (secret ou public) :
- **Prosperité** — atteindre 20 pièces
- **Bien-aimé** — atteindre 10 de réputation
- **Constructeur** — compléter 4 améliorations

Après 15 tours, le score combiné le plus élevé remporte la partie.

## Qu'est-ce que le mode journal ?

Chaque tour, la console peut produire une **preuve** — une empreinte du
état du jeu. Si quelqu'un modifie le score, l'empreinte ne correspondra pas.

Facultativement, cette empreinte peut être publiée sur le **XRPL Testnet** — un
registre public. Considérez-le comme écrire le score sur un mur que personne ne peut effacer.

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

Seul l'hôte a besoin d'un portefeuille. Personne d'autre n'interagit avec un écran. Le jeu
fonctionne parfaitement sans ancrage — c'est juste le journal qui se souvient.

## Trois niveaux

| Niveau | Nom | Statut | Ce que cela ajoute |
|------|------|--------|-------------|
| 1 | **Campfire** | Jouable | Pièces, réputation, promesses, dettes |
| 2 | **Town Hall** | Jouable | Marché partagé, rareté des ressources |
| 3 | **Treaty Table** | Jouable | Traités avec des enjeux – des promesses contraignantes |

Les règles de base sont stables dans la version 1.x. Consultez la [feuille de route](docs/roadmap.md).

## Packs de scénarios

Aucune nouvelle règle. Juste une ambiance. Chaque pack définit un niveau, une recette et une atmosphère.

| Scénario | Niveau | Idéal pour |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | Feu de camp / Journée du marché | Première partie, groupes mixtes |
| [Market Panic](docs/scenarios/market-panic.md) | Salle municipale | Drames économiques |
| [Promises Matter](docs/scenarios/promises-matter.md) | Feu de camp | Confiance et engagement |
| [Treaty Night](docs/scenarios/treaty-night.md) | Table des traités | Accords à enjeux élevés |

Utilisez `sov scenario list` pour parcourir les scénarios depuis la console.

## Structure du projet

```
sovereignty/
  sov_engine/       # Pure game logic (models, rules, serialization, hashing)
  sov_transport/    # Ledger transport (offline + XRPL Testnet)
  sov_cli/          # Typer CLI (the "Round Console")
  tests/            # Engine, transport, and CLI tests
  docs/             # Rules, cards, print-and-play, play-with-strangers
  assets/print/     # Printable cards, player mat, quick reference
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

Les joueurs apprennent en pratiquant : en émettant des dettes, en rompant des promesses, en échangeant à des prix variables. Les concepts correspondent aux primitives de Web3 – portefeuilles, jetons, lignes de confiance – mais les joueurs n'ont pas besoin de le savoir pour s'amuser.

## Contribution

La façon la plus simple de contribuer est d'[ajouter une carte](CONTRIBUTING.md).
Aucune connaissance du moteur n'est nécessaire, juste un nom, une description et un texte descriptif.

## Sécurité

Clés de portefeuille, état du jeu et fichiers de preuve – ce qu'il faut partager et ce qu'il ne faut pas.
Aucune télémétrie, aucune analyse, aucun signalement. Le seul appel réseau facultatif est l'ancrage XRPL Testnet.

Consultez [SECURITY.md](SECURITY.md).

## Modèle de menace

| Menace | Atténuation |
|--------|-----------|
| Fuite de clés via les preuves | Les preuves ne contiennent que des hachages, jamais de clés. |
| Clé dans Git | `.sov/` ignoré par Git ; `sov wallet` avertit. |
| Manipulation de l'état du jeu | Les preuves de chaque tour (`envelope_hash`) couvrent `game_id`, `round`, `ruleset`, `rng_seed`, `timestamp_utc`, `players` et `state`. `sov verify` détecte toute modification de l'intégralité de l'enveloppe. Le format de preuve v1 n'est plus pris en charge dans la version 2.0.0+. |
| Fausse ancre XRPL | Le hachage de la preuve est ancré sur la chaîne ; détection des incohérences lors de la vérification. |
| Confidentialité des noms de joueurs | Les noms de joueurs SONT inclus dans les preuves (liste `players` de niveau supérieur et dans les instantanés des joueurs). Pour une partie privée, ne publiez pas `proof.json` et ne partagez pas les cartes postales. |

## Licence

MIT

---

Créé par [MCP Tool Shop](https://mcp-tool-shop.github.io/)
