<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.md">English</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

```text
<!--
徽标样式策略 (阶段 D / W7CIDOCS-001): 所有徽标都使用 shields.io
默认使用 `flat` 样式，以保持视觉一致性。 每个 shields.io URL 都设置了
`cacheSeconds=3600`，因此当上游注册中心速度较慢时，缓存未命中会回退到
上一次已知的值，而不是显示空白。 CI 徽标是 GitHub 的原生 SVG，
并且不受此限制——GitHub 使用其自己的缓存从 camo 服务器提供该徽标。
-->
<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/sovereignty-game/"><img src="https://img.shields.io/pypi/v/sovereignty-game?include_prereleases&style=flat&cacheSeconds=3600" alt="PyPI version"></a>
  <a href="https://pypi.org/project/sovereignty-game/"><img src="https://img.shields.io/pypi/pyversions/sovereignty-game?style=flat&cacheSeconds=3600" alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat&cacheSeconds=86400" alt="License: MIT"></a>
  <a href="https://mcp-tool-shop-org.github.io/sovereignty/"><img src="https://img.shields.io/badge/Landing_Page-live-blue?style=flat&cacheSeconds=86400" alt="Landing Page"></a>
</p>

## 安装 + 首次游戏

最快的开始方式：安装，然后开始游戏：

```bash
pip install sovereignty-game
sov play campfire_v1
```

`sov play campfire_v1` 是无需配置的快速启动方式，一个玩家和一个默认的对手，使用 Campfire 规则集。 对于多人游戏，请使用 `sov new -p Alice -p Bob -p Carol`。 要进行 60 秒的引导教程，请使用 `sov tutorial`。

没有 Python？ `npx` 方式会下载预构建的二进制文件：

```bash
npx @mcptoolshop/sovereignty tutorial
```

## 你的第一个游戏

当您和 2-3 位朋友在桌边时，控制台会运行每一轮，而您负责进行对话。 真实的对局会是这样：

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

`sov status` 显示一个富文本格式的表格，包含玩家的代币、声誉、升级、
位置和目标。 快速查看每轮之间的信息：

```bash
sov status --brief
```

```
R3 |  Alice: 7c 4r 0u | >Bob: 4c 3r 0u |  Carol: 6c 5r 0u
```

(`Nc Nr Nu` = 代币 / 声誉 / 升级； `>` 标记当前玩家。)

重复 15 轮。 `sov game-end` 会打印最终得分。

- **多个已保存的游戏** (v2.1+): `sov games` 列出已保存的游戏； `sov resume <game-id>` 在它们之间切换。
- **批量锚定** (v2.1+): 在游戏结束时，使用 `sov anchor` 将所有待处理的轮次批量打包到一个 XRPL 交易中，每个游戏有一个可验证的链指针。 使用 `sov anchor --checkpoint` 在游戏过程中刷新。
- **网络选择** (v2.1+): `sov anchor --network testnet|mainnet|devnet` (或 `SOV_XRPL_NETWORK` 环境变量；默认为 `testnet`)。
- **守护进程模式** (v2.1+，可选): `sov daemon start` 运行一个本地 HTTP/JSON 服务器，用于桌面集成和后台链轮询。 详情请参见下面的 [守护进程模式](#daemon-mode-optional-v21)。
- **审计查看器桌面应用程序** (v2.1+，可选): `npm --prefix app run tauri dev`。 详情请参见下面的 [桌面应用程序](#desktop-app-optional-v21)。

> 想先进行应用程序内的引导教程吗？ 运行 `sov tutorial`。
> 想在完全不使用任何软件的情况下进行游戏吗？ 请参阅 [Print & Play](docs/print-and-play.md)。
> 想更深入地了解游戏规则吗？ 请参阅 [开始](docs/start_here.md) 或
> [完整手册](https://mcp-tool-shop-org.github.io/sovereignty/handbook/)。

上面的 `sov turn` 示例显示了控制台中一轮游戏的样子；要查看 v2.1 桌面可视化效果，请参阅下面的 [桌面应用程序](#desktop-app-optional-v21)。

## 无需控制台即可游戏

打印卡片，准备一个骰子和一些代币，与 2-4 个人一起坐下来。
游戏可以在桌面上完全运行。

**[开始](docs/start_here.md)** | **[Print & Play](docs/print-and-play.md)** | **[完整规则](docs/rules/campfire_v1.md)** | **[与陌生人一起玩](docs/play-with-strangers.md)**

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

控制台负责记分。 您负责遵守承诺。

## 守护进程模式 (可选，v2.1+)

要进行桌面集成 (审计查看器、Tauri 壳) 或后台链轮询，请将 sovereignty 作为本地 HTTP 守护进程运行：

```bash
pip install 'sovereignty-game[daemon]'
sov daemon start --readonly        # audit-only, no wallet seed
sov daemon start                   # full daemon with anchor endpoints (loads XRPL_SEED)
sov daemon status                  # running | stale | none
sov daemon stop
```

守护进程绑定到 `127.0.0.1` 的一个随机端口；连接详细信息（端口 + 令牌）位于 `.sov/daemon.json` 文件中。 每个项目根目录只能有一个守护进程。 详情请参见 [docs/v2.1-daemon-ipc.md](docs/v2.1-daemon-ipc.md)。

## 桌面应用程序 (可选，v2.1+)

审计查看器是 v2.1 桌面应用程序，它是一个 Tauri 壳 (Rust + webview)，在守护进程之上运行审计查看器和只读的游戏视图。

### 安装 (二进制文件)

v2.1.0 包含预构建的二进制文件，请访问 [GitHub 发布页面](https://github.com/mcp-tool-shop-org/sovereignty/releases/latest)：
```

