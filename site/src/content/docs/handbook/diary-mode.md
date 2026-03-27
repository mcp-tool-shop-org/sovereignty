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
