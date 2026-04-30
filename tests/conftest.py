"""Shared test fixtures.

Resets module-level counters in ``sov_engine.rules.campfire`` between every
test. The voucher and deal counters are global mutable state that would
otherwise create hidden ordering dependencies (test_a issues v_0001, then
test_b expects v_0001 and gets v_0002 because the counter wasn't reset).
This autouse fixture removes that class of flake.
"""

from __future__ import annotations

import pytest

from sov_engine.rules import campfire as _campfire


@pytest.fixture(autouse=True)
def _reset_campfire_counters() -> None:
    """Reset voucher and deal counters before every test."""
    _campfire._voucher_counter = 0
    _campfire._deal_counter = 0