- **macOS (通用版):** `sovereignty-app-2.1.0-darwin-universal.dmg` — 支持 Intel 和 Apple Silicon 芯片
- **Windows (x64):** `sovereignty-app-2.1.0-win-x64.msi`
- **Linux (x64):** `sovereignty-app-2.1.0-linux-x64.AppImage`

您还需要一个 Python 后台程序来支持该应用：`pip install 'sovereignty-game[daemon]'==2.1.0`。

> **首次启动时可能会出现警告。** macOS 会显示“未识别的开发者”——右键单击 .app 文件，选择“打开”，然后确认。Windows SmartScreen 会显示“未知的发布者”——单击“更多信息”，然后单击“继续运行”。这两个警告都表明 v2.1 版本仅包含构建来源验证信息（使用 `gh attestation verify` 进行验证），不包含操作系统级别的代码签名。操作系统级别的代码签名功能将在 v2.2 版本中提供。

### 验证来源

每个发布版本都包含 SLSA 构建来源验证信息。在运行之前，请进行验证：

```bash
gh attestation verify \
  --repo mcp-tool-shop-org/sovereignty \
  ./sovereignty-app-2.1.0-darwin-universal.dmg
```

成功的验证证明该二进制文件是由特定的提交，以及发布流程，在这个仓库中构建的。这与操作系统级别的代码签名是不同的信任层级——该二进制文件仍然会触发操作系统的警告，但其供应链来源已通过密码学方式进行固定。

### 从源代码构建

如果您想从源代码构建（或者该二进制文件无法在您的平台上运行）：

```bash
# 1. Install Python + daemon deps
pip install -e '.[xrpl,daemon]'

# 2. Install frontend + Rust deps (one-time)
cd app && npm install && cd ..
cargo build --manifest-path app/src-tauri/Cargo.toml

# 3. Start the dev shell (auto-starts the daemon in readonly mode)
npm --prefix app run tauri dev
```

Tauri 壳程序在启动时会自动启动一个只读后台程序，并在退出时自动停止它。外部启动的后台程序（使用 `sov daemon start` 命令）将在 shell 重启后继续运行。

请参阅 [docs/v2.1-tauri-shell.md](docs/v2.1-tauri-shell.md) 了解完整说明。

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

审计查看器包含三个视图：

- **`/audit`** — 基于 XRPL 的证明查看器。可折叠的每个游戏列表、每个回合的锚定状态，"验证所有回合" 会在本地重新计算证明并进行链查找。审计员的视图：确认游戏以诚实的方式运行，而无需读取原始 JSON 数据。
- **`/game`** — 实时显示当前游戏的运行状态。玩家资源卡、回合时间线、最近 20 个 SSE 事件日志。只读；请在另一个终端中使用 CLI 进行游戏。
- **`/settings`** — 显示后台程序配置，并提供网络切换器（测试网络/主网络/开发网络），并带有主网络确认保护措施。

完整的视图说明请参阅 [docs/v2.1-views.md](docs/v2.1-views.md)。

## 工作原理

您从 **5 个硬币** 和 **3 个声誉** 开始。掷骰子，在 16 个格子的棋盘上移动，并停留在可以为您提供选择的格子上：交易、帮助
他人、冒险或抽取卡牌。

**28 张事件卡** 描述了场景：*"有人看到一个小皮囊吗？"* (丢失的钱包) 或 *"没有人看到... 吧？"* (发现捷径)。
包含 8 个市场变化事件，适用于 Town Hall 游戏。

