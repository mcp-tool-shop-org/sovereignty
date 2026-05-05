<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.md">English</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

## Juega esta noche

Imprime [todo el paquete para imprimir y jugar](assets/print/pdf/Sovereignty-Print-Pack.pdf): tablero, láminas para los jugadores, referencia rápida y tres mazos de cartas en 11 hojas de papel de formato US Letter. Busca un dado y algunas monedas. Siéntate con dos o tres amigos. Podrás jugar en veinte minutos.

Si quieres las hojas individuales:

- **[Tablero](assets/print/pdf/board.pdf)**: el circuito de 16 espacios "Campfire", en una página.
- **[Lámina para el jugador](assets/print/pdf/mat.pdf)**: monedas, reputación, mejoras, promesas. Una por jugador.
- **[Referencia rápida](assets/print/pdf/quickref.pdf)**: espacios del tablero, orden de turno, reglas de las promesas.
- **[Cartas de evento](assets/print/pdf/events.pdf)**: 20 cartas, tres páginas, recorta a lo largo de las líneas.
- **[Cartas de trato](assets/print/pdf/deals.pdf)**: 10 cartas, dos páginas.
- **[Cartas de vale](assets/print/pdf/vouchers.pdf)**: 10 "IOUs" (órdenes de pago) entre jugadores, dos páginas.
- **[Referencia rápida de tratados](assets/print/pdf/treaty.pdf)**: solo para el nivel 3.

Los archivos PDF son vectoriales y tienen fuentes integradas, por lo que se imprimen correctamente en cualquier impresora doméstica. Las instrucciones de configuración están disponibles en [Imprimir y jugar](docs/print-and-play.md).

## ¿Quieres una interfaz para llevar la cuenta?

Opcional. El juego funciona bien en papel. Pero si alguien tiene una computadora portátil a mano, `sov` puede llevar la cuenta de las monedas, la reputación, las promesas y generar un recibo a prueba de manipulaciones al final:

```bash
pip install sovereignty-game
sov play campfire_v1
```

`sov play campfire_v1` es la forma más rápida de empezar, sin configuración: un jugador humano y un oponente predeterminado. Para jugar con varios jugadores, usa `sov new -p Alice -p Bob -p Carol`. Para una guía paso a paso de 60 segundos, usa `sov tutorial`.

¿No tienes Python? La opción `npx` descarga un binario precompilado:

```bash
npx @mcptoolshop/sovereignty tutorial
```

## Una sesión real

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

