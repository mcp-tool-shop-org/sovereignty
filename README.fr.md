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
  <a href="https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://mcp-tool-shop-org.github.io/sovereignty/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

## Jouez ce soir

Imprimez les cartes, prenez un dé et quelques pièces, asseyez-vous avec 2 à 4 personnes.
Aucun écran requis. La partie dure environ 30 minutes.

**[Commencez ici](docs/start_here.md)** | **[Imprimer et jouer](docs/print-and-play.md)** | **[Règles complètes](docs/rules/campfire_v1.md)** | **[Jouer avec des inconnus](docs/play-with-strangers.md)**

## Ou utilisez la console

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

La console garde le score. Vous tenez parole.

## Comment ça marche

Vous commencez avec **5 pièces** et **3 points de réputation**. Lancez le dé, déplacez-vous
sur un plateau de 16 cases et atterrissez sur des cases qui vous offrent des choix : échanger, aider
quelqu'un, prendre un risque ou piocher une carte.

**20 cartes d'événements** ressemblent à des moments : *"Est-ce que quelqu'un a vu un petit
pochette en cuir ?"* (Portefeuille perdu) ou *"Personne n'a rien vu... n'est-ce pas ?"* (Un raccourci trouvé).

**20 cartes de transactions** encouragent la conversation : *"Tu me avances 2 pièces ? Je te rembourse 3."*
ou *"Je suis là pour toi si tu es là pour moi."*

**La règle de la promesse :** Une fois par tour, dites à voix haute "Je promets..." et
engagez-vous sur quelque chose. Tenez votre promesse : +1 point de réputation. Rompez-la : -2 points de réputation.
Le groupe décide.

**Les excuses :** Une fois par partie, si vous avez rompu une promesse, présentez publiquement vos excuses.
Payez 1 pièce à la personne que vous avez lésée et regagnez +1 point de réputation.

**Choisissez votre objectif** (secret ou public) :
- **Prospérité** — atteindre 20 pièces
- **Bien-aimé** — atteindre 10 points de réputation
- **Constructeur** — compléter 4 améliorations

Après 15 tours, le joueur avec le score combiné le plus élevé gagne.

## Qu'est-ce que le mode journal ?

Chaque tour, la console peut produire une **preuve** — une empreinte de
l'état du jeu. Si quelqu'un modifie le score, l'empreinte ne correspondra pas.

Facultativement, cette empreinte peut être publiée sur le **XRPL Testnet** — un
registre public. Considérez cela comme écrire le score sur un mur que personne
ne peut effacer.

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

Seul l'hôte a besoin d'un portefeuille. Personne d'autre n'utilise un écran. Le jeu
fonctionne parfaitement sans enregistrement — c'est juste le journal qui se souvient.

## Trois niveaux

| Niveau | Nom | Statut | Ce qu'il ajoute |
|------|------|--------|-------------|
| 1 | **Campfire** | Jouable | Pièces, réputation, promesses, dettes |
| 2 | **Town Hall** | Jouable | Marché partagé, rareté des ressources |
| 3 | **Treaty Table** | Jouable | Traités avec enjeux — promesses avec des conséquences |

Les règles de base sont stables dans la version 1.x. Consultez la [feuille de route](docs/roadmap.md).

## Packs de scénarios

Aucune nouvelle règle. Juste l'ambiance. Chaque pack définit un niveau, une recette et une ambiance.

| Scénario | Niveau | Idéal pour |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | Campfire / Marché | Première partie, groupes mixtes |
| [Market Panic](docs/scenarios/market-panic.md) | Salle municipale | Drames économiques |
| [Promises Matter](docs/scenarios/promises-matter.md) | Coin du feu | Confiance et engagement |
| [Treaty Night](docs/scenarios/treaty-night.md) | Table des traités | Accords à enjeux élevés |

`sov scenario list` pour parcourir depuis la console.

## Structure du projet

```
sovereignty/
  sov_engine/       # Pure game logic (models, rules, serialization, hashing)
  sov_transport/    # Ledger transport (offline + XRPL Testnet)
  sov_cli/          # Typer CLI (the "Round Console")
  tests/            # 143 tests
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

> "Enseignez par les conséquences, pas par la terminologie."

Les joueurs apprennent en faisant : émettre des dettes, rompre des promesses, échanger à des prix variables. Les concepts correspondent aux primitives Web3 — portefeuilles, jetons, lignes de confiance — mais les joueurs n'ont pas besoin de le savoir pour s'amuser.

## Contribution

La façon la plus simple de contribuer est d'[ajouter une carte](CONTRIBUTING.md).
Aucune connaissance du moteur requise — juste un nom, une description et un texte descriptif.

## Sécurité

Clés de portefeuille, état du jeu et fichiers de preuve — ce qu'il faut partager et ce qu'il ne faut pas.
Aucune télémétrie, aucune analyse, aucun appel à la maison. La seule connexion réseau facultative est l'ancrage XRPL Testnet.

Consultez [SECURITY.md](SECURITY.md).

## Modèle de menace

| Menace | Atténuation |
|--------|-----------|
| Fuite de clés de chiffrement via les preuves | Les preuves ne contiennent que des hachages, jamais de clés de chiffrement. |
| Clé de chiffrement dans Git | Le répertoire `.sov/` est ignoré par Git ; la commande `sov wallet` affiche un avertissement. |
| Manipulation de l'état du jeu | Les preuves de chaque tour hachent l'état complet ; `sov verify` détecte toute modification. |
| Fausse déclaration de l'ancre XRPL | Le hachage de la preuve est ancré sur la chaîne de blocs ; les incohérences sont détectées par `verify`. |
| Confidentialité des noms de joueurs | L'état du jeu est uniquement local ; les preuves ne contiennent pas les noms. |

## Licence

MIT

---

Développé par [MCP Tool Shop](https://mcp-tool-shop.github.io/)
