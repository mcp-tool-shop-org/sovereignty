# Canon Packs

> **Canon checklist:** Playtested. Lint-passing. Postcard-proven.

A canon pack is an official scenario that ships with Sovereignty.
It's been played, it passes lint, and it has a postcard to prove it.

## What "canon" means

- **Playtested.** Someone played it and the game felt right.
- **Lint-passing.** `sov scenario lint` reports no errors.
- **Postcard-proven.** There's at least one postcard or feedback
  artifact showing a real session.

Canon packs live in `docs/scenarios/` at the root level.
Community packs live in `docs/scenarios/community/` when they arrive.

## Current canon packs

| Pack | Tier | Recipe |
|------|------|--------|
| [Cozy Night](cozy-night.md) | Campfire / Market Day | cozy |
| [Market Panic](market-panic.md) | Town Hall | market |
| [Promises Matter](promises-matter.md) | Campfire | promise |
| [Treaty Night](treaty-night.md) | Treaty Table | — |

## How a community pack becomes canon

1. **Passes lint.** Run `sov scenario lint your-pack.md` — no errors.
2. **Has been played.** Share a feedback blob (`sov feedback`) or
   a postcard (`sov postcard`) from a real session.
3. **Maintainer review.** A maintainer reads the pack, checks tone
   and structure, and merges it into the root.

The bar is low on purpose. "Show me the postcard" is the default
proof of quality. If you played it and it worked, it's probably good.

## Writing a new pack

Start from the [template](_TEMPLATE.md). A scenario is just a tier,
a recipe, a player count, and a paragraph that sets the tone. No code
needed — the engine does the rest.

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for the full submission guide.
