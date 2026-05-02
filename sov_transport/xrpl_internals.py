"""Pure shared helpers + types for the XRPL transport family.

This module is the single source of truth for the **deterministic**, **I/O-free**
XRPL transport bits that both ``sov_transport.xrpl.XRPLTransport`` (sync) and
``sov_transport.xrpl_async.AsyncXRPLTransport`` (async) consume. Lifting these
into a sibling module avoids the sync/async impls drifting on memo grammar,
error classification, retry policy constants, or network-table keys.

What lives here
---------------

* ``XRPLNetwork`` — the ``StrEnum`` of selectable networks.
* ``ChainLookupResult`` — 3-state result from ``is_anchored_on_chain``
  distinguishing FOUND / NOT_FOUND / LOOKUP_FAILED so engine-side state
  composition can tell "definitively not on chain" from "could not reach
  the chain to ask".
* ``MainnetFaucetError`` — the typed exception raised by ``fund_dev_wallet``
  when invoked against ``MAINNET``.
* ``_NETWORK_TABLE`` — JSON-RPC URL + explorer-prefix per network.
* ``_MAX_MEMO_BYTES`` — the per-memo size cap (``1024``).
* ``_MAX_BATCH_MEMO_BYTES`` — the conservative per-tx ceiling for the sum of
  memo bytes in ``anchor_batch``. Leaves headroom for the rest of the
  Payment envelope (account, fee, sequence, signature, etc.) below the
  XRPL practical wire limit.
* ``_SUBMIT_MAX_ATTEMPTS`` / ``_SUBMIT_BACKOFF_SECONDS`` /
  ``_SUBMIT_DEADLINE_SECONDS`` — bounded-retry policy constants. Both sync and
  async impls run their own retry loop (``time.sleep`` vs ``await
  asyncio.sleep``); only the *constants* are shared.
* ``_to_hex`` / ``_from_hex`` — pure UTF-8 hex codecs used at the memo wire
  layer. ``_from_hex`` is intentionally lenient (returns ``""`` on malformed
  input) to keep adversarial memos on fetched txs from DoS-ing memo decode.
* ``_extract_memos`` — pure dict-shape helper that pulls the ``Memos`` list
  out of a (possibly version-shifted) xrpl-py ``Tx`` response result dict.
* ``_classify_submit_error`` — maps a submit_and_wait exception to a stable,
  grep-able token (``"network"``, ``"ledger_not_found"``, ``"signing_failed"``,
  ``"timeout"``, ``"unknown"``).
* ``_format_memo`` — renders a ``BatchEntry`` to its SOV-grammar wire string.

What does NOT live here
-----------------------

The retry **loop** stays per-impl, because the sleep primitive differs (sync
``time.sleep`` vs async ``await asyncio.sleep``). The submit + memo build path
also differs (sync ``JsonRpcClient`` + ``submit_and_wait`` vs async
``AsyncJsonRpcClient`` + async ``submit_and_wait``). Only the deterministic
helpers above are shared.
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Any

from sov_transport.base import BatchEntry, ChainLookupResult

# Maximum memo length in bytes. XRPL allows ~1KB per memo field; we cap at
# 1024 to give the user a clear, actionable error before submission rather
# than a silent network-side rejection or truncation. NOTE: this cap is
# per-memo, not per-tx — multi-memo batching with ``anchor_batch`` is
# bounded by ``_MAX_MEMOS_PER_TX`` below, not by the per-memo cap.
_MAX_MEMO_BYTES = 1024

# Wave 10 BRIDGE-A-bis-003: the binding constraint for multi-memo batching
# is rippled's aggregate-Memos-field cap, not the per-memo cap. Empirical
# boundary on testnet at the SOV grammar (``SOV|<ruleset>|<game-id>|r<N>|
# sha256:<64-hex>``, ~95 bytes/memo): 8 memos submit OK, 9 memos reject
# with "fails local checks: The memo exceeds the maximum allowed size."
# That's rippled's ``Memos`` field aggregate limit (~1 KB on the wire,
# including hex encoding + per-memo struct overhead).
#
# The cap below is a hard mechanical bound that ``anchor_batch`` honors by
# splitting batches >8 memos into N sequential txs of ≤8 memos each. The
# audit thesis remains "small constant of chain pointers per game, not
# 30+"; a typical 16-round Campfire game produces 2 anchor txs at game-end,
# indexed by ``round_key`` in memo body — operators verify by walking the
# trail. The single-tx aspiration was a Wave-2 idealization based on
# per-memo size; the actual XRPL constraint is aggregate.
#
# Pinned by ``tests/test_xrpl_integration.py::
# test_real_testnet_anchor_batch_boundary_8_memos_succeeds`` and
# ``test_real_testnet_anchor_batch_boundary_9_memos_rejected_locally``.
# Future memo-format changes (longer game-id, longer ruleset, additional
# grammar fields) that shift the empirical boundary get caught by these
# real-testnet tests rather than discovered at production submit time.
_MAX_MEMOS_PER_TX = 8

# Per-tx ceiling for the sum of memo bytes in a single submit call. The
# binding constraint is ``_MAX_MEMOS_PER_TX`` above (rippled aggregate
# Memos-field cap); this byte-level cap is a defensive secondary guard
# for unusually long memo strings that might push 8 memos past ~960 bytes.
# Set conservatively at 1 KB (matching rippled's observed aggregate limit)
# rather than 8 KB so the byte-check fires before the count-check on
# pathological long-memo inputs. ValueError raised pre-submit with an
# operator-actionable message.
_MAX_BATCH_MEMO_BYTES = 1024

# submit_and_wait retry policy. Bounded retry with exponential backoff
# guards against transient testnet glitches (LedgerNotFound, brief network
# drops) without hanging the user's CLI turn indefinitely. ``anchor_batch``
# reuses the same retry policy — we don't re-derive it for batches.
_SUBMIT_MAX_ATTEMPTS = 3
_SUBMIT_BACKOFF_SECONDS = (1.0, 2.0, 4.0)
_SUBMIT_DEADLINE_SECONDS = 30.0

logger = logging.getLogger("sov_transport")


class XRPLNetwork(StrEnum):
    """Selectable XRPL networks for ``XRPLTransport`` / ``AsyncXRPLTransport``.

    ``StrEnum`` so the value round-trips through CLI flags / env vars / JSON
    config without bespoke (de)serialization. The string values
    (``"testnet"``, ``"mainnet"``, ``"devnet"``) are the canonical user-facing
    names — same vocabulary the operator sees in ``--network`` flags and the
    ``SOV_XRPL_NETWORK`` env var.
    """

    TESTNET = "testnet"
    MAINNET = "mainnet"
    DEVNET = "devnet"


class MainnetFaucetError(RuntimeError):
    """Raised by ``fund_dev_wallet(MAINNET)``.

    Mainnet has no faucet. Operator action: provide a funded mainnet seed via
    ``XRPL_SEED`` (or ``sov wallet --network testnet`` for a testnet wallet
    instead). Surfaced via the structured-error code ``MAINNET_FAUCET_REJECTED``
    by the engine layer.
    """


# Internal endpoint table. Exposed via ``XRPLTransport.explorer_tx_url`` so
# CLI surfaces stop hardcoding ``testnet.xrpl.org``. Order: rpc-url first,
# explorer-prefix second.
_NETWORK_TABLE: dict[XRPLNetwork, tuple[str, str]] = {
    XRPLNetwork.TESTNET: (
        "https://s.altnet.rippletest.net:51234/",
        "https://testnet.xrpl.org/transactions/",
    ),
    XRPLNetwork.MAINNET: (
        "https://s1.ripple.com:51234/",
        "https://livenet.xrpl.org/transactions/",
    ),
    XRPLNetwork.DEVNET: (
        "https://s.devnet.rippletest.net:51234/",
        "https://devnet.xrpl.org/transactions/",
    ),
}


def _to_hex(text: str) -> str:
    return text.encode("utf-8").hex()


def _from_hex(hex_str: str) -> str:
    """Decode a hex-encoded UTF-8 memo field.

    Returns the empty string on malformed input (odd-length hex, non-hex
    characters, or invalid UTF-8 byte sequences). This guards
    ``is_anchored_on_chain`` and ``get_memo_text`` against DoS via adversarial
    memos attached to fetched transactions.
    """
    if not hex_str:
        return ""
    try:
        return bytes.fromhex(hex_str).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return ""


def _classify_submit_error(exc: BaseException) -> str:
    """Classify a submit_and_wait exception into a stable, grep-able token.

    Returns one of: ``"network"``, ``"ledger_not_found"``, ``"signing_failed"``,
    ``"timeout"``, ``"unknown"``. The token is stable across releases so
    operators can grep logs (``reason=ledger_not_found``) and dashboards can
    aggregate by failure mode.
    """
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    if "ledger" in name or "ledger_not_found" in msg or "ledgernotfound" in name:
        return "ledger_not_found"
    if "sign" in name or "wallet" in name or "signing" in msg:
        return "signing_failed"
    if "timeout" in name or "timeout" in msg or "timed out" in msg:
        return "timeout"
    if (
        "connection" in name
        or "network" in name
        or "http" in name
        or "connect" in msg
        or "refused" in msg
        or "unreachable" in msg
    ):
        return "network"
    return "unknown"


def _extract_memos(result: dict[str, Any]) -> list[Any]:
    """Extract the Memos list from an xrpl-py Tx response result.

    The xrpl-py Tx response shape varies across versions: memos may live at
    the top level of ``result``, nested under ``result['tx_json']`` (xrpl-py
    4.5.0+), nested under ``result['tx']`` (legacy; dict or list-of-dicts),
    or be entirely absent. We try the documented shapes and fall back to an
    empty list with a WARNING log on unexpected shapes so operators can see
    the drift instead of silently getting empty results.

    Wave 10 BRIDGE-A-bis-002: xrpl-py 4.5.0 wraps the transaction body in
    ``result.tx_json`` (alongside ``meta``, ``hash``, ``ledger_index``).
    The legacy ``result.tx`` and top-level ``result.Memos`` shapes are
    preserved for back-compat against pinned older xrpl-py installs.
    """
    if not isinstance(result, dict):
        logger.warning(
            "_extract_memos: unexpected result type %s; returning []",
            type(result).__name__,
        )
        return []

    memos = result.get("Memos")
    if isinstance(memos, list) and memos:
        return memos

    # xrpl-py 4.5.0+ envelope.
    tx_json = result.get("tx_json")
    if isinstance(tx_json, dict):
        nested = tx_json.get("Memos")
        if isinstance(nested, list):
            return nested

    tx = result.get("tx")
    if isinstance(tx, dict):
        nested = tx.get("Memos")
        return nested if isinstance(nested, list) else []
    if isinstance(tx, list) and tx:
        first = tx[0]
        if isinstance(first, dict):
            nested = first.get("Memos")
            return nested if isinstance(nested, list) else []
        logger.warning(
            "_extract_memos: result['tx'] is a list but first element is %s; returning []",
            type(first).__name__,
        )
        return []

    return []


def _format_memo(entry: BatchEntry) -> str:
    """Render a ``BatchEntry`` to its on-wire SOV memo string.

    The SOV grammar is ``SOV|<ruleset>|<game-id>|r<round_key>|sha256:<hash>``.
    The ``FINAL`` round_key is a literal ``FINAL`` (no ``r`` prefix) — this
    matches the existing single-round ``anchor()`` format produced by the
    engine layer. Numeric round_keys render with the ``r`` prefix.
    """
    round_key = entry["round_key"]
    round_field = "FINAL" if round_key == "FINAL" else f"r{round_key}"
    return (
        f"SOV|{entry['ruleset']}|{entry['game_id']}|{round_field}|sha256:{entry['envelope_hash']}"
    )


__all__ = [
    "ChainLookupResult",
    "MainnetFaucetError",
    "XRPLNetwork",
    "_MAX_BATCH_MEMO_BYTES",
    "_MAX_MEMO_BYTES",
    "_MAX_MEMOS_PER_TX",
    "_NETWORK_TABLE",
    "_SUBMIT_BACKOFF_SECONDS",
    "_SUBMIT_DEADLINE_SECONDS",
    "_SUBMIT_MAX_ATTEMPTS",
    "_classify_submit_error",
    "_extract_memos",
    "_format_memo",
    "_from_hex",
    "_to_hex",
    "logger",
]
