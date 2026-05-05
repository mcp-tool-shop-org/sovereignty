<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.md">English</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

```
<!--
徽标样式策略 (Stage D / W7CIDOCS-001): 所有徽标都使用 shields.io
默认使用 `flat` 样式，以保持视觉一致性。 每个 shields.io URL 都设置了
`cacheSeconds=3600`，因此当上游注册中心速度较慢时，缓存未命中会回退到
上一次已知的值，而不是显示空白。 GitHub 的 CI 徽标是 GitHub 自己的 SVG 格式，
因此不受此处的限制，GitHub 会使用其自己的缓存机制提供该徽标。
-->
<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/sovereignty-game/"><img src="https://img.shields.io/pypi/v/sovereignty-game?include_prereleases&style=flat&cacheSeconds=3600" alt="PyPI version"></a>
  <a href="https://pypi.org/project/sovereignty-game/"><img src="https://img.shields.io/pypi/pyversions/sovereignty-game?style=flat&cacheSeconds=3600" alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat&cacheSeconds=86400" alt="License: MIT"></a>
  <a href="https://mcp-tool-shop-org.github.io/sovereignty/"><img src="https://img.shields.io/badge/Landing_Page-live-blue?style=flat&cacheSeconds=86400" alt="Landing Page"></a>
</p>

## 今晚开始游戏

打印 [完整的打印游戏包](assets/print/pdf/Sovereignty-Print-Pack.pdf)——包括游戏板、玩家垫、快速参考以及 11 张美国标准信纸上的三副卡牌。 找一个骰子和一些硬币。 找两个或三个朋友一起玩。 你们可以在 20 分钟内开始游戏。

如果您需要单独的卡牌：

- **[游戏板](assets/print/pdf/board.pdf)** — 包含 16 个营火地点的游戏板，单页。
- **[玩家垫](assets/print/pdf/mat.pdf)** — 用于记录硬币、声誉、升级和承诺。 每个玩家一张。
- **[快速参考](assets/print/pdf/quickref.pdf)** — 包含游戏板上的地点、回合顺序和承诺规则。
- **[事件卡](assets/print/pdf/events.pdf)** — 20 张卡牌，3 页，沿虚线剪裁。
- **[交易卡](assets/print/pdf/deals.pdf)** — 10 张卡牌，2 页。
- **[代金券卡](assets/print/pdf/vouchers.pdf)** — 10 张玩家之间的 IOU，2 页。
- **[条约快速参考](assets/print/pdf/treaty.pdf)** — 仅适用于 3 级。

这些 PDF 文件是矢量格式，并嵌入了字体，因此可以在任何家用打印机上清晰打印。 游戏设置的详细说明请参考 [打印游戏](docs/print-and-play.md)。

## 想要一个控制台来记录分数吗？

可选。 游戏可以在纸上进行。 但是，如果有人有一台笔记本电脑，`sov` 可以跟踪硬币、声誉、承诺，并在游戏结束时生成一个防篡改的收据：

```bash
pip install sovereignty-game
sov play campfire_v1
```

`sov play campfire_v1` 是一个无需配置的快速启动版本，包含一个真人玩家和一个默认的对手。 对于多人游戏，请使用 `sov new -p Alice -p Bob -p Carol`。 要进行 60 秒的引导教程，请使用 `sov tutorial`。

没有安装 Python 吗？ 使用 `npx` 命令可以下载预编译的二进制文件：

```bash
npx @mcptoolshop/sovereignty tutorial
```

## 一个真实的对局

当您和 2-3 个朋友在桌边时，控制台会运行游戏回合，而您负责进行游戏。 真实的对局会是这样：

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

`sov status` 会显示一个格式化的表格，其中包含玩家的硬币、声誉、升级、位置和目标。 在每个回合之间快速查看：

```bash
sov status --brief
```

```
R3 |  Alice: 7c 4r 0u | >Bob: 4c 3r 0u |  Carol: 6c 5r 0u
```

(`Nc Nr Nu` = 硬币 / 声誉 / 升级； `>` 标记当前玩家。)

重复 15 个回合。 `sov game-end` 会打印最终得分。

- **多个已保存的游戏** (v2.1+): `sov games` 列出已保存的游戏； `sov resume <game-id>` 可以在它们之间切换。
- **批量锚定** (v2.1+): 在游戏结束时，使用 `sov anchor` 将所有待处理的回合批量处理到一个 XRPL 交易中，从而为每个游戏创建一个可验证的链指针。 使用 `sov anchor --checkpoint` 在游戏过程中刷新数据。
- **网络选择** (v2.1+): `sov anchor --network testnet|mainnet|devnet` (或 `SOV_XRPL_NETWORK` 环境变量；默认为 `testnet`)。
- **守护进程模式** (v2.1+，可选): `sov daemon start` 运行一个本地 HTTP/JSON 服务器，用于桌面集成和后台链轮询。 详情请参阅 [守护进程模式](#daemon-mode-optional-v21) 部分。
- **审计查看器桌面应用程序** (v2.1+，可选): `npm --prefix app run tauri dev`。 详情请参阅 [桌面应用程序](#desktop-app-optional-v21) 部分。

> 想要先进行一个引导式的应用程序内教程吗？ 运行 `sov tutorial`。
> 想要更深入地了解游戏规则吗？ 请参阅 [开始](docs/start_here.md) 或
> [完整指南](https://mcp-tool-shop-org.github.io/sovereignty/handbook/)。

上面的 `sov turn` 示例展示了游戏回合在控制台中的样子；要查看 v2.1 桌面应用程序的可视化效果，请参阅 [桌面应用程序](#desktop-app-optional-v21) 部分。
```

