<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.md">English</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

## आज रात खेलें

प्रिंट करें [पूरे प्रिंट-एंड-प्ले पैकेज](assets/print/pdf/Sovereignty-Print-Pack.pdf) — बोर्ड, खिलाड़ी के लिए शीट, त्वरित संदर्भ, और कार्ड के तीन डेक, जो 11 अमेरिकी लेटर पेपर शीट पर हैं। एक पासा और कुछ सिक्के ढूंढें। दो या तीन दोस्तों के साथ बैठें। आप बीस मिनट में खेल रहे होंगे।

यदि आप व्यक्तिगत शीट चाहते हैं:

- **[बोर्ड](assets/print/pdf/board.pdf)** — 16 स्थानों वाला कैम्पफायर लूप, एक पृष्ठ।
- **[खिलाड़ी की शीट](assets/print/pdf/mat.pdf)** — सिक्के, प्रतिष्ठा, अपग्रेड, वादे। प्रत्येक खिलाड़ी के लिए एक।
- **[त्वरित संदर्भ](assets/print/pdf/quickref.pdf)** — बोर्ड के स्थान, बारी का क्रम, वादे के नियम।
- **[इवेंट कार्ड](assets/print/pdf/events.pdf)** — 20 कार्ड, तीन पृष्ठ, रेखाओं के साथ काटें।
- **[डील कार्ड](assets/print/pdf/deals.pdf)** — 10 कार्ड, दो पृष्ठ।
- **[वॉउचर कार्ड](assets/print/pdf/vouchers.pdf)** — खिलाड़ियों के बीच 10 ऋण, दो पृष्ठ।
- **[ट्रीटि का त्वरित संदर्भ](assets/print/pdf/treaty.pdf)** — केवल स्तर 3 के लिए।

पीडीएफ वेक्टर हैं और उनमें एम्बेडेड फ़ॉन्ट हैं — वे किसी भी होम प्रिंटर पर साफ प्रिंट होते हैं। सेटअप का विवरण [प्रिंट एंड प्ले](docs/print-and-play.md) पर दिया गया है।

## क्या आप स्कोर रखने के लिए एक कंसोल चाहते हैं?

वैकल्पिक। खेल कागज पर ठीक से चलता है। लेकिन अगर किसी के पास लैपटॉप है, तो `sov` सिक्कों, प्रतिष्ठा, वादों को ट्रैक करता है, और अंत में एक छेड़छाड़-रोधी रसीद उत्पन्न करता है:

```bash
pip install sovereignty-game
sov play campfire_v1
```

`sov play campfire_v1` कोई कॉन्फ़िगरेशन नहीं वाला त्वरित शुरुआत है — एक मानव और एक डिफ़ॉल्ट प्रतिद्वंद्वी। मल्टी-प्लेयर गेम के लिए, `sov new -p Alice -p Bob -p Carol` का उपयोग करें। एक निर्देशित 60-सेकंड के विवरण के लिए, `sov tutorial` का उपयोग करें।

क्या आपके पास पायथन नहीं है? `npx` पथ एक पहले से निर्मित बाइनरी डाउनलोड करता है:

```bash
npx @mcptoolshop/sovereignty tutorial
```

## एक वास्तविक सत्र

जब आप और 2-3 दोस्त एक साथ हों, तो कंसोल राउंड चलाएगा और आप बातचीत करेंगे। एक वास्तविक सत्र ऐसा दिखता है:

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

`sov status` खिलाड़ियों के सिक्के, प्रतिष्ठा, अपग्रेड, स्थिति और लक्ष्य के साथ एक रिच-फॉर्मेटेड टेबल दिखाता है। प्रत्येक बारी के बीच त्वरित जानकारी के लिए:

```bash
sov status --brief
```

```
R3 |  Alice: 7c 4r 0u | >Bob: 4c 3r 0u |  Carol: 6c 5r 0u
```

(`Nc Nr Nu` = सिक्के / प्रतिष्ठा / अपग्रेड; `>` सक्रिय खिलाड़ी को दर्शाता है।)

15 राउंड तक दोहराएं। `sov game-end` अंतिम स्कोर प्रिंट करेगा।

