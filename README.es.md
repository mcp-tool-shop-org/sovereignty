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
  <a href="https://codecov.io/gh/mcp-tool-shop-org/sovereignty"><img src="https://codecov.io/gh/mcp-tool-shop-org/sovereignty/graph/badge.svg" alt="Coverage"></a>
  <a href="https://pypi.org/project/sovereignty-game/"><img src="https://img.shields.io/pypi/v/sovereignty-game?include_prereleases&style=flat&cacheSeconds=3600" alt="PyPI version"></a>
  <a href="https://pypi.org/project/sovereignty-game/"><img src="https://img.shields.io/pypi/pyversions/sovereignty-game?style=flat&cacheSeconds=3600" alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat&cacheSeconds=86400" alt="License: MIT"></a>
  <a href="https://mcp-tool-shop-org.github.io/sovereignty/"><img src="https://img.shields.io/badge/Landing_Page-live-blue?style=flat&cacheSeconds=86400" alt="Landing Page"></a>
</p>

## Juguemos esta noche

Imprime [todo el paquete para imprimir y jugar](assets/print/pdf/Sovereignty-Print-Pack.pdf): el tablero, las alfombrillas para los jugadores, la guía de referencia rápida, el tablero del mercado y tres mazos de cartas en 13 hojas de papel tamaño carta estadounidense. Busca un dado y algunas monedas. Siéntate con dos o tres amigos. Estarán jugando en veinte minutos.

Si quieres hojas individuales:

- **[Tablero](assets/print/pdf/board.pdf)**: el circuito de la fogata de 16 espacios, una página.
- **[Alfombrilla para el jugador](assets/print/pdf/mat.pdf)**: monedas, reputación, mejoras, promesas. Una por jugador.
- **[Guía de referencia rápida](assets/print/pdf/quickref.pdf)**: espacios del tablero, orden de turno, reglas de las promesas.
- **[Cartas de evento](assets/print/pdf/events.pdf)**: 28 cartas, cuatro páginas, cortar a lo largo de las líneas.
- **[Cartas de trato](assets/print/pdf/deals.pdf)**: 12 cartas, dos páginas.
- **[Cartas de vale](assets/print/pdf/vouchers.pdf)**: 10 vales entre los jugadores, dos páginas.
- **[Tablero del mercado](assets/print/pdf/market.pdf)**: Día de mercado / Ayuntamiento, una página.
- **[Guía de referencia rápida del tratado](assets/print/pdf/treaty.pdf)**: solo nivel 3.

Los archivos PDF son vectoriales con fuentes incrustadas, por lo que se imprimen con claridad en cualquier impresora doméstica. La guía paso a paso para la configuración está en [Imprimir y jugar](docs/print-and-play.md).

## ¿Quieres una consola para llevar la cuenta?

Opcional. El juego funciona bien en papel. Pero si alguien tiene una computadora portátil a mano, `sov` rastrea las monedas, la reputación, las promesas y genera un recibo a prueba de manipulaciones al final:

```bash
pip install sovereignty-game
sov play campfire_v1
```

`sov play campfire_v1` es el inicio rápido sin configuración: un jugador más un oponente predeterminado. Para jugar entre varios jugadores en la mesa, usa `sov new -p Alice -p Bob -p Carol`. Para una guía paso a paso de 60 segundos, usa `sov tutorial`.

¿No tienes Python? La opción `npx` descarga un archivo binario precompilado:

```bash
npx @mcptoolshop/sovereignty tutorial
```

O ejecútalo en Docker, con tus partidas guardadas en un volumen con nombre:

```bash
docker run --rm -it -v sov-data:/data ghcr.io/mcp-tool-shop-org/sovereignty tutorial
```

## Una sesión real

Una vez que tú y 2-3 amigos estén sentados a la mesa, la consola ejecuta la ronda y ustedes hablan. Una sesión real se ve así:

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

`sov status` muestra una tabla con formato enriquecido con las monedas, la reputación, las mejoras, la posición y el objetivo de cada jugador. Para una rápida revisión de una línea entre turnos:

