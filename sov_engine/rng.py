"""Deterministic RNG for reproducible game state."""

from __future__ import annotations

import random
from typing import Any


class GameRng:
    """Seeded RNG wrapper for deterministic game replay."""

    def __init__(self, seed: int) -> None:
        self.seed = seed
        self._rng = random.Random(seed)

    def roll_d6(self) -> int:
        return self._rng.randint(1, 6)

    def shuffle(self, items: list) -> None:  # type: ignore[type-arg]
        self._rng.shuffle(items)

    def choice(self, items: list) -> object:  # type: ignore[type-arg]
        return self._rng.choice(items)

    def randint(self, a: int, b: int) -> int:
        return self._rng.randint(a, b)

    def getstate(self) -> list[Any]:
        """Return a JSON-serializable copy of the underlying stream state.

        Shape is ``[version, list(internal_mt_state), gauss_next]`` — the
        stdlib ``random.Random.getstate()`` tuple with the internals tuple
        expanded so it round-trips through ``json``. Restore with
        ``setstate``. Persisted next to the seed so a fresh CLI process
        continues the stream instead of replaying roll 1 of the seed.
        """
        version, intern, gauss = self._rng.getstate()
        return [version, list(intern), gauss]

    def setstate(self, state: object) -> None:
        """Restore stream state previously produced by ``getstate``."""
        if not isinstance(state, (list, tuple)) or len(state) != 3:
            raise ValueError("rng_state must be a 3-element sequence")
        version_raw, intern_raw, gauss = state
        if not isinstance(intern_raw, (list, tuple)):
            raise ValueError("rng_state internals must be a sequence")
        intern = tuple(int(x) for x in intern_raw)
        self._rng.setstate((int(version_raw), intern, gauss))