**[开始](docs/start_here.md)** | **[打印版](docs/print-and-play.md)** | **[完整规则](docs/rules/campfire_v1.md)** | **[与陌生人一起玩](docs/play-with-strangers.md)**

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

控制台记录分数。你遵守承诺。

## 守护进程模式（可选，v2.1+）

要进行桌面集成（审计查看器、Tauri 壳）或后台链轮询，请将 sovereignty 作为本地 HTTP 守护进程运行：

```bash
pip install 'sovereignty-game[daemon]'
sov daemon start --readonly        # audit-only, no wallet seed
sov daemon start                   # full daemon with anchor endpoints (loads XRPL_SEED)
sov daemon status                  # running | stale | none
sov daemon stop
```

守护进程绑定到 `127.0.0.1` 的一个随机端口；连接信息（端口 + 令牌）位于 `.sov/daemon.json` 文件中。每个项目根目录只能有一个守护进程。有关完整的 IPC 协议，请参阅 [docs/v2.1-daemon-ipc.md](docs/v2.1-daemon-ipc.md)。

## 桌面应用程序（可选，v2.1+）

审计查看器是 v2.1 桌面应用程序，它是一个 Tauri 壳（Rust + Web 视图），在守护进程之上运行审计查看器和只读游戏视图。

### 安装（二进制文件）

