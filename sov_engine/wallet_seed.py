"""OS keychain-backed mainnet wallet seed (JOB-025).

Production uses PyPI ``keyring``, which wraps Windows Credential Manager,
macOS Keychain, or libsecret when those OS stores are present. This Linux
sandbox often has no backend (``NoKeyringError``); callers treat that as
"no keyring seed" and must not fall back to silently writing plaintext for
mainnet.

Tests inject an in-memory ``keyring`` backend — never a second native
package, never ``keyrings.alt``.

Never log or print seed values.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger("sov_engine")

#: keyring service name (stable across releases).
KEYRING_SERVICE = "sovereignty-game"
#: Username / account key for the mainnet XRPL seed.
KEYRING_MAINNET_USER = "xrpl-mainnet-seed"


class KeyringUnavailableError(RuntimeError):
    """Raised when the OS keychain cannot store a mainnet seed."""


def get_mainnet_seed() -> str | None:
    """Return the mainnet seed from the OS keychain, or ``None``.

    Missing backend / empty entry → ``None``. Never logs the seed.
    """
    try:
        import keyring
    except ImportError:
        logger.info("wallet_seed.keyring.unavailable reason=import")
        return None
    try:
        value = keyring.get_password(KEYRING_SERVICE, KEYRING_MAINNET_USER)
    except Exception as exc:  # noqa: BLE001 — backend may raise NoKeyringError
        logger.info(
            "wallet_seed.keyring.get_failed exc=%s",
            type(exc).__name__,
        )
        return None
    if not value:
        return None
    stripped = value.strip()
    return stripped or None


def set_mainnet_seed(seed: str) -> None:
    """Store ``seed`` in the OS keychain for mainnet.

    Raises:
        KeyringUnavailableError: no usable OS store (do not write plaintext).
        ValueError: empty seed.
    """
    cleaned = seed.strip()
    if not cleaned:
        raise ValueError("empty seed")
    try:
        import keyring
    except ImportError as exc:
        raise KeyringUnavailableError("keyring package is not installed") from exc
    try:
        keyring.set_password(KEYRING_SERVICE, KEYRING_MAINNET_USER, cleaned)
    except Exception as exc:  # noqa: BLE001
        raise KeyringUnavailableError(f"OS keychain unavailable ({type(exc).__name__})") from exc
    logger.info("wallet_seed.keyring.set_ok service=%s", KEYRING_SERVICE)


def clear_mainnet_seed() -> None:
    """Delete the mainnet seed from the OS keychain if present."""
    try:
        import keyring
    except ImportError:
        return
    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_MAINNET_USER)
    except Exception:  # noqa: BLE001
        logger.info("wallet_seed.keyring.clear_skipped")


def resolve_wallet_seed(
    *,
    network: str,
    signer_file: Path | None = None,
    seed_env: str | None = "XRPL_SEED",
    wallet_file: Path | None = None,
) -> str | None:
    """Resolve a wallet seed for the given XRPL network.

    Precedence:
      1. ``signer_file`` (explicit operator override)
      2. OS keychain when ``network == "mainnet"`` (preferred over plaintext)
      3. ``wallet_file`` / ``.sov/wallet_seed.txt`` plaintext
      4. ``seed_env`` environment variable

    Never logs the seed value.
    """
    if signer_file is not None:
        try:
            text = signer_file.read_text(encoding="utf-8").strip()
        except OSError:
            text = ""
        if text:
            return text

    if network == "mainnet":
        keyed = get_mainnet_seed()
        if keyed:
            return keyed

    if wallet_file is not None:
        try:
            text = wallet_file.read_text(encoding="utf-8").strip()
        except OSError:
            text = ""
        if text:
            return text

    if seed_env:
        value = os.environ.get(seed_env, "").strip()
        if value:
            return value
    return None
