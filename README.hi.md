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
  <a href="https://pypi.org/project/sovereignty-game/"><img src="https://img.shields.io/pypi/v/sovereignty-game?include_prereleases&style=flat&cacheSeconds=3600" alt="PyPI version"></a>
  <a href="https://pypi.org/project/sovereignty-game/"><img src="https://img.shields.io/pypi/pyversions/sovereignty-game?style=flat&cacheSeconds=3600" alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat&cacheSeconds=86400" alt="License: MIT"></a>
  <a href="https://mcp-tool-shop-org.github.io/sovereignty/"><img src="https://img.shields.io/badge/Landing_Page-live-blue?style=flat&cacheSeconds=86400" alt="Landing Page"></a>
</p>

## आज रात खेलें

[संपूर्ण प्रिंट-एंड-प्ले पैकेज](assets/print/pdf/Sovereignty-Print-Pack.pdf) प्रिंट करें — बोर्ड, खिलाड़ी मैट, त्वरित संदर्भ और यूएस लेटर पेपर की 11 शीट पर तीन डेक कार्ड। एक पासा और कुछ सिक्के ढूंढें। दो या तीन दोस्तों के साथ बैठें। आप बीस मिनट में खेल रहे होंगे।

यदि आप अलग-अलग शीट चाहते हैं:

- **[बोर्ड](assets/print/pdf/board.pdf)** — 16-स्पेस कैम्पफ़ायर लूप, एक पृष्ठ।
- **[खिलाड़ी मैट](assets/print/pdf/mat.pdf)** — सिक्के, प्रतिष्ठा, अपग्रेड, वादे। प्रति खिलाड़ी एक।
- **[त्वरित संदर्भ](assets/print/pdf/quickref.pdf)** — बोर्ड स्पेस, टर्न ऑर्डर, वादा नियम।
- **[इवेंट कार्ड](assets/print/pdf/events.pdf)** — 20 कार्ड, तीन पृष्ठ, रेखाओं के साथ काटें।
- **[डील कार्ड](assets/print/pdf/deals.pdf)** — 10 कार्ड, दो पृष्ठ।
- **[वाउचर कार्ड](assets/print/pdf/vouchers.pdf)** — खिलाड़ियों के बीच 10 आईओयू, दो पृष्ठ।
- **[संधि त्वरित संदर्भ](assets/print/pdf/treaty.pdf)** — केवल टियर 3।

पीडीएफ वेक्टर हैं जिनमें एम्बेडेड फ़ॉन्ट होते हैं - वे किसी भी घरेलू प्रिंटर पर स्पष्ट रूप से प्रिंट होते हैं। सेटअप वॉकथ्रू [प्रिंट एंड प्ले](docs/print-and-play.md) पर उपलब्ध है।

## क्या आप स्कोर रखने के लिए एक कंसोल चाहते हैं?

वैकल्पिक। गेम कागज पर ठीक चलता है। लेकिन अगर किसी के पास लैपटॉप हो, तो `sov` सिक्के, प्रतिष्ठा और वादों को ट्रैक करता है, और अंत में छेड़छाड़-रोधी रसीद तैयार करता है:

```bash
pip install sovereignty-game
sov play campfire_v1
```

`sov play campfire_v1` त्वरित शुरुआत है जिसमें कोई कॉन्फ़िगरेशन नहीं है - एक मानव और एक डिफ़ॉल्ट प्रतिद्वंद्वी। मल्टी-प्लेयर के लिए, `sov new -p Alice -p Bob -p Carol` का उपयोग करें। निर्देशित 60-सेकंड वॉकथ्रू के लिए, `sov tutorial` का उपयोग करें।

क्या आपके पास पायथन नहीं है? `npx` पथ एक पूर्व-निर्मित बाइनरी डाउनलोड करता है:

