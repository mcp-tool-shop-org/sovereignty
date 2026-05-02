"""Tests for the transport base — NullTransport only.

The XRPL-specific tests moved to ``tests/test_xrpl_transport.py`` (v2.1
unified ``XRPLTransport``). Legacy ``XRPLTestnetTransport`` shim coverage
moved to ``tests/test_xrpl_transport_legacy.py`` (which captures the
``DeprecationWarning`` that shim must emit).
"""

from __future__ import annotations

from sov_transport.null import NullTransport


def test_null_transport_anchor() -> None:
    t = NullTransport()
    result = t.anchor("sha256:abc123", "memo", "signer")
    assert result.startswith("offline:")


def test_null_transport_verify() -> None:
    """Legacy ``verify()`` shim — DeprecationWarning expected; suppressed
    in this test because the deprecation contract is covered by
    ``tests/test_xrpl_transport_legacy.py``.
    """
    import warnings

    t = NullTransport()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        assert t.verify("offline:abc123", "anything") is True
        assert t.verify("xrpl:abc123", "anything") is False
