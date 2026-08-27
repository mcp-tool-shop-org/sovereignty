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

## 今夜遊ぼう

[印刷して遊べるパッケージ全体](assets/print/pdf/Sovereignty-Print-Pack.pdf)を印刷してください。ボード、プレイヤーマット、クイックリファレンス、カード3種類がそれぞれ11枚のUSレターサイズの用紙に収まるようにデザインされています。サイコロといくつかのコインを用意し、2～3人の友人と一緒に座ってゲームを始めましょう。20分以内にプレイできます。

個別のシートが必要な場合：

- **[ボード](assets/print/pdf/board.pdf)** — 16マスからなるキャンプファイアのループ、1ページ。
- **[プレイヤーマット](assets/print/pdf/mat.pdf)** — コイン、評判、アップグレード、約束。各プレイヤーに1つずつ。
- **[クイックリファレンス](assets/print/pdf/quickref.pdf)** — ボードのマス、ターンの順番、約束に関するルール。
- **[イベントカード](assets/print/pdf/events.pdf)** — 20枚、3ページ。線に沿って切り取ってください。
- **[取引カード](assets/print/pdf/deals.pdf)** — 10枚、2ページ。
- **[引換券カード](assets/print/pdf/vouchers.pdf)** — プレイヤー間のIOU（借用証）10枚、2ページ。
- **[条約クイックリファレンス](assets/print/pdf/treaty.pdf)** — Tier 3のみ。

PDFはベクター形式でフォントが埋め込まれているため、どの家庭用プリンターでもきれいに印刷できます。セットアップの手順については、[Print & Play](docs/print-and-play.md)をご覧ください。

## スコアを記録するためのコンソールが必要ですか？

オプションです。このゲームは紙の上でも問題なくプレイできます。ただし、誰かがラップトップを持っている場合は、`sov`を使用してコイン、評判、約束を追跡し、最後に改ざん防止のレシートを作成できます。

```bash
pip install sovereignty-game
sov play campfire_v1
```

`sov play campfire_v1`は設定不要のクイックスタート版で、1人のプレイヤーとデフォルトの対戦相手がいます。複数人でテーブルゲームをする場合は、`sov new -p Alice -p Bob -p Carol`を使用してください。60秒間のガイド付きチュートリアルが必要な場合は、`sov tutorial`を使用してください。

Pythonがない場合：`npx`パスでは、事前にビルドされたバイナリをダウンロードします。

```bash
npx @mcptoolshop/sovereignty tutorial
```

## 実際のゲームセッション

あなたと2～3人の友人がテーブルに座ったら、コンソールがラウンドを実行し、あなたは会話を行います。実際のゲームセッションは次のようになります。

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

`sov status`は、プレイヤーのコイン、評判、アップグレード、位置、目標をRich形式の表で表示します。ターンの合間にすばやく確認するには：

```bash
sov status --brief
```

```
R3 |  Alice: 7c 4r 0u | >Bob: 4c 3r 0u |  Carol: 6c 5r 0u
```

（`Nc Nr Nu` = コイン / 評判 / アップグレード；`>`はアクティブなプレイヤーを示します。）

これを15ラウンド繰り返します。`sov game-end`が最終スコアを印刷します。

