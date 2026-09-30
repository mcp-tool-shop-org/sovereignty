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
  <a href="https://codecov.io/gh/mcp-tool-shop-org/sovereignty"><img src="https://codecov.io/gh/mcp-tool-shop-org/sovereignty/graph/badge.svg" alt="Coverage"></a>
  <a href="https://pypi.org/project/sovereignty-game/"><img src="https://img.shields.io/pypi/v/sovereignty-game?include_prereleases&style=flat&cacheSeconds=3600" alt="PyPI version"></a>
  <a href="https://pypi.org/project/sovereignty-game/"><img src="https://img.shields.io/pypi/pyversions/sovereignty-game?style=flat&cacheSeconds=3600" alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat&cacheSeconds=86400" alt="License: MIT"></a>
  <a href="https://mcp-tool-shop-org.github.io/sovereignty/"><img src="https://img.shields.io/badge/Landing_Page-live-blue?style=flat&cacheSeconds=86400" alt="Landing Page"></a>
</p>

## 今夜はゲームをしよう

[印刷して遊べるパッケージ全体](assets/print/pdf/Sovereignty-Print-Pack.pdf)を印刷してください。内容は、ゲームボード、プレイヤーマット、クイックリファレンス、マーケットボード、そしてUSレターサイズの用紙13枚に印刷された3種類のカードデッキです。サイコロといくつかのコインを用意し、2～3人の友人と一緒に座って、20分以内にゲームを始めましょう。

個別のシートが必要な場合：

- **[ゲームボード](assets/print/pdf/board.pdf)**：16マスからなるキャンプファイアのループ、1ページ。
- **[プレイヤーマット](assets/print/pdf/mat.pdf)**：コイン、評判、アップグレード、約束。プレイヤーごとに1つ。
- **[クイックリファレンス](assets/print/pdf/quickref.pdf)**：ゲームボードのマス、ターンの順番、約束のルール。
- **[イベントカード](assets/print/pdf/events.pdf)**：28枚、4ページ。線に沿って切り取ってください。
- **[取引カード](assets/print/pdf/deals.pdf)**：12枚、2ページ。
- **[引換券カード](assets/print/pdf/vouchers.pdf)**：プレイヤー間の10枚のI/Oカード、2ページ。
- **[マーケットボード](assets/print/pdf/market.pdf)**：マーケットデー/タウンホール、1ページ。
- **[条約クイックリファレンス](assets/print/pdf/treaty.pdf)**：ティア3のみ。

PDFはベクター形式でフォントが埋め込まれているため、どの家庭用プリンターでもきれいに印刷できます。セットアップの手順は、[印刷して遊ぶ](docs/print-and-play.md)にあります。

## スコアを記録するためのコンソールが必要ですか？

オプションです。このゲームは紙の上でも問題なくプレイできます。しかし、もし誰かがノートパソコンを持っているなら、`sov`はコイン、評判、約束を記録し、最後に改ざん防止のレシートを作成します。

```bash
pip install sovereignty-game
sov play campfire_v1
```

`sov play campfire_v1`は、設定不要のクイックスタート版で、1人のプレイヤーとデフォルトの対戦相手です。複数人でテーブルでプレイする場合は、`sov new -p Alice -p Bob -p Carol`を使用してください。60秒のガイド付きチュートリアルが必要な場合は、`sov tutorial`を使用してください。

Pythonがインストールされていませんか？ `npx`を使用すると、事前に構築されたバイナリをダウンロードできます。

```bash
npx @mcptoolshop/sovereignty tutorial
```

または、Dockerで実行し、保存データを名前付きボリュームに保存することもできます。

```bash
docker run --rm -it -v sov-data:/data ghcr.io/mcp-tool-shop-org/sovereignty tutorial
```

## 実際のゲームプレイ

あなたと2～3人の友人がテーブルに着いたら、コンソールがラウンドを進行させ、あなたは会話をします。実際のゲームプレイは次のようになります。

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

`sov status`は、プレイヤーのコイン、評判、アップグレード、位置、目標をRich形式の表で表示します。ターンの合間に、簡潔な情報を確認したい場合は、次のようになります。

