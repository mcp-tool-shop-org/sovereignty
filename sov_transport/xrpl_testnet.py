"""Deprecated — use ``sov_transport.xrpl``.

This module is the v2.0.x entry point; everything here re-exports from
``sov_transport.xrpl`` and emits ``DeprecationWarning`` on the legacy class
and faucet helper. The shim is kept until v2.2; do not delete.

The five private helpers (``_to_hex``, ``_from_hex``, ``_extract_memos``,
``_classify_submit_error``) plus the ``TESTNET_URL`` constant are still
reachable here for v2.0.x test compatibility, but each access emits a
``DeprecationWarning`` via PEP-562 ``__getattr__`` (BRIDGE-B-002). The
canonical home for these helpers is ``sov_transport.xrpl_internals``.
"""

from __future__ import annotations

import warnings
from typing import Any

from sov_transport.xrpl import (
    XRPLNetwork,
    XRPLTransport,
    fund_dev_wallet,
)

# ``__all__`` lists deprecated re-exports that resolve via ``__getattr__``
# (PEP-562). Ruff's F822 rule flags them because the names are not bound at
# module scope; the ``noqa: F822`` suppressions are correct here — Python's
# import machinery consults ``__getattr__`` for ``from ... import *`` so the
# re-exports remain reachable through the documented v2.2 deprecation window.
__all__ = [
    "TESTNET_URL",  # noqa: F822 — resolved via __getattr__ (BRIDGE-B-002)
    "XRPLNetwork",
    "XRPLTestnetTransport",
    "_classify_submit_error",  # noqa: F822 — resolved via __getattr__
    "_extract_memos",  # noqa: F822 — resolved via __getattr__
    "_from_hex",  # noqa: F822 — resolved via __getattr__
    "_to_hex",  # noqa: F822 — resolved via __getattr__
    "fund_testnet_wallet",
]


# Names re-exported under DeprecationWarning via PEP-562 ``__getattr__``.
# Listing them here (rather than as bound module-level names) is what lets
# ``__getattr__`` fire on access — Python only consults ``__getattr__`` when
# the requested name is NOT already in the module dict.
_DEPRECATED_REEXPORTS = frozenset(
    {
        "_to_hex",
        "_from_hex",
        "_extract_memos",
        "_classify_submit_error",
        "TESTNET_URL",
    }
)


def __getattr__(name: str) -> Any:
    """PEP-562 lookup for deprecated re-exports (BRIDGE-B-002).

    Python invokes this only when ``name`` is not already bound at module
    scope. Each of the names in ``_DEPRECATED_REEXPORTS`` resolves through
    ``sov_transport.xrpl_internals`` (the canonical home) and emits a
    ``DeprecationWarning`` so callers still importing them by the legacy
    path see the migration window before the v2.2 removal.
    """
    if name in _DEPRECATED_REEXPORTS:
        warnings.warn(
            f"Importing {name!r} from sov_transport.xrpl_testnet is deprecated; "
            f"import from sov_transport.xrpl_internals instead. "
            f"This shim is removed in v2.2.",
            DeprecationWarning,
            stacklevel=2,
        )
        from sov_transport import xrpl_internals

        if name == "TESTNET_URL":
            # ``xrpl_internals`` does not expose a bare ``TESTNET_URL``
            # constant — the canonical value lives in ``_NETWORK_TABLE``.
            # Return the same string the legacy constant carried so existing
            # call sites keep working unchanged through the v2.2 removal.
            return xrpl_internals._NETWORK_TABLE[XRPLNetwork.TESTNET][0]
        return getattr(xrpl_internals, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
