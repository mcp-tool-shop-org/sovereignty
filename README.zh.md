<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.md">English</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

## 今晚一起玩吧

打印[完整的打印版游戏套装](assets/print/pdf/Sovereignty-Print-Pack.pdf)，包括游戏板、玩家垫、快速参考、市场板和三副卡牌，共13张美国信纸大小的纸。找一个骰子和一些硬币。和两三个朋友坐在一起。你们可以在二十分钟内开始游戏。

如果你想要单独的纸张：

- **[游戏板](assets/print/pdf/board.pdf)**——16个格子组成的篝火环，一张纸。
- **[玩家垫](assets/print/pdf/mat.pdf)**——硬币、声望、升级、承诺。每位玩家一张。
- **[快速参考](assets/print/pdf/quickref.pdf)**——游戏板格子、回合顺序、承诺规则。
- **[事件卡](assets/print/pdf/events.pdf)**——28张卡牌，四页，沿着线剪开。
- **[交易卡](assets/print/pdf/deals.pdf)**——12张卡牌，两页。
- **[凭证卡](assets/print/pdf/vouchers.pdf)**——玩家之间的10张借条，两页。
- **[市场板](assets/print/pdf/market.pdf)**——市场日/市政厅，一张纸。
- **[条约快速参考](assets/print/pdf/treaty.pdf)**——仅适用于第三层。

这些PDF文件都是矢量图，并嵌入了字体，因此可以在任何家用打印机上清晰地打印。设置指南请参见[打印版游戏](docs/print-and-play.md)。

## 想要一个控制台来记录分数吗？

可选。游戏也可以在纸上进行。但是，如果有人手边有笔记本电脑，`sov`可以跟踪硬币、声望、承诺，并在游戏结束时生成一个防篡改的收据：

```bash
pip install sovereignty-game
sov play campfire_v1
```

`sov play campfire_v1`是一个无需配置的快速启动版本——一个玩家加上一个默认对手。对于桌面上的多人游戏，请使用`sov new -p Alice -p Bob -p Carol`。对于一个60秒的引导教程，请使用`sov tutorial`。

没有Python？`npx`路径会下载一个预构建的二进制文件：

```bash
npx @mcptoolshop/sovereignty tutorial
```

或者在Docker中运行，并将你的存档保存在一个命名的卷中：

```bash
docker run --rm -it -v sov-data:/data ghcr.io/mcp-tool-shop-org/sovereignty tutorial
```

## 一次真实的会话

一旦你和2-3个朋友坐在桌子旁，控制台就会运行一轮，而你们则进行对话。一次真实的会话看起来像这样：

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

`sov status`会显示一个格式丰富的表格，其中包含玩家的硬币、声望、升级、位置和目标。为了在回合之间快速查看：

```bash
sov status --brief
```

```
R3 |  Alice: 7c 4r 0u | >Bob: 4c 3r 0u |  Carol: 6c 5r 0u
```

（`Nc Nr Nu` = 硬币/声望/升级；`>`标记了当前玩家。）

重复15轮。`sov game-end`会打印出最终分数。

