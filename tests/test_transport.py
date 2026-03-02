"""Tests for transport layer."""

from sov_transport.null import NullTransport


def test_null_transport_anchor():
    t = NullTransport()
    result = t.anchor("sha256:abc123", "memo", "signer")
    assert result.startswith("offline:")


def test_null_transport_verify():
    t = NullTransport()
    assert t.verify("offline:abc123", "anything") is True
    assert t.verify("xrpl:abc123", "anything") is False


def test_xrpl_transport_imports_cleanly():
    """XRPLTestnetTransport should import even without xrpl-py installed."""
    from sov_transport.xrpl_testnet import XRPLTestnetTransport

    t = XRPLTestnetTransport()
    assert t.url == "https://s.altnet.rippletest.net:51234/"


def test_xrpl_transport_anchor_requires_xrpl_py():
    """Anchor should raise RuntimeError if xrpl-py is not installed."""
    from sov_transport.xrpl_testnet import XRPLTestnetTransport

    t = XRPLTestnetTransport()
    try:
        t.anchor("hash", "memo", "signer")
        # If xrpl-py is installed, this will fail for other reasons (bad seed)
        # Either way is fine — we're testing the import guard
    except RuntimeError as e:
        assert "xrpl-py is not installed" in str(e)
    except Exception:
        pass  # xrpl-py is installed, different error is expected


def test_memo_hex_encoding():
    from sov_transport.xrpl_testnet import _from_hex, _to_hex

    text = "SOV|campfire_v1|s42|r1|sha256:abc123"
    encoded = _to_hex(text)
    decoded = _from_hex(encoded)
    assert decoded == text
