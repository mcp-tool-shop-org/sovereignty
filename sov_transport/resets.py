"""Announced resets of the public XRPL test networks.

A reset deletes every account and transaction on a test network. A round
proof anchored before one still has a valid local hash, but its anchor
transaction is on no ledger any more. A chain lookup then answers "no such
transaction", which is also the answer for a txid that was never real.

This module holds the one signal that tells those apart without trusting the
proof: the list of resets the network's operators announced. When an
announced reset covers the time a proof was made, and the anchor transaction
is absent, the lookup is reported as ``ChainLookupResult.RESET``: the anchor
can no longer be checked. That is never a pass. A proof with a made-up txid
and a date before the reset reads the same way, so only the local hash is
left as evidence.

The announcement gives a day and no hour or timezone. So a reset covers a
proof made before the day has ended everywhere (UTC-12), and counts as having
happened only once the day has begun everywhere (UTC+14). Mainnet is never
reset and is never listed here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sov_transport.base import LedgerTransport

#: What a RESET verdict rests on. One value today: an announced reset.
RESET_SIGNAL_ANNOUNCED = "announced"


@dataclass(frozen=True)
class KnownReset:
    """An announced reset of one network, on one day."""

    network: str
    day: date
    source: str

    @property
    def starts(self) -> datetime:
        """The earliest instant the reset day exists anywhere (UTC+14)."""
        return datetime.combine(self.day, time.min, tzinfo=UTC) - timedelta(hours=14)

    @property
    def ends(self) -> datetime:
        """The last instant the reset day exists anywhere (UTC-12)."""
        next_day = self.day + timedelta(days=1)
        return datetime.combine(next_day, time.min, tzinfo=UTC) + timedelta(hours=12)

    def label(self) -> str:
        return f"{self.network.capitalize()} was reset on {self.day.isoformat()}"


# The same list is kept in xrpl-lab (xrpl_lab/resets.py, the source) and
# xrpl-camp (xrpl_camp/resets.py). A new announced reset is added to all three.
_RESET_2026_11_25 = "https://xrpl.org/blog/2026/testnet-devnet-reset"

KNOWN_RESETS: tuple[KnownReset, ...] = (
    KnownReset("testnet", date(2026, 11, 25), _RESET_2026_11_25),
    KnownReset("devnet", date(2026, 11, 25), _RESET_2026_11_25),
)


def _now() -> datetime:
    """The current time. A seam: the test suite pins it, so results do not
    change on the day a listed reset happens."""
    return datetime.now(tz=UTC)


def parse_time(value: object) -> datetime | None:
    """An ISO 8601 time from a proof, as an aware datetime, or None."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def announced_reset_after(
    network: str,
    recorded_at: datetime | None,
    *,
    now: datetime | None = None,
    resets: tuple[KnownReset, ...] = KNOWN_RESETS,
) -> KnownReset | None:
    """The first announced reset of ``network`` after ``recorded_at``.

    Only a reset that has (possibly) already happened counts. A proof with no
    recorded time is covered by any reset that has happened, since nothing
    says it came later.
    """
    now = now or _now()
    for reset in sorted(resets, key=lambda r: r.day):
        if reset.network != network or now < reset.starts:
            continue
        if recorded_at is None or recorded_at < reset.ends:
            return reset
    return None


def reset_explains_missing_anchor(
    transport: LedgerTransport | object,
    network: str,
    txid: str,
    proof_timestamp: object,
) -> KnownReset | None:
    """The announced reset that explains a missing anchor, or None.

    Call this only after a chain lookup answered ``NOT_FOUND``. That answer
    covers two cases: the transaction is absent, or it exists and carries a
    different hash. A reset explains only the first, so the transport is
    asked whether the transaction is there. A transport that cannot say
    (no ``tx_exists``, or the read failed) gives no reset verdict: the
    ``NOT_FOUND`` stands.
    """
    reset = announced_reset_after(network, parse_time(proof_timestamp))
    if reset is None:
        return None
    probe = getattr(transport, "tx_exists", None)
    if not callable(probe):
        return None
    if probe(txid) is False:
        return reset
    return None
