"""Deterministic RNG for reproducible game state."""

from __future__ import annotations

import random


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
