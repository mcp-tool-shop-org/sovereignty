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
  <a href="https://pypi.org/project/sovereignty-game/"><img src="https://img.shields.io/pypi/v/sovereignty-game?include_prereleases&style=flat&cacheSeconds=3600" alt="PyPI version"></a>
  <a href="https://pypi.org/project/sovereignty-game/"><img src="https://img.shields.io/pypi/pyversions/sovereignty-game?style=flat&cacheSeconds=3600" alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat&cacheSeconds=86400" alt="License: MIT"></a>
  <a href="https://mcp-tool-shop-org.github.io/sovereignty/"><img src="https://img.shields.io/badge/Landing_Page-live-blue?style=flat&cacheSeconds=86400" alt="Landing Page"></a>
</p>

## 今晚一起玩吧

打印[完整的纸质游戏套装](assets/print/pdf/Sovereignty-Print-Pack.pdf)，包括棋盘、玩家垫板、快速参考指南和三副卡牌，共11张美国信纸大小的纸。找一个骰子和一些硬币。和两三个朋友坐在一起。你们可以在二十分钟内开始游戏。

如果您需要单独的页面：

- **[棋盘](assets/print/pdf/board.pdf)**——16格篝火环，一页。
- **[玩家垫板](assets/print/pdf/mat.pdf)**——硬币、声望、升级、承诺。每位玩家一张。
- **[快速参考指南](assets/print/pdf/quickref.pdf)**——棋盘格子、回合顺序、承诺规则。
- **[事件卡牌](assets/print/pdf/events.pdf)**——20张卡牌，三页，沿着线切割。
- **[交易卡牌](assets/print/pdf/deals.pdf)**——10张卡牌，两页。
- **[凭证卡牌](assets/print/pdf/vouchers.pdf)**——玩家之间的10个IOU（欠条），两页。
- **[条约快速参考指南](assets/print/pdf/treaty.pdf)**——仅适用于第三层。

这些PDF文件是矢量图，并嵌入了字体——它们可以在任何家用打印机上清晰地打印出来。设置教程请访问[纸质游戏](docs/print-and-play.md)。

## 想要一个控制台来记录分数吗？

可选。这款游戏也可以在纸上进行。但是，如果有人手边有笔记本电脑，`sov`可以跟踪硬币、声望、承诺，并在最后生成一份防篡改的收据：

```bash
pip install sovereignty-game
sov play campfire_v1
```

`sov play campfire_v1`是一个无需配置的快速启动版本——一个玩家加上一个默认对手。对于桌面上的多人游戏，请使用`sov new -p Alice -p Bob -p Carol`。如果需要一个60秒的引导教程，请使用`sov tutorial`。

没有Python？ `npx`路径会下载一个预构建的二进制文件：

```bash
npx @mcptoolshop/sovereignty tutorial
```

## 一次真实的体验

一旦您和2-3个朋友坐在桌旁，控制台将运行一轮游戏，而你们则进行对话。一次真实的体验如下所示：

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

`sov status`会显示一个格式丰富的表格，其中包含玩家的硬币、声望、升级、位置和目标。为了在回合之间快速查看单行信息：

```bash
sov status --brief
```

```
R3 |  Alice: 7c 4r 0u | >Bob: 4c 3r 0u |  Carol: 6c 5r 0u
```

（`Nc Nr Nu` = 硬币/声望/升级；`>`标记当前玩家。）

重复进行15轮游戏。 `sov game-end`会打印出最终分数。