```bash
sov status --brief
```

```
R3 |  Alice: 7c 4r 0u | >Bob: 4c 3r 0u |  Carol: 6c 5r 0u
```

(`Nc Nr Nu` = monedas / reputación / mejoras; `>` marca al jugador activo).

Repite durante 15 rondas. `sov game-end` imprime las puntuaciones finales.

- **Múltiples partidas guardadas** (v2.1+): `sov games` muestra las partidas guardadas; `sov resume <game-id>` cambia entre ellas.
- **Anclaje por lotes** (v2.1+): `sov anchor` al final del juego guarda las rondas pendientes en una pequeña constante de AccountSet transacciones de XRPL (≤8 memorandos cada una; un juego típico de Campfire de 16 rondas → 2 transacciones) — no una sola transacción / un solo puntero de cadena. Usa `sov anchor --checkpoint` para guardar a la mitad del juego.
- **Selección de red** (v2.1+): `sov anchor --network testnet|mainnet|devnet` (o la variable de entorno `SOV_XRPL_NETWORK`; por defecto `testnet`).
- **Modo daemon** (v2.1+, opcional): `sov daemon start` ejecuta un servidor HTTP/JSON en localhost para la integración con el escritorio y la consulta de la cadena en segundo plano. Consulta [Modo daemon](#modo-daemon-opcional-v21) a continuación.
- **Aplicación de escritorio Audit Viewer** (v2.1+, opcional): `npm --prefix app run tauri dev`. Consulta [Aplicación de escritorio](#aplicación-de-escritorio-opcional-v21) a continuación.

> ¿Quieres una guía paso a paso dentro de la aplicación primero? Ejecuta `sov tutorial`.
> ¿Quieres un recorrido más profundo de las reglas? Consulta [Comienza aquí](docs/start_here.md) o
> el [manual completo](https://mcp-tool-shop-org.github.io/sovereignty/handbook/).

El ejemplo en línea de `sov turn` anterior muestra cómo se ve una ronda en la consola; para la visualización de escritorio de v2.1, consulta [Aplicación de escritorio](#aplicación-de-escritorio-opcional-v21) a continuación.

**[Comienza aquí](docs/start_here.md)** | **[Imprimir y jugar](docs/print-and-play.md)** | **[Reglas completas](docs/rules/campfire_v1.md)** | **[Jugar con extraños](docs/play-with-strangers.md)**

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

La consola lleva la cuenta. Tú cumples tu palabra.

## Modo daemon (opcional, v2.1+)

Para la integración con el escritorio (Audit Viewer, carcasa Tauri) o la consulta de la cadena en segundo plano, ejecuta Sovereignty como un daemon HTTP en localhost:

```bash
pip install 'sovereignty-game[daemon]'
sov daemon start --readonly        # audit-only, no wallet seed
sov daemon start                   # full daemon with anchor endpoints (loads XRPL_SEED)
sov daemon status                  # running | stale | none
sov daemon stop
```

El daemon se enlaza a `127.0.0.1` en un puerto aleatorio; los detalles de la conexión (puerto + token de acceso) se encuentran en `.sov/daemon.json`. Un daemon por directorio raíz del proyecto. Consulta [docs/v2.1-daemon-ipc.md](docs/v2.1-daemon-ipc.md) para conocer el contrato IPC completo.

> Los extras de `[daemon]` necesitan **2.3.2 o posterior**. Las versiones hasta 2.3.1 no incluyeron el paquete `sov_daemon`, por lo que `sov daemon start` falló en una instalación de PyPI.

## Docker (opcional, v2.3.2+)

La imagen en `ghcr.io/mcp-tool-shop-org/sovereignty` contiene la CLI de `sov` y el daemon, para `linux/amd64` y `linux/arm64`. Todo lo que el juego recuerda se guarda en `/data/.sov`: juegos, pruebas de ronda, `anchors.json`, el registro de la temporada, la semilla de la billetera y el apretón de manos del daemon. Monta un volumen en `/data` o el contenedor lo olvidará todo.

Ejecuta el daemon con el [`compose.yaml`](compose.yaml) incluido:

```bash
docker compose up -d                  # readonly audit daemon on 127.0.0.1:47823
docker compose run --rm sov doctor    # any sov command, same saves
docker compose run --rm sov play campfire_v1
docker compose logs -f
```

El contenedor tiene un daemon **de solo lectura** en **testnet** de forma predeterminada. El puerto se publica solo en el bucle invertido del host (`127.0.0.1:47823`), y cada solicitud aún necesita el token de acceso de `.sov/daemon.json`.

| Configuración | Predeterminado | Qué hace |
|---|---|---|
| `SOV_DATA` | `sov-data` (volumen con nombre) | De dónde proviene `/data`. Establécelo en una carpeta (`SOV_DATA=./`) para guardar las partidas en el host. |
| `SOV_DAEMON_PORT` | `47823` | Puerto del daemon, dentro y en el host. Los dos deben coincidir. |
| `SOV_DAEMON_NETWORK` | `testnet` | `testnet`, `devnet` o `mainnet`. |
| `SOV_DAEMON_READONLY` | `1` | `0` habilita los puntos de conexión de anclaje. |
| `SOV_DAEMON_TOKEN` | aleatorio en cada inicio | Fíjalo para que los clientes permanezcan conectados entre reinicios. |
| `SOV_DAEMON_LOG_FORMAT` | `human` | `json` para líneas de registro estructuradas. |

**Adjunta la aplicación de escritorio.** Apunta `SOV_DATA` a la carpeta del proyecto que abre la aplicación. El daemon escribe su apretón de manos allí, y la aplicación se comunica con `127.0.0.1:47823` con el token que contiene:

```bash
SOV_DATA=./ docker compose up -d
```

Mientras el contenedor posee el daemon, gestiona con `docker compose`, no con `sov daemon start|stop|status` en el host. La CLI del host no puede ver el proceso de un contenedor, por lo que informa que el apretón de manos está desactualizado, y `sov daemon start` lo borraría.

**Ancla desde el contenedor.** Crea una billetera de testnet en el volumen y luego desactiva la opción de solo lectura:

```bash
docker compose run --rm sov wallet
SOV_DAEMON_READONLY=0 docker compose up -d
```

Para mantener la semilla fuera del volumen, proporciónala como un secreto de Docker. El bloque comentado `secrets` en `compose.yaml` muestra cómo.

## Aplicación de escritorio (opcional, v2.1+)

Audit Viewer es la aplicación de escritorio v2.1: una carcasa Tauri (Rust + webview) que ejecuta el visor de auditoría y una vista de juego de solo lectura sobre el daemon.

### Instala (binarios)

**v2.4.0** es la versión actual. La versión de GitHub **v2.3.0** no incluyó wheels ni archivos de la aplicación de escritorio, así que no fije `pip install …==2.3.0`.

- **Python / daemon:** `pip install 'sovereignty-game[daemon]'` (versión 2.3.2 o posterior para el daemon).
- **Aplicación de escritorio:** [la última versión de GitHub](https://github.com/mcp-tool-shop-org/sovereignty/releases/latest) cuando CI adjunta archivos de plataforma. Si falla un trabajo de plataforma, ejecute desde el código fuente (a continuación).

> Se espera la **advertencia de inicio del sistema operativo** cuando se distribuyen binarios autenticados. Estas versiones solo incluyen la atestación de la procedencia de la compilación SLSA, no la firma a nivel del sistema operativo de Apple Developer ID / Authenticode. macOS: haga clic con el botón derecho en el archivo .app → Abrir. Windows SmartScreen: Más información → Ejecutar de todos modos.

### Verificar la procedencia

Cuando una versión adjunta realmente artefactos de escritorio, verifique el archivo que descargó:

```bash
gh attestation verify \
  --repo mcp-tool-shop-org/sovereignty \
  ./<downloaded-artifact>
```

Una verificación correcta demuestra que el binario se compiló a partir de un commit específico, mediante el flujo de trabajo de la versión, en este repositorio. Es una capa de confianza diferente a la firma de código a nivel del sistema operativo; el binario aún activa la advertencia del sistema operativo, pero su procedencia de la cadena de suministro está encriptada.

### Ejecutar desde el código fuente

Si prefiere compilar desde el código fuente (o el binario no se ejecuta en su plataforma):

```bash
# 1. Install Python + daemon deps
pip install -e '.[xrpl,daemon]'

# 2. Install frontend + Rust deps (one-time)
cd app && npm install && cd ..
cargo build --manifest-path app/src-tauri/Cargo.toml

# 3. Start the dev shell (auto-starts the daemon in readonly mode)
npm --prefix app run tauri dev
```

El shell de Tauri inicia automáticamente un daemon de solo lectura al iniciarse y lo detiene automáticamente al salir. Los daemons iniciados externamente (`sov daemon start`) permanecen activos entre reinicios del shell.

Consulte [docs/v2.1-tauri-shell.md](docs/v2.1-tauri-shell.md) para conocer el contrato completo.

El visor de auditoría se distribuye con tres vistas:

- **`/audit`** — visor de pruebas ancladas a XRPL. Lista por juego que se puede contraer, estado del ancla por ronda y "Verificar todas las rondas" ejecuta la recompilación local de la prueba + búsqueda en la cadena en serie. La vista del auditor: confirmar que un juego se ejecutó de manera honesta sin leer el JSON sin procesar.
- **`/game`** — visualización pasiva del estado en tiempo real para el juego activo. Tarjetas de recursos del jugador, línea de tiempo de la ronda, registro de los últimos 20 eventos SSE. Solo lectura; juegue en la CLI en otra terminal.
- **`/settings`** — visualización de la configuración del daemon + conmutador de red (testnet / mainnet / devnet) con protección de confirmación de mainnet.

La especificación completa de la vista en [docs/v2.1-views.md](docs/v2.1-views.md).

## Cómo funciona

Comienza con **5 monedas** y **3 puntos de reputación**. Lanza un dado, muévete por un tablero de 16 casillas y aterriza en casillas que te ofrecen opciones: intercambiar, ayudar a alguien, asumir un riesgo o robar una carta.

**28 cartas de evento** se leen como momentos: *"¿Alguien ha visto una pequeña bolsa de cuero?"* (Cartera perdida) o *"Nadie lo vio... ¿verdad?"* (Encontró un atajo). Incluye eventos de cambio de mercado para juegos de Ayuntamiento.

**12 cartas de acuerdo + 10 cartas de vale** obligan a la conversación: *"¿Me prestas 2 monedas? Te devolveré 3".* o *"Te cubro la espalda si tú me la cubres a mí".* Los acuerdos establecen objetivos con plazos; los vales son pagarés que emites a otros jugadores.

**La regla de la promesa:** Una vez por ronda, di en voz alta "Lo prometo..." y comprométete a algo. Cúmplelo: +1 punto de reputación. Incúmplelo: -2 puntos de reputación. La mesa decide.

**La disculpa:** Una vez por juego, si rompiste una promesa, discúlpate públicamente. Paga 1 moneda a quien perjudicaste y recupera +1 punto de reputación.

**Elige tu objetivo** (secreto o público):
- **Prosperidad:** alcanza 20 monedas
- **Amado:** alcanza 10 puntos de reputación
- **Constructor:** completa 4 mejoras

Después de 15 rondas, la puntuación combinada más alta gana.

## ¿Qué es el modo diario?

Cada ronda, la consola puede generar una **prueba**: una huella digital del estado del juego. Si alguien cambia la puntuación, la huella digital no coincidirá.

Opcionalmente, esa huella digital se puede publicar en el **XRPL Testnet**: un libro mayor público. Piense en ello como escribir la puntuación en una pared que nadie puede borrar.

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

Solo el anfitrión necesita una billetera. Nadie más toca una pantalla. El juego funciona perfectamente sin anclaje; es solo el diario el que recuerda.

Testnet y Devnet se borran periódicamente (la próxima vez el 25 de noviembre de 2026), y un ancla creado antes de un borrado desaparece después. `sov verify --tx` indica entonces que el ancla ya no se puede verificar (código de salida 3), nunca que pasó la verificación. Ejecute `sov wallet` y `sov anchor --reanchor` para volver a colocar las rondas del juego en el libro mayor. Consulte [el manual](https://mcp-tool-shop-org.github.io/sovereignty/handbook/diary-mode/).

## Tres niveles

| Nivel | Nombre | Estado | Lo que agrega |
|------|------|--------|-------------|
| 1 | **Campfire** | Jugable | Monedas, reputación, promesas, pagarés |
| 2 | **Town Hall** | Jugable | Mercado compartido, escasez de recursos |
| 3 | **Treaty Table** | Jugable | Tratados con apuestas: promesas con consecuencias |

Las reglas básicas son estables hasta v1.x. Consulte [la hoja de ruta](docs/roadmap.md).

## Paquetes de escenarios

Cero reglas nuevas. Solo ambiente. Cada paquete establece un nivel, una receta y un estado de ánimo.

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
  sov_daemon/       # Localhost HTTP/SSE daemon for the desktop app
  app/              # Tauri desktop app (Audit Viewer)
  docker/           # Container entrypoint + healthcheck
  site/             # Landing page + handbook
  tests/            # Engine, transport, daemon, and CLI tests
  docs/             # Rules, cards, print-and-play, play-with-strangers
  assets/print/     # Print pack — markdown sources, rendered PDFs, JSX render sources
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

> "Enseñar a través de las consecuencias, no de la terminología".

Los jugadores aprenden haciendo: emitiendo pagarés, rompiendo promesas, intercambiando a precios fluctuantes. Los conceptos se corresponden con los Web3 primitivos: billeteras, tokens, líneas de confianza, pero los jugadores no necesitan saber eso para divertirse.

## Contribuyendo

La forma más fácil de contribuir es [agregar una carta](CONTRIBUTING.md). No se necesitan conocimientos del motor; solo un nombre, una descripción y algo de texto descriptivo.

## Seguridad

Semillas de billetera, estado del juego y archivos de prueba: qué compartir y qué no. Sin telemetría, sin análisis, sin llamadas al servidor. La única llamada de red opcional es el anclaje de XRPL Testnet.

Consulte [SECURITY.md](SECURITY.md).

## Modelo de amenazas

| Amenaza | Mitigación |
|--------|-----------|
| Fuga de semillas a través de pruebas | Las pruebas contienen solo hashes, nunca semillas. |
| Semilla en Git | `.sov/` ignorado por Git; `sov wallet` muestra advertencias |
| Manipulación del estado del juego | Las pruebas de ronda `envelope_hash` cubren `game_id`, `round`, `ruleset`, `rng_seed`, `timestamp_utc`, `players` y `state`. `sov verify` detecta manipulaciones en todo el conjunto. El formato de prueba v1 ya no es compatible en v2.0.0+. |
| Suplantación de un nodo ancla de XRPL | Hash de la prueba anclado en la cadena; detección de discrepancias durante la verificación |
| Exposición del contenedor | La imagen del demonio se publica solo en el host `127.0.0.1`; token de acceso en cada solicitud; solo lectura de forma predeterminada; se ejecuta como un usuario que no es root con un sistema de archivos raíz de solo lectura y sin capacidades |
| Privacidad del nombre del jugador | Los nombres de los jugadores SÍ se incluyen en las pruebas (lista de nivel superior `players` y dentro de las instantáneas de los jugadores). Para jugar de forma privada, no publique `proof.json` ni comparta postales. |

## Licencia

MIT

---

Creado por [MCP Tool Shop](https://mcp-tool-shop.github.io/)
