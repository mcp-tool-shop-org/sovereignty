"""XRPL transport layer — swappable backends for online play."""

from __future__ import annotations


class TransportError(Exception):
    """Raised by ledger transports for sanitized, operator-facing failures.

    The transport layer raises this type when the underlying ledger client
    fails in a way that should be surfaced to operators without leaking
    sensitive material (wallet seeds, signers) via traceback locals or
    chained __cause__ frames.

    Operator guidance: messages on this exception are designed to be shown
    to humans. They explain what happened, whether the failure is likely
    transient or permanent, and what action to take next (retry, check
    network status, or file an issue with the response shape).
    """
