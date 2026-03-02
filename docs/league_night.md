# League Night

**Turn "play tonight" into "play again next week."**

---

## Seasons

A **season** is 3-5 games with the same group. Same people, growing trust.

After each game, the console tallies **Story Points** — a simple way to
track who's been playing well across games without power creep.

### Story Points (per game)

| Award               | Points | How                                    |
|---------------------|--------|----------------------------------------|
| Winner              | +1     | Won the game                           |
| Promise Keeper      | +1     | Most promises kept (ties: all get it)  |
| Most Helpful        | +1     | Most Help Desk visits (helped_last_round) |
| Table's Choice      | +1     | Won "MVP" in `sov vote` (table vote)  |

No penalties. No negative points. Keep it positive.

Season totals are tracked in `.sov/season.json` (created by `sov game-end`).

### Season winner

After the final game, the player with the most Story Points is the
**Season Champion**. Ties are celebrated, not broken.

---

## Game end ritual

When a game is over (someone wins or 15 rounds pass), run:

```
sov game-end
```

This command:
1. Calculates Story Points for the game
2. Prints a final recap panel with scores + awards
3. Shows the season standings (if a season is active)
4. Generates a "FINAL" round proof

Optional: `sov game-end --anchor` to stamp the final hash on XRPL Testnet.

---

## Table votes

Before `sov game-end`, the host can record table votes:

```
sov vote mvp Alice            # Most Valuable Player
sov vote chaos Bob            # Chaos Gremlin (spiciest moment)
sov vote promise "help Carol" # Best Promise (the one everyone remembers)
```

Votes are log entries. They show up in the final postcard.
The table decides who gets what — the console just records it.

---

## Diary Mode: Anchor Bundle

For groups that care about the record, the final anchor is special:

```
sov game-end --anchor
```

The memo format:
```
SOV|<ruleset>|<game_id>|FINAL|sha256:<hash>
```

This gives the group one canonical receipt per game. Share the explorer
link in your group chat. That's the handshake that says "this happened."

---

## Recommended league format

### Quick League (3 games)

| Game | Tier        | Rounds | Focus                  |
|------|-------------|--------|------------------------|
| 1    | Campfire    | 8      | Learn promises + offers |
| 2    | Market Day  | 10     | Learn inventory        |
| 3    | Town Hall   | 12     | The full experience    |

### Full League (5 games)

| Game | Tier        | Rounds | Focus                  |
|------|-------------|--------|------------------------|
| 1    | Campfire    | 8      | Learn the basics       |
| 2    | Campfire    | 10     | Master social play     |
| 3    | Market Day  | 10     | Learn inventory        |
| 4    | Town Hall   | 12     | Experience scarcity    |
| 5    | Town Hall   | 15     | The championship       |

---

## After the season

- Share the season standings (screenshot `sov game-end` output)
- Each player names their favorite moment from the whole season
- Call a final Toast for the Season Champion
- Ask: "Same group, higher tier?" If yes, you've built something real
