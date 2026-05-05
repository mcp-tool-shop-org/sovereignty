<p align="center">
  <a href="README.md">English</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

## 今夜プレイしましょう

[印刷してプレイできるパッケージ全体](assets/print/pdf/Sovereignty-Print-Pack.pdf)を印刷します。これには、ゲームボード、プレイヤー用マット、クイックリファレンス、そして11枚のUSレターサイズの紙に印刷されるカードの3つのデッキが含まれます。サイコロとコインを用意してください。2～3人の友達と集まってください。20分でプレイできます。

個別のシートが必要な場合は、以下をご覧ください。

- **[ゲームボード](assets/print/pdf/board.pdf)**：16マス構成のキャンプファイヤーのループ、1ページ。
- **[プレイヤー用マット](assets/print/pdf/mat.pdf)**：コイン、評判、アップグレード、約束などを記録するためのマット。1人1枚。
- **[クイックリファレンス](assets/print/pdf/quickref.pdf)**：ゲームボードのマス、ターン順、約束のルールなどをまとめたもの。
- **[イベントカード](assets/print/pdf/events.pdf)**：20枚のカード、3ページ。線に沿ってカットしてください。
- **[取引カード](assets/print/pdf/deals.pdf)**：10枚のカード、2ページ。
- **[バウチャーカード](assets/print/pdf/vouchers.pdf)**：プレイヤー間の借用証、10枚、2ページ。
- **[条約のクイックリファレンス](assets/print/pdf/treaty.pdf)**：Tier 3のみ。

これらのPDFファイルはベクター形式で、フォントが埋め込まれているため、家庭用プリンターでも綺麗に印刷できます。セットアップの手順は[印刷してプレイ](docs/print-and-play.md)で確認できます。

## スコアを記録するためのツールが必要ですか？

オプションです。このゲームは紙でも十分にプレイできます。ただし、もし誰かがノートパソコンを持っているなら、`sov`というツールがコイン、評判、約束などを記録し、最後に改ざん防止のレシートを出力します。

```bash
pip install sovereignty-game
sov play campfire_v1
```

`sov play campfire_v1` は、設定不要で簡単に開始できるコマンドです。これは、1人のプレイヤーと、デフォルトの対戦相手が「Campfire」のルールセットで対戦するものです。複数人でプレイする場合は、`sov new -p Alice -p Bob -p Carol` を使用してください。詳細な手順については、`sov tutorial` を実行してください。

Python がインストールされていない場合：`npx` コマンドを使用すると、あらかじめコンパイルされたバイナリをダウンロードできます。

```bash
npx @mcptoolshop/sovereignty tutorial
```

## 本格的なプレイ

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

- **保存されたゲームの複数保存** (v2.1 以降): `sov games` で保存されたゲームの一覧を表示し、`sov resume <ゲームID>` でゲームを切り替えます。
- **バッチアンカー** (v2.1 以降): ゲーム終了時に `sov anchor` を実行すると、保留中のすべてのラウンドが単一の XRPL トランザクションにまとめられます。これにより、ゲームごとに検証可能なチェーンポインタが 1 つ作成されます。ゲーム中にフラッシュする場合は、`sov anchor --checkpoint` を使用してください。
- **ネットワークの選択** (v2.1 以降): `sov anchor --network testnet|mainnet|devnet` (または環境変数 `SOV_XRPL_NETWORK` を設定。デフォルトは `testnet`)。
- **デーモンモード** (v2.1 以降、オプション): `sov daemon start` を実行すると、デスクトップ統合とバックグラウンドでのチェーン監視を行うための、ローカルホストの HTTP/JSON サーバーが起動します。詳細は、以下の「デーモンモード」を参照してください。
- **監査ビューアデスクトップアプリ** (v2.1 以降、オプション): `npm --prefix app run tauri dev`。詳細は、以下の「デスクトップアプリ」を参照してください。