```bash
sov status --brief
```

```
R3 |  Alice: 7c 4r 0u | >Bob: 4c 3r 0u |  Carol: 6c 5r 0u
```

（`Nc Nr Nu` = コイン / 評判 / アップグレード；`>`はアクティブなプレイヤーを示します。）

これを15ラウンド繰り返します。`sov game-end`は最終スコアを印刷します。

- **複数の保存ゲーム**（v2.1以降）：`sov games`は保存ゲームをリスト表示します。`sov resume <game-id>`で切り替えます。
- **バッチアンカー処理**（v2.1以降）：ゲーム終了時に`sov anchor`を実行すると、保留中のラウンドが、XRPL AccountSetトランザクションの小さな一定のセット（各トランザクションに最大8個のメモ）にまとめて保存されます（典型的な16ラウンドのキャンプファイアゲームでは2つのトランザクション）。これは、単一のトランザクション/単一のチェーンポインタではありません。ゲーム中にデータを保存する場合は、`sov anchor --checkpoint`を使用します。
- **ネットワークの選択**（v2.1以降）：`sov anchor --network testnet|mainnet|devnet`（または`SOV_XRPL_NETWORK`環境変数、デフォルトは`testnet`）。
- **デーモンモード**（v2.1以降、オプション）：`sov daemon start`を実行すると、ローカルホストのHTTP/JSONサーバーが起動し、デスクトップアプリケーションとの統合やバックグラウンドでのチェーンポーリングが可能になります。詳細は、[デーモンモード](#daemon-mode-optional-v21)を参照してください。
- **監査ビューアデスクトップアプリ**（v2.1以降、オプション）：`npm --prefix app run tauri dev`。詳細は、[デスクトップアプリ](#desktop-app-optional-v21)を参照してください。

> まず、アプリ内のガイド付きチュートリアルを実行しますか？ `sov tutorial`を実行してください。
> より詳細なルールを知りたいですか？ [ここから始める](docs/start_here.md)または[完全なハンドブック](https://mcp-tool-shop-org.github.io/sovereignty/handbook/)をご覧ください。

上記のインラインの`sov turn`の例は、コンソールでのラウンドの表示方法を示しています。v2.1のデスクトップでの表示については、[デスクトップアプリ](#desktop-app-optional-v21)を参照してください。

**[ここから始める](docs/start_here.md)** | **[印刷して遊ぶ](docs/print-and-play.md)** | **[完全なルール](docs/rules/campfire_v1.md)** | **[見知らぬ人と遊ぶ](docs/play-with-strangers.md)**

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

コンソールがスコアを記録します。あなたは約束を守ります。

## デーモンモード（オプション、v2.1以降）

デスクトップアプリケーションとの統合（監査ビューア、Tauriシェル）またはバックグラウンドでのチェーンポーリングのために、ソブリンティをローカルホストのHTTPデーモンとして実行します。

```bash
pip install 'sovereignty-game[daemon]'
sov daemon start --readonly        # audit-only, no wallet seed
sov daemon start                   # full daemon with anchor endpoints (loads XRPL_SEED)
sov daemon status                  # running | stale | none
sov daemon stop
```

デーモンは、ランダムなポートで`127.0.0.1`にバインドされます。接続の詳細（ポートとベアラー・トークン）は、`.sov/daemon.json`に保存されます。プロジェクトのルートごとに1つのデーモンを実行します。完全なIPC（プロセス間通信）契約については、[docs/v2.1-daemon-ipc.md](docs/v2.1-daemon-ipc.md)を参照してください。

> `[daemon]`の追加機能を使用するには、**2.3.2以降**が必要です。2.3.1までのバージョンでは、`sov_daemon`パッケージが含まれていなかったため、PyPIからのインストール時に`sov daemon start`が失敗しました。

## Docker（オプション、v2.3.2以降）

`ghcr.io/mcp-tool-shop-org/sovereignty`にあるイメージには、`sov` CLIとデーモンが含まれており、`linux/amd64`と`linux/arm64`で使用できます。ゲームが記憶するすべてのデータは、`/data/.sov`に保存されます。ゲーム、ラウンドの証拠、`anchors.json`、シーズンの記録、ウォレットのシード、およびデーモンのハンドシェイクです。ボリュームを`/data`にマウントしないと、コンテナはすべてのデータを忘れてしまいます。

バンドルされた[`compose.yaml`](compose.yaml)を使用して、デーモンを実行します。

```bash
docker compose up -d                  # readonly audit daemon on 127.0.0.1:47823
docker compose run --rm sov doctor    # any sov command, same saves
docker compose run --rm sov play campfire_v1
docker compose logs -f
```

コンテナはデフォルトで、**読み取り専用**のデーモンを**テストネット**で実行します。ポートはホストのループバックのみに公開され（`127.0.0.1:47823`）、すべてのリクエストには`.sov/daemon.json`からのベアラー・トークンが必要です。

| 設定 | デフォルト | その機能 |
|---|---|---|
| `SOV_DATA` | `sov-data`（名前付きボリューム） | `/data`の由来。ホストに保存データを保持するには、フォルダ（`SOV_DATA=./`）に設定します。 |
| `SOV_DAEMON_PORT` | `47823` | デーモンポート。コンテナ内とホストで同じである必要があります。 |
| `SOV_DAEMON_NETWORK` | `testnet` | `testnet`、`devnet`、または`mainnet`。 |
| `SOV_DAEMON_READONLY` | `1` | `0`はアンカーエンドポイントを有効にします。 |
| `SOV_DAEMON_TOKEN` | 起動ごとにランダム | 再起動時にクライアントが接続を維持できるようにします。 |
| `SOV_DAEMON_LOG_FORMAT` | `human` | `json`は、構造化されたログ行を有効にします。 |

**デスクトップアプリを接続します。** `SOV_DATA`を、アプリが起動するプロジェクトフォルダに設定します。デーモンは、ハンドシェイクをそこに書き込み、アプリは`127.0.0.1:47823`からトークンを取得して接続します。

```bash
SOV_DATA=./ docker compose up -d
```

コンテナがデーモンを所有している場合は、ホストの`sov daemon start|stop|status`ではなく、`docker compose`を使用して管理します。ホストのCLIはコンテナのプロセスを表示できないため、ハンドシェイクが古いものとして報告され、`sov daemon start`はそれをクリアします。

**コンテナからアンカー処理を行います。** ボリュームにテストネットウォレットを作成し、読み取り専用モードをオフにします。

```bash
docker compose run --rm sov wallet
SOV_DAEMON_READONLY=0 docker compose up -d
```

シードをボリュームに含めないように、Dockerシークレットとして提供してください。`compose.yaml`のコメントアウトされた`secrets`のブロックにその方法が示されています。

## デスクトップアプリ（オプション、v2.1以降）

監査ビューアーは、v2.1デスクトップアプリです。これは、監査ビューアーと読み取り専用のゲームビューをデーモンの上に実行するTauriシェル（Rust + webview）です。

### インストール（バイナリ）

**v2.3.5** が現在のリリースです。GitHub リリース **v2.3.0** には、ホイールやデスクトップアセットが含まれていませんでしたので、`pip install …==2.3.0` を指定しないでください。

- **Python / デーモン:** `pip install 'sovereignty-game[daemon]'`（デーモンの場合は2.3.2以降）。
- **デスクトップアプリ:** CIでプラットフォームファイルがアタッチされた最新のGitHubリリース（[https://github.com/mcp-tool-shop-org/sovereignty/releases/latest](https://github.com/mcp-tool-shop-org/sovereignty/releases/latest)）。プラットフォームジョブが失敗した場合は、ソースから実行してください（以下参照）。

> 認証されたバイナリが実際にリリースされた場合、**初回起動時のOS警告が表示される**ことが予想されます。これらのビルドには、SLSAビルドプロビナンス認証のみが含まれており、OSレベルのApple Developer ID / Authenticode署名は含まれていません。macOS：.appファイルをcontrol-click → Open。Windows SmartScreen：More info → Run anyway。

### プロビナンスの検証

デスクトップアーティファクトが実際にリリースされたら、ダウンロードしたファイルを検証してください。

```bash
gh attestation verify \
  --repo mcp-tool-shop-org/sovereignty \
  ./<downloaded-artifact>
```

クリーンな検証により、バイナリがこのリポジトリのリリースワークフローによって、特定のコミットからビルドされたことが証明されます。これは、OSレベルのコード署名とは異なる信頼の層です。バイナリはOS警告を引き起こしますが、そのサプライチェーンプロビナンスは暗号化的に固定されています。

### ソースから実行

ソースからビルドしたい場合（またはバイナリがプラットフォームで実行されない場合）：

```bash
# 1. Install Python + daemon deps
pip install -e '.[xrpl,daemon]'

# 2. Install frontend + Rust deps (one-time)
cd app && npm install && cd ..
cargo build --manifest-path app/src-tauri/Cargo.toml

# 3. Start the dev shell (auto-starts the daemon in readonly mode)
npm --prefix app run tauri dev
```

Tauriシェルは、起動時に読み取り専用のデーモンを自動的に起動し、終了時に自動的に停止します。外部から起動されたデーモン（`sov daemon start`）は、シェルの再起動後も実行され続けます。

完全な仕様については、[docs/v2.1-tauri-shell.md](docs/v2.1-tauri-shell.md)を参照してください。

監査ビューアーには、次の3つのビューが含まれています。

- **`/audit`** — XRPLにアンカーされた証拠ビューアー。ゲームごとのリストを折りたたみ可能にし、ラウンドごとのアンカーステータスを表示し、「すべてのラウンドを検証」を実行すると、ローカルで証拠を再計算し、チェーンを連続して検索します。監査者のビュー：生のJSONを読まずに、ゲームが正直に実行されたことを確認します。
- **`/game`** — アクティブなゲームのパッシブなリアルタイム状態表示。プレイヤーのリソースカード、ラウンドのタイムライン、最新の20件のSSEイベントログ。読み取り専用です。別のターミナルでCLIでプレイしてください。
- **`/settings`** — デーモンの構成表示 + ネットワークスイッチャー（テストネット / メインネット / デブネット）。メインネットの確認ガードレール付き。

完全なビュー仕様については、[docs/v2.1-views.md](docs/v2.1-views.md)を参照してください。

## 仕組み

**5枚のコイン**と**3ポイントの評判**から始めます。サイコロを振って、16マスあるボード上を移動し、取引、誰かの手伝い、リスクを冒す、またはカードを引くという選択肢があるマスに着地します。

**28枚のイベントカード**は、まるで瞬間を描写したように書かれています。たとえば、*"誰か、小さな革のポーチを見た人はいますか？"*（紛失した財布）または*"誰も見ていない... そうだよね？"*（近道を見つけた）。タウンホールゲーム用の市場変動イベントも含まれています。

**12枚の取引カード + 10枚のバウチャーカード**は、会話を促します。*"2枚のコインを貸してくれませんか？3枚返します。"*または*"もしあなたが私を助けてくれるなら、私もあなたを助けます。"*取引は、期限付きの目標を設定します。バウチャーは、他のプレイヤーに発行するIOUです。

**約束のルール:** 1ラウンドに1回、声に出して「私は約束します...」と言い、何かを約束します。それを守る：+1の評判。破る：-2の評判。テーブルが決定します。

**謝罪:** ゲーム中に1回、約束を破った場合は、公に謝罪します。約束を破った相手に1枚のコインを支払い、+1の評判を取り戻します。

**自分の目標を選択します**（秘密または公開）：
- **繁栄** — 20枚のコインに到達
- **愛される** — 10ポイントの評判に到達
- **建設者** — 4つのアップグレードを完了

15ラウンド後、最も高い合計スコアが勝ちます。

## ダイアリーモードとは何ですか？

各ラウンドで、コンソールは**証拠**（ゲーム状態のフィンガープリント）を生成できます。誰かがスコアを変更すると、フィンガープリントは一致しません。

オプションで、そのフィンガープリントを**XRPLテストネット**（パブリックレジャー）に投稿できます。これは、誰も消すことのできない壁にスコアを書き込むようなものです。

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

ホストだけがウォレットを必要とします。他の人は画面に触れません。ゲームは、ダイアリーが記憶していなくても、完全に機能します。

## 3つの階層

| 階層 | 名前 | ステータス | 追加されるもの |
|------|------|--------|-------------|
| 1 | **Campfire** | プレイ可能 | コイン、評判、約束、IOU |
| 2 | **Town Hall** | プレイ可能 | 共有市場、リソースの希少性 |
| 3 | **Treaty Table** | プレイ可能 | ステーク付きの条約 — 守るべき約束 |

コアルールはv1.xを通じて安定しています。 [ロードマップ](docs/roadmap.md)を参照してください。

## シナリオパック

新しいルールはありません。単に雰囲気です。各パックは、階層、レシピ、およびムードを設定します。

| シナリオ | 階層 | 最適な対象 |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | キャンプファイヤー / マーケットデー | 最初のゲーム、混合グループ |
| [Market Panic](docs/scenarios/market-panic.md) | タウンホール | 経済ドラマ |
| [Promises Matter](docs/scenarios/promises-matter.md) | キャンプファイヤー | 信頼とコミットメント |
| [Treaty Night](docs/scenarios/treaty-night.md) | 条約テーブル | ハイステークスの合意 |

`sov scenario list`でコンソールから閲覧できます。

## プロジェクト構造

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

## 開発

```bash
git clone https://github.com/mcp-tool-shop-org/sovereignty.git
cd sovereignty
uv sync --dev
uv run pytest tests/ -v
uv run ruff check .
```

## 設計原則

> 「用語ではなく、結果を通じて教える」。

プレイヤーは、IOUの発行、約束の破り、変動する価格での取引を通じて学習します。これらの概念は、ウォレット、トークン、信頼ラインなどのWeb3のプリミティブに対応しますが、プレイヤーはそれを知らなくても楽しむことができます。

## 貢献

最も簡単な貢献方法は、[カードを追加する](CONTRIBUTING.md)ことです。エンジンに関する知識は必要ありません。名前、説明、およびいくつかのフレーバーテキストがあれば十分です。

## セキュリティ

ウォレットのシード、ゲームの状態、および証明ファイル — 共有すべきものと共有すべきでないもの。テレメトリー、分析、または外部への通信は行いません。オプションのネットワーク呼び出しは、XRPLテストネットへのアンカーリングのみです。

[SECURITY.md](SECURITY.md) を参照してください。

## 脅威モデル

| 脅威 | 緩和策 |
|--------|-----------|
| 証明を介したシードの漏洩 | 証明にはハッシュのみが含まれ、シードは含まれません。 |
| Gitにシードが含まれる | `.sov/` はGitで無視されます。`sov wallet` は警告を表示します。 |
| ゲームの状態の改ざん | ラウンド証明 `envelope_hash` は、`game_id`、`round`、`ruleset`、`rng_seed`、`timestamp_utc`、`players`、および`state`をカバーします。`sov verify` は、完全なエンベロープ全体での改ざんを検出します。証明形式v1は、v2.0.0以降ではサポートされなくなりました。 |
| XRPLアンカーの偽装 | 証明ハッシュはオンチェーンにアンカーされ、検証時に不一致を検出します。 |
| コンテナの露出 | デーモンイメージは、ホスト `127.0.0.1` にのみ公開されます。すべてのリクエストにベアラートークンを使用し、デフォルトでは読み取り専用で、読み取り専用のルートファイルシステムと権限のない非ルートユーザーとして実行されます。 |
| プレイヤー名のプライバシー | プレイヤー名は証明に含まれます（最上位の `players` リストとプレイヤーのスナップショット内）。プライベートなプレイを行う場合は、`proof.json` を公開したり、ポストカードを共有したりしないでください。 |

## ライセンス

MIT

---

[MCP Tool Shop](https://mcp-tool-shop.github.io/) によって作成されました。
