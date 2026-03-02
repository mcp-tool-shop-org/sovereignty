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
  <a href="https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://mcp-tool-shop-org.github.io/sovereignty/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

## Juega esta noche

Imprime las cartas, consigue un dado y algunas monedas, siéntate con 2-4 personas.
No se requieren pantallas. Dura unos 30 minutos.

**[Comienza aquí](docs/start_here.md)** | **[Imprime y juega](docs/print-and-play.md)** | **[Reglas completas](docs/rules/campfire_v1.md)** | **[Juega con desconocidos](docs/play-with-strangers.md)**

## O usa la consola

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

La consola lleva la cuenta. Tú mantienes tu palabra.

## Cómo funciona

Comienzas con **5 monedas** y **3 puntos de reputación**. Lanza el dado, muévete por
un tablero de 16 casillas y aterriza en casillas que te ofrecen opciones: comerciar, ayudar
a alguien, asumir un riesgo o robar una carta.

**20 cartas de evento** que suenan como momentos: *"¿Alguien ha visto una pequeña
bolsa de cuero?"* (Cartera perdida) o *"Nadie lo vio... ¿verdad?"* (Encontró un atajo).

**20 cartas de trato** que fomentan la conversación: *"¿Me prestas 2 monedas? Te devolveré 3."*
o *"Te cubro si tú me cubres a mí."*

**La regla de la promesa:** Una vez por ronda, di en voz alta "Prometo..." y
comprométete con algo. Cúmplelo: +1 punto de reputación. Rompe la promesa: -2 puntos de reputación.
La mesa decide.

**La disculpa:** Una vez por partida, si rompiste una promesa, discúlpate públicamente.
Paga 1 moneda a la persona que perjudicaste y recupera +1 punto de reputación.

**Elige tu objetivo** (secreto o público):
- **Prosperidad** — alcanza 20 monedas
- **Amado** — alcanza 10 puntos de reputación
- **Constructor** — completa 4 mejoras

Después de 15 rondas, el jugador con la puntuación total más alta gana.

## ¿Qué es el Modo Diario?

Cada ronda, la consola puede generar una **prueba** — una huella digital del
estado del juego. Si alguien cambia la puntuación, la huella digital no coincidirá.

Opcionalmente, esa huella digital se puede publicar en la **XRPL Testnet** — un
libro mayor público. Piensa en ello como escribir la puntuación en una pared que nadie
puede borrar.

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

Solo el anfitrión necesita una billetera. Nadie más toca una pantalla. El juego
funciona perfectamente sin necesidad de "anclaje"; solo el diario recuerda.

## Tres niveles

| Nivel | Nombre | Estado | Lo que añade |
|------|------|--------|-------------|
| 1 | **Campfire** | Jugable | Monedas, reputación, promesas, favores |
| 2 | **Town Hall** | Jugable | Mercado compartido, escasez de recursos |
| 3 | **Treaty Table** | Jugable | Tratados con consecuencias — promesas con peso |

Las reglas básicas son estables en la versión 1.x. Consulta el [hoja de ruta](docs/roadmap.md).

## Paquetes de escenarios

Sin nuevas reglas. Solo ambiente. Cada paquete establece un nivel, una receta y un estado de ánimo.

| Escenario | Nivel | Ideal para |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | Fogata / Día de mercado | Primer juego, grupos mixtos |
| [Market Panic](docs/scenarios/market-panic.md) | Ayuntamiento | Drama económico |
| [Promises Matter](docs/scenarios/promises-matter.md) | Fogata | Confianza y compromiso |
| [Treaty Night](docs/scenarios/treaty-night.md) | Mesa de tratados | Acuerdos de alto riesgo |

`sov scenario list` para explorar desde la consola.

## Estructura del proyecto

```
sovereignty/
  sov_engine/       # Pure game logic (models, rules, serialization, hashing)
  sov_transport/    # Ledger transport (offline + XRPL Testnet)
  sov_cli/          # Typer CLI (the "Round Console")
  tests/            # 143 tests
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

> "Enseñar a través de las consecuencias, no de la terminología."

Los jugadores aprenden haciendo: otorgando favores, rompiendo promesas, comerciando a
precios cambiantes. Los conceptos se relacionan con los elementos básicos de Web3 — billeteras, tokens,
líneas de confianza — pero los jugadores no necesitan saber eso para divertirse.

## Contribución

La forma más fácil de contribuir es [añadir una carta](CONTRIBUTING.md).
No se necesita conocimiento del motor — solo un nombre, una descripción y algo de texto descriptivo.

## Seguridad

Semillas de billetera, estado del juego y archivos de prueba — qué compartir y qué no.
Sin telemetría, sin análisis, sin "llamar a casa". La única llamada de red opcional es el anclaje en XRPL Testnet.

Consulta [SECURITY.md](SECURITY.md).

## Modelo de amenazas

| Amenaza | Mitigación |
|--------|-----------|
| Fuga de semillas a través de pruebas. | Las pruebas contienen solo hashes, nunca semillas. |
| Semilla en Git. | `.sov/` está ignorado por Git; el comando `sov wallet` muestra una advertencia. |
| Manipulación del estado del juego. | Las pruebas hash del estado completo; `sov verify` detecta manipulaciones. |
| Suplantación de anclajes de XRPL. | El hash de la prueba está anclado en la cadena de bloques; la verificación detecta inconsistencias. |
| Privacidad del nombre del jugador. | El estado del juego es solo local; las pruebas no incluyen nombres. |

## Licencia

MIT.

---

Desarrollado por [MCP Tool Shop](https://mcp-tool-shop.github.io/)
