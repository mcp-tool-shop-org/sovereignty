"""Regression test for BACKEND-C-002 — _validate_game_id ValueError shape.

Stage 8-C amend (Wave 11) brought the engine-layer ValueError into
voice consistency with ``sov_cli/errors.py``'s SovError factories
(``invalid_game_id_error`` and ``daemon_invalid_game_id_error``):

  - canonical phrasing is ``s<digits>`` (not ``s<integer>``);
  - the message names ``sov games`` as the recovery command.

Defense-in-depth: the bare ValueError surfaces in test failures, direct
API consumers, or any future code path that forgets to catch + wrap it.
The engine-layer message must stand on its own.
"""

from __future__ import annotations

import pytest

from sov_engine.io_utils import _validate_game_id


def test_validate_game_id_rejects_traversal() -> None:
    """The validator continues to reject path-traversal payloads."""
    with pytest.raises(ValueError, match="invalid game_id"):
        _validate_game_id("../escape")


def test_validate_game_id_message_uses_canonical_s_digits_phrasing() -> None:
    """Engine-layer message says ``s<digits>``, matching the SovError
    factories at sov_cli/errors.py. Voice-consistency drift was the
    Stage C carryover lens."""
    with pytest.raises(ValueError) as exc_info:
        _validate_game_id("not-a-game-id")
    rendered = str(exc_info.value)
    assert "s<digits>" in rendered, (
        f"engine-layer message must use canonical s<digits> phrasing; got: {rendered!r}"
    )
    # And the legacy "s<integer>" phrasing must be gone.
    assert "s<integer>" not in rendered, (
        f"legacy s<integer> phrasing must be replaced; got: {rendered!r}"
    )


def test_validate_game_id_message_names_sov_games_recovery() -> None:
    """Engine-layer message points at ``sov games`` as the recovery
    command. DISPATCH target A row for path-validation rejections requires
    the discovery hint."""
    with pytest.raises(ValueError) as exc_info:
        _validate_game_id("not-a-game-id")
    rendered = str(exc_info.value)
    assert "sov games" in rendered, (
        f"engine-layer message must reference `sov games` recovery; got: {rendered!r}"
    )


def test_validate_game_id_message_quotes_the_offending_input() -> None:
    """The bad input is quoted for support-bundle / log readability."""
    with pytest.raises(ValueError) as exc_info:
        _validate_game_id("not-a-game-id")
    assert "'not-a-game-id'" in str(exc_info.value), (
        f"message should quote the offending input; got: {exc_info.value!r}"
    )


def test_validate_game_id_accepts_canonical_form() -> None:
    """Positive control: the canonical ``s<digits>`` form is accepted."""
    # Should not raise.
    _validate_game_id("s42")
    _validate_game_id("s0")
    _validate_game_id("s12345")