- **कई सहेजे गए गेम** (v2.1+): `sov games` सेव किए गए गेम की सूची दिखाता है; `sov resume <game-id>` का उपयोग करके आप उनके बीच स्विच कर सकते हैं।
- **बैच एंकरिंग** (v2.1+): `sov anchor` गेम के अंत में सभी लंबित राउंड को एक एकल XRPL लेनदेन में समूहित करता है — प्रत्येक गेम के लिए एक सत्यापन योग्य चेन पॉइंटर। मध्य-खेल में फ्लश करने के लिए `sov anchor --checkpoint` का उपयोग करें।
- **नेटवर्क चयन** (v2.1+): `sov anchor --network testnet|mainnet|devnet` (या `SOV_XRPL_NETWORK` पर्यावरण चर; डिफ़ॉल्ट `testnet`)।
- **डेमन मोड** (v2.1+, वैकल्पिक): `sov daemon start` एक लोकलहोस्ट HTTP/JSON सर्वर चलाता है जो डेस्कटॉप एकीकरण और पृष्ठभूमि चेन पोलिंग के लिए उपयोग किया जाता है। नीचे [डेमन मोड](#daemon-mode-optional-v21) देखें।
- **ऑडिट व्यूअर डेस्कटॉप ऐप** (v2.1+, वैकल्पिक): `npm --prefix app run tauri dev`। नीचे [डेस्कटॉप ऐप](#desktop-app-optional-v21) देखें।

> क्या आप पहले ऐप में एक निर्देशित विवरण देखना चाहते हैं? `sov tutorial` चलाएं।
> क्या आप नियमों के बारे में अधिक जानना चाहते हैं? [यहां से शुरू करें](docs/start_here.md) या
> [पूरा मैनुअल](https://mcp-tool-shop-org.github.io/sovereignty/handbook/) देखें।

ऊपर दिया गया `sov turn` का इनलाइन उदाहरण दिखाता है कि कंसोल में एक राउंड कैसा दिखता है; v2.1 डेस्कटॉप विज़ुअलाइज़ेशन के लिए, नीचे [डेस्कटॉप ऐप](#desktop-app-optional-v21) देखें।

**[यहां से शुरू करें](docs/start_here.md)** | **[प्रिंट और खेलें](docs/print-and-play.md)** | **[नियम](docs/rules/campfire_v1.md)** | **[अजनबियों के साथ खेलें](docs/play-with-strangers.md)**

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

कंसोल स्कोर रखता है। आप अपने वादे निभाते हैं।

## डेमन मोड (वैकल्पिक, v2.1+)

डेस्कटॉप एकीकरण (ऑडिट व्यूअर, टाउरी शेल) या पृष्ठभूमि चेन पोलिंग के लिए, सॉवरेनिटी को एक लोकलहोस्ट HTTP डेमन के रूप में चलाएं:

```bash
pip install 'sovereignty-game[daemon]'
sov daemon start --readonly        # audit-only, no wallet seed
sov daemon start                   # full daemon with anchor endpoints (loads XRPL_SEED)
sov daemon status                  # running | stale | none
sov daemon stop
```

डेमन `127.0.0.1` पर एक यादृच्छिक पोर्ट पर बंधा होता है; कनेक्शन विवरण (पोर्ट + बेयरर टोकन) `.sov/daemon.json` में होते हैं। प्रत्येक प्रोजेक्ट रूट में एक डेमन होता है। पूर्ण आईपीसी अनुबंध के लिए [docs/v2.1-daemon-ipc.md](docs/v2.1-daemon-ipc.md) देखें।

## डेस्कटॉप ऐप (वैकल्पिक, v2.1+)

ऑडिट व्यूअर v2.1 डेस्कटॉप ऐप है — एक टाउरी शेल (रस्ट + वेबव्यू) जो ऑडिट व्यूअर और एक रीड-ओनली गेम व्यू को डेमन के ऊपर चलाता है।

### इंस्टॉल करें (बाइनरी)

v2.1.0 में पहले से निर्मित बाइनरी [GitHub रिलीज़ पृष्ठ](https://github.com/mcp-tool-shop-org/sovereignty/releases/latest) पर उपलब्ध हैं:

- **macOS (यूनिवर्सल):** `sovereignty-app-2.1.0-darwin-universal.dmg` — इंटेल + एप्पल सिलिकॉन
- **विंडोज (x64):** `sovereignty-app-2.1.0-win-x64.msi`
- **लिनक्स (x64, .deb):** `sovereignty-app-2.1.0-linux-x64.deb` — डेबियन / उबंटू / व्युत्पन्न। `sudo dpkg -i sovereignty-app-2.1.0-linux-x64.deb` के साथ स्थापित करें। ऐपइमेज सपोर्ट संस्करण 2.2 में उपलब्ध होगा (अपस्ट्रीम `linuxdeploy` / उबंटू 24.04 FUSE इंटरैक्शन)।

आपको ऐप के लिए आवश्यक पायथन डेमॉन भी स्थापित करना होगा: `pip install 'sovereignty-game[daemon]'==2.1.0`.

> **पहली बार चलाने पर चेतावनी दिखाई दे सकती है।** macOS में "अज्ञात डेवलपर" लिखा दिखाई देगा — कंट्रोल-क्लिक करें, "ओपन" चुनें, और पुष्टि करें। विंडोज स्मार्टस्क्रीन में "अपरिचित प्रकाशक" लिखा दिखाई देगा — "अधिक जानकारी" पर क्लिक करें, फिर "फिर भी चलाएं"। दोनों चेतावनियाँ दर्शाती हैं कि संस्करण 2.1 केवल बिल्ड-प्रूवेनेंस प्रमाणन के साथ आता है (इसे `gh attestation verify` से सत्यापित करें), न कि ऑपरेटिंग सिस्टम-स्तरीय कोड साइनिंग के साथ। वर्कस्पेस-स्तरीय साइनिंग इंफ्रास्ट्रक्चर संस्करण 2.2 में उपलब्ध होगा।

### प्रूवेनेंस सत्यापित करें

प्रत्येक रिलीज़ आर्टिफैक्ट में SLSA बिल्ड-प्रूवेनेंस प्रमाणन होता है। चलाने से पहले इसे सत्यापित करें:

```bash
gh attestation verify \
  --repo mcp-tool-shop-org/sovereignty \
  ./sovereignty-app-2.1.0-darwin-universal.dmg
```

सफलतापूर्वक सत्यापन यह साबित करता है कि बाइनरी एक विशिष्ट कमिट से बनाई गई थी, रिलीज़ वर्कफ़्लो द्वारा, इस रिपॉजिटरी में। यह ऑपरेटिंग सिस्टम-स्तरीय कोड साइनिंग से अलग एक अलग स्तर का विश्वास है — बाइनरी अभी भी ऑपरेटिंग सिस्टम की चेतावनी को ट्रिगर करता है, लेकिन इसकी सप्लाई-चेन प्रूवेनेंस क्रिप्टोग्राफिक रूप से सुरक्षित है।

### स्रोत कोड से चलाएं

यदि आप स्रोत कोड से बनाना चाहते हैं (या बाइनरी आपके प्लेटफ़ॉर्म पर नहीं चल रहा है):

```bash
# 1. Install Python + daemon deps
pip install -e '.[xrpl,daemon]'

# 2. Install frontend + Rust deps (one-time)
cd app && npm install && cd ..
cargo build --manifest-path app/src-tauri/Cargo.toml

# 3. Start the dev shell (auto-starts the daemon in readonly mode)
npm --prefix app run tauri dev
```

टॉरी शेल लॉन्च होने पर स्वचालित रूप से एक रीड-ओनली डेमॉन शुरू करता है और बंद होने पर इसे स्वचालित रूप से बंद कर देता है। बाहरी रूप से शुरू किए गए डेमॉन (`sov daemon start`) शेल रीस्टार्ट होने पर भी सक्रिय रहते हैं।

पूरे विवरण के लिए [docs/v2.1-tauri-shell.md](docs/v2.1-tauri-shell.md) देखें।

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

ऑडिट व्यूअर में तीन दृश्य शामिल हैं:

- **`/audit`** — XRPL-आधारित प्रमाण दर्शक। प्रत्येक गेम की सूची, प्रत्येक राउंड की स्थिति, "सभी राउंड सत्यापित करें" स्थानीय प्रमाण की पुनर्गणना और श्रृंखला लुकअप को एक साथ चलाता है। ऑडिटर का दृश्य: यह पुष्टि करें कि कोई गेम बिना कच्चे JSON डेटा पढ़े ईमानदारी से चला।
- **`/game`** — सक्रिय गेम के लिए वास्तविक समय की स्थिति प्रदर्शित करता है। खिलाड़ी संसाधन कार्ड, राउंड टाइमलाइन, पिछले 20 SSE इवेंट लॉग। केवल पढ़ने के लिए; अन्य टर्मिनल में CLI में खेलें।
- **`/settings`** — डेमॉन कॉन्फ़िगरेशन प्रदर्शित करता है + नेटवर्क स्विचर (टेस्टनेट / मेननेट / डेवनेट) जिसमें मेननेट-पुष्टि सुरक्षा उपाय शामिल हैं।

पूरे विवरण के लिए [docs/v2.1-views.md](docs/v2.1-views.md) देखें।

## यह कैसे काम करता है

आप **5 सिक्के** और **3 प्रतिष्ठा** के साथ शुरुआत करते हैं। एक पासा फेंकें, 16 स्थानों वाले बोर्ड पर घूमें, और उन स्थानों पर पहुंचें जो आपको विकल्प देते हैं: व्यापार करें, किसी की मदद करें, जोखिम लें, या एक कार्ड निकालें।

**28 इवेंट कार्ड** ऐसे क्षणों की तरह होते हैं: *"क्या किसी ने एक छोटा चमड़े का पाउच देखा है?"* (खोया हुआ वॉलेट) या *"क्या किसी ने... देखा?"* (एक शॉर्टकट मिला)। टाउन हॉल गेम्स के लिए 8 मार्केट-शिफ्ट इवेंट शामिल हैं।

**22 डील और वाउचर कार्ड** बातचीत को प्रोत्साहित करते हैं: *"क्या आप मुझे 2 सिक्के उधार दे सकते हैं? मैं 3 वापस कर दूंगा।"* या *"अगर आपका साथ है, तो मैं आपका साथ दूंगा।"* डील लक्ष्यों को समय सीमा के साथ निर्धारित करते हैं; वाउचर वे ऋण हैं जो आप अन्य खिलाड़ियों को देते हैं।

**वादा नियम:** प्रत्येक राउंड में एक बार, ज़ोर से "मैं वादा करता हूं..." कहें और किसी चीज़ के लिए प्रतिबद्ध हों। इसे निभाएं: +1 प्रतिष्ठा। इसे तोड़ें: -2 प्रतिष्ठा। टेबल तय करती है।

**माफी:** खेल में एक बार, यदि आपने कोई वादा तोड़ा है, तो सार्वजनिक रूप से माफी मांगें। आपने जिस व्यक्ति को नुकसान पहुंचाया है, उसे 1 सिक्का दें, +1 प्रतिष्ठा प्राप्त करें।

**अपना लक्ष्य चुनें** (गुप्त या सार्वजनिक):
- **समृद्धि** — 20 सिक्के प्राप्त करें
- **प्रिय** — 10 प्रतिष्ठा प्राप्त करें
- **निर्माता** — 4 अपग्रेड पूरा करें

15 राउंड के बाद, उच्चतम संयुक्त स्कोर वाला खिलाड़ी जीतता है।

## डायरी मोड क्या है?

प्रत्येक राउंड में, कंसोल एक **प्रूफ** उत्पन्न कर सकता है — खेल की स्थिति का एक फिंगरप्रिंट। यदि कोई स्कोर बदलता है, तो फिंगरप्रिंट मेल नहीं खाएगा।

वैकल्पिक रूप से, उस फिंगरप्रिंट को **XRPL टेस्टनेट** पर पोस्ट किया जा सकता है — एक सार्वजनिक खाता बही। इसे दीवार पर स्कोर लिखने जैसा सोचें जिसे कोई भी मिटा नहीं सकता।

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

केवल होस्ट को एक वॉलेट की आवश्यकता होती है। कोई और स्क्रीन को नहीं छूता है। खेल बिना किसी कनेक्शन के पूरी तरह से काम करता है — यह केवल डायरी है जो याद रखती है।

## तीन स्तर

| स्तर | नाम | स्थिति | यह क्या जोड़ता है |
|------|------|--------|-------------|
| 1 | **Campfire** | खेलने योग्य | सिक्के, प्रतिष्ठा, वादे, ऋण |
| 2 | **Town Hall** | खेलने योग्य | साझा बाजार, संसाधनों की कमी |
| 3 | **Treaty Table** | खेलने योग्य | शर्तों के साथ समझौते — ऐसे वादे जिनका पालन करना ज़रूरी है |

मुख्य नियम v1.x में स्थिर हैं। [रोडमैप](docs/roadmap.md) देखें।

## परिदृश्य पैकेज

कोई नया नियम नहीं। सिर्फ़ माहौल। प्रत्येक पैकेज एक स्तर, रेसिपी और मूड निर्धारित करता है।

| परिदृश्य | स्तर | किसके लिए सबसे उपयुक्त |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | कैंप फायर / बाजार दिवस | पहला खेल, मिश्रित समूह |
| [Market Panic](docs/scenarios/market-panic.md) | टाउन हॉल | आर्थिक नाटक |
| [Promises Matter](docs/scenarios/promises-matter.md) | कैंप फायर | विश्वास और प्रतिबद्धता |
| [Treaty Night](docs/scenarios/treaty-night.md) | समझौता तालिका | महत्वपूर्ण समझौते |

कंसोल से ब्राउज़ करने के लिए `sov scenario list` का उपयोग करें।

## परियोजना संरचना

```
sovereignty/
  sov_engine/       # Pure game logic (models, rules, serialization, hashing)
  sov_transport/    # Ledger transport (offline + XRPL Testnet)
  sov_cli/          # Typer CLI (the "Round Console")
  tests/            # Engine, transport, and CLI tests
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

## डिज़ाइन सिद्धांत

> "परिणामों के माध्यम से सिखाएं, शब्दावली के माध्यम से नहीं।"

खिलाड़ी करके सीखते हैं: ऋण जारी करना, वादे तोड़ना, बदलते मूल्यों पर व्यापार करना। अवधारणाएं Web3 के मूल सिद्धांतों से जुड़ी हैं - वॉलेट, टोकन, विश्वास रेखाएं - लेकिन खिलाड़ियों को मज़े करने के लिए इन चीज़ों को जानने की ज़रूरत नहीं है।

## योगदान

योगदान करने का सबसे आसान तरीका है [एक कार्ड जोड़ना](CONTRIBUTING.md)।
किसी भी इंजन के ज्ञान की आवश्यकता नहीं है - बस एक नाम, एक विवरण और कुछ अतिरिक्त जानकारी।

## सुरक्षा

वॉलेट बीज, गेम स्टेट और प्रूफ फाइलें - क्या साझा करना है और क्या नहीं।
कोई टेलीमेट्री नहीं, कोई एनालिटिक्स नहीं, कोई डेटा संग्रह नहीं। एकमात्र वैकल्पिक नेटवर्क कॉल XRPL टेस्टनेट एंकरिंग है।

[SECURITY.md](SECURITY.md) देखें।

## खतरे का मॉडल

| खतरा | शमन |
|--------|-----------|
| प्रूफ के माध्यम से बीज का रिसाव | प्रूफ में केवल हैश होते हैं, बीज नहीं |
| गिट में बीज | `.sov/` को गिट द्वारा अनदेखा किया गया है; `sov wallet` चेतावनी देता है |
| गेम स्टेट में छेड़छाड़ | राउंड प्रूफ `envelope_hash` में `game_id`, `round`, `ruleset`, `rng_seed`, `timestamp_utc`, `players` और `state` शामिल हैं। `sov verify` पूरे एन्वेलप में छेड़छाड़ का पता लगाता है। प्रूफ फॉर्मेट v1 अब v2.0.0+ में समर्थित नहीं है। |
| XRPL एंकर स्पूफिंग | प्रूफ हैश को ऑन-चेन एंकर किया गया है; सत्यापन में बेमेल का पता लगाना |
| खिलाड़ी के नाम की गोपनीयता | खिलाड़ियों के नाम प्रूफ में शामिल हैं (शीर्ष-स्तरीय `players` सूची और खिलाड़ी स्नैपशॉट के अंदर)। निजी खेलने के लिए, `proof.json` प्रकाशित न करें या पोस्टकार्ड साझा न करें। |

## लाइसेंस

MIT

---

[MCP Tool Shop](https://mcp-tool-shop.github.io/) द्वारा बनाया गया।