- **多个已保存的游戏**（v2.1+）：`sov games`列出已保存的游戏；`sov resume <game-id>`在它们之间切换。
- **批量锚定**（v2.1+）：游戏结束时，`sov anchor` 会把待处理回合刷入少量 XRPL AccountSet 交易（每笔最多 8 条 memo；典型的 16 回合 Campfire 会产生 2 笔交易）——不是单笔交易、也不是单个链上指针。中途刷新请用 `sov anchor --checkpoint`。
- **网络选择**（v2.1+）：`sov anchor --network testnet|mainnet|devnet`（或`SOV_XRPL_NETWORK`环境变量；默认值为`testnet`）。
- **守护进程模式**（v2.1+，可选）：`sov daemon start`在本地运行一个HTTP/JSON服务器，用于桌面集成和后台链轮询。请参阅下方的[守护进程模式](#daemon-mode-optional-v21)。
- **审计查看器桌面应用程序**（v2.1+，可选）：`npm --prefix app run tauri dev`。请参阅下方的[桌面应用程序](#desktop-app-optional-v21)。

> 是否想要先进行一个引导式应用内教程？运行`sov tutorial`。
> 是否想要更深入地了解游戏规则？请参见[从这里开始](docs/start_here.md)或[完整手册](https://mcp-tool-shop-org.github.io/sovereignty/handbook/)。

上面的内联`sov turn`示例显示了控制台中一轮游戏的样子；对于v2.1桌面可视化，请参见下方的[桌面应用程序](#desktop-app-optional-v21)。

**[从这里开始](docs/start_here.md)** | **[纸质游戏](docs/print-and-play.md)** | **[完整规则](docs/rules/campfire_v1.md)** | **[与陌生人一起玩](docs/play-with-strangers.md)**

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

为了进行桌面集成（审计查看器、Tauri shell）或后台链轮询，请将主权游戏作为本地HTTP守护进程运行：

```bash
pip install 'sovereignty-game[daemon]'
sov daemon start --readonly        # audit-only, no wallet seed
sov daemon start                   # full daemon with anchor endpoints (loads XRPL_SEED)
sov daemon status                  # running | stale | none
sov daemon stop
```

守护进程绑定到`127.0.0.1`上的随机端口；连接详细信息（端口+ bearer token）位于`.sov/daemon.json`中。每个项目根目录一个守护进程。有关完整的IPC协议，请参见[docs/v2.1-daemon-ipc.md](docs/v2.1-daemon-ipc.md)。

## 桌面应用程序（可选，v2.1+）

审计查看器是v2.1桌面应用程序——一个Tauri shell（Rust + webview），它在守护进程之上运行审计查看器和只读游戏视图。

### 安装（二进制文件）

v2.3.0 已在 git 打标签，但 **未发布 wheel 或桌面资源。** `publish.yml` 运行 33118253060 失败：PyPI 没有 2.3.0 发行版，GitHub Release v2.3.0 的 assets 为空。文件名 `sovereignty-app-2.3.0-{darwin-universal.dmg,win-x64.msi,linux-x64.deb,linux-x64.AppImage}` 会 404。不要固定 `pip install …==2.3.0`。

在后续标签（2.3.1 或修复后的 2.3.x）真正附上文件之前：

- **Python / 守护进程：** `pip install 'sovereignty-game[daemon]'`（当前 PyPI 为 **2.2.1**；未固定的 `pipx` / `npx @mcptoolshop/sovereignty` 也解析到 2.2.1）。
- **桌面应用：** 从源码运行（见下）。在 [GitHub Releases latest](https://github.com/mcp-tool-shop-org/sovereignty/releases/latest) 有对应文件之前，不要从该页下载二进制。

> **首次启动的操作系统警告** 会在确有 attested 二进制发布时出现。那些构建只有 SLSA 构建来源证明——没有 Apple Developer ID / Authenticode 系统级签名。macOS：按住 Control 点击 .app → 打开。Windows SmartScreen：更多信息 → 仍要运行。

### 验证来源

当某个发行版真正附上桌面工件时，请验证你下载的文件：

```bash
gh attestation verify \
  --repo mcp-tool-shop-org/sovereignty \
  ./<downloaded-artifact>
```

清晰的验证证明二进制文件是从特定的提交中构建的，由发布工作流程在当前存储库中构建。这与操作系统级别的代码签名不同——二进制文件仍然会触发操作系统的警告，但其供应链来源已通过密码方式固定。

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

Tauri shell会在启动时自动启动只读守护进程，并在退出时自动停止它。外部启动的守护进程（`sov daemon start`）将在shell重启后继续运行。

请参阅[docs/v2.1-tauri-shell.md](docs/v2.1-tauri-shell.md)以获取完整的协议。

审计查看器提供了三个视图：

- **`/audit`** — 基于 XRPL 的游戏状态验证器。可折叠的游戏列表、每轮锚点状态，“验证所有回合”功能可在本地重新计算证明并按顺序在链上查找。审计员视图：确认游戏是否以诚实的方式进行，无需读取原始 JSON 数据。
- **`/game`** — 当前游戏的被动实时状态显示。玩家资源卡、回合时间线、最近 20 个 SSE 事件日志。仅供阅读；在另一个终端的 CLI 中进行游戏操作。
- **`/settings`** — 守护进程配置显示 + 网络切换器（测试网/主网/开发网），并具有主网确认保护机制。

完整视图规范请参见 [docs/v2.1-views.md](docs/v2.1-views.md)。

## 工作原理

游戏开始时，您拥有 **5 枚硬币**和 **3 点声望**。掷骰子，在 16 格棋盘上移动，并停留在提供各种选择的格子上：交易、帮助他人、冒险或抽取卡牌。

**20 张事件卡**就像一个个小故事：“有人见过一个小皮包吗？”（丢失的钱包）或者“没人看到……对吧？”（发现捷径）。包含适用于市政厅游戏的市场变化事件。

**10 张交易卡 + 10 张凭证卡**促使玩家进行交流：“借我 2 枚硬币好吗？我会还 3 枚。”或者“如果你需要帮助，我也会支持你。”交易设定具有截止日期的目标；凭证是您发给其他玩家的欠条。

**承诺规则：**每轮游戏时，大声说出“我保证……”并承诺做某事。信守承诺：+1 声望。违背承诺：-2 声望。由大家决定。

**道歉：**在整个游戏中，如果违反了承诺，请公开道歉一次。向您伤害的人支付 1 枚硬币，并恢复 +1 声望。

**选择您的目标**（秘密或公开）：
- **繁荣** — 达到 20 枚硬币
- **受人喜爱** — 达到 10 点声望
- **建设者** — 完成 4 次升级

经过 15 轮游戏后，总分最高者获胜。

## 什么是日记模式？

每轮游戏时，控制台都可以生成一个**证明**——游戏状态的指纹。如果有人更改了分数，指纹将不匹配。

可选地，可以将该指纹发布到 **XRPL 测试网**——一个公共账本。您可以将其视为将分数写在墙上，没有人可以擦除。

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

只有主持人需要拥有钱包。其他玩家不需要触碰屏幕。游戏即使没有锚定也可以完美运行——只是日记会记住一切。

## 三个等级

| 等级 | 名称 | 状态 | 新增内容 |
|------|------|--------|-------------|
| 1 | **Campfire** | 可玩 | 硬币、声望、承诺、欠条 |
| 2 | **Town Hall** | 可玩 | 共享市场，资源稀缺 |
| 3 | **Treaty Table** | 可玩 | 带有赌注的协议——具有约束力的承诺 |

核心规则在 v1.x 版本中保持稳定。请参见 [roadmap](docs/roadmap.md)。

## 场景包

没有新的规则。只是氛围不同。每个包都设定了一个等级、配方和情绪。

| 场景 | 等级 | 最适合 |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | 篝火 / 市场日 | 第一次游戏，混合群体 |
| [Market Panic](docs/scenarios/market-panic.md) | 市政厅 | 经济戏剧 |
| [Promises Matter](docs/scenarios/promises-matter.md) | 篝火 | 信任和承诺 |
| [Treaty Night](docs/scenarios/treaty-night.md) | 协议桌 | 高风险协议 |

`sov scenario list` 从控制台浏览。

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

> “通过后果进行教学，而不是通过术语。”

玩家通过实践学习：发行欠条、违背承诺、在不断变化的价格中进行交易。这些概念与 Web3 的基本要素（钱包、令牌、信任关系）相关联，但玩家不必了解这些才能获得乐趣。

## 贡献

最简单的贡献方式是 [添加一张卡牌](CONTRIBUTING.md)。不需要引擎知识——只需要一个名称、描述和一些背景文字。

## 安全性

钱包种子、游戏状态和证明文件——哪些可以共享，哪些不可以共享。没有遥测数据、分析数据或“回家”功能。唯一的可选网络调用是 XRPL 测试网锚定。

请参见 [SECURITY.md](SECURITY.md)。

## 威胁模型

| 威胁 | 缓解措施 |
|--------|-----------|
| 通过证明泄露种子 | 证明仅包含哈希值，绝不包含种子 |
| 种子存储在 git 中 | `.sov/` 已被 git 忽略；`sov wallet` 发出警告 |
| 游戏状态操纵 | 回合证明 `envelope_hash` 涵盖 `game_id`、`round`、`ruleset`、`rng_seed`、`timestamp_utc`、`players` 和 `state`。`sov verify` 检测整个信封中的篡改行为。v2.0.0+ 版本不再支持 v1 版本的证明格式。 |
| XRPL 锚点欺骗 | 将证明哈希值锚定在链上；验证中检测不匹配情况 |
| 玩家姓名隐私 | 玩家姓名包含在证明中（顶级 `players` 列表和玩家快照内部）。对于私有游戏，请不要发布 `proof.json` 或共享明信片。 |

## 许可证

MIT

---

由 [MCP Tool Shop](https://mcp-tool-shop.github.io/) 构建
