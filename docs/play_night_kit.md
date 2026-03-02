# Play Night Kit

**Hosting Sovereignty: 10 minutes to set the table.**

---

## What to prepare

### Print

- The board (16 spaces, fits one page)
- Event cards (28) and Deal cards (22) — cut along the lines
- One player mat per person (name, coins, rep, upgrades, resources)

### Put in the middle

- Coins: pennies, poker chips, or anything small and stackable
- Resource tokens (Market Day / Town Hall only): three colors for
  Food, Wood, and Tools — buttons, beads, or colored paper squares
- The Apology Reminder: a card that says "Once per game. 1 coin. +1 Rep."
- A phone or laptop running `sov` (one person operates it)

### Who runs the console

One person is the **Console Host**. They type `sov turn`, `sov offer`,
`sov market buy`, etc. Everyone else plays with their hands and voices.

The console keeps score. The table keeps order.

### How to handle disputes

> "The table decides."

If players disagree about whether a promise was kept or a trade was fair,
the group votes. Majority wins. If it's a tie, the disputed player
gets the benefit of the doubt.

If your group cares about the record, use Diary Mode (`sov anchor`) to
stamp the round proof on XRPL Testnet. Then nobody can rewrite history.

### Two table norms (say these out loud before you start)

1. **"Promises are said out loud."** If nobody heard it, it didn't happen.
2. **"One Offer per turn."** Keep it moving. You'll get another chance.

---

## Three recommended first sessions

### Session A: Campfire (30 min)

The "learn-by-playing" session. No resources, no market drama.

| Setting       | Value                        |
|---------------|------------------------------|
| Tier          | Campfire                     |
| Players       | 3 (ideal) or 2              |
| Rounds        | 8 (or first to win)         |
| Win condition | All pick Prosperity (simple) |
| Diary Mode    | Off                          |

**What to pay attention to:**
- Do players make promises? Remind them they can.
- Does anyone apologize? Celebrate it.
- Watch for the first Offer — that's when the game clicks.

**Start command:** `sov new -p Alice -p Bob -p Carol -s 1`

---

### Session B: Market Day (45 min)

"Now you own things." Same social game, but players learn inventory.

| Setting       | Value                          |
|---------------|--------------------------------|
| Tier          | Market Day                     |
| Players       | 3–4                           |
| Rounds        | 10                             |
| Win condition | Mix: 1 Prosperity, 1 Builder  |
| Diary Mode    | Optional                       |

**What to pay attention to:**
- Do players visit the Market, or forget it exists?
- Does anyone try to buy everything? (They can — it's a shop, not a casino.)
- Watch for the first resource-based Offer: "I'll trade you 1 Wood for 2 coins."

**Start command:** `sov new --tier market-day -p Alice -p Bob -p Carol -s 2`

---

### Session C: Town Hall (60 min)

"The market has moods." Scarcity creates drama without you adding rules.

| Setting       | Value                          |
|---------------|--------------------------------|
| Tier          | Town Hall                      |
| Players       | 3–4                           |
| Rounds        | 12–15                         |
| Win condition | Let players choose secretly    |
| Diary Mode    | Yes (anchor at least 1 round) |

**What to pay attention to:**
- When does scarcity first bite? (A resource hits supply 2.)
- Do players hoard or sell? Both are valid strategies.
- Watch the Market Moment in recap — it tells the story of the economy.
- Try the Toast near the end. It lands better after real tension.

**Start command:** `sov new --tier town-hall -p Alice -p Bob -p Carol -p Dave -s 3`

---

### Session D: Treaty Table (75-90 min)

"Agreements have teeth." Everything from Town Hall, plus treaties with stakes.

| Setting       | Value                          |
|---------------|--------------------------------|
| Tier          | Treaty Table                   |
| Players       | 3-4                           |
| Rounds        | 12-15                         |
| Win condition | Let players choose secretly    |
| Diary Mode    | Yes                            |

**What to pay attention to:**
- Who proposes the first treaty? Watch what they stake.
- Does anyone break a treaty? How does the table react?
- Do players use treaties strategically (lock up an opponent's coins)?
- Watch for the "treaty standoff" — two players both wanting to break but afraid to.
- The -3 Rep penalty for breaking is harsh. Does it change behavior?

**Start command:** `sov new --tier treaty-table -p Alice -p Bob -p Carol -p Dave -s 4`

---

## Postcard styles

After the game, run `sov postcard` to get a shareable screenshot.

Three styles emphasize different stories:

| Style    | Command                    | Best for          |
|----------|----------------------------|-------------------|
| Cozy     | `sov postcard --style cozy`     | Highlights help and apologies  |
| Spicy    | `sov postcard --style spicy`    | Highlights broken promises and trades |
| Economic | `sov postcard --style economic` | Highlights market mood and prices |

Default (`sov postcard`) shows everything.

Pick the one that matches the vibe of your night.

---

## After the game

- Share the postcard (screenshot the terminal)
- If you anchored, share the XRPL explorer link — it's the receipt
- Talk about one promise that mattered and one that didn't
- Ask: "Would you play again with more complexity?" If yes → next tier