```bash
npx @mcptoolshop/sovereignty tutorial
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

`sov status` खिलाड़ी के सिक्कों, प्रतिष्ठा, अपग्रेड, स्थिति और लक्ष्य वाली रिच-फॉर्मेटेड तालिका दिखाता है। त्वरित एक-पंक्ति अवलोकन के लिए:

```bash
sov status --brief
```

```
R3 |  Alice: 7c 4r 0u | >Bob: 4c 3r 0u |  Carol: 6c 5r 0u
```

(`Nc Nr Nu` = सिक्के / प्रतिष्ठा / अपग्रेड; `>` सक्रिय खिलाड़ी को चिह्नित करता है।)

15 राउंड तक दोहराएं। `sov game-end` अंतिम स्कोर प्रिंट करता है।

- **कई सहेजे गए गेम** (v2.1+): `sov games` सहेजता सूचीबद्ध करता है; `sov resume <game-id>` उनके बीच स्विच करता है।
- **बैच एंकरिंग** (v2.1+): `sov anchor` गेम के अंत में सभी लंबित राउंड को एक ही एक्सआरपीएल लेनदेन में बैच करता है - प्रति गेम एक सत्यापन योग्य श्रृंखला पॉइंटर। मध्य-गेम फ्लश के लिए `sov anchor --checkpoint` का उपयोग करें।
- **नेटवर्क चयन** (v2.1+): `sov anchor --network testnet|mainnet|devnet` (या `SOV_XRPL_NETWORK` पर्यावरण चर; डिफ़ॉल्ट `testnet`)।
- **डेमॉन मोड** (v2.1+, वैकल्पिक): `sov daemon start` डेस्कटॉप एकीकरण और पृष्ठभूमि श्रृंखला पोलिंग के लिए एक लोकलहोस्ट HTTP/JSON सर्वर चलाता है। नीचे [डेमॉन मोड](#daemon-mode-optional-v21) देखें।
- **ऑडिट व्यूअर डेस्कटॉप ऐप** (v2.1+, वैकल्पिक): `npm --prefix app run tauri dev`। नीचे [डेस्कटॉप ऐप](#desktop-app-optional-v21) देखें।

> क्या आप पहले एक निर्देशित इन-ऐप वॉकथ्रू चाहते हैं? `sov tutorial` चलाएं।
> क्या आप नियमों का अधिक विस्तृत दौरा चाहते हैं? [यहां से शुरू करें](docs/start_here.md) या
> [पूर्ण हैंडबुक](https://mcp-tool-shop-org.github.io/sovereignty/handbook/) देखें।

ऊपर दिए गए इनलाइन `sov turn` उदाहरण में दिखाया गया है कि कंसोल में एक राउंड कैसा दिखता है; v2.1 डेस्कटॉप विज़ुअलाइज़ेशन के लिए, नीचे [डेस्कटॉप ऐप](#desktop-app-optional-v21) देखें।

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

डेस्कटॉप एकीकरण (ऑडिट व्यूअर, टौरी शेल) या पृष्ठभूमि श्रृंखला पोलिंग के लिए, सॉवरेनिटी को लोकलहोस्ट HTTP डेमॉन के रूप में चलाएं:

```bash
pip install 'sovereignty-game[daemon]'
sov daemon start --readonly        # audit-only, no wallet seed
sov daemon start                   # full daemon with anchor endpoints (loads XRPL_SEED)
sov daemon status                  # running | stale | none
sov daemon stop
```

डेमॉन `127.0.0.1` पर एक यादृच्छिक पोर्ट पर बाध्य होता है; कनेक्शन विवरण (पोर्ट + बेयरर टोकन) `.sov/daemon.json` में होते हैं। प्रति प्रोजेक्ट रूट एक डेमॉन। पूर्ण आईपीसी अनुबंध के लिए [docs/v2.1-daemon-ipc.md](docs/v2.1-daemon-ipc.md) देखें।

## डेस्कटॉप ऐप (वैकल्पिक, v2.1+)

ऑडिट व्यूअर v2.1 डेस्कटॉप ऐप है - एक टौरी शेल (रस्ट + वेबव्यू) जो ऑडिट व्यूअर और डेमॉन के शीर्ष पर केवल-पढ़ने योग्य गेम दृश्य चलाता है।

### स्थापित करें (बाइनरी)

v2.3.0 [गिटहब रिलीज़ पेज](https://github.com/mcp-tool-shop-org/sovereignty/releases/latest) पर पूर्व-निर्मित बाइनरी के साथ आता है:

- **macOS (यूनिवर्सल):** `sovereignty-app-2.3.0-darwin-universal.dmg` — इंटेल + एप्पल सिलिकॉन
- **विंडोज (x64):** `sovereignty-app-2.3.0-win-x64.msi`
- **लिनक्स (x64, .deb):** `sovereignty-app-2.3.0-linux-x64.deb` — डेबियन / उबंटू / डेरिवेटिव। `sudo dpkg -i sovereignty-app-2.3.0-linux-x64.deb` के साथ स्थापित करें।
- **लिनक्स (x64, AppImage):** `sovereignty-app-2.3.0-linux-x64.AppImage` — `chmod +x` फिर चलाएं।

आपको ऐप का समर्थन करने वाले पायथन डेमॉन की भी आवश्यकता है: `pip install 'sovereignty-game[daemon]'==2.3.0`।

> **पहली लॉन्च चेतावनी अपेक्षित है।** macOS "अज्ञात डेवलपर" कहेगा - .app पर नियंत्रण-क्लिक करें, खोलें चुनें, पुष्टि करें। विंडोज स्मार्टस्क्रीन कहेगा "अपरिचित प्रकाशक" — "अधिक जानकारी" पर क्लिक करें फिर "फिर भी चलाएं"। दोनों चेतावनियां दर्शाती हैं कि वर्तमान रिलीज़ केवल बिल्ड-प्रोवेनैंस एटेस्टेशन के साथ शिप होती हैं (`gh attestation verify` से सत्यापित करें), न कि ओएस-स्तरीय कोड साइनिंग।

### उत्पत्ति को सत्यापित करें

प्रत्येक रिलीज़ कलाकृति में एक SLSA बिल्ड-प्रोवेनैंस एटेस्टेशन होता है। चलाने से पहले सत्यापित करें:

```bash
gh attestation verify \
  --repo mcp-tool-shop-org/sovereignty \
  ./sovereignty-app-2.3.0-darwin-universal.dmg