v2.1.0 提供了预构建的二进制文件，位于 [GitHub 发布页面](https://github.com/mcp-tool-shop-org/sovereignty/releases/latest)：

- **macOS (通用):** `sovereignty-app-2.1.0-darwin-universal.dmg` — Intel + Apple Silicon
- **Windows (x64):** `sovereignty-app-2.1.0-win-x64.msi`
- **Linux (x64, .deb):** `sovereignty-app-2.1.0-linux-x64.deb` — Debian / Ubuntu / 及其衍生版本。使用 `sudo dpkg -i sovereignty-app-2.1.0-linux-x64.deb` 进行安装。AppImage 支持将在 v2.2 中实现（上游 `linuxdeploy` / Ubuntu 24.04 FUSE 交互）。

您还需要 Python 守护进程来支持该应用程序：`pip install 'sovereignty-game[daemon]'==2.1.0`。

> **首次启动时可能会出现警告。** macOS 会显示“未识别的开发者”——右键单击 .app 文件，选择“打开”，然后确认。Windows SmartScreen 会显示“未知的发布者”——单击“更多信息”，然后单击“继续运行”。这两个警告都表明 v2.1 包含构建来源证明（使用 `gh attestation verify` 进行验证），而不是操作系统级别的代码签名。工作区级别的签名基础设施将在 v2.2 中实现。

### 验证来源

每个发布版本都包含 SLSA 构建来源证明。在运行之前进行验证：

```bash
gh attestation verify \
  --repo mcp-tool-shop-org/sovereignty \
  ./sovereignty-app-2.1.0-darwin-universal.dmg
```

干净的验证证明该二进制文件是由特定提交，通过发布工作流程，在这个仓库中构建的。这与操作系统级别的代码签名是不同的信任层——该二进制文件仍然会触发操作系统警告，但其供应链来源是经过密码学验证的。

### 从源代码构建

如果您更喜欢从源代码构建（或者二进制文件无法在您的平台上运行）：

```bash
# 1. Install Python + daemon deps
pip install -e '.[xrpl,daemon]'

# 2. Install frontend + Rust deps (one-time)
cd app && npm install && cd ..
cargo build --manifest-path app/src-tauri/Cargo.toml

# 3. Start the dev shell (auto-starts the daemon in readonly mode)
npm --prefix app run tauri dev
```

Tauri 壳在启动时会自动启动一个只读守护进程，并在退出时自动停止它。外部启动的守护进程（`sov daemon start`）将在 shell 重启后保持运行。

有关完整的协议，请参阅 [docs/v2.1-tauri-shell.md](docs/v2.1-tauri-shell.md)。

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

- **`/audit`** — 基于 XRPL 的证明查看器。可折叠的每个游戏列表，每个回合的锚定状态，"验证所有回合" 会运行本地证明重新计算 + 链查找。审计员的视图：确认游戏是否诚实运行，而无需读取原始 JSON。
- **`/game`** — 用于活动游戏的实时状态显示。玩家资源卡、回合时间线、最后 20 个 SSE 事件日志。只读；在另一个终端的 CLI 中进行游戏。
- **`/settings`** — 守护进程配置显示 + 网络切换器（测试网络 / 主网络 / 开发网络），带有主网络确认保护。

完整的视图规范位于 [docs/v2.1-views.md](docs/v2.1-views.md)。

## 工作原理

您从 **5 个硬币** 和 **3 个声誉** 开始。掷骰子，在 16 个空间的棋盘上移动，并停留在提供选择的格子上：交易、帮助他人、冒险或抽取卡牌。

**20张事件卡**，内容如同生活中的瞬间：“谁看到一个小的皮质小包了吗？”（丢失的钱包）或者“没有人看到……对吧？”（发现了一条捷径）。包含适用于“市政厅”游戏的市场变化事件。

**10张交易卡 + 10张凭证卡**，旨在促进交流：“借我2个硬币？我之后会还3个。”或者“我罩你，你罩我。” 交易卡设定目标和截止日期；凭证卡是您发给其他玩家的欠款凭证。

**“承诺”规则：** 每轮，您可以大声说出“我承诺……”并承诺某事。如果遵守承诺：+1声誉。如果违背承诺：-2声誉。由大家决定。

**“道歉”：** 每局游戏，如果您违背了承诺，请公开道歉。向您伤害的人支付1个硬币，恢复+1声誉。

**选择您的目标**（秘密或公开）：
- **繁荣** — 获得20个硬币
- **受人喜爱** — 获得10点声誉
- **建设者** — 完成4次升级

15轮后，总得分最高的玩家获胜。

## 什么是日记模式？

每轮，控制台可以生成一个**证明**——游戏状态的指纹。如果有人更改分数，指纹将不匹配。

可选地，可以将此指纹发布到**XRPL测试网**——一个公共账本。可以把它想象成在墙上写下分数，没有人可以擦除。

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

只有主机需要一个钱包。其他人不需要触碰屏幕。游戏在没有锚定的情况下也能完美运行——只是日记会记住。

## 三个等级

| 等级 | 名称 | 状态 | 新增内容 |
|------|------|--------|-------------|
| 1 | **Campfire** | 可玩 | 硬币、声誉、承诺、IOU |
| 2 | **Town Hall** | 可玩 | 共享市场、资源稀缺 |
| 3 | **Treaty Table** | 可玩 | 带有约束的条约——带有约束力的承诺 |

核心规则在v1.x版本中保持稳定。请参阅[路线图](docs/roadmap.md)。

## 情景包

没有新的规则。只是不同的氛围。每个包都设置了等级、配方和氛围。

| 情景 | 等级 | 最适合 |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | 篝火/市场日 | 第一局游戏，混合群体 |
| [Market Panic](docs/scenarios/market-panic.md) | 市政厅 | 经济剧 |
| [Promises Matter](docs/scenarios/promises-matter.md) | 篝火 | 信任与承诺 |
| [Treaty Night](docs/scenarios/treaty-night.md) | 条约表 | 高风险协议 |

使用`sov scenario list`命令，可以在控制台中浏览情景。

## 项目结构

```
sovereignty/
  sov_engine/       # Pure game logic (models, rules, serialization, hashing)
  sov_transport/    # Ledger transport (offline + XRPL Testnet)
  sov_cli/          # Typer CLI (the "Round Console")
  tests/            # Engine, transport, and CLI tests
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

> “通过后果来学习，而不是通过术语。”

玩家通过实践学习：发行IOU、违背承诺、以不断变化的价格进行交易。这些概念映射到Web3的基本原理——钱包、令牌、信任线——但玩家不需要了解这些才能获得乐趣。

## 贡献

贡献最简单的方法是[添加一张卡片](CONTRIBUTING.md)。不需要了解引擎知识——只需要一个名称、一个描述和一些描述性文字。

## 安全

钱包密钥、游戏状态和证明文件——哪些应该分享，哪些不应该分享。没有遥测、没有分析、没有“回传”功能。唯一的可选网络调用是XRPL测试网的锚定。

请参阅[SECURITY.md](SECURITY.md)。

## 威胁模型

| 威胁 | 缓解措施 |
|--------|-----------|
| 通过证明泄露的密钥 | 证明只包含哈希值，不包含密钥 |
| 密钥存储在git中 | `.sov/`目录被git忽略；`sov wallet`命令会发出警告 |
| 游戏状态篡改 | 轮次证明的`envelope_hash`包含`game_id`、`round`、`ruleset`、`rng_seed`、`timestamp_utc`、`players`和`state`。`sov verify`命令可以检测到整个信封的篡改。v2.0.0+版本不再支持v1格式的证明。 |
| XRPL锚定欺骗 | 哈希值与链上数据锚定；验证过程中检测不匹配情况。 |
| 玩家姓名隐私 | 玩家姓名包含在证明数据中（顶级 `players` 列表以及玩家快照内部）。为了保护隐私，请不要发布 `proof.json` 文件，也不要分享明信片。 |

## 许可协议

MIT 协议

---

由 [MCP Tool Shop](https://mcp-tool-shop.github.io/) 构建。
