# Treaty Night

> Promises are nice. Stakes are real. Tonight, when you say "I'll defend
> your position," you put coins on the table. When you say "I won't buy
> tools," you escrow resources. Break your word and you lose what you
> staked — to the person you wronged. The table doesn't judge. The
> collateral does.

| Setting | Value |
|---------|-------|
| Tier | Treaty Table |
| Recipe | — (no filter) |
| Players | 3-4 |
| Rounds | 12-15 |
| Time | 75-90 min |

## What to expect

Treaty Table gives you everything: the full market with scarcity pricing,
promises, apologies, toasts — and treaties. A treaty is a promise with
stakes. Both parties escrow coins or resources. Keep the treaty: +1 Rep
and your collateral back. Break it: -3 Rep and your stake goes to the
other party.

For a stakes-forward session, steer the table toward early treaties.
The first treaty usually happens around round 3-4 when players have
enough coins to stake comfortably. Watch for the "treaty standoff" —
two players both wanting to break but afraid of the -3 Rep penalty.

**Taming the market:** If you want the drama to come from treaties, not
supply shocks, pull these market events from the deck before shuffling:
Warehouse Fire (evt_25), Drought (evt_09), and Tool Shortage (evt_27).
This keeps prices stable so the tension lives in the agreements, not
the economy. Entirely optional — some tables love both.

## Start command

```bash
sov new --tier treaty-table -p Alice -p Bob -p Carol -p Dave -s 4
```

## After the game

Run `sov postcard` (default style shows everything — treaties, market, promises).

Debrief question: *"Did anyone keep a treaty they wanted to break?
What would it have taken to make you break it?"*
