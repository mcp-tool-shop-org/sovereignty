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
  <a href="https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/sovereignty/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://mcp-tool-shop-org.github.io/sovereignty/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

## आज रात खेलें

कार्ड प्रिंट करें, एक पासा और कुछ सिक्के लें, 2-4 लोगों के साथ बैठें।
किसी भी स्क्रीन की आवश्यकता नहीं है। इसमें लगभग 30 मिनट लगते हैं।

**[यहां से शुरू करें](docs/start_here.md)** | **[प्रिंट करें और खेलें](docs/print-and-play.md)** | **[पूर्ण नियम](docs/rules/campfire_v1.md)** | **[अजनबियों के साथ खेलें](docs/play-with-strangers.md)**

## या कंसोल का उपयोग करें

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

कंसोल स्कोर रखता है। आप अपने वादे निभाते हैं।

## यह कैसे काम करता है

आप **5 सिक्के** और **3 प्रतिष्ठा** के साथ शुरुआत करते हैं। पासा फेंकें, 16 स्थानों वाले बोर्ड पर घूमें, और उन स्थानों पर पहुंचें जो आपको विकल्प देते हैं: व्यापार करें, किसी की मदद करें, जोखिम लें, या एक कार्ड निकालें।

**20 इवेंट कार्ड** ऐसे क्षणों की तरह होते हैं: *"क्या किसी ने एक छोटा चमड़े का पाउच देखा है?"* (खोया हुआ वॉलेट) या *"किसी ने... नहीं देखा, है ना?"* (एक शॉर्टकट मिला)।

**20 डील कार्ड** बातचीत को प्रोत्साहित करते हैं: *"क्या आप मुझे 2 सिक्के उधार दे सकते हैं? मैं 3 वापस कर दूंगा।"* या *"अगर आपका साथ है, तो मैं आपका साथ दूंगा।"*

**वादे का नियम:** प्रत्येक राउंड में एक बार, ज़ोर से "मैं वादा करता हूं..." कहें और किसी चीज़ के लिए प्रतिबद्ध हों। उस पर टिके रहें: +1 प्रतिष्ठा। वादा तोड़ें: -2 प्रतिष्ठा।
टेबल तय करता है।

**माफी:** खेल में एक बार, यदि आपने कोई वादा तोड़ा है, तो सार्वजनिक रूप से माफी मांगें।
जिस व्यक्ति को आपने चोट पहुंचाई है, उसे 1 सिक्का दें, +1 प्रतिष्ठा प्राप्त करें।

**अपना लक्ष्य चुनें** (गुप्त या सार्वजनिक):
- **समृद्धि** — 20 सिक्के प्राप्त करें
- **प्रिय** — 10 प्रतिष्ठा प्राप्त करें
- **निर्माता** — 4 अपग्रेड पूरे करें

15 राउंड के बाद, उच्चतम संयुक्त स्कोर वाला व्यक्ति जीतता है।

## डायरी मोड क्या है?

प्रत्येक राउंड में, कंसोल एक **प्रमाण** उत्पन्न कर सकता है — खेल की स्थिति का एक "फिंगरप्रिंट"। यदि कोई स्कोर बदलता है, तो फिंगरप्रिंट मेल नहीं खाएगा।

वैकल्पिक रूप से, उस फिंगरप्रिंट को **XRPL टेस्टनेट** पर पोस्ट किया जा सकता है — एक सार्वजनिक खाता बही। इसे दीवार पर स्कोर लिखने जैसा सोचें जिसे कोई भी मिटा नहीं सकता।

```bash
sov end-round                        # generate proof
sov wallet                           # create testnet wallet (free)
sov anchor                           # post hash to XRPL (optional)
sov verify proof.json --tx <txid>    # trust but verify
```

केवल होस्ट को एक वॉलेट की आवश्यकता होती है। कोई और स्क्रीन को नहीं छूता है। खेल बिना किसी "एंकरिंग" के पूरी तरह से काम करता है - यह सिर्फ डायरी है जो याद रखती है।

## तीन स्तर

