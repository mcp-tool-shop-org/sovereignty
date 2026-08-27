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

## Juega esta noche

Imprime [todo el paquete para imprimir y jugar](assets/print/pdf/Sovereignty-Print-Pack.pdf): tablero, tapetes de jugador, referencia rápida y tres mazos de cartas en 11 hojas de papel tamaño carta estadounidense. Busca un dado y algunas monedas. Siéntate con dos o tres amigos. Estarán jugando en veinte minutos.

Si quieres hojas individuales:

- **[Tablero](assets/print/pdf/board.pdf)**: el circuito de la fogata de 16 espacios, una página.
- **[Tapete de jugador](assets/print/pdf/mat.pdf)**: monedas, reputación, mejoras, promesas. Uno por jugador.
- **[Referencia rápida](assets/print/pdf/quickref.pdf)**: espacios del tablero, orden de turno, reglas de las promesas.
- **[Cartas de evento](assets/print/pdf/events.pdf)**: 20 cartas, tres páginas, cortar por las líneas.
- **[Cartas de acuerdo](assets/print/pdf/deals.pdf)**: 10 cartas, dos páginas.
- **[Cartas de vale](assets/print/pdf/vouchers.pdf)**: 10 vales entre jugadores, dos páginas.
- **[Referencia rápida del tratado](assets/print/pdf/treaty.pdf)**: solo nivel 3.

Los archivos PDF son vectoriales con fuentes incrustadas; se imprimen de forma nítida en cualquier impresora doméstica. Las instrucciones paso a paso están disponibles en [Imprimir y jugar](docs/print-and-play.md).

## ¿Quieres una consola para llevar la cuenta?

Opcional. El juego funciona bien en papel. Pero si alguien tiene una computadora portátil a mano, `sov` rastrea las monedas, la reputación, las promesas y genera un recibo a prueba de manipulaciones al final:

```bash
pip install sovereignty-game
sov play campfire_v1
```

`sov play campfire_v1` es el inicio rápido sin configuración: un jugador más un oponente predeterminado. Para partidas multijugador en la mesa, usa `sov new -p Alice -p Bob -p Carol`. Para una guía paso a paso de 60 segundos, usa `sov tutorial`.

¿No tienes Python? La opción `npx` descarga un archivo binario precompilado:

```bash
npx @mcptoolshop/sovereignty tutorial
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

`sov status` muestra una tabla con formato enriquecido con las monedas, la reputación, las mejoras, la posición y el objetivo de cada jugador. Para echar un vistazo rápido entre turnos:

```bash
sov status --brief
```

```
R3 |  Alice: 7c 4r 0u | >Bob: 4c 3r 0u |  Carol: 6c 5r 0u
```

(`Nc Nr Nu` = monedas / reputación / mejoras; `>` marca al jugador activo).

Repite durante 15 rondas. `sov game-end` imprime las puntuaciones finales.

- **Múltiples juegos guardados** (v2.1+): `sov games` muestra los juegos guardados; `sov resume <game-id>` cambia entre ellos.
- **Anclaje por lotes** (v2.1+): `sov anchor` al final del juego agrupa todas las rondas pendientes en una sola transacción XRPL: un puntero de cadena verificable por juego. Usa `sov anchor --checkpoint` para guardar los datos a la mitad del juego.
- **Selección de red** (v2.1+): `sov anchor --network testnet|mainnet|devnet` (o variable de entorno `SOV_XRPL_NETWORK`; predeterminado `testnet`).
- **Modo daemon** (v2.1+, opcional): `sov daemon start` ejecuta un servidor HTTP/JSON en localhost para la integración con el escritorio y la recopilación de datos de la cadena en segundo plano. Consulta [Modo daemon](#daemon-mode-optional-v21) a continuación.
- **Aplicación de escritorio Audit Viewer** (v2.1+, opcional): `npm --prefix app run tauri dev`. Consulta [Aplicación de escritorio](#desktop-app-optional-v21) a continuación.

> ¿Quieres una guía paso a paso dentro de la aplicación primero? Ejecuta `sov tutorial`.
> ¿Quieres conocer las reglas en detalle? Consulta [Comienza aquí](docs/start_here.md) o el [manual completo](https://mcp-tool-shop-org.github.io/sovereignty/handbook/).

El ejemplo de `sov turn` anterior muestra cómo se ve una ronda en la consola; para la visualización de escritorio v2.1, consulta [Aplicación de escritorio](#desktop-app-optional-v21) a continuación.

**[Comienza aquí](docs/start_here.md)** | **[Imprimir y jugar](docs/print-and-play.md)** | **[Reglas completas](docs/rules/campfire_v1.md)** | **[Juega con extraños](docs/play-with-strangers.md)**

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

Para la integración con el escritorio (Audit Viewer, carcasa Tauri) o la recopilación de datos de la cadena en segundo plano, ejecuta Sovereignty como un daemon HTTP en localhost:

```bash
pip install 'sovereignty-game[daemon]'
sov daemon start --readonly        # audit-only, no wallet seed
sov daemon start                   # full daemon with anchor endpoints (loads XRPL_SEED)
sov daemon status                  # running | stale | none
sov daemon stop
```

El daemon se enlaza a `127.0.0.1` en un puerto aleatorio; los detalles de la conexión (puerto + token de acceso) están disponibles en `.sov/daemon.json`. Un daemon por directorio raíz del proyecto. Consulta [docs/v2.1-daemon-ipc.md](docs/v2.1-daemon-ipc.md) para conocer el contrato IPC completo.

## Aplicación de escritorio (opcional, v2.1+)

Audit Viewer es la aplicación de escritorio v2.1: una carcasa Tauri (Rust + webview) que ejecuta el visor de auditoría y una vista del juego de solo lectura sobre el daemon.

### Instalar (archivos binarios)

v2.3.0 incluye archivos binarios precompilados en la [página de lanzamientos de GitHub](https://github.com/mcp-tool-shop-org/sovereignty/releases/latest):

- **macOS (universal):** `sovereignty-app-2.3.0-darwin-universal.dmg`: Intel + Apple Silicon
- **Windows (x64):** `sovereignty-app-2.3.0-win-x64.msi`
- **Linux (x64, .deb):** `sovereignty-app-2.3.0-linux-x64.deb`: Debian / Ubuntu / derivados. Instalar con `sudo dpkg -i sovereignty-app-2.3.0-linux-x64.deb`.
- **Linux (x64, AppImage):** `sovereignty-app-2.3.0-linux-x64.AppImage`: `chmod +x` y luego ejecutar.

También necesitas el daemon de Python que respalda la aplicación: `pip install 'sovereignty-game[daemon]'==2.3.0`.

> **Se espera una advertencia al iniciar por primera vez.** macOS mostrará "desarrollador no identificado"; haz clic con el botón derecho en el archivo .app, elige Abrir y confirma. SmartScreen de Windows dirá "editor desconocido"; haz clic en "Más información" y luego en "Ejecutar de todos modos". Ambas advertencias reflejan que las versiones actuales se envían solo con la atestación de procedencia de la compilación (verificar con `gh attestation verify`), no con la firma de código a nivel del sistema operativo.

### Verificar la procedencia

Cada artefacto de lanzamiento incluye una atestación de procedencia de la compilación SLSA. Verifica antes de ejecutar:

```bash
gh attestation verify \
  --repo mcp-tool-shop-org/sovereignty \
  ./sovereignty-app-2.3.0-darwin-universal.dmg
