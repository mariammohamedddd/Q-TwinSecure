"""Freshness of one sensor's latest observation; authentication belongs upstream."""

from collections.abc import Callable
from datetime import datetime, timezone
import math


def _aware_time(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("Time must be a timezone-aware datetime")
    return value.astimezone(timezone.utc)


class TwinMonitor:
    """Track a single sensor, using observation time rather than arrival time.

    Thresholds and ages are seconds. Defaults are demo parameters, not agreed
    experiment settings. Future observations and out-of-order updates are rejected.
    The caller must authenticate readings before passing them to this class.
    """

    def __init__(
        self,
        current_threshold: float = 5.0,
        missing_threshold: float = 15.0,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        for threshold in (current_threshold, missing_threshold):
            if (isinstance(threshold, bool) or not isinstance(threshold, (int, float))
                    or not math.isfinite(threshold)):
                raise ValueError("Thresholds must be finite numbers")
        if not 0 <= current_threshold < missing_threshold:
            raise ValueError("Require 0 <= current_threshold < missing_threshold")
        self.current_threshold = float(current_threshold)
        self.missing_threshold = float(missing_threshold)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._reading: dict | None = None
        self._observed_at: datetime | None = None
        self._received_at: datetime | None = None

    def update_observation(self, reading: dict, received_at=None) -> None:
        """Validate atomically; ValueError leaves the previous observation intact."""
        if not isinstance(reading, dict):
            raise ValueError("Reading must be a dictionary")
        sensor_id = reading.get("sensor_id")
        value = reading.get("value_ppm")
        timestamp = reading.get("timestamp")
        if not isinstance(sensor_id, str) or not sensor_id.strip():
            raise ValueError("sensor_id must be a non-empty string")
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value < 0):
            raise ValueError("value_ppm must be a finite non-negative number")
        if not isinstance(timestamp, str):
            raise ValueError("timestamp must be an ISO-8601 string")
        try:
            observed = _aware_time(datetime.fromisoformat(timestamp))
        except ValueError as exc:
            raise ValueError("timestamp must be timezone-aware ISO-8601") from exc
        received = _aware_time(self._clock() if received_at is None else received_at)
        if observed > received:
            raise ValueError("Observation timestamp cannot be after receive time")
        if self._reading is not None:
            if sensor_id != self._reading["sensor_id"]:
                raise ValueError("Use a separate monitor for each sensor")
            if observed < self._observed_at:
                raise ValueError("Observation is older than the latest observation")
        self._reading = {"sensor_id": sensor_id, "value_ppm": value, "timestamp": timestamp}
        self._observed_at = observed
        self._received_at = received

    def get_freshness(self, now=None) -> str:
        return self.get_status(now)["freshness"]

    def get_status(self, now=None) -> dict:
        """Return a detached snapshot, including configuration for experiment logs."""
        instant = _aware_time(self._clock() if now is None else now)
        age = None
        freshness = "MISSING"
        if self._observed_at is not None:
            age = (instant - self._observed_at).total_seconds()
            if age < 0:
                raise ValueError("Query time cannot precede the observation")
            if age <= self.current_threshold:
                freshness = "CURRENT"
            elif age <= self.missing_threshold:
                freshness = "DELAYED"
        return {
            "sensor_id": self._reading["sensor_id"] if self._reading else None,
            "value_ppm": self._reading["value_ppm"] if self._reading else None,
            "timestamp": self._reading["timestamp"] if self._reading else None,
            "received_at": self._received_at.isoformat() if self._received_at else None,
            "age_seconds": age,
            "freshness": freshness,
            "current_threshold": self.current_threshold,
            "missing_threshold": self.missing_threshold,
        }