```

एक स्वच्छ सत्यापन साबित करता है कि बाइनरी को इस रिपो में, रिलीज़ वर्कफ़्लो द्वारा, एक विशिष्ट कमिट से बनाया गया था। ओएस-स्तरीय कोड साइनिंग की तुलना में विश्वास का एक अलग स्तर - बाइनरी अभी भी ओएस चेतावनी को ट्रिगर करती है, लेकिन इसकी आपूर्ति-श्रृंखला उत्पत्ति क्रिप्टोग्राफिक रूप से पिन की जाती है।

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

टौरी शेल लॉन्च पर एक रीडओनली डेमॉन को स्वचालित रूप से शुरू करता है और बाहर निकलने पर इसे स्वचालित रूप से बंद कर देता है। बाहरी रूप से शुरू किए गए डेमॉन (`sov daemon start`) शेल पुनरारंभ के बीच जीवित रहते हैं।

पूर्ण अनुबंध के लिए [docs/v2.1-tauri-shell.md](docs/v2.1-tauri-shell.md) देखें।

ऑडिट व्यूअर में तीन दृश्य होते हैं:

- **`/audit`** — XRPL-आधारित प्रमाण दर्शक। प्रति गेम सूची को संकुचित किया जा सकता है, प्रति राउंड एंकर स्थिति, "सभी राउंड सत्यापित करें" स्थानीय रूप से प्रमाण की पुनर्गणना करता है + श्रृंखला में खोज करता है। ऑडिटर का दृष्टिकोण: कच्चे JSON को पढ़े बिना यह पुष्टि करें कि गेम ईमानदारी से खेला गया था।
- **`/game`** — सक्रिय गेम के लिए निष्क्रिय वास्तविक समय की स्थिति प्रदर्शन। खिलाड़ी संसाधन कार्ड, राउंड टाइमलाइन, अंतिम 20 SSE इवेंट लॉग। केवल पढ़ने के लिए; इसे किसी अन्य टर्मिनल में CLI में चलाएं।
- **`/settings`** — डेमॉन कॉन्फ़िगरेशन प्रदर्शन + नेटवर्क स्विचर (टेस्टनेट / मेननेट / देवनेट) जिसमें मेननेट-पुष्टि सुरक्षा उपाय है।

पूर्ण दृश्य विनिर्देश [docs/v2.1-views.md](docs/v2.1-views.md) पर देखें।

## यह कैसे काम करता है

आप **5 सिक्कों** और **3 प्रतिष्ठा** के साथ शुरुआत करते हैं। एक पासा पलटें, 16-स्थान वाले बोर्ड पर घूमें, और उन स्थानों पर उतरें जो आपको विकल्प देते हैं: व्यापार करें, किसी की मदद करें, जोखिम उठाएं या एक कार्ड खींचें।

**20 इवेंट कार्ड** क्षणों की तरह पढ़े जाते हैं: *"क्या किसी ने एक छोटा चमड़े का पाउच देखा है?"* (खोया हुआ वॉलेट) या *"किसी ने नहीं देखा... सही?"* (एक शॉर्टकट मिला)। टाउन हॉल गेम के लिए बाजार-परिवर्तन घटनाओं को शामिल करता है।

**10 डील कार्ड + 10 वाउचर कार्ड** बातचीत को मजबूर करते हैं: *"क्या आप मुझे 2 सिक्के देंगे? मैं 3 वापस कर दूंगा।"* या *"अगर आपके पास मेरा समर्थन है, तो मेरे पास आपका समर्थन है।"* सौदे समय सीमा के साथ लक्ष्य निर्धारित करते हैं; वाउचर वे IOUs हैं जिन्हें आप अन्य खिलाड़ियों को जारी करते हैं।

**वादा नियम:** प्रत्येक राउंड में एक बार, ज़ोर से कहें "मैं वादा करता हूँ..." और किसी चीज़ के लिए प्रतिबद्ध रहें। इसे निभाएं: +1 प्रतिष्ठा। तोड़ें: -2 प्रतिष्ठा। तालिका निर्णय लेती है।

**माफ़ी:** यदि आपने किसी वादे को तोड़ा है, तो गेम में एक बार सार्वजनिक रूप से माफ़ी मांगें। जिस व्यक्ति के साथ आपने गलत किया, उसे 1 सिक्का दें, और +1 प्रतिष्ठा वापस प्राप्त करें।

**अपना लक्ष्य चुनें** (गुप्त या सार्वजनिक):
- **समृद्धि** — 20 सिक्के तक पहुंचें
- **प्रिय** — 10 प्रतिष्ठा तक पहुंचें
- **निर्माता** — 4 अपग्रेड पूरे करें

15 राउंड के बाद, उच्चतम संयुक्त स्कोर जीतता है।

## डायरी मोड क्या है?

प्रत्येक राउंड में, कंसोल एक **प्रमाण** उत्पन्न कर सकता है — गेम स्थिति की उंगलियों का निशान। यदि कोई स्कोर बदलता है, तो उंगलियों का निशान मेल नहीं खाएगा।

वैकल्पिक रूप से, उस उंगलियों के निशान को **XRPL टेस्टनेट** पर पोस्ट किया जा सकता है — एक सार्वजनिक लेज़र। इसे दीवार पर स्कोर लिखने जैसा समझें जिसे कोई भी मिटा न सके।

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

केवल होस्ट को ही वॉलेट की आवश्यकता होती है। कोई और स्क्रीन को नहीं छूता है। गेम एंकरिंग के बिना पूरी तरह से काम करता है - यह सिर्फ डायरी है जो याद रखती है।

## तीन स्तर

| स्तर | नाम | स्थिति | यह क्या जोड़ता है |
|------|------|--------|-------------|
| 1 | **Campfire** | खेलने योग्य | सिक्के, प्रतिष्ठा, वादे, IOUs |
| 2 | **Town Hall** | खेलने योग्य | साझा बाजार, संसाधन की कमी |
| 3 | **Treaty Table** | खेलने योग्य | दांव वाली संधियाँ - मजबूत वादे |

मुख्य नियम v1.x के माध्यम से स्थिर हैं। [रोडमैप](docs/roadmap.md) देखें।

## परिदृश्य पैक

कोई नया नियम नहीं। बस माहौल। प्रत्येक पैक एक स्तर, रेसिपी और मूड निर्धारित करता है।

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

## डिजाइन सिद्धांत

> "परिणामों के माध्यम से सिखाएं, शब्दावली नहीं।"

खिलाड़ी करके सीखते हैं: IOUs जारी करना, वादे तोड़ना, बदलते मूल्यों पर व्यापार करना। अवधारणाएँ Web3 प्राइमेटिव्स - वॉलेट, टोकन, ट्रस्ट लाइन - से मेल खाती हैं, लेकिन खिलाड़ियों को मज़े करने के लिए यह जानने की आवश्यकता नहीं है।

## योगदान

योगदान करने का सबसे आसान तरीका [एक कार्ड जोड़ना](CONTRIBUTING.md) है। इंजन ज्ञान की आवश्यकता नहीं है - बस एक नाम, एक विवरण और कुछ स्वाद पाठ।

## सुरक्षा

वॉलेट बीज, गेम स्थिति और प्रमाण फ़ाइलें - क्या साझा करना है और क्या नहीं। कोई टेलीमेट्री, कोई एनालिटिक्स, कोई फोन-होम नहीं। एकमात्र वैकल्पिक नेटवर्क कॉल XRPL टेस्टनेट एंकरिंग है।

[SECURITY.md](SECURITY.md) देखें।

## खतरा मॉडल

| खतरा | शमन |
|--------|-----------|
| प्रमाणों के माध्यम से बीज का रिसाव | प्रमाणों में केवल हैश होते हैं, कभी भी बीज नहीं |
| गिट में बीज | `.sov/` गिट द्वारा अनदेखा किया गया; `sov wallet` चेतावनी देता है |
| गेम स्थिति का हेरफेर | राउंड प्रमाण `envelope_hash`, `game_id`, `round`, `ruleset`, `rng_seed`, `timestamp_utc`, `players` और `state` को कवर करता है। `sov verify` पूरे लिफाफे में छेड़छाड़ का पता लगाता है। प्रारूप v1 अब v2.0.0+ में समर्थित नहीं है। |
| XRPL एंकर स्पूफिंग | प्रमाण हैश ऑन-चेन पर लंगर डाला गया; सत्यापन में बेमेल का पता लगाना |
| खिलाड़ी के नाम की गोपनीयता | खिलाड़ियों के नाम प्रमाणों (शीर्ष-स्तरीय `players` सूची और खिलाड़ी स्नैपशॉट के अंदर) में शामिल हैं। निजी गेम के लिए, `proof.json` प्रकाशित न करें या पोस्टकार्ड साझा न करें। |

## लाइसेंस

MIT

---

[MCP टूल शॉप](https://mcp-tool-shop.github.io/) द्वारा निर्मित