- **多个已保存的游戏**（v2.1+）：`sov games`列出已保存的游戏；`sov resume <game-id>`在它们之间切换。
- **批量锚定**（v2.1+）：游戏结束时，`sov anchor`会将待处理的回合合并到一个小的、恒定的XRPL AccountSet事务集合中（每个事务最多包含8个备忘录；典型的16轮篝火游戏→2个事务），而不是单个事务/单个链指针。使用`sov anchor --checkpoint`进行游戏中期的合并。
- **网络选择**（v2.1+）：`sov anchor --network testnet|mainnet|devnet`（或`SOV_XRPL_NETWORK`环境变量；默认值为`testnet`）。
- **守护进程模式**（v2.1+，可选）：`sov daemon start`运行一个localhost HTTP/JSON服务器，用于桌面集成和后台链轮询。请参见下方的[守护进程模式](#daemon-mode-optional-v21)。
- **审计查看器桌面应用程序**（v2.1+，可选）：`npm --prefix app run tauri dev`。请参见下方的[桌面应用程序](#desktop-app-optional-v21)。

>想要先进行一个引导式应用程序教程吗？运行`sov tutorial`。
>想要更深入地了解游戏规则吗？请参见[从这里开始](docs/start_here.md)或[完整手册](https://mcp-tool-shop-org.github.io/sovereignty/handbook/)。

上面的内联`sov turn`示例显示了控制台中一轮游戏的样子；对于v2.1桌面可视化，请参见下方的[桌面应用程序](#desktop-app-optional-v21)。

**[从这里开始](docs/start_here.md)** | **[打印版游戏](docs/print-and-play.md)** | **[完整规则](docs/rules/campfire_v1.md)** | **[与陌生人一起玩](docs/play-with-strangers.md)**

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

控制台记录分数。你们遵守承诺。

## 守护进程模式（可选，v2.1+）

为了进行桌面集成（审计查看器、Tauri shell）或后台链轮询，请将主权游戏作为localhost HTTP守护进程运行：

```bash
pip install 'sovereignty-game[daemon]'
sov daemon start --readonly        # audit-only, no wallet seed
sov daemon start                   # full daemon with anchor endpoints (loads XRPL_SEED)
sov daemon status                  # running | stale | none
sov daemon stop
```

守护进程绑定到`127.0.0.1`上的一个随机端口；连接详细信息（端口+bearer token）位于`.sov/daemon.json`中。每个项目根目录一个守护进程。请参见[docs/v2.1-daemon-ipc.md](docs/v2.1-daemon-ipc.md)，了解完整的IPC协议。

> `[daemon]`附加项需要**2.3.2或更高版本**。2.3.1及更早版本的软件包缺少`sov_daemon`，因此在PyPI安装时，`sov daemon start`会失败。

## Docker（可选，v2.3.2+）

位于`ghcr.io/mcp-tool-shop-org/sovereignty`的镜像包含`sov`CLI和守护进程，用于`linux/amd64`和`linux/arm64`。游戏记住的所有内容都位于`/data/.sov`中：游戏、回合证明、`anchors.json`、赛季记录、钱包种子和守护进程握手。将一个卷挂载到`/data`，否则容器会忘记所有内容。

使用捆绑的[`compose.yaml`](compose.yaml)运行守护进程：

```bash
docker compose up -d                  # readonly audit daemon on 127.0.0.1:47823
docker compose run --rm sov doctor    # any sov command, same saves
docker compose run --rm sov play campfire_v1
docker compose logs -f
```

容器默认情况下运行一个**只读**守护进程，在**测试网络**上。端口仅发布到主机的环回地址（`127.0.0.1:47823`），并且每个请求仍然需要来自`.sov/daemon.json`的bearer token。

| 设置 | 默认值 | 它的作用 |
|---|---|---|
| `SOV_DATA` | `sov-data`（命名卷） | `/data`的来源。将其设置为一个文件夹（`SOV_DATA=./`），以在主机上保存存档。 |
| `SOV_DAEMON_PORT` | `47823` | 守护进程端口，在容器内部和主机上。两者必须匹配。 |
| `SOV_DAEMON_NETWORK` | `testnet` | `testnet`、`devnet`或`mainnet`。 |
| `SOV_DAEMON_READONLY` | `1` | `0`启用锚定端点。 |
| `SOV_DAEMON_TOKEN` | 每次启动时随机生成 | 修复，使客户端在重新启动后保持连接。 |
| `SOV_DAEMON_LOG_FORMAT` | `human` | `json`用于结构化日志行。 |

**连接桌面应用程序。**将`SOV_DATA`指向应用程序打开的项目文件夹。守护进程会将它的握手信息写入其中，并且应用程序会使用其中的token拨打`127.0.0.1:47823`：

```bash
SOV_DATA=./ docker compose up -d
```

当容器拥有守护进程时，请使用`docker compose`对其进行管理，而不是使用主机上的`sov daemon start|stop|status`。主机CLI无法看到容器的进程，因此它会将握手信息报告为过时，并且`sov daemon start`会清除它。

**从容器中进行锚定。**在卷中创建一个测试网络钱包，然后关闭只读模式：

```bash
docker compose run --rm sov wallet
SOV_DAEMON_READONLY=0 docker compose up -d
```

为了防止种子进入卷中，请将其作为 Docker 密钥提供。`compose.yaml` 中的注释块 `secrets` 演示了如何操作。

## 桌面应用程序（可选，v2.1+）

审核查看器是 v2.1 桌面应用程序——一个 Tauri shell（Rust + webview），它在守护进程之上运行审核查看器和只读游戏视图。

### 安装（二进制文件）

**v2.3.5** 是当前的发布版本。GitHub 发布版本 **v2.3.0** 中未包含预编译的 wheel 文件或桌面资源，因此请不要固定使用 `pip install …==2.3.0`。

- **Python / 守护进程：** `pip install 'sovereignty-game[daemon]'`（守护进程的版本为 2.3.2 或更高版本）。
- **桌面应用程序：** 当 CI 附加了平台文件时，请使用 [最新的 GitHub 发布版](https://github.com/mcp-tool-shop-org/sovereignty/releases/latest)。如果某个平台任务失败，请从源代码运行（如下）。

> 当发布经过验证的二进制文件时，预计会出现**首次启动的操作系统警告**。这些构建仅包含 SLSA 构建溯源证明——不包含操作系统级别的 Apple Developer ID / Authenticode 签名。macOS：右键单击 .app → 打开。Windows SmartScreen：更多信息 → 仍然运行。

### 验证溯源

当发布版本实际附加桌面工件时，请验证您下载的文件：

```bash
gh attestation verify \
  --repo mcp-tool-shop-org/sovereignty \
  ./<downloaded-artifact>
```

清晰的验证证明，该二进制文件是从特定的提交构建的，由此仓库中的发布工作流程构建。这与操作系统级别的代码签名不同——二进制文件仍然会触发操作系统警告，但其供应链溯源已通过密码方式固定。

### 从源代码运行

如果您想从源代码构建（或者二进制文件无法在您的平台上运行）：

```bash
# 1. Install Python + daemon deps
pip install -e '.[xrpl,daemon]'

# 2. Install frontend + Rust deps (one-time)
cd app && npm install && cd ..
cargo build --manifest-path app/src-tauri/Cargo.toml

# 3. Start the dev shell (auto-starts the daemon in readonly mode)
npm --prefix app run tauri dev
```

Tauri shell 在启动时自动启动一个只读守护进程，并在退出时自动停止它。外部启动的守护进程（`sov daemon start`）在 shell 重启期间保持运行。

有关完整协议，请参阅 [docs/v2.1-tauri-shell.md](docs/v2.1-tauri-shell.md)。

审核查看器包含三个视图：

- **`/audit`** — 基于 XRPL 的证明查看器。可折叠的每个游戏列表、每个回合的锚状态，“验证所有回合”会按顺序运行本地证明重新计算 + 链查找。审核员视图：在不读取原始 JSON 的情况下，确认游戏是否诚实地进行。
- **`/game`** — 活动游戏的被动实时状态显示。玩家资源卡、回合时间线、最近 20 个 SSE 事件日志。只读；在另一个终端的 CLI 中进行游戏。
- **`/settings`** — 守护进程配置显示 + 网络切换器（测试网 / 主网 / 开发网），并带有主网确认保护。

完整的视图规范请参见 [docs/v2.1-views.md](docs/v2.1-views.md)。

## 工作原理

您从 **5 个硬币**和 **3 点声誉**开始。掷骰子，在 16 个格子的棋盘上移动，并停留在提供选择的格子上：交易、帮助他人、冒险或抽取卡牌。

**28 张事件卡** 就像一个个瞬间：“有人见过一个小皮包吗？”（丢失的钱包）或“没人看到……对吧？”（找到了一条捷径）。包括用于市政厅游戏的市场变化事件。

**12 张交易卡 + 10 张凭证卡** 促使进行对话：“你能先借给我 2 个硬币吗？我会还 3 个。”或“如果你支持我，我也会支持你。”交易设定具有截止日期的目标；凭证是您发给其他玩家的欠条。

**承诺规则：** 每个回合，大声说出“我承诺……”并承诺做某事。遵守承诺：+1 声誉。违背承诺：-2 声誉。由大家决定。

**道歉：** 在游戏中，如果您违背了承诺，请公开道歉。向您伤害的人支付 1 个硬币，并恢复 +1 声誉。

**选择您的目标**（秘密或公开）：
- **繁荣** — 达到 20 个硬币
- **受人喜爱** — 达到 10 点声誉
- **建设者** — 完成 4 次升级

15 个回合后，综合得分最高者获胜。

## 什么是日记模式？

每个回合，控制台都可以生成一个**证明**——游戏状态的指纹。如果有人更改了分数，指纹将不匹配。

可选地，可以将该指纹发布到**XRPL 测试网**——一个公共账本。您可以将其视为将分数写在墙上，没有人可以擦除。

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

只有主持人需要一个钱包。其他人都不需要触摸屏幕。游戏即使没有锚定也可以完美运行——只是日记会记住。

## 三个层级

| 层级 | 名称 | 状态 | 它增加了什么 |
|------|------|--------|-------------|
| 1 | **Campfire** | 可玩 | 硬币、声誉、承诺、欠条 |
| 2 | **Town Hall** | 可玩 | 共享市场、资源稀缺 |
| 3 | **Treaty Table** | 可玩 | 带有赌注的条约——带有约束力的承诺 |

核心规则在 v1.x 版本中保持稳定。请参阅 [路线图](docs/roadmap.md)。

## 场景包

没有新的规则。只是氛围。每个包都设置一个层级、配方和氛围。

| 场景 | 层级 | 最适合 |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | 篝火 / 市场日 | 第一次游戏，混合群体 |
| [Market Panic](docs/scenarios/market-panic.md) | 市政厅 | 经济戏剧 |
| [Promises Matter](docs/scenarios/promises-matter.md) | 篝火 | 信任和承诺 |
| [Treaty Night](docs/scenarios/treaty-night.md) | 条约桌 | 高风险协议 |

`sov scenario list` 以从控制台浏览。

## 项目结构

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

## 开发

```bash
git clone https://github.com/mcp-tool-shop-org/sovereignty.git
cd sovereignty
uv sync --dev
uv run pytest tests/ -v
uv run ruff check .
```

## 设计原则

> “通过后果进行教学，而不是通过术语。”

玩家通过实践来学习：发行欠条、违背承诺、在不断变化的价格中进行交易。这些概念与 Web3 原语相关联——钱包、令牌、信任线路——但玩家不需要知道这些才能获得乐趣。

## 贡献

最简单的贡献方式是 [添加一张卡牌](CONTRIBUTING.md)。不需要引擎知识——只需要一个名称、一个描述和一些风味文本。

## 安全性

钱包种子、游戏状态和证明文件——哪些可以共享，哪些不可以。不收集遥测数据，不进行数据分析，不进行远程连接。唯一的可选网络调用是 XRPL 测试网络锚定。

请参阅 [SECURITY.md](SECURITY.md)。

## 威胁模型

| 威胁 | 缓解措施 |
|--------|-----------|
| 通过证明泄露种子 | 证明仅包含哈希值，绝不包含种子 |
| 种子存储在 git 中 | `.sov/` 通过 git 忽略；`sov wallet` 给出警告 |
| 游戏状态操纵 | 回合证明 `envelope_hash` 涵盖 `game_id`、`round`、`ruleset`、`rng_seed`、`timestamp_utc`、`players` 和 `state`。`sov verify` 检测整个信封中的篡改。证明格式 v1 不再受 v2.0.0+ 版本支持。 |
| XRPL 锚点欺骗 | 证明哈希值锚定在链上；在验证过程中检测不匹配 |
| 容器暴露 | 守护程序镜像仅发布到主机 `127.0.0.1`；每个请求都使用令牌；默认情况下为只读；以非 root 用户身份运行，具有只读的 root 文件系统且不具有任何权限 |
| 玩家姓名隐私 | 玩家姓名包含在证明中（顶级 `players` 列表和玩家快照中）。如果需要进行私密游戏，请不要发布 `proof.json` 或共享明信片。 |

## 许可

MIT

---

由 [MCP Tool Shop](https://mcp-tool-shop.github.io/) 构建
