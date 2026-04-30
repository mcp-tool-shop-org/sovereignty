<p align="center">
  <a href="README.md">English</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

## 30秒でインストール

最も簡単な方法：Pythonユーザー向け：

```bash
pipx install sovereignty-game
sov tutorial
```

Pythonをお使いでない場合でも、問題ありません。`npx` コマンドを使用すると、あらかじめビルドされたバイナリをダウンロードできます。

```bash
npx @mcptoolshop/sovereignty tutorial
```

これで完了です。`sov tutorial` コマンドを実行すると、約60秒でルールを学ぶことができます。

## 最初のゲーム

あなたと2～3人の友人がテーブルを囲んだら、コンソールがゲームの進行を管理し、あなたが会話をします。実際のプレイは次のようになります。

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

`sov status` コマンドは、プレイヤーのコイン、評判、アップグレード、位置、目標などを表示する、Rich形式の表を表示します。ターン間の簡単な確認には、次の形式を使用します。

```bash
sov status --brief
```

```
R3 |  Alice: 7c 4r 0u | >Bob: 4c 3r 0u |  Carol: 6c 5r 0u
```

(`Nc Nr Nu` = コイン / 評判 / アップグレード; `>` はアクティブなプレイヤーを示します。)

15ラウンド繰り返します。`sov game-end` コマンドを実行すると、最終スコアが表示されます。

