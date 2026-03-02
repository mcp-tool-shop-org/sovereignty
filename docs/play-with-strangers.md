# Playing With Strangers

You don't need to know anyone to play Sovereignty. You just need a table,
a die, and this page.

## Roles

**Host** — One person runs the console (laptop or phone terminal).
They type commands, read card text aloud, and keep the game moving.
If you're anchoring to XRPL, only the host needs a wallet.

**Players** — Everyone else just plays. No screens, no accounts, no setup.
Listen for your name, make trades, keep (or break) your promises.

## Before you start

1. Print the cards and player mats (see `docs/print-and-play.md`), or use the console.
2. Grab a six-sided die and some coins/tokens (~40 total).
3. Pick 2-4 players. First names work fine.

## The social script

Here's what to say when you sit down:

> "This is Campfire. It takes about 30 minutes. You're building a small
> community — trading, making promises, and trying to reach your goal
> before everyone else.
>
> I'll run the console. It keeps score. You just play.
>
> On your turn, I'll roll for you and tell you what happens. If you land
> on a space where you make a choice, I'll ask you. If you want to trade,
> just talk to someone.
>
> One special thing: once per round, you can say 'I promise' and commit
> to something. Keep it, you earn trust. Break it... well, people remember.
>
> Ready?"

## During the game

- **Read card text like a story.** "You drew... Lost Wallet. Has anyone
  seen a small leather pouch? You can't trade this turn — unless someone
  lends you a coin."
- **Don't explain the math.** Just say "you lost 1 rep" not "your reputation
  decreased from 4 to 3 due to the promise penalty modifier."
- **Let people talk.** The best moments happen between turns.
- **Use `sov recap` at the end of each round.** It reminds everyone what happened.

## If there's a dispute

This almost never matters, but if someone claims the score is wrong:

1. Run `sov end-round` to generate a proof file.
2. Run `sov verify <proof-file>` to confirm the hash matches.
3. If you anchored, run `sov verify <proof-file> --tx <txid>` to check the chain.

The proof settles it. No arguments needed.

## Anchoring (optional)

If you want receipts:

1. Host runs `sov wallet` once to get a Testnet wallet (free, play money).
2. At the end of each round, `sov anchor` posts the game hash to XRPL Testnet.
3. That's it. A permanent record that this round happened exactly this way.

Nobody else at the table needs to know what XRPL is. If they ask, say:
"It's a public notebook that remembers our game. Like writing it on a wall
that nobody can erase."

## After the game

Run `sov postcard` to see a shareable summary. Screenshot it if you want.

That's all. Have fun. Keep your promises. Or don't — and see what happens.
