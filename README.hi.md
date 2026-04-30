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

## 30 सेकंड में इंस्टॉल करें

सबसे तेज़ तरीका — पायथन उपयोगकर्ताओं के लिए:

```bash
pipx install sovereignty-game
sov tutorial
```

क्या आपके पास पायथन नहीं है? कोई बात नहीं। `npx` का उपयोग करके, एक पहले से तैयार बाइनरी डाउनलोड हो जाएगी:

```bash
npx @mcptoolshop/sovereignty tutorial
```

बस इतना ही। `sov tutorial` आपको लगभग 60 सेकंड में नियमों के बारे में बताएगा।

## आपका पहला खेल

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

> क्या आप पहले एक निर्देशित इन-ऐप ट्यूटोरियल चाहते हैं? `sov tutorial` चलाएं।
> क्या आप बिना किसी सॉफ्टवेयर के खेलना चाहते हैं? [प्रिंट और खेलें](docs/print-and-play.md) देखें।
> क्या आप नियमों के बारे में अधिक जानना चाहते हैं? [यहां से शुरू करें](docs/start_here.md) या
> [पूरा मैनुअल](https://mcp-tool-shop-org.github.io/sovereignty/handbook/) देखें।

> _एक छोटा डेमो GIF या स्क्रीनशॉट यहां होना चाहिए — इसे स्टेज डी के रूप में ट्रैक किया गया है
> ताकि README यह दिखा सके कि एक बारी वास्तव में कैसी दिखती है।_

## कंसोल के बिना खेलें

कार्ड प्रिंट करें, एक पासा और कुछ सिक्के लें, 2-4 लोगों के साथ बैठें।
यह खेल पूरी तरह से टेबल पर खेला जा सकता है।

**[यहां से शुरू करें](docs/start_here.md)** | **[प्रिंट और खेलें](docs/print-and-play.md)** | **[नियम](docs/rules/campfire_v1.md)** | **[अजनबियों के साथ खेलें](docs/play-with-strangers.md)**

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

कंसोल स्कोर रखता है। आप अपने वादे निभाते हैं।

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
