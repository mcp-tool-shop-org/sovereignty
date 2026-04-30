<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.md">English</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

## Instalación en 30 segundos

La forma más rápida: para usuarios de Python:

```bash
pipx install sovereignty-game
sov tutorial
```

¿No usas Python? No hay problema. La opción `npx` descarga un binario precompilado:

```bash
npx @mcptoolshop/sovereignty tutorial
```

Eso es todo. `sov tutorial` te guiará a través de las reglas en aproximadamente 60 segundos.

## Tu primer juego

Una vez que tú y 2-3 amigos estén sentados, la consola gestiona la ronda y
tú te encargas de la interacción. Una partida real se ve así:

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

`sov status` muestra una tabla con formato Rich que incluye las monedas, la reputación, las mejoras,
la posición y el objetivo de cada jugador. Para una visión rápida de una línea entre turnos:

```bash
sov status --brief
```

```
R3 |  Alice: 7c 4r 0u | >Bob: 4c 3r 0u |  Carol: 6c 5r 0u
```

(`Nc Nr Nu` = monedas / reputación / mejoras; `>` indica al jugador activo.)

Repite durante 15 rondas. `sov game-end` muestra las puntuaciones finales.

> ¿Quieres una guía interactiva dentro de la aplicación primero? Ejecuta `sov tutorial`.
> ¿Quieres jugar sin ningún software? Consulta [Juego de mesa](docs/print-and-play.md).
> ¿Quieres una explicación más detallada de las reglas? Consulta [Comienza aquí](docs/start_here.md) o
> el [manual completo](https://mcp-tool-shop-org.github.io/sovereignty/handbook/).

> _Un GIF o captura de pantalla de demostración debe estar aquí: se rastrea como un seguimiento de la Fase D
> para que el README pueda mostrar cómo se ve realmente una ronda._

## Juega sin la consola

Imprime las cartas, toma un dado y algunas monedas, siéntate con 2-4 personas.
El juego funciona completamente sobre la mesa.

**[Comienza aquí](docs/start_here.md)** | **[Juego de mesa](docs/print-and-play.md)** | **[Reglas completas](docs/rules/campfire_v1.md)** | **[Juega con desconocidos](docs/play-with-strangers.md)**

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

La consola lleva la cuenta. Tú mantienes tu palabra.

## Cómo funciona

Comienzas con **5 monedas** y **3 de reputación**. Lanza un dado, muévete
por un tablero de 16 espacios y aterriza en casillas que te ofrecen opciones: comerciar, ayudar
a alguien, asumir un riesgo o robar una carta.

**28 cartas de evento** que suenan como momentos: *"¿Alguien ha visto una pequeña bolsa de cuero?"* (Cartera perdida) o *"¿Nadie lo vio... verdad?"* (Encontraste un atajo).
Incluye 8 eventos de cambio de mercado para juegos en el Ayuntamiento.

**22 cartas de trato y vale** que fomentan la conversación: *"¿Me adelantas 2 monedas? Te devolveré 3".* o *"Te cubro si tú me cubres a mí".* Los tratos establecen objetivos con plazos; los vales son promesas que le haces a otros jugadores.

**La regla de la promesa:** Una vez por ronda, di en voz alta "Prometo..." y
comprométete con algo. Cúmplelo: +1 de reputación. Rompe la promesa: -2 de reputación.
El grupo decide.

**La disculpa:** Una vez por juego, si rompiste una promesa, discúlpate públicamente.
Paga 1 moneda a la persona que perjudicaste y recupera +1 de reputación.

**Elige tu objetivo** (secreto o público):
- **Prosperidad** — alcanza 20 monedas
- **Amado** — alcanza 10 de reputación
- **Constructor** — completa 4 mejoras

Después de 15 rondas, el jugador con la puntuación combinada más alta gana.

## ¿Qué es el Modo Diario?

Cada ronda, la consola puede generar una **prueba** — una huella digital del
estado del juego. Si alguien cambia la puntuación, la huella digital no coincidirá.

Opcionalmente, esa huella digital se puede publicar en la **Red de pruebas XRPL** — un
libro de contabilidad público. Piensa en ello como escribir la puntuación en una pared que nadie
puede borrar.

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

Solo el anfitrión necesita una billetera. Nadie más toca una pantalla. El juego
funciona perfectamente sin necesidad de una cadena de bloques; es solo el diario el que recuerda.

## Tres niveles

| Nivel | Nombre | Estado | Lo que añade |
|------|------|--------|-------------|
| 1 | **Campfire** | Jugable | Monedas, reputación, promesas, pagarés |
| 2 | **Town Hall** | Jugable | Mercado compartido, escasez de recursos |
| 3 | **Treaty Table** | Jugable | Tratados con consecuencias: promesas con peso. |

Las reglas básicas son estables en la versión 1.x. Consulte [el plan de desarrollo](docs/roadmap.md).

## Paquetes de escenarios

Sin nuevas reglas. Solo ambiente. Cada paquete define un nivel, una receta y un estado de ánimo.

| Escenario | Nivel | Ideal para |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | Fogata / Día de mercado | Primera partida, grupos mixtos |
| [Market Panic](docs/scenarios/market-panic.md) | Ayuntamiento | Drama económico |
| [Promises Matter](docs/scenarios/promises-matter.md) | Fogata | Confianza y compromiso |
| [Treaty Night](docs/scenarios/treaty-night.md) | Mesa de tratados | Acuerdos de alto riesgo |

Utilice `sov scenario list` para explorar desde la consola.

## Estructura del proyecto

```
sovereignty/
  sov_engine/       # Pure game logic (models, rules, serialization, hashing)
  sov_transport/    # Ledger transport (offline + XRPL Testnet)
  sov_cli/          # Typer CLI (the "Round Console")
  tests/            # Engine, transport, and CLI tests
  docs/             # Rules, cards, print-and-play, play-with-strangers
  assets/print/     # Printable cards, player mat, quick reference
```

## Desarrollo

```bash
git clone https://github.com/mcp-tool-shop-org/sovereignty.git
cd sovereignty
uv sync --dev
uv run pytest tests/ -v
uv run ruff check .
```

## Principio de diseño

> "Enseñar a través de las consecuencias, no a través de la terminología."

Los jugadores aprenden haciendo: emitiendo pagarés, rompiendo promesas, comerciando a precios variables. Los conceptos se relacionan con los elementos básicos de Web3, como billeteras, tokens y líneas de confianza, pero los jugadores no necesitan saber eso para divertirse.

## Contribuciones

La forma más fácil de contribuir es [añadir una tarjeta](CONTRIBUTING.md).
No se necesita conocimiento del motor: solo un nombre, una descripción y un texto descriptivo.

## Seguridad

Semillas de billetera, estado del juego y archivos de prueba: qué compartir y qué no.
Sin telemetría, sin análisis, sin "llamar a casa". La única llamada de red opcional es el anclaje en la red de pruebas XRPL.

Consulte [SECURITY.md](SECURITY.md).

## Modelo de amenazas

| Amenaza | Mitigación |
|--------|-----------|
| Fuga de semillas a través de pruebas | Las pruebas contienen solo hashes, nunca semillas. |
| Semillas en git | `.sov/` está ignorado en git; `sov wallet` muestra una advertencia. |
| Manipulación del estado del juego | Las pruebas de cada ronda incluyen el `envelope_hash`, que cubre el `game_id`, la `round`, el `ruleset`, el `rng_seed`, la `timestamp_utc`, los `players` y el `state`. `sov verify` detecta cualquier manipulación en todo el paquete. El formato de prueba v1 ya no es compatible en la versión 2.0.0+. |
| Suplantación de identidad del ancla XRPL | El hash de la prueba está anclado en la cadena de bloques; la detección de discrepancias se realiza durante la verificación. |
| Privacidad de los nombres de los jugadores | Los nombres de los jugadores SÍ se incluyen en las pruebas (lista de `players` de nivel superior y dentro de las instantáneas de los jugadores). Para jugar en privado, no publique `proof.json` ni comparta las tarjetas postales. |

## Licencia

MIT

---

Desarrollado por [MCP Tool Shop](https://mcp-tool-shop.github.io/)
