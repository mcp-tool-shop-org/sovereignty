---
title: Beginners
description: New to Sovereignty? This page walks you through everything you need to play your first game.
sidebar:
  order: 99
---

New to Sovereignty? This page covers everything you need to go from zero to your first complete game.

## What is Sovereignty?

Sovereignty is a board game about trust, trade, and keeping your word. 2 to 4 players sit around a table (physical or digital), roll dice, and move around a 16-space board. The game takes about 30 minutes.

What makes Sovereignty different from other board games: your reputation matters. You can make promises, issue IOUs, and form agreements -- but if you break your word, everyone sees it in the score. The game teaches concepts from economics and governance (wallets, tokens, trust) through natural play rather than jargon.

You can play with physical cards and coins, or use the digital console (`sov`) to track scores and generate cryptographic proofs of each round.

## Installation

The fastest way to start is with npx (no Python needed):

```bash
npx @mcptoolshop/sovereignty tutorial
```

This downloads a prebuilt binary and runs the built-in tutorial.

If you prefer Python:

```bash
pipx install sovereignty-game
sov tutorial
```

Requires Python 3.11 or later. The only runtime dependencies are [Typer](https://typer.tiangolo.com/) and [Rich](https://github.com/Textualize/rich).

For the physical version, print the cards and reference sheets from the `assets/print/` directory in the repository. You need a six-sided die and some coins or tokens.

## Your first game

Start a 2-player game:

```bash
sov new -p Alice -p Bob
```

Each player starts with 5 coins and 3 reputation. The board has 16 spaces. On your turn:

1. **Roll the die** and move forward that many spaces
2. **Resolve the space** you land on (the console does this for you)
3. **Optionally make a promise** ("I promise to help Bob next round")
4. **Pass the turn** to the next player

```bash
sov turn          # take your turn
sov status        # see everyone's scores
sov recap         # see what happened this round
```

After everyone has taken a turn, the round ends. After 15 rounds, the player with the highest combined score wins.

## Key concepts

**Coins** are your basic currency. You earn them from safe spaces (Campfire, Mint, Faucet) and lose them from risky ones (Trouble, Taxman). You spend them on upgrades, donations, and trades.

**Reputation** tracks how trustworthy you are. It ranges from 0 to 10. You start at 3. Keeping promises and helping others raises it. Breaking promises and dodging obligations lowers it. High reputation (5+) makes you a trusted issuer with bonus voucher payouts. Low reputation (below 3) makes you vulnerable to Trust Crisis events.

**Promises** are spoken commitments. Once per round, say "I promise..." out loud and the table holds you to it. Keep it for +1 reputation. Break it for -2 reputation. The apology mechanic lets you recover once per game: pay 1 coin to the person you wronged and regain +1 reputation.

**Goals** shape your strategy. At the start, each player picks one (secret or public):
- **Prosperity** -- reach 20 coins
- **Beloved** -- reach 10 reputation
- **Builder** -- complete 4 upgrades

**Vouchers** are IOUs. When you draw a Voucher card, you can issue a debt to another player ("I owe you 2 coins in 3 rounds"). If you pay up, the voucher is redeemed. If you cannot pay, you default and lose reputation. You need reputation 2 or higher to issue vouchers.

**Deals** are timed challenges. When you draw a Deal card at Crossroads, you can accept or pass. Accepted deals have a deadline -- complete the task for rewards, or fail and lose reputation.

## Common commands

Here are the commands you will use most often:

```bash
# Starting and playing
sov new -p Alice -p Bob       # start a new game
sov turn                       # take your turn
sov status                     # show all player scores
sov board                      # show the board layout

# Promises
sov promise make "help Bob"    # make a promise
sov promise keep "help Bob"    # you kept it (+1 Rep)
sov promise break "help Bob"   # you broke it (-2 Rep)
sov apologize Bob              # apologize (once per game)

# Social
sov toast Alice                # toast a player (+1 Rep)
sov offer "2 coins" --to Bob   # propose a trade

# End of game
sov end-round                  # generate round proof
sov game-end                   # final scores and season update
sov postcard                   # shareable game summary
```

Run `sov --help` to see all available commands.

## Tips for your first session

**Start with Campfire tier.** It is the default and has the fewest moving parts. No market, no resources, no treaties -- just coins, reputation, promises, and cards.

**Make promises early.** The promise mechanic is the heart of the game. Even small promises ("I will not land on Trouble this round") create fun tension. Say them out loud so the table remembers.

**Use the tutorial.** Run `sov tutorial` before your first real game. It walks through one round in 60 seconds.

**Run doctor before game night.** The `sov doctor` command checks that everything is ready. It verifies your save directory, active game state, and wallet setup.

**Do not worry about Diary Mode.** XRPL anchoring is completely optional. It is educational, not required. You can always add it later with `sov wallet` and `sov anchor`.

**Try recipes for variety.** Once you have played a basic game, use recipes to set the mood:
- `sov new --recipe cozy -p ...` -- gentle events, helpful cards
- `sov new --recipe spicy -p ...` -- more conflict, harder choices
- `sov new --recipe market -p ...` -- economy-focused events
- `sov new --recipe promise -p ...` -- trust and commitment focus

## Next steps

Once you are comfortable with Campfire:

1. **Try Market Day** (`sov new --tier market-day -p ...`) -- introduces resources (food, wood, tools) with fixed prices. A gentle step up.
2. **Move to Town Hall** (`sov new --tier town-hall -p ...`) -- dynamic market prices that shift with supply and demand. Events can crash or boost prices.
3. **Graduate to Treaty Table** (`sov new --tier treaty-table -p ...`) -- binding agreements with real stakes. Put your coins in escrow and see who blinks first.
4. **Explore scenarios** (`sov scenario list`) -- curated vibes with preset tier, recipe, and mood.
5. **Enable Diary Mode** -- create a testnet wallet and anchor your game proofs to a public ledger. See [Diary Mode](/sovereignty/handbook/diary-mode/).

For the complete command reference, see the [Reference](/sovereignty/handbook/reference/) page.