**22 张交易和凭证卡** 会引发对话：*"借我 2 个硬币？我会
还 3 个。"* 或 *"我会支持你，如果你也支持我。"* 交易会设定
目标和截止日期；凭证是您发给其他玩家的欠款。

**承诺规则：** 每回合一次，大声说出“我承诺……”并
承诺某事。遵守承诺：+1 声誉。违反承诺：-2 声誉。
由大家决定。

**道歉：** 游戏中，如果违反了承诺，公开道歉。
向您受到的伤害者支付 1 个硬币，恢复 +1 声誉。

**选择您的目标**（秘密或公开）：
- **繁荣** — 达到 20 个硬币
- **受人喜爱** — 达到 10 个声誉
- **建设者** — 完成 4 个升级

15 轮后，总分最高的获胜。

## 什么是日记模式？

每个回合，控制台可以生成一个 **证明** — 游戏状态的指纹。如果任何
人更改了分数，指纹将不匹配。

可选地，可以将该指纹发布到 **XRPL 测试网络** — 一个
公共账本。可以将其视为在墙上写下分数，没有人
能够擦除。

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

只有主机需要钱包。其他人不需要触摸屏幕。游戏
可以在没有锚定的情况下完美运行——只是日记会记住。

## 三个等级

| 等级 | 名称 | 状态 | 它增加的内容 |
|------|------|--------|-------------|
| 1 | **Campfire** | 可玩 | 金币、声誉、承诺、欠款 |
| 2 | **Town Hall** | 可玩 | 共享市场、资源稀缺 |
| 3 | **Treaty Table** | 可玩 | 带有附加条件的条约——有约束力的承诺 |

核心规则在 v1.x 版本中保持稳定。请参阅 [路线图](docs/roadmap.md)。

## 情景包

没有新的规则。只有氛围。每个包设置一个等级、配方和氛围。

| 情景 | 等级 | 最适合 |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | 篝火/集市日 | 第一局游戏，混合群体 |
| [Market Panic](docs/scenarios/market-panic.md) | 市政厅 | 经济剧 |
| [Promises Matter](docs/scenarios/promises-matter.md) | 篝火 | 信任和承诺 |
| [Treaty Night](docs/scenarios/treaty-night.md) | 条约表 | 高风险协议 |

使用 `sov scenario list` 命令可以在控制台中浏览情景。

## 项目结构

```
sovereignty/
  sov_engine/       # Pure game logic (models, rules, serialization, hashing)
  sov_transport/    # Ledger transport (offline + XRPL Testnet)
  sov_cli/          # Typer CLI (the "Round Console")
  tests/            # Engine, transport, and CLI tests
  docs/             # Rules, cards, print-and-play, play-with-strangers
  assets/print/     # Printable cards, player mat, quick reference
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

> “通过后果来教学，而不是术语。”

玩家通过实践学习：发行欠款、违背承诺、以不断变化的价格进行交易。这些概念与 Web3 的基本原理相关，例如钱包、令牌和信任关系，但玩家无需了解这些知识即可获得乐趣。

## 贡献

贡献最简单的方法是 [添加一张卡片](CONTRIBUTING.md)。
不需要了解引擎知识，只需要一个名称、一个描述和一些描述性文字。

## 安全

钱包密钥、游戏状态和证明文件——哪些应该共享，哪些不应该共享。
没有遥测数据，没有分析，没有向服务器发送数据。唯一的可选网络调用是 XRPL 测试网的锚定。

请参阅 [SECURITY.md](SECURITY.md)。

## 威胁模型

| 威胁 | 缓解措施 |
|--------|-----------|
| 通过证明文件泄露密钥 | 证明文件只包含哈希值，不包含密钥 |
| 密钥存储在 Git 仓库中 | `.sov/` 目录被 Git 忽略；`sov wallet` 命令会发出警告 |
| 游戏状态篡改 | 回合证明的 `envelope_hash` 包含 `game_id`、`round`、`ruleset`、`rng_seed`、`timestamp_utc`、`players` 和 `state`。`sov verify` 命令可以检测到整个信封的篡改。v2.0.0+ 版本不再支持 v1 格式的证明文件。 |
| XRPL 锚定欺骗 | 证明文件的哈希值在链上锚定；`sov verify` 命令可以检测到不匹配的情况 |
| 玩家姓名隐私 | 玩家姓名包含在证明文件（顶级 `players` 列表和玩家快照中）。对于私密游戏，请不要发布 `proof.json` 文件，也不要分享明信片。 |

## 许可证

MIT

---

由 [MCP Tool Shop](https://mcp-tool-shop.github.io/) 构建。
