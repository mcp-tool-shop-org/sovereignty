<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.md">English</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

## आज रात खेलें

[संपूर्ण प्रिंट-एंड-प्ले पैकेज](assets/print/pdf/Sovereignty-Print-Pack.pdf) प्रिंट करें — बोर्ड, खिलाड़ी मैट, त्वरित संदर्भ, मार्केट बोर्ड और 13 यूएस लेटर पेपर शीट पर तीन डेक कार्ड। एक पासा और कुछ सिक्के ढूंढें। दो या तीन दोस्तों के साथ बैठें। आप बीस मिनट में खेल रहे होंगे।

यदि आप अलग-अलग शीट चाहते हैं:

- **[बोर्ड](assets/print/pdf/board.pdf)** — 16-स्पेस कैम्पफ़ायर लूप, एक पृष्ठ।
- **[खिलाड़ी मैट](assets/print/pdf/mat.pdf)** — सिक्के, प्रतिष्ठा, अपग्रेड, वादे। प्रति खिलाड़ी एक।
- **[त्वरित संदर्भ](assets/print/pdf/quickref.pdf)** — बोर्ड स्पेस, टर्न ऑर्डर, वादा नियम।
- **[इवेंट कार्ड](assets/print/pdf/events.pdf)** — 28 कार्ड, चार पृष्ठ, रेखाओं के साथ काटें।
- **[डील कार्ड](assets/print/pdf/deals.pdf)** — 12 कार्ड, दो पृष्ठ।
- **[वाउचर कार्ड](assets/print/pdf/vouchers.pdf)** — खिलाड़ियों के बीच 10 आईओयू, दो पृष्ठ।
- **[मार्केट बोर्ड](assets/print/pdf/market.pdf)** — मार्केट डे / टाउन हॉल, एक पृष्ठ।
- **[संधि त्वरित संदर्भ](assets/print/pdf/treaty.pdf)** — केवल टियर 3।

पीडीएफ वेक्टर हैं जिनमें एम्बेडेड फ़ॉन्ट हैं — वे किसी भी घरेलू प्रिंटर पर स्पष्ट रूप से प्रिंट होते हैं। सेटअप वॉकथ्रू [प्रिंट एंड प्ले](docs/print-and-play.md) पर उपलब्ध है।

## क्या आप स्कोर रखने के लिए एक कंसोल चाहते हैं?

वैकल्पिक। गेम कागज पर ठीक चलता है। लेकिन अगर किसी के पास एक लैपटॉप है, तो `sov` सिक्के, प्रतिष्ठा, वादे ट्रैक करता है, और अंत में एक छेड़छाड़-रोधी रसीद तैयार करता है:

```bash
pip install sovereignty-game
sov play campfire_v1
```

`sov play campfire_v1` नो-कॉन्फ़िगर त्वरित शुरुआत है — एक मानव और एक डिफ़ॉल्ट प्रतिद्वंद्वी। मल्टी-प्लेयर के लिए, `sov new -p Alice -p Bob -p Carol` का उपयोग करें। 60 सेकंड के निर्देशित वॉकथ्रू के लिए, `sov tutorial` का उपयोग करें।

कोई पायथन नहीं? `npx` पथ एक पूर्व-निर्मित बाइनरी डाउनलोड करता है:

```bash
npx @mcptoolshop/sovereignty tutorial
```

या इसे डॉकर में चलाएं, जिसमें आपकी सेव एक नामित वॉल्यूम में रखी जाती हैं:

```bash
docker run --rm -it -v sov-data:/data ghcr.io/mcp-tool-shop-org/sovereignty tutorial
```

## एक वास्तविक सत्र

एक बार जब आप और 2-3 दोस्त टेबल पर हों, तो कंसोल राउंड चलाता है और आप बातचीत करते हैं। एक वास्तविक सत्र इस तरह दिखता है:

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

`sov status` खिलाड़ी के सिक्कों, प्रतिष्ठा, अपग्रेड, स्थिति और लक्ष्य के साथ एक रिच-फॉर्मेटेड तालिका दिखाता है। त्वरित एक-पंक्ति झलक के लिए:

```bash
sov status --brief
```

```
R3 |  Alice: 7c 4r 0u | >Bob: 4c 3r 0u |  Carol: 6c 5r 0u
```

