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
  <a href="https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://mcp-tool-shop-org.github.io/sovereignty/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

## 今晚玩游戏

打印卡牌，准备一个骰子和一些硬币，与2-4人一起玩。
无需使用任何屏幕。大约需要30分钟。

**[从这里开始](docs/start_here.md)** | **[打印并玩](docs/print-and-play.md)** | **[完整规则](docs/rules/campfire_v1.md)** | **[与陌生人一起玩](docs/play-with-strangers.md)**

## 或者使用控制台

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

控制台记录分数。你遵守承诺。

## 游戏方式

你从**5个硬币**和**3点声望**开始。掷骰子，在16个格子的棋盘上移动，并到达可以让你做出选择的格子：交易、帮助他人、冒险或抽取卡牌。

**20张事件卡牌**描述了各种场景：*"有人看到一个小的皮质小袋子吗？"*（丢失的钱包）或者*"没有人看到……对吧？"*（发现捷径）。

**20张交易卡牌**会引发对话：*"借我2个硬币？我会还3个。"* 或者*"我支持你，如果你也支持我。"*

**承诺规则：** 每回合一次，大声说出“我承诺……”并承诺某事。如果遵守承诺，则获得+1点声望。如果违背承诺，则损失-2点声望。由大家决定。

**道歉：** 游戏中，如果违背了承诺，公开道歉。向受害人支付1个硬币，并恢复+1点声望。

**选择你的目标**（秘密或公开）：
- **繁荣** — 获得20个硬币
- **受人喜爱** — 获得10点声望
- **建设者** — 完成4项升级

15回合后，总分最高的获胜。

## 什么是日记模式？

每个回合，控制台可以生成一个**证明**——游戏的快照。如果有人更改分数，则快照将不匹配。

可选地，可以将此快照发布到**XRPL测试网**——一个公共账本。可以把它想象成在墙上写下分数，没有人可以擦除。

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

只有主机需要一个钱包。其他人不需要使用任何屏幕。游戏在没有锚定的情况下也能完美运行——只是日记会记住。

## 三个等级

| 等级 | 名称 | 状态 | 新增内容 |
|------|------|--------|-------------|
| 1 | **Campfire** | 可玩 | 硬币、声望、承诺、欠款 |
| 2 | **Town Hall** | 可玩 | 共享市场、资源稀缺 |
| 3 | **Treaty Table** | 可玩 | 带有附加条件的条约——有约束力的承诺 |

核心规则在v1.x版本中保持稳定。请参阅[路线图](docs/roadmap.md)。

## 情景包

没有新的规则。只是不同的氛围。每个包都设置了等级、配方和氛围。

| 情景 | 等级 | 适合 |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | 篝火/市场日 | 新手游戏，混合人群 |
| [Market Panic](docs/scenarios/market-panic.md) | 市政厅 | 经济剧 |
| [Promises Matter](docs/scenarios/promises-matter.md) | 篝火 | 信任与承诺 |
| [Treaty Night](docs/scenarios/treaty-night.md) | 条约表 | 高风险协议 |

使用`sov scenario list`命令可以在控制台中浏览情景。

## 项目结构

```
sovereignty/
  sov_engine/       # Pure game logic (models, rules, serialization, hashing)
  sov_transport/    # Ledger transport (offline + XRPL Testnet)
  sov_cli/          # Typer CLI (the "Round Console")
  tests/            # 143 tests
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

> "通过后果来学习，而不是通过术语。"

玩家通过实践来学习：发出欠款单、违背承诺、以不断变化的价格进行交易。这些概念对应于Web3的基本原理——钱包、令牌、信任线——但玩家不需要了解这些才能获得乐趣。

## 贡献

贡献的最简单方法是[添加一张卡牌](CONTRIBUTING.md)。
不需要了解任何引擎知识——只需要一个名称、一个描述和一些描述性文字。

## 安全

钱包密钥、游戏状态和证明文件——哪些应该分享，哪些不应该分享。
没有遥测、没有分析、没有向服务器发送数据。唯一的可选网络调用是XRPL测试网的锚定。

请参阅[SECURITY.md](SECURITY.md)。

## 威胁模型

| 威胁 | 缓解措施 |
|--------|-----------|
| 通过证明文件泄露的种子信息 | 证明文件仅包含哈希值，不包含种子信息。 |
| 种子信息存储在 Git 仓库中。 | `.sov/` 目录被 Git 忽略；`sov wallet` 会发出警告。 |
| 游戏状态的篡改 | 回合证明文件包含完整的游戏状态哈希值；`sov verify` 可以检测到篡改。 |
| XRPL 锚点欺骗 | 证明文件的哈希值与链上锚点相关联；`sov verify` 可以检测到不匹配的情况。 |
| 玩家名称的隐私保护 | 游戏状态仅在本地存储；证明文件不包含玩家名称。 |

## 许可证

MIT

---

由 [MCP Tool Shop](https://mcp-tool-shop.github.io/) 构建。