- **Múltiples partidas guardadas** (v2.1+): `sov games` muestra las partidas guardadas; `sov resume <id-de-la-partida>` te permite cambiar entre ellas.
- **Anclaje por lotes** (v2.1+): `sov anchor` al final de la partida agrupa todas las rondas pendientes en una única transacción de XRPL, creando un único puntero de cadena verificable por partida. Usa `sov anchor --checkpoint` para actualizar la cadena durante la partida.
- **Selección de red** (v2.1+): `sov anchor --network testnet|mainnet|devnet` (o la variable de entorno `SOV_XRPL_NETWORK`; el valor predeterminado es `testnet`).
- **Modo demonio** (v2.1+, opcional): `sov daemon start` ejecuta un servidor HTTP/JSON local para la integración con el escritorio y la monitorización de la cadena en segundo plano. Consulta [Modo demonio](#daemon-mode-optional-v21) a continuación.
- **Aplicación de escritorio Audit Viewer** (v2.1+, opcional): `npm --prefix app run tauri dev`. Consulta [Aplicación de escritorio](#desktop-app-optional-v21) a continuación.

> ¿Quieres una guía paso a paso dentro de la aplicación? Ejecuta `sov tutorial`.
> ¿Quieres una explicación más detallada de las reglas? Consulta [Comienza aquí](docs/start_here.md) o
> el [manual completo](https://mcp-tool-shop-org.github.io/sovereignty/handbook/).

El ejemplo de `sov turn` que se muestra arriba ilustra cómo es una ronda en la consola; para la visualización de escritorio de la versión 2.1, consulta [Aplicación de escritorio](#desktop-app-optional-v21) a continuación.

**[Comienza aquí](docs/start_here.md)** | **[Juego de mesa](docs/print-and-play.md)** | **[Reglas completas](docs/rules/campfire_v1.md)** | **[Juega con desconocidos](docs/play-with-strangers.md)**

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

La consola lleva la cuenta. Tú mantienes tu palabra.

## Modo demonio (opcional, v2.1+)

Para la integración con el escritorio (Audit Viewer, Tauri shell) o la monitorización de la cadena en segundo plano, ejecuta sovereignty como un demonio HTTP local:

```bash
pip install 'sovereignty-game[daemon]'
sov daemon start --readonly        # audit-only, no wallet seed
sov daemon start                   # full daemon with anchor endpoints (loads XRPL_SEED)
sov daemon status                  # running | stale | none
sov daemon stop
```

El demonio se conecta a `127.0.0.1` en un puerto aleatorio; los detalles de la conexión (puerto + token de acceso) se encuentran en `.sov/daemon.json`. Un demonio por directorio raíz del proyecto. Consulta [docs/v2.1-daemon-ipc.md](docs/v2.1-daemon-ipc.md) para obtener información completa sobre el contrato IPC.

## Aplicación de escritorio (opcional, v2.1+)

El Audit Viewer es la aplicación de escritorio de la versión 2.1: una capa Tauri (Rust + webview) que ejecuta el visor de auditoría y una vista de juego de solo lectura, además del demonio.

### Instalación (binarios)

La versión 2.1.0 incluye binarios precompilados en la [página de lanzamientos de GitHub](https://github.com/mcp-tool-shop-org/sovereignty/releases/latest):

- **macOS (universal):** `sovereignty-app-2.1.0-darwin-universal.dmg` — Intel + Apple Silicon
- **Windows (x64):** `sovereignty-app-2.1.0-win-x64.msi`
- **Linux (x64, .deb):** `sovereignty-app-2.1.0-linux-x64.deb` — Debian / Ubuntu / derivados. Instale con `sudo dpkg -i sovereignty-app-2.1.0-linux-x64.deb`. El soporte para AppImage se pospone a la versión 2.2 (interacción de `linuxdeploy` / Ubuntu 24.04 FUSE).

También necesita el demonio de Python que da soporte a la aplicación: `pip install 'sovereignty-game[daemon]'==2.1.0`.

> **Se espera una advertencia al iniciar por primera vez.** macOS mostrará "desarrollador no identificado": haga clic con el botón derecho en el archivo .app, elija "Abrir" y confirme. Windows SmartScreen mostrará "editor no reconocido": haga clic en "Más información" y luego en "Ejecutar de todos modos". Ambas advertencias indican que la versión 2.1 incluye solo la certificación de la procedencia de la compilación (verifique con `gh attestation verify`), y no la firma de código a nivel del sistema operativo. La infraestructura de firma a nivel de espacio de trabajo se incluirá en la versión 2.2.

### Verifique la procedencia

Cada archivo de la versión incluye una certificación de la procedencia de la compilación según SLSA. Verifique antes de ejecutar:

```bash
gh attestation verify \
  --repo mcp-tool-shop-org/sovereignty \
  ./sovereignty-app-2.1.0-darwin-universal.dmg
```

Una verificación correcta demuestra que el binario se compiló a partir de un commit específico, utilizando el flujo de trabajo de la versión, en este repositorio. Es un nivel de confianza diferente a la firma de código a nivel del sistema operativo; el binario aún genera la advertencia del sistema operativo, pero su procedencia en la cadena de suministro está protegida criptográficamente.

### Ejecute desde el código fuente

Si prefiere compilar desde el código fuente (o si el binario no se ejecuta en su plataforma):

```bash
# 1. Install Python + daemon deps
pip install -e '.[xrpl,daemon]'

# 2. Install frontend + Rust deps (one-time)
cd app && npm install && cd ..
cargo build --manifest-path app/src-tauri/Cargo.toml

# 3. Start the dev shell (auto-starts the daemon in readonly mode)
npm --prefix app run tauri dev
```

La capa Tauri inicia automáticamente un demonio de solo lectura al iniciarse y lo detiene automáticamente al cerrarse. Los demonios iniciados externamente (`sov daemon start`) permanecen activos incluso después de reiniciar la capa.

Consulte [docs/v2.1-tauri-shell.md](docs/v2.1-tauri-shell.md) para obtener la especificación completa.

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

El visor de auditoría incluye tres vistas:

- **`/audit`** — Visor de pruebas anclado a XRPL. Lista de juegos que se puede contraer, estado de anclaje por ronda, "Verificar todas las rondas" ejecuta un nuevo cálculo de la prueba y una búsqueda en la cadena. La vista del auditor: confirma que un juego se ejecutó de manera honesta sin leer JSON sin formato.
- **`/game`** — Visualización pasiva del estado en tiempo real para el juego activo. Tarjetas de recursos del jugador, línea de tiempo de la ronda, registro de los últimos 20 eventos SSE. Solo lectura; juegue en la CLI en otra terminal.
- **`/settings`** — Visualización de la configuración del demonio y conmutador de red (testnet / mainnet / devnet) con una protección para la confirmación de la red principal.

Consulte la especificación completa de la vista en [docs/v2.1-views.md](docs/v2.1-views.md).

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