(`Nc Nr Nu` = सिक्के / प्रतिष्ठा / अपग्रेड; `>` सक्रिय खिलाड़ी को चिह्नित करता है।)

15 राउंड के लिए दोहराएं। `sov game-end` अंतिम स्कोर प्रिंट करता है।

- **एकाधिक सहेजे गए गेम** (v2.1+): `sov games` सेव की सूची देता है; `sov resume <game-id>` उनके बीच स्विच करता है।
- **बैच एंकरिंग** (v2.1+): `sov anchor` गेम-एंड पर लंबित राउंड को XRPL AccountSet लेनदेन के एक छोटे से स्थिर सेट में फ्लश करता है (प्रत्येक में ≤8 मेमो; एक विशिष्ट 16-राउंड कैम्पफ़ायर गेम → 2 लेनदेन) — एक एकल लेनदेन / एकल श्रृंखला पॉइंटर नहीं। मध्य-गेम फ्लश के लिए `sov anchor --checkpoint` का उपयोग करें।
- **नेटवर्क चयन** (v2.1+): `sov anchor --network testnet|mainnet|devnet` (या `SOV_XRPL_NETWORK` पर्यावरण चर; डिफ़ॉल्ट `testnet`)।
- **डेमॉन मोड** (v2.1+, वैकल्पिक): `sov daemon start` डेस्कटॉप एकीकरण और पृष्ठभूमि श्रृंखला पोलिंग के लिए एक लोकलहोस्ट HTTP/JSON सर्वर चलाता है। नीचे [डेमॉन मोड](#daemon-mode-optional-v21) देखें।
- **ऑडिट व्यूअर डेस्कटॉप ऐप** (v2.1+, वैकल्पिक): `npm --prefix app run tauri dev`। नीचे [डेस्कटॉप ऐप](#desktop-app-optional-v21) देखें।

> क्या आप पहले एक निर्देशित इन-ऐप वॉकथ्रू चाहते हैं? `sov tutorial` चलाएं।
> क्या आप नियमों का अधिक विस्तृत दौरा चाहते हैं? [यहां से शुरू करें](docs/start_here.md) या
> [पूर्ण हैंडबुक](https://mcp-tool-shop-org.github.io/sovereignty/handbook/) देखें।

ऊपर दिए गए इनलाइन `sov turn` उदाहरण से पता चलता है कि कंसोल में एक राउंड कैसा दिखता है; v2.1 डेस्कटॉप विज़ुअलाइज़ेशन के लिए, नीचे [डेस्कटॉप ऐप](#desktop-app-optional-v21) देखें।

**[यहां से शुरू करें](docs/start_here.md)** | **[प्रिंट एंड प्ले](docs/print-and-play.md)** | **[पूर्ण नियम](docs/rules/campfire_v1.md)** | **[अजनबियों के साथ खेलें](docs/play-with-strangers.md)**

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

कंसोल स्कोर रखता है। आप अपने वादे निभाते हैं।

## डेमॉन मोड (वैकल्पिक, v2.1+)

डेस्कटॉप एकीकरण (ऑडिट व्यूअर, टाउरी शेल) या पृष्ठभूमि श्रृंखला पोलिंग के लिए, सॉवरेनिटी को एक लोकलहोस्ट HTTP डेमॉन के रूप में चलाएं:

```bash
pip install 'sovereignty-game[daemon]'
sov daemon start --readonly        # audit-only, no wallet seed
sov daemon start                   # full daemon with anchor endpoints (loads XRPL_SEED)
sov daemon status                  # running | stale | none
sov daemon stop
```

डेमॉन `127.0.0.1` पर एक यादृच्छिक पोर्ट पर बाध्य होता है; कनेक्शन विवरण (पोर्ट + बेयरर टोकन) `.sov/daemon.json` में रहते हैं। प्रति प्रोजेक्ट रूट एक डेमॉन। पूर्ण IPC अनुबंध के लिए [docs/v2.1-daemon-ipc.md](docs/v2.1-daemon-ipc.md) देखें।

> `[daemon]` अतिरिक्त को **2.3.2 या बाद के संस्करण** की आवश्यकता है। 2.3.1 तक के पहिए `sov_daemon` पैकेज को छोड़ देते हैं, इसलिए `sov daemon start` PyPI पर इंस्टॉल होने पर विफल हो जाता है।

## डॉकर (वैकल्पिक, v2.3.2+)

`ghcr.io/mcp-tool-shop-org/sovereignty` पर छवि में `sov` CLI और डेमॉन है, जो `linux/amd64` और `linux/arm64` के लिए है। गेम जो कुछ भी याद रखता है, वह `/data/.sov` के अंतर्गत रहता है: गेम, राउंड प्रमाण, `anchors.json`, सीज़न रिकॉर्ड, वॉलेट सीड और डेमॉन हैंडशेक। `/data` पर एक वॉल्यूम माउंट करें या कंटेनर यह सब भूल जाएगा।

बंडल [`compose.yaml`](compose.yaml) के साथ डेमॉन चलाएं:

```bash
docker compose up -d                  # readonly audit daemon on 127.0.0.1:47823
docker compose run --rm sov doctor    # any sov command, same saves
docker compose run --rm sov play campfire_v1
docker compose logs -f
```

कंटेनर डिफ़ॉल्ट रूप से **रीडओनली** डेमॉन पर **टेस्टनेट** पर है। पोर्ट केवल होस्ट के लूपबैक पर प्रकाशित किया जाता है (`127.0.0.1:47823`), और प्रत्येक अनुरोध को अभी भी `.sov/daemon.json` से बेयरर टोकन की आवश्यकता होती है।

| सेटिंग | डिफ़ॉल्ट | यह क्या करता है |
|---|---|---|
| `SOV_DATA` | `sov-data` (नामित वॉल्यूम) | `/data` कहां से आता है। इसे एक फ़ोल्डर (`SOV_DATA=./`) पर सेट करें ताकि सेव को होस्ट पर रखा जा सके। |
| `SOV_DAEMON_PORT` | `47823` | डेमॉन पोर्ट, अंदर और होस्ट पर। दोनों को मेल खाना चाहिए। |
| `SOV_DAEMON_NETWORK` | `testnet` | `testnet`, `devnet`, या `mainnet`। |
| `SOV_DAEMON_READONLY` | `1` | `0` एंकर एंडपॉइंट को सक्षम करता है। |
| `SOV_DAEMON_TOKEN` | प्रत्येक स्टार्टअप पर यादृच्छिक | इसे ठीक करें ताकि क्लाइंट पुनरारंभ के बीच जुड़े रहें। |
| `SOV_DAEMON_LOG_FORMAT` | `human` | `json` संरचित लॉग लाइनों के लिए। |

**डेस्कटॉप ऐप संलग्न करें।** `SOV_DATA` को उस प्रोजेक्ट फ़ोल्डर पर इंगित करें जिसे ऐप खोलता है। डेमॉन अपना हैंडशेक वहां लिखता है, और ऐप `127.0.0.1:47823` से टोकन के साथ डायल करता है:

```bash
SOV_DATA=./ docker compose up -d
```

जबकि कंटेनर डेमॉन का मालिक है, इसे `docker compose` से प्रबंधित करें, न कि होस्ट पर `sov daemon start|stop|status` से। होस्ट CLI कंटेनर की प्रक्रिया को नहीं देख सकता है, इसलिए यह हैंडशेक को पुराना बताता है, और `sov daemon start` इसे साफ़ कर देगा।

**कंटेनर से एंकर करें।** वॉल्यूम में एक टेस्टनेट वॉलेट बनाएं, फिर रीडओनली को बंद करें:

```bash
docker compose run --rm sov wallet
SOV_DAEMON_READONLY=0 docker compose up -d
```

बीज को वॉल्यूम से बाहर रखने के लिए, इसे डॉकर सीक्रेट के रूप में प्रदान करें। `compose.yaml` में टिप्पणी की गई `secrets` ब्लॉक दिखाता है कि यह कैसे करें।

## डेस्कटॉप ऐप (वैकल्पिक, v2.1+)

ऑडिट व्यूअर v2.1 डेस्कटॉप ऐप है - एक टाउरी शेल (रस्ट + वेबव्यू) जो ऑडिट व्यूअर और डेमॉन के ऊपर एक रीड-ओनली गेम व्यू चलाता है।

### इंस्टॉल करें (बाइनरी)

**v2.3.2** वर्तमान रिलीज़ है। GitHub रिलीज़ **v2.3.0** में व्हील या डेस्कटॉप एसेट्स शामिल नहीं थे, इसलिए `pip install …==2.3.0` को पिन न करें।

- **पायथन / डेमॉन:** `pip install 'sovereignty-game[daemon]'` (डेमॉन के लिए 2.3.2 या बाद का संस्करण)।
- **डेस्कटॉप ऐप:** [नवीनतम GitHub रिलीज़](https://github.com/mcp-tool-shop-org/sovereignty/releases/latest) जब CI ने प्लेटफ़ॉर्म फ़ाइलें संलग्न की हों। यदि किसी प्लेटफ़ॉर्म जॉब में विफलता हुई, तो स्रोत से चलाएं (नीचे)।

> **पहली बार लॉन्च होने पर OS चेतावनी की अपेक्षा की जाती है** जब प्रमाणित बाइनरी जारी की जाती हैं। इन बिल्ड में केवल SLSA बिल्ड-प्रोवेनैंस प्रमाणन होता है - OS-स्तरीय Apple डेवलपर ID / ऑथेंटिकोड हस्ताक्षर नहीं। macOS: .app पर नियंत्रण-क्लिक करें → खोलें। विंडोज स्मार्टस्क्रीन: अधिक जानकारी → वैसे भी चलाएं।

### प्रोवेनैंस सत्यापित करें

जब कोई रिलीज़ वास्तव में डेस्कटॉप कलाकृतियों को संलग्न करता है, तो आपके द्वारा डाउनलोड की गई फ़ाइल को सत्यापित करें:

```bash
gh attestation verify \
  --repo mcp-tool-shop-org/sovereignty \
  ./<downloaded-artifact>
```

एक स्वच्छ सत्यापन साबित करता है कि बाइनरी को इस रिपो में रिलीज़ वर्कफ़्लो द्वारा, एक विशिष्ट कमिट से बनाया गया था। OS-स्तरीय कोड साइनिंग की तुलना में विश्वास का एक अलग स्तर - बाइनरी अभी भी OS चेतावनी को ट्रिगर करता है, लेकिन इसकी आपूर्ति-श्रृंखला प्रोवेनैंस क्रिप्टोग्राफ़िक रूप से पिन की गई है।

### स्रोत से चलाएं

यदि आप स्रोत से बनाना चाहते हैं (या बाइनरी आपके प्लेटफ़ॉर्म पर नहीं चलेगी):

```bash
# 1. Install Python + daemon deps
pip install -e '.[xrpl,daemon]'

# 2. Install frontend + Rust deps (one-time)
cd app && npm install && cd ..
cargo build --manifest-path app/src-tauri/Cargo.toml

# 3. Start the dev shell (auto-starts the daemon in readonly mode)
npm --prefix app run tauri dev
```

टाउरी शेल लॉन्च पर स्वचालित रूप से एक रीड-ओनली डेमॉन शुरू करता है और बाहर निकलने पर इसे स्वचालित रूप से बंद कर देता है। बाहरी रूप से शुरू किए गए डेमॉन (`sov daemon start`) शेल पुनरारंभ के दौरान भी सक्रिय रहते हैं।

पूर्ण अनुबंध के लिए [docs/v2.1-tauri-shell.md](docs/v2.1-tauri-shell.md) देखें।

ऑडिट व्यूअर तीन व्यू के साथ आता है:

- **`/audit`** - XRPL-आधारित प्रमाण व्यूअर। प्रति-गेम सूची, प्रति-राउंड एंकर स्थिति, "सभी राउंड सत्यापित करें" स्थानीय प्रमाण पुनर्गणना + श्रृंखला लुकअप को श्रृंखला में चलाता है। ऑडिटर का दृश्य: कच्चे JSON को पढ़े बिना, पुष्टि करें कि एक गेम ईमानदारी से चला।
- **`/game`** - सक्रिय गेम के लिए निष्क्रिय वास्तविक समय स्थिति प्रदर्शन। खिलाड़ी संसाधन कार्ड, राउंड टाइमलाइन, अंतिम-20 SSE इवेंट लॉग। केवल पढ़ने के लिए; दूसरे टर्मिनल में CLI में खेलें।
- **`/settings`** - डेमॉन कॉन्फ़िगरेशन प्रदर्शन + नेटवर्क स्विचर (टेस्टनेट / मेननेट / डेवनेट) मेननेट-पुष्टि गार्डरेल के साथ।

[docs/v2.1-views.md](docs/v2.1-views.md) पर पूर्ण व्यू विनिर्देश।

## यह कैसे काम करता है

आप **5 सिक्के** और **3 प्रतिष्ठा** के साथ शुरुआत करते हैं। एक पासा पलटें, 16-स्थान वाले बोर्ड पर घूमें, और उन स्थानों पर उतरें जो आपको विकल्प देते हैं: व्यापार करें, किसी की मदद करें, जोखिम उठाएं, या एक कार्ड खींचें।

**28 इवेंट कार्ड** क्षणों की तरह पढ़े जाते हैं: *"क्या किसी ने एक छोटा चमड़े का पाउच देखा है?"* (खोया हुआ वॉलेट) या *"किसी ने नहीं देखा... है ना?"* (एक शॉर्टकट मिला)। टाउन हॉल गेम के लिए बाजार-शिफ्ट इवेंट शामिल हैं।

**12 डील कार्ड + 10 वाउचर कार्ड** बातचीत को मजबूर करते हैं: *"क्या आप मुझे 2 सिक्के उधार देंगे? मैं 3 वापस कर दूंगा।"* या *"अगर आपके पास मेरा है, तो मेरे पास आपका है।"* सौदे समय सीमा के साथ लक्ष्य निर्धारित करते हैं; वाउचर IOUs हैं जिन्हें आप अन्य खिलाड़ियों को जारी करते हैं।

**प्रॉमिस नियम:** प्रत्येक राउंड में, जोर से कहें "मैं वादा करता हूं..." और किसी चीज़ के लिए प्रतिबद्ध रहें। इसे निभाएं: +1 प्रतिष्ठा। तोड़ें: -2 प्रतिष्ठा। तालिका तय करती है।

**माफ़ी:** यदि आपने एक गेम में एक वादा तोड़ा है, तो सार्वजनिक रूप से माफी मांगें। जिसे आपने गलत किया है, उसे 1 सिक्का दें, +1 प्रतिष्ठा वापस पाएं।

**अपना लक्ष्य चुनें** (गुप्त या सार्वजनिक):
- **समृद्धि** - 20 सिक्के तक पहुंचें
- **प्रिय** - 10 प्रतिष्ठा तक पहुंचें
- **बिल्डर** - 4 अपग्रेड पूरा करें

15 राउंड के बाद, उच्चतम संयुक्त स्कोर जीतता है।

## डायरी मोड क्या है?

प्रत्येक राउंड में, कंसोल एक **प्रूफ** उत्पन्न कर सकता है - गेम स्थिति की एक उंगलियों का निशान। यदि कोई स्कोर बदलता है, तो उंगलियों का निशान मेल नहीं खाएगा।

वैकल्पिक रूप से, उस उंगलियों के निशान को **XRPL टेस्टनेट** पर पोस्ट किया जा सकता है - एक सार्वजनिक लेज़र। इसे स्कोर को एक दीवार पर लिखने के रूप में सोचें जिसे कोई भी मिटा नहीं सकता।

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

केवल होस्ट को एक वॉलेट की आवश्यकता है। कोई और स्क्रीन को नहीं छूता है। गेम बिना एंकरिंग के भी पूरी तरह से काम करता है - यह सिर्फ डायरी है जो याद रखती है।

## तीन स्तर

| स्तर | नाम | स्थिति | यह क्या जोड़ता है |
|------|------|--------|-------------|
| 1 | **Campfire** | खेलने योग्य | सिक्के, प्रतिष्ठा, वादे, IOUs |
| 2 | **Town Hall** | खेलने योग्य | साझा बाजार, संसाधन की कमी |
| 3 | **Treaty Table** | खेलने योग्य | दांव के साथ संधियाँ - वादों के साथ दांत |

मुख्य नियम v1.x के माध्यम से स्थिर हैं। [रोडमैप](docs/roadmap.md) देखें।

## परिदृश्य पैक

कोई नया नियम नहीं। बस वाइब्स। प्रत्येक पैक एक स्तर, नुस्खा और मूड सेट करता है।

| परिदृश्य | स्तर | सर्वोत्तम किसके लिए |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | कैम्पफ़ायर / मार्केट डे | पहला गेम, मिश्रित समूह |
| [Market Panic](docs/scenarios/market-panic.md) | टाउन हॉल | आर्थिक नाटक |
| [Promises Matter](docs/scenarios/promises-matter.md) | कैम्पफ़ायर | विश्वास और प्रतिबद्धता |
| [Treaty Night](docs/scenarios/treaty-night.md) | संधि तालिका | उच्च-दांव समझौते |

कंसोल से ब्राउज़ करने के लिए `sov scenario list`।

## परियोजना संरचना

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

## विकास

```bash
git clone https://github.com/mcp-tool-shop-org/sovereignty.git
cd sovereignty
uv sync --dev
uv run pytest tests/ -v
uv run ruff check .
```

## डिजाइन सिद्धांत

> "परिणामों के माध्यम से सिखाएं, शब्दावली से नहीं।"

खिलाड़ी करके सीखते हैं: IOUs जारी करना, वादे तोड़ना, बदलते मूल्यों पर व्यापार करना। अवधारणाएं Web3 प्राइमेटिव्स में मैप करती हैं - वॉलेट, टोकन, ट्रस्ट लाइनें - लेकिन खिलाड़ियों को मज़े करने के लिए यह जानने की आवश्यकता नहीं है।

## योगदान

योगदान करने का सबसे आसान तरीका है [एक कार्ड जोड़ना](CONTRIBUTING.md)। इंजन के ज्ञान की आवश्यकता नहीं है - बस एक नाम, एक विवरण और कुछ स्वाद पाठ।

## सुरक्षा

वॉलेट सीड, गेम की स्थिति और प्रमाण फ़ाइलें – क्या साझा करना है और क्या नहीं। कोई टेलीमेट्री नहीं, कोई विश्लेषण नहीं, कोई होम-कनेक्शन नहीं। एकमात्र वैकल्पिक नेटवर्क कॉल XRPL टेस्टनेट एंकरिंग है।

[सुरक्षा.एमडी](SECURITY.md) देखें।

## खतरा मॉडल

| खतरा | निवारण |
|--------|-----------|
| प्रमाणों के माध्यम से सीड का रिसाव | प्रमाणों में केवल हैश होते हैं, कभी भी सीड नहीं |
| गिट में सीड | `.sov/` गिट द्वारा अनदेखा किया गया; `sov wallet` चेतावनी देता है |
| गेम की स्थिति में हेरफेर | राउंड प्रमाण `envelope_hash`, `game_id`, `round`, `ruleset`, `rng_seed`, `timestamp_utc`, `players` और `state` को कवर करता है। `sov verify` पूरे लिफाफे में छेड़छाड़ का पता लगाता है। प्रमाण प्रारूप v1 अब v2.0.0+ में समर्थित नहीं है। |
| XRPL एंकर स्पूफिंग | प्रमाण हैश ऑन-चेन पर एंकर किया गया; सत्यापन में बेमेल का पता लगाना |
| कंटेनर एक्सपोजर | डेमॉन इमेज केवल होस्ट `127.0.0.1` पर प्रकाशित होती है; प्रत्येक अनुरोध पर बेयरर टोकन; डिफ़ॉल्ट रूप से केवल-पढ़ने योग्य; एक गैर-रूट उपयोगकर्ता के रूप में चलती है जिसमें केवल-पढ़ने योग्य रूट फ़ाइल सिस्टम और कोई क्षमता नहीं होती है |
| खिलाड़ी के नाम की गोपनीयता | खिलाड़ियों के नाम प्रमाणों में शामिल हैं (शीर्ष-स्तरीय `players` सूची और खिलाड़ी स्नैपशॉट के अंदर)। निजी गेम के लिए, `proof.json` प्रकाशित न करें या पोस्टकार्ड साझा न करें। |

## लाइसेंस

एमआईटी

---

[एमसीपी टूल शॉप](https://mcp-tool-shop.github.io/) द्वारा निर्मित
