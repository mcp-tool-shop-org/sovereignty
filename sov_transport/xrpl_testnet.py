"""Deprecated — use ``sov_transport.xrpl``.

This module is the v2.0.x entry point; everything here re-exports from
``sov_transport.xrpl`` and emits ``DeprecationWarning`` on the legacy class
and faucet helper. The shim is kept until v2.2; do not delete.

Internal helpers (``_to_hex``, ``_from_hex``, ``_extract_memos``,
``_classify_submit_error``) are re-exported because existing tests under
``tests/test_transport.py`` import them by their old path.
"""

from __future__ import annotations

import warnings

from sov_transport.xrpl import (
    XRPLNetwork,
    XRPLTransport,
    _classify_submit_error,
    _extract_memos,
    _from_hex,
    _to_hex,
    fund_dev_wallet,
)

# Back-compat constant — v2.0.x callers may import this directly.
TESTNET_URL = "https://s.altnet.rippletest.net:51234/"

__all__ = [
    "TESTNET_URL",
    "XRPLNetwork",
    "XRPLTestnetTransport",
    "_classify_submit_error",
    "_extract_memos",
    "_from_hex",
    "_to_hex",
    "fund_testnet_wallet",
]


class XRPLTestnetTransport(XRPLTransport):
    """Deprecated subclass — use ``XRPLTransport(network=XRPLNetwork.TESTNET)``.

    Constructor signature mirrors the v2.0.x form
    (``XRPLTestnetTransport(url=...)``) so existing call sites and tests keep
    working unchanged. Emits ``DeprecationWarning`` once per instantiation.
    Removed in v2.2.
    """

    def __init__(
        self,
        url: str | None = None,
        *,
        allow_insecure: bool = False,
    ) -> None:
        warnings.warn(
            "XRPLTestnetTransport is deprecated; use "
            "XRPLTransport(network=XRPLNetwork.TESTNET). "
            "This class will be removed in v2.2.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(
            network=XRPLNetwork.TESTNET,
            url=url,
            allow_insecure=allow_insecure,
        )


def fund_testnet_wallet() -> tuple[str, str]:
    """Deprecated — use ``fund_dev_wallet(XRPLNetwork.TESTNET)``.

    Removed in v2.2. Emits ``DeprecationWarning`` on call.
    """
    warnings.warn(
        "fund_testnet_wallet() is deprecated; use "
        "fund_dev_wallet(XRPLNetwork.TESTNET). "
        "This will be removed in v2.2.",
        DeprecationWarning,
        stacklevel=2,
    )
    return fund_dev_wallet(XRPLNetwork.TESTNET)