> まずは、アプリ内ガイド付きのチュートリアルを試してみたいですか？ `sov tutorial`を実行してください。
> より詳細なルール説明が必要ですか？ [ここから始めましょう](docs/start_here.md)をご覧ください。
> または、[完全なハンドブック](https://mcp-tool-shop-org.github.io/sovereignty/handbook/)を参照してください。

上記の `sov turn` の例は、コンソール上でラウンドがどのように見えるかを示しています。v2.1 のデスクトップでの可視化については、以下の「デスクトップアプリ」を参照してください。

**[ここから始めましょう](docs/start_here.md)** | **[Print & Play](docs/print-and-play.md)** | **[完全なルール](docs/rules/campfire_v1.md)** | **[見知らぬ人とプレイ](docs/play-with-strangers.md)**

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

コンソールがスコアを記録します。あなたは約束を守ります。

## デーモンモード (オプション、v2.1 以降)

デスクトップ統合 (監査ビューア、Tauri シェル) またはバックグラウンドでのチェーン監視を行うには、sovereignty をローカルホストの HTTP デーモンとして実行します。

```bash
pip install 'sovereignty-game[daemon]'
sov daemon start --readonly        # audit-only, no wallet seed
sov daemon start                   # full daemon with anchor endpoints (loads XRPL_SEED)
sov daemon status                  # running | stale | none
sov daemon stop
```

デーモンは `127.0.0.1` のポート番号をランダムに選択して接続し、接続情報は `.sov/daemon.json` に保存されます。プロジェクトのルートディレクトリには、デーモンを 1 つだけ実行できます。詳細については、[docs/v2.1-daemon-ipc.md](docs/v2.1-daemon-ipc.md) を参照してください。

## デスクトップアプリ (オプション、v2.1 以降)

監査ビューアは、v2.1 のデスクトップアプリです。これは、Tauri シェル (Rust + Webview) で、監査ビューアと、読み取り専用のゲームビューをデーモンの上で実行します。

### インストール (バイナリ)

v2.1.0 は、あらかじめコンパイルされたバイナリを [GitHub Releases ページ](https://github.com/mcp-tool-shop-org/sovereignty/releases/latest) で提供しています。

- **macOS (universal):** `sovereignty-app-2.1.0-darwin-universal.dmg` — Intel + Apple Silicon
- **Windows (x64):** `sovereignty-app-2.1.0-win-x64.msi`
- **Linux (x64, .deb):** `sovereignty-app-2.1.0-linux-x64.deb` — Debian / Ubuntu / その派生版。`sudo dpkg -i sovereignty-app-2.1.0-linux-x64.deb`でインストールしてください。AppImageのサポートはv2.2で実装予定（upstream `linuxdeploy` / Ubuntu 24.04 FUSEとの連携）。

アプリのバックグラウンドで動作する Python デーモンも必要です。`pip install 'sovereignty-game[daemon]'==2.1.0` でインストールしてください。

> **初回起動時の警告が表示される場合があります。** macOS では「身元不明の開発者」と表示される場合があります。この場合、.app を右クリックし、「開く」を選択して確認してください。Windows の SmartScreen では「未登録のパブリッシャー」と表示される場合があります。「詳細情報」をクリックし、「とにかく実行する」を選択してください。これらの警告は、v2.1 がビルドの信頼性情報を付与しているだけで、OS レベルでのコード署名が行われていないことを示しています。ワークスペースレベルの署名機能は v2.2 で提供されます。

### 信頼性の検証

すべてのリリースアーティファクトには、SLSA のビルド信頼性情報が付与されています。実行する前に、必ず検証してください。

```bash
gh attestation verify \
  --repo mcp-tool-shop-org/sovereignty \
  ./sovereignty-app-2.1.0-darwin-universal.dmg
```

検証が成功すると、そのバイナリが特定のコミットから、リリースワークフローによって、このリポジトリでビルドされたことが証明されます。これは、OS レベルのコード署名とは異なる信頼性の層です。バイナリは引き続き OS の警告を引き起こしますが、そのサプライチェーンの信頼性は暗号的に検証されています。

### ソースコードからのビルド

ソースコードからビルドしたい場合、またはバイナリがプラットフォームで動作しない場合は、こちらの手順に従ってください。

```bash
# 1. Install Python + daemon deps
pip install -e '.[xrpl,daemon]'

# 2. Install frontend + Rust deps (one-time)
cd app && npm install && cd ..
cargo build --manifest-path app/src-tauri/Cargo.toml

# 3. Start the dev shell (auto-starts the daemon in readonly mode)
npm --prefix app run tauri dev
```

Tauri シェルは、起動時に読み取り専用のデーモンを自動的に起動し、終了時に自動的に停止します。外部から起動されたデーモン (`sov daemon start`) は、シェルを再起動しても動作し続けます。

詳細については、[docs/v2.1-tauri-shell.md](docs/v2.1-tauri-shell.md) を参照してください。

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

監査ビューアには、次の 3 つのビューが用意されています。

- **`/audit`**：XRPLに紐づいた検証結果表示機能。ゲームごとのリストは折りたたみ可能で、ラウンドごとの検証状況が表示されます。「すべてのラウンドを検証」を実行すると、ローカルでの検証計算とチェーンの参照が順番に実行されます。監査担当者向けの機能で、生のJSONデータを読まずに、ゲームが正当に実行されたかどうかを確認できます。
- **`/game`**：現在進行中のゲームのリアルタイムの状態を表示します。プレイヤーのリソースカード、ラウンドのタイムライン、過去20件のSSEイベントログが表示されます。読み取り専用であり、コマンドラインインターフェース（CLI）で別のターミナルからプレイできます。
- **`/settings`**：デーモンの設定を表示し、ネットワークの切り替え（テストネット/メインネット/開発ネット）が可能です。メインネットへの接続には、確認が必要です。

詳細な仕様については、[docs/v2.1-views.md](docs/v2.1-views.md) を参照してください。

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
  assets/print/     # Print pack — markdown sources, rendered PDFs, JSX render sources
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
