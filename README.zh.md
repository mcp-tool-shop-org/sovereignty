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

```text
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

## 30秒内安装

最快的方法——Python用户：

```bash
pipx install sovereignty-game
sov tutorial
```

没有Python？没问题。`npx`命令会下载一个预构建的二进制文件：

```bash
npx @mcptoolshop/sovereignty tutorial
```

就这样。`sov tutorial`会引导您了解游戏规则，大约需要60秒。

## 您的第一个游戏

当您和2-3位朋友围坐在桌旁时，控制台会运行每一轮，而您则负责进行互动。一个完整的游戏过程如下：

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

`sov status`会显示一个富文本格式的表格，包含玩家的金币、声望、升级、位置和目标。为了在每回合之间快速查看：

```bash
sov status --brief
```

```
R3 |  Alice: 7c 4r 0u | >Bob: 4c 3r 0u |  Carol: 6c 5r 0u
```

(`Nc Nr Nu` = 金币 / 声望 / 升级；`>`表示当前玩家。)

重复15轮。`sov game-end`会打印最终得分。

> 想先进行一次应用内引导吗？运行`sov tutorial`。
> 想完全不使用任何软件来玩吗？请查看[Print & Play](docs/print-and-play.md)。
> 想更深入地了解游戏规则吗？请查看[开始这里](docs/start_here.md)或
> [完整手册](https://mcp-tool-shop-org.github.io/sovereignty/handbook/)。

> _一个简短的演示GIF或截图应该放在这里——作为一个Stage D的后续任务，以便README可以展示一个回合的实际过程。_

## 无需控制台即可游戏

打印卡牌，准备一个骰子和一些金币，与2-4人一起坐下来。游戏可以在桌面上完全进行。

**[开始这里](docs/start_here.md)** | **[Print & Play](docs/print-and-play.md)** | **[完整规则](docs/rules/campfire_v1.md)** | **[与陌生人一起玩](docs/play-with-strangers.md)**

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

控制台负责记分。您负责信守承诺。

## 工作原理

您从**5个金币**和**3点声望**开始。掷骰子，在16个格子的棋盘上移动，并停留在可以做出选择的格子上：交易、帮助他人、冒险或抽取卡牌。

**28张事件卡**描述了各种场景：*"有人看到一个小皮囊吗？"*（丢失的钱包）或*"没有人看到...对吧？"*（发现捷径）。包含8张市场变动事件卡，用于市政厅游戏。

**22张交易和优惠券卡**会引发对话：*"借我2个金币吗？我会还3个。"*或*"我罩你，你罩我。"* 交易会设定带有截止日期的目标；优惠券是您发给其他玩家的IOU（即欠条）。

**承诺规则：** 每回合一次，大声说出“我承诺...”并做出承诺。遵守承诺：+1声望。违背承诺：-2声望。由大家决定。

**道歉：** 游戏中，如果违反了承诺，公开道歉。支付1个金币给您伤害的人，恢复+1声望。

**选择您的目标**（秘密或公开）：
- **繁荣** — 达到20个金币
- **受人喜爱** — 达到10点声望
- **建设者** — 完成4次升级

15轮后，总得分最高的获胜。

## 什么是日记模式？

每回合，控制台可以生成一个**证明**——游戏状态的指纹。如果有人更改了得分，指纹将不匹配。

可选地，可以将该指纹发布到**XRPL Testnet**——一个公共账本。可以将其视为在没有人能擦除的墙上写下得分。

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

只有主机需要一个钱包。其他人不需要触碰屏幕。游戏可以在没有锚定的情况下完美运行——只是日记会记住。

## 三个等级

| 等级 | 名称 | 状态
``` | 它增加的内容 |
|------|------|--------|-------------|
| 1 | **Campfire** | 可玩性 | 金币、声誉、承诺、欠款 |
| 2 | **Town Hall** | 可玩性 | 共享市场、资源稀缺 |
| 3 | **Treaty Table** | 可玩性 | 带有约束条件的条约——有实际意义的承诺 |

核心规则在 v1.x 版本中保持稳定。请参阅[路线图](docs/roadmap.md)。

## 情景包

没有新的规则。只有氛围。每个包都设置一个等级、配方和氛围。

| 情景 | 等级 | 最适合 |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | 篝火/集市日 | 新手游戏，混合团队 |
| [Market Panic](docs/scenarios/market-panic.md) | 市政厅 | 经济剧 |
| [Promises Matter](docs/scenarios/promises-matter.md) | 篝火 | 信任与承诺 |
| [Treaty Night](docs/scenarios/treaty-night.md) | 条约桌 | 高风险协议 |

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

> “通过后果来学习，而不是通过术语。”

玩家通过实践学习：发行欠款、违背承诺、以不断变化的价格进行交易。这些概念与 Web3 的基本原理相关，例如钱包、令牌和信任关系，但玩家无需了解这些知识即可获得乐趣。

## 贡献

贡献最简单的方法是[添加一张卡片](CONTRIBUTING.md)。
无需了解引擎知识，只需要一个名称、一个描述和一些补充说明。

## 安全性

钱包密钥、游戏状态和证明文件——哪些应该共享，哪些不应该共享。
没有遥测数据，没有分析，没有“远程控制”功能。唯一的可选网络调用是 XRPL 测试网的锚定。

请参阅[SECURITY.md](SECURITY.md)。

## 威胁模型

| 威胁 | 缓解措施 |
|--------|-----------|
| 通过证明文件泄露密钥 | 证明文件仅包含哈希值，不包含密钥 |
| 密钥存储在 Git 仓库中 | `.sov/` 目录被 Git 忽略；`sov wallet` 命令会发出警告 |
| 游戏状态篡改 | 回合证明的 `envelope_hash` 包含 `game_id`、`round`、`ruleset`、`rng_seed`、`timestamp_utc`、`players` 和 `state`。`sov verify` 命令可以检测到整个信封的篡改。v2.0.0+ 版本不再支持 v1 格式的证明文件。 |
| XRPL 锚点伪造 | 证明文件的哈希值在链上进行锚定；`sov verify` 命令可以检测到不匹配的情况。 |
| 玩家姓名隐私 | 玩家姓名包含在证明文件（顶级 `players` 列表和玩家快照中）中。对于私密游戏，请不要发布 `proof.json` 文件或分享明信片。 |

## 许可证

MIT

---

由 [MCP Tool Shop](https://mcp-tool-shop.github.io/) 构建。
