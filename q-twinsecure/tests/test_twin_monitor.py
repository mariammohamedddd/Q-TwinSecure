"""Deterministic tests; runnable using standard-library unittest or pytest."""

from datetime import datetime, timedelta, timezone
import unittest

from digital_twin import TwinMonitor


class TwinMonitorTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 5, 12, 30, tzinfo=timezone.utc)
        self.monitor = TwinMonitor(clock=lambda: self.now)
        self.reading = {"sensor_id": "co2-simulator-01", "value_ppm": 650.0,
                        "timestamp": self.now.isoformat()}

    def test_no_reading(self):
        status = self.monitor.get_status()
        self.assertEqual(status["freshness"], "MISSING")
        self.assertIsNone(status["age_seconds"])
        self.assertIsNone(status["value_ppm"])

    def test_transitions_and_boundaries(self):
        self.monitor.update_observation(self.reading)
        for age, expected in [(0, "CURRENT"), (5, "CURRENT"), (5.001, "DELAYED"),
                              (15, "DELAYED"), (15.001, "MISSING")]:
            with self.subTest(age=age):
                self.assertEqual(self.monitor.get_freshness(
                    self.now + timedelta(seconds=age)), expected)

    def test_observation_age_includes_delivery_delay(self):
        self.monitor.update_observation(self.reading, self.now + timedelta(seconds=8))
        status = self.monitor.get_status(self.now + timedelta(seconds=8))
        self.assertEqual(status["age_seconds"], 8)
        self.assertEqual(status["freshness"], "DELAYED")
        self.assertEqual(status["received_at"], (self.now + timedelta(seconds=8)).isoformat())

    def test_invalid_readings_preserve_previous_status(self):
        self.monitor.update_observation(self.reading)
        before = self.monitor.get_status()
        invalid = [None, {}, {**self.reading, "sensor_id": " "},
                   {**self.reading, "value_ppm": True},
                   {**self.reading, "value_ppm": -1},
                   {**self.reading, "value_ppm": float("nan")},
                   {**self.reading, "value_ppm": float("inf")},
                   {**self.reading, "timestamp": "bad"},
                   {**self.reading, "timestamp": "2026-11-05T12:30:00"},
                   {**self.reading, "timestamp": (self.now + timedelta(seconds=1)).isoformat()},
                   {**self.reading, "timestamp": (self.now - timedelta(seconds=1)).isoformat()},
                   {**self.reading, "sensor_id": "other"}]
        for reading in invalid:
            with self.subTest(reading=reading):
                with self.assertRaises(ValueError):
                    self.monitor.update_observation(reading)
                self.assertEqual(self.monitor.get_status(), before)

    def test_recovery_and_input_snapshot(self):
        self.monitor.update_observation(self.reading)
        self.reading["value_ppm"] = 999
        self.assertEqual(self.monitor.get_status()["value_ppm"], 650)
        self.now += timedelta(seconds=20)
        self.assertEqual(self.monitor.get_freshness(), "MISSING")
        self.monitor.update_observation({**self.reading, "timestamp": self.now.isoformat()})
        self.assertEqual(self.monitor.get_freshness(), "CURRENT")

    def test_custom_thresholds(self):
        monitor = TwinMonitor(1, 2, clock=lambda: self.now)
        monitor.update_observation(self.reading)
        self.assertEqual(monitor.get_freshness(self.now + timedelta(seconds=1.5)), "DELAYED")
        self.assertEqual(monitor.get_freshness(self.now + timedelta(seconds=3)), "MISSING")

    def test_invalid_configuration(self):
        for current, missing in [(-1, 15), (5, 5), (16, 15), (True, 15),
                                 (float("nan"), 15), (5, float("inf"))]:
            with self.subTest(current=current, missing=missing):
                with self.assertRaises(ValueError):
                    TwinMonitor(current, missing)

    def test_timezone_offsets_and_z(self):
        for timestamp in ("2026-11-05T14:30:00+02:00", "2026-11-05T12:30:00Z"):
            self.monitor.update_observation({**self.reading, "timestamp": timestamp})
            self.assertEqual(self.monitor.get_status()["age_seconds"], 0)

    def test_invalid_clock_values(self):
        self.monitor.update_observation(self.reading)
        for instant in (datetime(2026, 11, 5), self.now - timedelta(seconds=1)):
            with self.assertRaises(ValueError):
                self.monitor.get_status(instant)


if __name__ == "__main__":
    unittest.main()
