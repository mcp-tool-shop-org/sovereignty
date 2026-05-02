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


# Re-exports below intentionally come after ``TransportError`` is defined to
# avoid a circular-import hazard: ``sov_transport.xrpl`` imports
# ``TransportError`` from this module.
from sov_transport.base import BatchEntry, LedgerTransport  # noqa: E402
from sov_transport.xrpl import (  # noqa: E402
    MainnetFaucetError,
    XRPLNetwork,
    XRPLTransport,
    fund_dev_wallet,
)
from sov_transport.xrpl_async import AsyncXRPLTransport  # noqa: E402
from sov_transport.xrpl_internals import ChainLookupResult  # noqa: E402

__all__ = [
    "AsyncXRPLTransport",
    "BatchEntry",
    "ChainLookupResult",
    "LedgerTransport",
    "MainnetFaucetError",
    "TransportError",
    "XRPLNetwork",
    "XRPLTransport",
    "fund_dev_wallet",
]
