"""Small, reproducible CO2 simulator; no hardware or teammate dependencies."""

from collections.abc import Callable, Iterable
from datetime import datetime, timezone
import math
import random


def _number(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("CO2 values must be finite non-negative numbers")
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError("CO2 values must be finite non-negative numbers")
    return value


class CO2SensorSimulator:
    """Generate random readings or cycle a fixed sequence indefinitely.

    A local seeded RNG supports repeatability without affecting global randomness.
    The injected clock must return timezone-aware datetimes. Fixed values must
    lie within the configured inclusive range. Status never generates a reading.
    """

    def __init__(
        self,
        sensor_id: str = "co2-simulator-01",
        min_ppm: float = 400.0,
        max_ppm: float = 1000.0,
        *,
        values: Iterable[float] | None = None,
        seed: int | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(sensor_id, str) or not sensor_id.strip():
            raise ValueError("sensor_id must be a non-empty string")
        self.sensor_id = sensor_id
        self.min_ppm = _number(min_ppm)
        self.max_ppm = _number(max_ppm)
        if self.min_ppm > self.max_ppm:
            raise ValueError("min_ppm must not exceed max_ppm")
        self._values = None if values is None else tuple(_number(v) for v in values)
        if self._values is not None:
            if not self._values:
                raise ValueError("fixed values must not be empty")
            if any(not self.min_ppm <= v <= self.max_ppm for v in self._values):
                raise ValueError("fixed values must lie within the configured range")
        self._random = random.Random(seed)
        self._clock = clock if clock is not None else lambda: datetime.now(timezone.utc)
        self._count = 0
        self._latest: dict | None = None

    def read(self) -> dict:
        """Return a JSON-ready reading, recording the latest generated value."""
        timestamp = self._clock()
        if (not isinstance(timestamp, datetime) or timestamp.tzinfo is None
                or timestamp.utcoffset() is None):
            raise ValueError("clock must return a timezone-aware datetime")
        value = (self._random.uniform(self.min_ppm, self.max_ppm)
                 if self._values is None
                 else self._values[self._count % len(self._values)])
        reading = {"sensor_id": self.sensor_id, "value_ppm": value,
                   "timestamp": timestamp.isoformat()}
        self._count += 1
        self._latest = reading.copy()
        return reading

    def read_many(self, count: int) -> list[dict]:
        """Generate count readings immediately, without sleeping or scheduling."""
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("count must be a non-negative integer")
        return [self.read() for _ in range(count)]

    def get_status(self) -> dict | None:
        """Latest generated reading or None, matching planned API sensor state."""
        return None if self._latest is None else self._latest.copy()