| स्तर | नाम | स्थिति | यह क्या जोड़ता है |
|------|------|--------|-------------|
| 1 | **Campfire** | खेलने योग्य | सिक्के, प्रतिष्ठा, वादे, उधार |
| 2 | **Town Hall** | खेलने योग्य | साझा बाजार, संसाधनों की कमी |
| 3 | **Treaty Table** | खेलने योग्य | शर्तों के साथ समझौते — दांव के साथ वादे |

कोर नियम v1.x के माध्यम से स्थिर हैं। [रोडमैप](docs/roadmap.md) देखें।

## परिदृश्य पैक

कोई नया नियम नहीं। बस माहौल। प्रत्येक पैक एक स्तर, रेसिपी और मूड सेट करता है।

| परिदृश्य | स्तर | किसके लिए सबसे अच्छा |
|----------|------|----------|
| [Cozy Night](docs/scenarios/cozy-night.md) | कैंपफायर / मार्केट डे | पहला खेल, मिश्रित समूह |
| [Market Panic](docs/scenarios/market-panic.md) | टाउन हॉल | अर्थव्यवस्था का नाटक |
| [Promises Matter](docs/scenarios/promises-matter.md) | कैंपफायर | विश्वास और प्रतिबद्धता |
| [Treaty Night](docs/scenarios/treaty-night.md) | समझौता तालिका | उच्च-दांव समझौते |

कंसोल से ब्राउज़ करने के लिए `sov scenario list`।

## परियोजना संरचना

```
sovereignty/
  sov_engine/       # Pure game logic (models, rules, serialization, hashing)
  sov_transport/    # Ledger transport (offline + XRPL Testnet)
  sov_cli/          # Typer CLI (the "Round Console")
  tests/            # 143 tests
  docs/             # Rules, cards, print-and-play, play-with-strangers
  assets/print/     # Printable cards, player mat, quick reference
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

खिलाड़ी करके सीखते हैं: IOUs जारी करना, वादे तोड़ना, बदलते दामों पर व्यापार करना। अवधारणाएं Web3 primitives — वॉलेट, टोकन, ट्रस्ट लाइन्स — से संबंधित हैं, लेकिन खिलाड़ियों को मज़े करने के लिए उन्हें यह जानने की आवश्यकता नहीं है।

## योगदान

योगदान करने का सबसे आसान तरीका है [एक कार्ड जोड़ना](CONTRIBUTING.md)।
किसी भी इंजन के ज्ञान की आवश्यकता नहीं है - बस एक नाम, एक विवरण और कुछ अतिरिक्त पाठ।

## सुरक्षा

वॉलेट बीज, खेल की स्थिति और प्रमाण फ़ाइलें - क्या साझा करें और क्या नहीं।
कोई टेलीमेट्री नहीं, कोई एनालिटिक्स नहीं, कोई "फोन-होम" नहीं। एकमात्र वैकल्पिक नेटवर्क कॉल XRPL टेस्टनेट एंकरिंग है।

[सुरक्षा](SECURITY.md) देखें।

## खतरे का मॉडल

| खतरा | शमन (Mitigation) |
|--------|-----------|
| प्रूफ के माध्यम से सीड का रिसाव | प्रूफ में केवल हैश होते हैं, कभी भी सीड नहीं। |
| गिट में सीड | `.sov/` को गिट द्वारा अनदेखा किया गया है; `sov wallet` चेतावनी देता है। |
| गेम स्टेट में हेरफेर | राउंड प्रूफ में पूरी स्टेट का हैश होता है; `sov verify` से छेड़छाड़ का पता चलता है। |
| XRPL एंकर का जालसाजी | प्रूफ हैश को ब्लॉकचेन पर एंकर किया गया है; `verify` में बेमेल का पता लगाया जाता है। |
| खिलाड़ी के नाम की गोपनीयता | गेम स्टेट केवल स्थानीय होता है; प्रूफ में नाम शामिल नहीं होते हैं। |

## लाइसेंस

एमआईटी (MIT)

---

[MCP Tool Shop](https://mcp-tool-shop.github.io/) द्वारा निर्मित।
