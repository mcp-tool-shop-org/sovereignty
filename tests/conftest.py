"""Shared test fixtures.

Historically reset module-level counters in ``sov_engine.rules.campfire``
between every test. The voucher and deal counters were global mutable state
that created hidden ordering dependencies (test_a issues v_0001, then test_b
expects v_0001 and gets v_0002 because the counter wasn't reset). This
autouse fixture removed that class of flake.

NO-OP since W5: counters now live on ``GameState`` (engine moved
``_voucher_counter`` / ``_deal_counter`` from module globals into per-game
state). The fixture is preserved as a hook for future test isolation needs
(e.g. resetting other process-wide state) and to keep the
``conftest.py`` discovery surface stable for pytest plugins.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sov_engine.rules import campfire as _campfire


@pytest.fixture(autouse=True)
def _reset_campfire_counters() -> None:
    """No-op since W5: counters live on GameState; preserved as a hook for
    future test isolation needs.

    Defensive: if the module-level globals still exist (e.g. mid-migration),
    reset them anyway so this fixture remains safe to keep enabled.
    """
    if hasattr(_campfire, "_voucher_counter"):
        _campfire._voucher_counter = 0
    if hasattr(_campfire, "_deal_counter"):
        _campfire._deal_counter = 0


# Before every reset listed in ``sov_transport.resets.KNOWN_RESETS``.
BEFORE_ANY_KNOWN_RESET = datetime(2026, 11, 1, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _pin_reset_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the clock the network-reset check reads.

    A chain lookup that answers "not found" is re-judged once a listed
    network reset has happened. Without a pinned clock, tests that expect a
    plain mismatch could change their result on the reset day. Tests of the
    reset behaviour set their own time over this one.
    """
    monkeypatch.setattr("sov_transport.resets._now", lambda: BEFORE_ANY_KNOWN_RESET)