```

Una verificación correcta demuestra que el archivo binario se creó a partir de un commit específico, mediante el flujo de trabajo de lanzamiento, en este repositorio. Es una capa de confianza diferente a la firma de código a nivel del sistema operativo; el archivo binario aún activa la advertencia del sistema operativo, pero su procedencia de la cadena de suministro está fijada criptográficamente.

### Ejecutar desde el código fuente

Si prefieres compilar desde el código fuente (o si el archivo binario no se ejecuta en tu plataforma):

```bash
# 1. Install Python + daemon deps
pip install -e '.[xrpl,daemon]'

# 2. Install frontend + Rust deps (one-time)
cd app && npm install && cd ..
cargo build --manifest-path app/src-tauri/Cargo.toml

# 3. Start the dev shell (auto-starts the daemon in readonly mode)
npm --prefix app run tauri dev
```

La carcasa Tauri inicia automáticamente un daemon de solo lectura al iniciar y lo detiene automáticamente al salir. Los daemons iniciados externamente (`sov daemon start`) permanecen activos entre reinicios de la carcasa.

Consulta [docs/v2.1-tauri-shell.md](docs/v2.1-tauri-shell.md) para conocer el contrato completo.

Audit Viewer incluye tres vistas:

- **`/audit`** — Visor de pruebas anclado a XRPL. Lista desplegable por juego, estado del ancla por ronda y la opción "Verificar todas las rondas" ejecuta una nueva computación de prueba local + búsqueda en la cadena en serie. La vista para el auditor: confirmar que un juego se desarrolló de manera honesta sin leer el JSON sin procesar.
- **`/game`** — Pantalla pasiva del estado en tiempo real para el juego activo. Tarjetas de recursos del jugador, línea de tiempo de la ronda y registro de los últimos 20 eventos SSE. Solo lectura; jugar en la CLI en otra terminal.
- **`/settings`** — Pantalla de configuración del daemon + conmutador de red (testnet / mainnet / devnet) con protección de confirmación de mainnet.

La especificación completa se encuentra en [docs/v2.1-views.md](docs/v2.1-views.md).

## Cómo funciona

Comienzas con **5 monedas** y **3 puntos de reputación**. Lanza un dado, muévete por un tablero de 16 casillas y aterriza en las casillas que te ofrecen opciones: intercambiar, ayudar a alguien, asumir un riesgo o robar una carta.

**20 cartas de evento** se leen como momentos: *"¿Alguien ha visto una pequeña bolsa de cuero?"* (Cartera perdida) o *"Nadie lo vio... ¿verdad?"* (Encontró un atajo). Incluye eventos de cambio de mercado para juegos de Ayuntamiento.

**10 cartas de acuerdo + 10 cartas de vale** obligan a la conversación: *"¿Me prestas 2 monedas? Te devolveré 3."* o *"Te cubro las espaldas si tú me cubres a mí". Los acuerdos establecen objetivos con plazos; los vales son pagarés que emites a otros jugadores.

**La regla de la promesa:** Una vez por ronda, di en voz alta "Lo prometo..." y comprométete a algo. Cúmplelo: +1 punto de reputación. Incúmplelo: -2 puntos de reputación. La mesa decide.

**La disculpa:** Una vez por juego, si rompiste una promesa, discúlpate públicamente. Paga 1 moneda a la persona a la que perjudicaste y recupera +1 punto de reputación.

**Elige tu objetivo** (secreto o público):
- **Prosperidad:** Alcanza las 20 monedas.
- **Querido:** Alcanza los 10 puntos de reputación.
- **Constructor:** Completa 4 mejoras.

Después de 15 rondas, el jugador con la puntuación combinada más alta gana.

## ¿Qué es el modo Diario?

Cada ronda, la consola puede generar una **prueba**, una huella digital del estado del juego. Si alguien cambia la puntuación, la huella digital no coincidirá.

Opcionalmente, esa huella digital se puede publicar en el **XRPL Testnet**, un libro mayor público. Piensa en ello como escribir la puntuación en una pared que nadie puede borrar.

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

Solo el anfitrión necesita una billetera. Nadie más toca una pantalla. El juego funciona perfectamente sin anclaje; es solo el diario el que recuerda.

## Tres niveles

| Nivel | Nombre | Estado | Lo que añade |
|------|------|--------|-------------|
| 1 | **Campfire** | Jugable | Monedas, reputación, promesas, pagarés |
| 2 | **Town Hall** | Jugable | Mercado compartido, escasez de recursos |
| 3 | **Treaty Table** | Jugable | Tratados con apuestas: promesas con consecuencias |

Las reglas básicas son estables hasta la versión 1.x. Consulta [roadmap](docs/roadmap.md).

## Paquetes de escenarios

Cero nuevas reglas. Solo ambiente. Cada paquete establece un nivel, una receta y un estado de ánimo.

| Escenario | Nivel | Ideal para |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | Fogata / Día del mercado | Primer juego, grupos mixtos |
| [Market Panic](docs/scenarios/market-panic.md) | Ayuntamiento | Drama económico |
| [Promises Matter](docs/scenarios/promises-matter.md) | Fogata | Confianza y compromiso |
| [Treaty Night](docs/scenarios/treaty-night.md) | Mesa de tratados | Acuerdos de alto riesgo |

`sov scenario list` para navegar desde la consola.

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

> "Enseña a través de las consecuencias, no de la terminología".

Los jugadores aprenden haciendo: emitiendo pagarés, rompiendo promesas, intercambiando a precios fluctuantes. Los conceptos se corresponden con los primitivos de Web3: billeteras, tokens, líneas de confianza, pero los jugadores no necesitan saberlo para divertirse.

## Contribuyendo

La forma más fácil de contribuir es [añadir una carta](CONTRIBUTING.md). No se necesita conocimiento del motor; solo un nombre, una descripción y algo de texto descriptivo.

## Seguridad

Semillas de billetera, estado del juego y archivos de prueba: qué compartir y qué no. Sin telemetría, sin análisis, sin conexión a casa. La única llamada de red opcional es el anclaje en XRPL Testnet.

Consulta [SECURITY.md](SECURITY.md).

## Modelo de amenazas

| Amenaza | Mitigación |
|--------|-----------|
| Fuga de semillas a través de pruebas | Las pruebas contienen solo hashes, nunca semillas. |
| Semilla en git | `.sov/` ignorado por git; `sov wallet` advierte. |
| Manipulación del estado del juego | Las pruebas de ronda `envelope_hash` cubren `game_id`, `round`, `ruleset`, `rng_seed`, `timestamp_utc`, `players` y `state`. `sov verify` detecta la manipulación en todo el sobre. El formato de prueba v1 ya no es compatible en v2.0.0+. |
| Suplantación del ancla XRPL | Hash de prueba anclado en la cadena; detección de desajuste en la verificación. |
| Privacidad del nombre del jugador | Los nombres de los jugadores SÍ se incluyen en las pruebas (lista de nivel superior `players` y dentro de las instantáneas de los jugadores). Para jugar en privado, no publiques `proof.json` ni compartas postales. |

## Licencia

MIT

---

Creado por [MCP Tool Shop](https://mcp-tool-shop.github.io/)