> まず、ゲーム内チュートリアルを試してみたいですか？ `sov tutorial` コマンドを実行してください。
> ソフトウェアを使わずにプレイしたいですか？ [Print & Play](docs/print-and-play.md) を参照してください。
> より詳細なルールを知りたいですか？ [ここから始めましょう](docs/start_here.md) または、[完全なマニュアル](https://mcp-tool-shop-org.github.io/sovereignty/handbook/) を参照してください。

> _短いデモGIFまたはスクリーンショットがここに表示されるべきです。これはStage Dのフォローアップとして追跡され、READMEに実際のゲームプレイの様子を表示できるようにします。_

## コンソールなしでプレイ

カードを印刷し、サイコロとコインを用意して、2～4人でテーブルを囲みます。ゲームは完全にテーブル上でプレイできます。

**[ここから始めましょう](docs/start_here.md)** | **[Print & Play](docs/print-and-play.md)** | **[完全なルール](docs/rules/campfire_v1.md)** | **[見知らぬ人とプレイ](docs/play-with-strangers.md)**

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

コンソールがスコアを記録します。あなたは約束を守ります。

## 仕組み

ゲーム開始時に、**5つのコイン**と**3の評判**を持っています。サイコロを振り、16マスあるボード上を移動し、トレード、誰かを助ける、リスクを冒す、またはカードを引くなどの選択肢があるマスに止まります。

**28枚のイベントカード**は、まるで出来事のように書かれています。例えば、*"小さな革製の小銭入れを見た人いますか？"* (Lost Wallet) または *"誰も見ていないよね？"* (Found a Shortcut)。タウンホールゲーム用のマーケットシフトイベントが8枚含まれています。

**22枚の取引とバウチャーカード**は、会話を促します。例えば、*"2つのコインを貸してくれませんか？代わりに3つ返します。"* または *"もし君が助けてくれれば、僕も君を助けるよ。"* 取引は目標と期限を設定し、バウチャーは他のプレイヤーに発行する借用証です。

**約束のルール:** 1ラウンドに1回、「約束します…」と声に出して、何かを約束します。それを守ると、評判が+1上がります。約束を破ると、評判が-2下がります。テーブルの全員で判断します。

**謝罪:** 1ゲームに1回、約束を破った場合、公に謝罪します。不正を行った人に1つのコインを支払い、評判を+1回復します。

**目標を選択**（秘密または公開）：
- **繁栄:** 20個のコインに到達
- **愛される存在:** 10の評判に到達
- **建築家:** 4つのアップグレードを完了

15ラウンド後、合計スコアが最も高い人が勝ちます。

## Diary Modeとは？

各ラウンドで、コンソールはゲームの状態の**証明**（フィンガープリント）を生成できます。もし誰かがスコアを変更した場合、フィンガープリントは一致しません。

オプションで、そのフィンガープリントを**XRPL Testnet**（パブリックな台帳）に投稿できます。これは、誰も消去できない壁にスコアを書き込むようなものです。

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

ウォレットが必要なのはホストだけです。他のプレイヤーは画面に触れません。ゲームは完全にアンカーなしで動作します。記録を保持するのは、あくまで「日記」です。

## 3つのレベル

| レベル | 名前 | ステータス | 追加される機能 |
|------|------|--------|-------------|
| 1 | **Campfire** | プレイ可能 | コイン、評判、約束、借用証書 |
| 2 | **Town Hall** | プレイ可能 | 共有市場、資源の枯渇 |
| 3 | **Treaty Table** | プレイ可能 | 条件付き条約 — 実効力のある約束 |

コアとなるルールはv1.xのバージョンを通じて安定しています。詳細については、[ロードマップ](docs/roadmap.md)をご覧ください。

## シナリオパック

新しいルールは一切ありません。雰囲気だけです。各パックは、ティア、レシピ、ムードを設定します。

| シナリオ | レベル | 特におすすめな状況 |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | 焚き火 / マーケットデイ | 初めてのゲーム、様々なグループ |
| [Market Panic](docs/scenarios/market-panic.md) | タウンホール | 経済的なドラマ |
| [Promises Matter](docs/scenarios/promises-matter.md) | 焚き火 | 信頼とコミットメント |
| [Treaty Night](docs/scenarios/treaty-night.md) | 条約テーブル | 高リスクな合意 |

コンソールから`sov scenario list`でシナリオの一覧を表示できます。

## プロジェクトの構成

```
sovereignty/
  sov_engine/       # Pure game logic (models, rules, serialization, hashing)
  sov_transport/    # Ledger transport (offline + XRPL Testnet)
  sov_cli/          # Typer CLI (the "Round Console")
  tests/            # Engine, transport, and CLI tests
  docs/             # Rules, cards, print-and-play, play-with-strangers
  assets/print/     # Printable cards, player mat, quick reference
```

## 開発

```bash
git clone https://github.com/mcp-tool-shop-org/sovereignty.git
cd sovereignty
uv sync --dev
uv run pytest tests/ -v
uv run ruff check .
```

## 設計原則

> 「用語ではなく、結果を通して教える。」

プレイヤーは、借用証書を発行したり、約束を破ったり、変動する価格で取引したりすることで学びます。これらの概念は、Web3の基本的な要素（ウォレット、トークン、信用取引など）に対応していますが、プレイヤーはそれらを理解していなくても楽しむことができます。

## 貢献

最も簡単な貢献方法は、[カードを追加する](CONTRIBUTING.md)ことです。
エンジンに関する知識は不要です。名前、説明、そして簡単なテキストがあればOKです。

## セキュリティ

ウォレットのシード、ゲームの状態、および証明ファイル。何を共有し、何を共有しないか。
テレメトリー、アナリティクス、および自動的なデータ送信はありません。オプションのネットワーク接続は、XRPL Testnetへのアンカー接続のみです。

[SECURITY.md](SECURITY.md) をご確認ください。

## 脅威モデル

| 脅威 | 対策 |
|--------|-----------|
| 証明書を介したシード情報の漏洩 | 証明書にはハッシュのみが含まれており、シード情報は含まれていません。 |
| gitリポジトリへのシード情報の登録 | `.sov/` はgitで無視されます。`sov wallet` コマンドは、シード情報の取り扱いについて警告を表示します。 |
| ゲームの状態の改ざん | ラウンドの証明における `envelope_hash` は、`game_id`、`round`、`ruleset`、`rng_seed`、`timestamp_utc`、`players`、および `state` をカバーします。`sov verify` コマンドは、証明全体に対する改ざんを検出します。証明のフォーマット v1 は、v2.0.0 以降ではサポートされていません。 |
| XRPLアンカーの偽装 | 証明書のハッシュはオンチェーンでアンカーされており、`sov verify` コマンドで不一致を検出します。 |
| プレイヤー名のプライバシー | プレイヤー名は、証明書に含まれています（トップレベルの `players` リストと、プレイヤーのスナップショット内）。プライベートなプレイの場合、`proof.json` ファイルを公開したり、ポストカードを共有したりしないでください。 |

## ライセンス

MIT

---

[MCP Tool Shop](https://mcp-tool-shop.github.io/) が開発しました。
