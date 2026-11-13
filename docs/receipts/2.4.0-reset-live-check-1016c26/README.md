# 2.4.0 network-reset check, live on XRPL Testnet, on `1016c26`

2.4.0 is the release for the **2026-11-25** Testnet and Devnet wipe. This check ran the release commit against the
real Testnet on 2026-11-13. A round proof was made and anchored by the published **2.3.6**, then verified and
recovered by 2.4.0, each step against the live ledger.

- **Code:** `mcp-tool-shop-org/sovereignty` at `1016c26`, in the checkout's editable install. It reports
  `sovereignty 2.4.0`. The old version is `sovereignty-game==2.3.6` from PyPI, in its own environment, and has no
  `tx_exists` (`raw/00_preflight.txt`).
- **Network:** the public Testnet, default endpoint and faucet, no overrides. One faucet grant (`raw/03`), and two
  anchor transactions (`raw/04`, `raw/14`).
- **Game folder:** one scratch folder outside every repo. The wallet file never left it.
- **Redaction:** no seeds or wallet files are here. Paths read `<scratch>`, `<worktree>` or `<venv-2.3.6>`. The copy
  step stops if the seed, anything shaped like an XRPL seed, or a local path is left in a file.

## Verdict

**PASS.** A 2.3.6 proof verifies under 2.4.0. After the reset date, a missing anchor reads "can no longer be checked"
(exit 3) and is never reported as a pass. A transaction that is still there, with this proof's hash or another, reads
as it always did. `sov anchor --reanchor` sends again only the round whose transaction is gone, and the new anchor
verifies.

## What could not be run live

The Testnet has not been reset yet, so two things are stand-ins:

- **The date.** The reset verdict applies only once 2026-11-25 has begun somewhere (2026-11-24 10:00 UTC). Steps
  marked *after the reset* run the real CLI with one change: the reset clock (`sov_transport.resets._now`, the seam
  the test suite pins) reads 2026-12-01. The proof, the transport and the ledger lookups are all real.
- **The lost anchor.** A wipe removes the anchor transaction. Step 13 stands in for that by recording, for round 1,
  a transaction hash that is on no ledger (`F00DFACE…`). From the game's side that is exactly what a wipe leaves:
  a recorded txid the ledger does not have.

The daemon's verify endpoint and the desktop app's "network reset" pill are covered by the test suite, not here.

## A. A proof made by 2.3.6

| Step | File | Result |
|---|---|---|
| `sov new`, `sov end-round` (2.3.6) | `raw/01_*`, `raw/02_*` | exit 0; round 1 proof |
| `sov wallet` (2.3.6) | `raw/03_old_wallet.*` | exit 0; one faucet grant |
| `sov anchor --checkpoint` (2.3.6) | `raw/04_old_anchor.*` | exit 0; tx `D51B0DF6…481B47F6` |

## B. 2.4.0 reads it, before the reset

| Step | File | Result |
|---|---|---|
| `sov verify <proof> --tx D51B…` | `raw/05_verify_old_proof.*` | **exit 0**, Anchor verified |
| `sov anchor --reanchor` | `raw/06_reanchor_nothing_lost.*` | exit 0; "1 still on the ledger, 0 gone"; nothing sent |
| `sov verify <proof> --tx F00DFACE…` | `raw/11_verify_absent_before_reset.*` | **exit 1**, Anchor mismatch, as before 2.4.0 |

## C. After the reset date

| Step | File | Result |
|---|---|---|
| `sov verify <proof> --tx D51B…` | `raw/07_verify_after_reset_tx_present.*` | **exit 0**, Anchor verified: a found anchor is untouched |
| Another game's proof `--tx D51B…` | `raw/08_*`–`raw/10_*` | **exit 1**, Anchor mismatch: the transaction is there with another hash, so no reset is granted |
| `sov verify <proof> --tx F00DFACE…` | `raw/12_verify_absent_after_reset.*` | **exit 3**, `NET_ANCHOR_RESET`: "Anchor can no longer be checked — Testnet was reset on 2026-11-25" |

Step 12's hint says the local proof is all that is left, that a made-up `--tx` dated before the reset reads the same
way, and names `sov anchor --reanchor`. Step 11 is the same call before the reset date, for comparison.

## D. Recovery

| Step | File | Result |
|---|---|---|
| Record `F00DFACE…` for round 1 | `raw/13_record_absent_txid.out` | the stand-in for a wiped anchor |
| `sov anchor --reanchor` (after the reset date) | `raw/14_reanchor_lost.*` | exit 0; "0 still on the ledger, 1 gone"; tx `C4F55C5F…5902657A` |
| `sov verify <proof> --tx C4F5…` | `raw/15_verify_reanchored.*` | **exit 0**, Anchor verified |
| `sov anchor --reanchor` again | `raw/16_reanchor_again.*` | exit 0; "Nothing to anchor again"; nothing sent |
| The game's record afterwards | `raw/17_anchors_after.json` | round 1 → `C4F5…` |

Step 14 also printed the reset and its advice: the wallet from before a reset is gone too, so `sov wallet` makes a
new one. Here the wallet was not gone (the Testnet was not really reset), so the send succeeded with it.

## Two things about this run

1. **Steps 07, 10, 12 and 15 were run twice.** Their first run went through the clock wrapper under `python -I`,
   which ignores `PYTHONIOENCODING`, so the CLI wrote in the console's code page (cp1252) and two files were not
   UTF-8. They are read-only lookups, so they were run again with `-X utf8`, at the time in `raw/00_snapshot.txt`.
   The results matched. Step 14 wrote to the ledger and was not repeated. Its file is UTF-8, but its panel is
   drawn in ASCII for the same reason.
2. **This was the third live run for these changes.** The first two ran on the PR heads before the version bump
   (`b0d975e`, for `--reanchor`). This one is on the release commit and is the receipt.

## Layout

`raw/NN_name.out`, `.err` and `.exit` are each command's stdout, stderr and exit code. `raw/00_preflight.txt`
records both versions and where each was loaded from, and `raw/00_snapshot.txt` the start, end and re-run times.
`raw/13_record_absent_txid.out` and `raw/17_anchors_after.json` were written by the check's helper: the game's anchor
record only, never a wallet file.