- **複数の保存ゲーム**（v2.1以降）：`sov games`で保存されたゲームの一覧が表示され、`sov resume <game-id>`で切り替えることができます。
- **バッチアンカー処理**（v2.1以降）：ゲーム終了時の`sov anchor`は、保留中のラウンドを少数の XRPL AccountSet トランザクションにフラッシュします（各トランザクション最大8メモ。典型的な16ラウンドのCampfireは2件）。単一トランザクション／単一チェーンポインタではありません。ゲーム中のフラッシュには`sov anchor --checkpoint`を使います。
- **ネットワーク選択**（v2.1以降）：`sov anchor --network testnet|mainnet|devnet`（または環境変数`SOV_XRPL_NETWORK`；デフォルトは`testnet`）。
- **デーモンモード**（v2.1以降、オプション）：`sov daemon start`を実行すると、ローカルホストのHTTP/JSONサーバーが起動し、デスクトップ統合やバックグラウンドでのチェーンポーリングが可能になります。詳細は[デーモンモード](#daemon-mode-optional-v21)をご覧ください。
- **監査ビューアデスクトップアプリ**（v2.1以降、オプション）：`npm --prefix app run tauri dev`。詳細は[デスクトップアプリ](#desktop-app-optional-v21)をご覧ください。

> まず、ゲーム内ガイド付きチュートリアルを実行しますか？ `sov tutorial` を実行してください。
> より詳細なルールを知りたいですか？ [ここから始めましょう](docs/start_here.md) または [完全なハンドブック](https://mcp-tool-shop-org.github.io/sovereignty/handbook/)をご覧ください。

上記のインラインの`sov turn`の例は、コンソールでのラウンドがどのように表示されるかを示しています。v2.1デスクトップ版の視覚化については、[デスクトップアプリ](#desktop-app-optional-v21)をご覧ください。

**[ここから始めましょう](docs/start_here.md)** | **[印刷して遊ぼう](docs/print-and-play.md)** | **[完全なルール](docs/rules/campfire_v1.md)** | **[見知らぬ人と一緒にプレイする](docs/play-with-strangers.md)**

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

デスクトップ統合（監査ビューア、Tauriシェル）またはバックグラウンドでのチェーンポーリングのために、ソブリンティをローカルホストのHTTPデーモンとして実行します。

```bash
pip install 'sovereignty-game[daemon]'
sov daemon start --readonly        # audit-only, no wallet seed
sov daemon start                   # full daemon with anchor endpoints (loads XRPL_SEED)
sov daemon status                  # running | stale | none
sov daemon stop
```

デーモンは`127.0.0.1`にランダムなポートでバインドされます。接続の詳細（ポートとベアラートークン）は`.sov/daemon.json`に保存されます。プロジェクトルートごとに1つのデーモンを実行します。完全なIPCコントラクトについては、[docs/v2.1-daemon-ipc.md](docs/v2.1-daemon-ipc.md)をご覧ください。

## デスクトップアプリ（オプション、v2.1以降）

監査ビューアは、v2.1のデスクトップアプリです。Tauriシェル（Rust + webview）で、監査ビューアと読み取り専用のゲームビューをデーモンの上に実行します。

### インストール（バイナリ）

v2.3.0はgitにタグされていますが、**ホイールもデスクトップ資産も公開されていません。** `publish.yml` の実行 33118253060 は失敗しました。PyPIに2.3.0配布はなく、GitHub Release v2.3.0のアセットは空です。ファイル名 `sovereignty-app-2.3.0-{darwin-universal.dmg,win-x64.msi,linux-x64.deb,linux-x64.AppImage}` は404です。`pip install …==2.3.0` をピン止めしないでください。

後続タグ（2.3.1または修復した2.3.x）が実際にファイルを添付するまで：

- **Python / デーモン:** `pip install 'sovereignty-game[daemon]'`（現行PyPIは **2.2.1**。ピンなしの `pipx` / `npx @mcptoolshop/sovereignty` も2.2.1です）。
- **デスクトップアプリ:** ソースから実行（下記）。一致するファイルが載るまで [GitHub Releases latest](https://github.com/mcp-tool-shop-org/sovereignty/releases/latest) からバイナリを取らないでください。

> **初回起動時のOS警告は、アテステーション付きバイナリが実際に出荷されたときに想定されます。** それらのビルドはSLSAビルドプロベナンスのみで、Apple Developer ID / Authenticode のOS署名はありません。macOS: .appをコントロールクリック → 開く。Windows SmartScreen: 詳細情報 → 実行する。

### プロベナンスを検証する

リリースが実際にデスクトップ成果物を添付したら、ダウンロードしたファイルを検証してください。

```bash
gh attestation verify \
  --repo mcp-tool-shop-org/sovereignty \
  ./<downloaded-artifact>
```

正常に検証されると、バイナリが特定のコミットから、このリポジトリのリリースワークフローによってビルドされたことが証明されます。これはOSレベルでのコード署名とは異なる信頼の層です。バイナリはOS警告を引き起こしますが、そのサプライチェーンプロベナンスは暗号化的に固定されています。

### ソースから実行する

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

Tauriシェルは、起動時に読み取り専用のデーモンを自動的に開始し、終了時に自動的に停止します。外部で開始されたデーモン（`sov daemon start`）は、シェルの再起動時にも存続します。

完全なコントラクトについては、[docs/v2.1-tauri-shell.md](docs/v2.1-tauri-shell.md)をご覧ください。

監査ビューアには、次の3つのビューが含まれています。

- **`/audit`** — XRPLに紐付けられたゲームの証拠を表示するツール。各ゲームごとのリストを折りたたみ可能、各ラウンドのアンカー状況を表示し、「すべてのラウンドを確認」機能では、ローカルで証拠を再計算し、チェーン上で検証を行う。監査者の視点：生のJSONデータを読み込まずに、ゲームが公正に実行されたことを確認する。
- **`/game`** — 進行中のゲームの状態をリアルタイムで表示するツール。プレイヤーのリソースカード、ラウンドのタイムライン、過去20件のSSEイベントログを表示。読み取り専用であり、別のターミナルでCLI上でプレイできる。
- **`/settings`** — デーモン設定を表示し、ネットワーク（テストネット/メインネット/開発ネット）を切り替える機能。メインネットでの確認機能を備えている。

完全な仕様は[docs/v2.1-views.md](docs/v2.1-views.md)を参照。

## 仕組み

最初に**5つのコイン**と**3の評判ポイント**から始める。サイコロを振って、16マスあるボード上を移動し、取引、誰かを助ける、リスクを取る、またはカードを引くという選択肢があるマスに止まる。

**20枚のイベントカード**は、まるで出来事のように書かれている。「誰か小さな革製のポーチを見た？」(紛失した財布)や「誰も見ていない…そうだろう？」（隠された抜け道）など。タウンホールゲーム用の市場変動イベントも含まれている。

**10枚の取引カードと10枚の引換券**は、会話を促す。「2つのコイン貸してくれないか？3つ返済するよ」や「君が困っているなら、私も助けるよ」。取引では期限付きの目標を設定し、引換券は他のプレイヤーに発行する借用証書である。

**約束のルール:** 各ラウンドで一度だけ、「私は～することを約束します…」と声に出して宣言し、何かを約束する。それを守る：+1の評判ポイント。破る：-2の評判ポイント。テーブル全体で判断する。

**謝罪:** ゲーム中に一度だけ、もし約束を破った場合、公に謝罪する。過ちを犯した相手に1つのコインを支払い、+1の評判ポイントを取り戻す。

**自分の目標を選ぶ**（秘密または公開）：
- **繁栄** — 20枚のコインを集める
- **愛される存在** — 10の評判ポイントを集める
- **建設者** — 4つのアップグレードを完了する

15ラウンド後、最も高い合計スコアを獲得した人が勝つ。

## ダイアリーモードとは？

各ラウンドで、コンソールは**証拠**（ゲームの状態のフィンガープリント）を生成できる。誰かがスコアを変更した場合、フィンガープリントが一致しない。

オプションとして、そのフィンガープリントを**XRPLテストネット**（パブリックな台帳）に投稿することができる。これは、誰も消すことのできない壁にスコアを書くようなものだ。

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

ホストだけがウォレットを持つ必要がある。他のプレイヤーは画面に触れる必要はない。ゲームはアンカーしなくても完全に機能する。ダイアリーモードは単に記録するためである。

## 3つのレベル

| レベル | 名前 | ステータス | 追加されるもの |
|------|------|--------|-------------|
| 1 | **Campfire** | プレイ可能 | コイン、評判ポイント、約束、借用証書 |
| 2 | **Town Hall** | プレイ可能 | 共有市場、リソースの希少性 |
| 3 | **Treaty Table** | プレイ可能 | 拘束力のある条約 — 守らなければならない約束 |

コアルールはv1.xまで安定している。詳細については[roadmap](docs/roadmap.md)を参照。

## シナリオパック

新しいルールはない。単に雰囲気だけだ。各パックは、レベル、レシピ、ムードを設定する。

| シナリオ | レベル | 最適 |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | キャンプファイヤー / マーケットデー | 最初のゲーム、混合グループ向け |
| [Market Panic](docs/scenarios/market-panic.md) | タウンホール | 経済ドラマ |
| [Promises Matter](docs/scenarios/promises-matter.md) | キャンプファイヤー | 信頼とコミットメント |
| [Treaty Night](docs/scenarios/treaty-night.md) | 条約テーブル | ハイリスクな合意 |

`sov scenario list`からコンソールで閲覧する。

## プロジェクト構造

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

## デザイン原則

> 「用語ではなく、結果を通して教える」

プレイヤーは実践を通じて学ぶ：借用証書を発行する、約束を破る、変動する価格で取引する。これらの概念は、ウォレット、トークン、信頼関係などのWeb3の基本的な要素に対応しているが、プレイヤーはそれを知らなくても楽しむことができる。

## 貢献

最も簡単な貢献方法は、[カードを追加すること](CONTRIBUTING.md)である。エンジンに関する知識は必要ない。名前、説明、そして少しのフレーバーテキストがあればよい。

## セキュリティ

ウォレットシード、ゲームの状態、および証拠ファイル — 何を共有し、何を共有しないか。テレメトリー、分析、または外部への通信は行わない。オプションのネットワーク呼び出しは、XRPLテストネットへのアンカーのみである。

[SECURITY.md](SECURITY.md)を参照。

## 脅威モデル

| 脅威 | 軽減策 |
|--------|-----------|
| 証拠を介したシードの漏洩 | 証拠にはハッシュのみが含まれ、シードは含まれない |
| Gitにシードが残っている | `.sov/`はgitで無視され、`sov wallet`は警告を表示する |
| ゲームの状態の改ざん | Round proofs `envelope_hash` covers `game_id`, `round`, `ruleset`, `rng_seed`, `timestamp_utc`, `players`, and `state`. `sov verify` detects tampering across the full envelope. Proof format v1 is no longer supported in v2.0.0+. |
| XRPLアンカーの偽装 | 証拠ハッシュがオンチェーンにアンカーされ、検証時に不一致を検出する |
| プレイヤー名のプライバシー | プレイヤー名は証拠（最上位レベルの`players`リストとプレイヤーのスナップショット内）に含まれている。プライベートなプレイを行う場合は、`proof.json`を公開したり、ポストカードを共有したりしないこと。 |

## ライセンス

MIT

---

[MCP Tool Shop](https://mcp-tool-shop.github.io/)によって作成
