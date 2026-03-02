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
  <a href="https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://mcp-tool-shop-org.github.io/sovereignty/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

## 今夜プレイしましょう

カードを印刷し、サイコロとコインを用意して、2～4人で一緒にプレイします。
画面は不要です。約30分で終わります。

**[ここから始める](docs/start_here.md)** | **[印刷してプレイ](docs/print-and-play.md)** | **[完全なルール](docs/rules/campfire_v1.md)** | **[見知らぬ人とプレイ](docs/play-with-strangers.md)**

## または、コンソールを使用します

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

コンソールがスコアを記録します。あなたは言葉を守ります。

## 遊び方

ゲーム開始時に、**5つのコイン**と**3の評判**があります。サイコロを振り、16マスある盤面を移動し、選択肢が現れるマスに止まります。選択肢は、取引、誰かを助ける、リスクを取る、またはカードを引く、です。

**20枚のイベントカード**は、まるで出来事のように書かれています。例えば、「小さな革製の小銭入れを見た人いますか？」（落とし物）や「誰も見ていないよね？」（抜け道を見つけた）。

**20枚の取引カード**は、会話を促します。「2つのコイン貸してくれませんか？代わりに3つ返します。」や「君が助けてくれれば、僕も君を助けるよ。」といった内容です。

**約束のルール:** 1ラウンドに1回、「約束します…」と言い、何かを約束します。それを守ると評判が+1、破ると評判が-2になります。誰が約束を守ったか、破ったかは、テーブルの全員で判断します。

**謝罪:** 1ゲームに1回、もし約束を破ってしまったら、公に謝罪します。違反した相手に1つのコインを支払い、評判を+1回復します。

**目標を選びましょう**（秘密でも公開でも可）：
- **繁栄:** 20個のコインを獲得する
- **愛される存在:** 10の評判を獲得する
- **建築家:** 4つのアップグレードを完了する

15ラウンド後、合計スコアが最も高い人が勝ちです。

## 「ダイアリーモード」とは？

各ラウンドで、コンソールはゲームの状態の「証拠」を生成できます。もし誰かがスコアを変更した場合、その証拠は一致しません。

オプションで、その証拠を**XRPLテストネット**という公開台帳に投稿できます。これは、誰も消せない壁にスコアを書き込むようなものです。

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

ウォレットが必要なのは、ホストだけです。他のプレイヤーは画面に触れる必要はありません。このゲームは、アンカーリング（外部との連携）なしでも完全に動作します。スコアを記録する「ダイアリー」だけが必要です。

## 3つのティア（段階）

| ティア | 名前 | ステータス | 追加されるもの |
|------|------|--------|-------------|
| 1 | **Campfire** | プレイ可能 | コイン、評判、約束、借用証書 |
| 2 | **Town Hall** | プレイ可能 | 共有マーケット、資源の枯渇 |
| 3 | **Treaty Table** | プレイ可能 | 条件付きの条約 — 義務を伴う約束 |

コアとなるルールは、v1.xのバージョンでは安定しています。ロードマップについては、[こちら](docs/roadmap.md)をご覧ください。

## シナリオパック

新しいルールはありません。雰囲気だけです。各パックは、ティア、レシピ、ムードを設定します。

| シナリオ | ティア | おすすめのプレイ人数 |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | キャンプファイヤー / マーケットデー | 初めてプレイする人、グループのメンバーが混ざっている場合 |
| [Market Panic](docs/scenarios/market-panic.md) | タウンホール | 経済的なドラマ |
| [Promises Matter](docs/scenarios/promises-matter.md) | キャンプファイヤー | 信頼と約束 |
| [Treaty Night](docs/scenarios/treaty-night.md) | 条約テーブル | リスクの高い合意 |

コンソールからシナリオリストを表示するには、`sov scenario list`と入力します。

## プロジェクトの構成

```
sovereignty/
  sov_engine/       # Pure game logic (models, rules, serialization, hashing)
  sov_transport/    # Ledger transport (offline + XRPL Testnet)
  sov_cli/          # Typer CLI (the "Round Console")
  tests/            # 143 tests
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

プレイヤーは、IOU（借用証書）を発行したり、約束を破ったり、価格が変動する中で取引をしたりすることで学びます。これらの概念は、ウォレット、トークン、信頼ラインなど、Web3の基本的な要素に対応していますが、プレイヤーはそれらを理解していなくても楽しめます。

## 貢献

最も簡単な貢献方法は、[カードを追加する](CONTRIBUTING.md)ことです。
エンジンに関する知識は必要ありません。名前、説明、そして少しの文章があればOKです。

## セキュリティ

ウォレットのシード、ゲームの状態、そして証拠ファイル — 何を共有し、何を共有しないか。
テレメトリー（遠隔監視）、分析、そして「電話で家に帰る」機能はありません。オプションのネットワーク接続は、XRPLテストネットへのアンカーリングだけです。

[SECURITY.md](SECURITY.md)をご覧ください。

## 脅威モデル

| 脅威 | 軽減策 |
|--------|-----------|
| 証明書からのシード情報の漏洩 | 証明書にはハッシュ値のみが含まれており、シード情報は含まれません。 |
| Gitリポジトリへのシード情報の保存 | `.sov/` フォルダはGitで無視されます。`sov wallet` コマンドは警告を表示します。 |
| ゲームの状態の改ざん | ラウンドの証明書はゲームの状態全体のハッシュ値を含みます。`sov verify` コマンドは改ざんを検出します。 |
| XRPL（XRP Ledger）の偽装 | 証明書のハッシュ値はブロックチェーン上に記録されます。`sov verify` コマンドで不一致を検出します。 |
| プレイヤー名のプライバシー保護 | ゲームの状態はローカルでのみ保存され、証明書にはプレイヤー名が含まれません。 |

## ライセンス

MITライセンス

---

[MCP Tool Shop](https://mcp-tool-shop.github.io/) によって作成されました。
