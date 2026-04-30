# Migrating from sovereignty v1.x to v2.0

## What changed

In v2.0.0, the proof envelope hash was widened to cover the FULL envelope (game_id, round, ruleset, rng_seed, timestamp_utc, players, state) instead of just the embedded `state` dict. The field was renamed from `state_hash` to `envelope_hash`, and a new `proof_version: 2` field was added.

This is a **breaking change**. Sovereignty v2.0+ rejects v1 proofs with `ProofFormatError`.

## Why

The v1 hash left envelope metadata tamperable: an attacker could change `proof.round` from 7 to 1, flip the ruleset, reorder player names, or change `rng_seed` without detection. The v2 envelope hash closes that gap.

## What this means for you

### If you have archived v1 proof.json files...

Two options:

1. **Verify with sovereignty <2.0.0**: `pipx install 'sovereignty-game<2.0.0'` and use that binary to verify legacy proofs.
2. **Re-run the original game**: if you still have the seed and the player list, re-running with the same seed in v2.0+ produces a v2 proof with the same gameplay outcomes.

### If you anchor proofs on XRPL Testnet...

The on-chain memo format for v2 anchors uses the new `envelope_hash` (raw 64-char hex) with the `sha256:` algorithm tag at the wire layer:

```
SOV|<ruleset>|<game_id>|r<round>|sha256:<envelope_hash>
```

Pre-existing v1 anchors on-chain remain valid for verification with sovereignty <2.0.0; new anchors use the v2 format.

### If you write tooling that consumes proof.json...

Update field references:

- `state_hash` → `envelope_hash`
- Add a `proof_version` check; reject `proof_version != 2` with a clear error.
- The hash now covers the full envelope; recompute as `sha256(canonical_json(envelope - envelope_hash_field))`.

## Tamper-detection coverage

v2 tamper tests cover round flip, ruleset flip, player reorder, player rename, rng_seed change, timestamp tweak, game_id change. See `tests/test_proofs.py` for the full vector list.

## See also

- [CHANGELOG.md](../CHANGELOG.md) for the full v1.4.x → v2.0.0 release notes
- [SECURITY.md](../SECURITY.md) for the v2 envelope threat model
