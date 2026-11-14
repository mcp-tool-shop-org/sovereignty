---
title: Diary Mode
description: Optional XRPL Testnet verification — proof anchoring and verification.
sidebar:
  order: 4
---

Every round, the console can produce a **proof** — a SHA-256 fingerprint of the game state. Optionally, that fingerprint can be posted to the XRPL Testnet.

## How it works

1. **End a round** — generates a proof hash of the full game state
2. **Create a wallet** — free Testnet wallet (test XRP has no value)
3. **Anchor the proof** — post the hash to the XRPL Testnet
4. **Verify later** — anyone can check the proof against the on-chain record

```bash
sov end-round          # generate proof
sov wallet             # create testnet wallet (free)
sov anchor             # post hash to XRPL (optional)
sov verify proof.json --tx <txid>   # trust but verify
```

Only the host needs a wallet. Nobody else touches a screen. The game works perfectly without anchoring — it's just the diary that remembers.

### When the test network is reset

The XRPL Testnet and Devnet are sometimes reset, which deletes every transaction on them. **Both are reset on 2026-11-25** ([xrpl.org notice](https://xrpl.org/blog/2026/testnet-devnet-reset)). Mainnet is never reset.

A proof you anchored before a reset is still valid on its own: its local hash still checks out. Its anchor is gone, though, so `sov verify --tx` can no longer find it:

| Result | Exit code | Meaning |
|--------|-----------|---------|
| Anchor verified | `0` | The transaction is on the ledger and carries this proof's hash |
| Anchor mismatch, or the lookup failed | `1` | The ledger has a different hash, the transaction is missing with no reset to explain it, or the ledger could not be reached |
| Anchor can no longer be checked (`NET_ANCHOR_RESET`) | `3` | The transaction is absent, and an announced reset covers the time the proof was made |

Exit code 3 is not a pass. A made-up `--tx` with a proof dated before the reset reads the same way, so the local proof hash is all that is left as evidence. The desktop app shows these rounds with a "network reset" pill, never the verified one.

To put a game's rounds back on the ledger after a reset:

```bash
sov wallet                          # the old account was deleted; this makes a new funded one
sov anchor --reanchor               # anchor again every round whose anchor is gone
sov verify <proof_file> --tx <new txid>
```

`sov anchor --reanchor` asks the ledger about every anchor recorded for the active game. It sends again only the rounds whose transaction is gone, and records the new transaction in place of the old one. A round still on the ledger is left alone, and so is one the ledger gave no answer for. Only a proof whose local hash still checks out is sent.

Plain `sov anchor` only sends rounds that are still pending, so it does nothing for a round already marked anchored.

## Security

- Proofs contain hashes and state snapshots, but never wallet seeds
- The `.sov/` directory is gitignored
- `sov wallet` warns about Testnet seed reuse on Mainnet
- Proofs include player names and game state (scores, positions, promises) -- share only with your play group
- Only the SHA-256 hash is posted to the ledger; the full proof stays local

## Why anchor?

Anchoring is optional and educational. It demonstrates:
- How cryptographic hashes create tamper-evident records
- How public ledgers provide independent verification
- How trust works when you can prove what happened
