"""XRPL transport layer — swappable backends for online play."""

from __future__ import annotations


class TransportError(Exception):
    """Raised by ledger transports for sanitized, operator-facing failures.

    The transport layer raises this type when the underlying ledger client
    fails in a way that should be surfaced to operators without leaking
    sensitive material (wallet seeds, signers) via traceback locals or
    chained __cause__ frames.
    """
