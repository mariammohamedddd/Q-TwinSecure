import json
import unittest
from datetime import datetime, timedelta, timezone

from sensor import CO2SensorSimulator


class SensorTests(unittest.TestCase):
    def test_reading_contract_and_serialization(self):
        now = datetime(2026, 11, 5, 12, 30, tzinfo=timezone.utc)
        sensor = CO2SensorSimulator(clock=lambda: now, values=[650])
        reading = sensor.read()
        self.assertEqual(reading, {"sensor_id": "co2-simulator-01",
                                  "value_ppm": 650.0, "timestamp": now.isoformat()})
        self.assertEqual(json.loads(json.dumps(reading, allow_nan=False)), reading)
        self.assertIsNotNone(datetime.fromisoformat(reading["timestamp"]).utcoffset())

    def test_default_clock_is_aware(self):
        timestamp = datetime.fromisoformat(CO2SensorSimulator().read()["timestamp"])
        self.assertEqual(timestamp.utcoffset(), timedelta(0))

    def test_seeded_range_and_stable_id(self):
        first = CO2SensorSimulator("room-01", 500, 600, seed=42).read_many(100)
        second = CO2SensorSimulator("room-01", 500, 600, seed=42).read_many(100)
        self.assertEqual([r["value_ppm"] for r in first], [r["value_ppm"] for r in second])
        self.assertTrue(all(500 <= r["value_ppm"] <= 600 and r["sensor_id"] == "room-01"
                            for r in first))

    def test_sequence_cycles_and_zero_count(self):
        sensor = CO2SensorSimulator(values=[400, 1000])
        self.assertEqual(sensor.read_many(0), [])
        self.assertIsNone(sensor.get_status())
        self.assertEqual([r["value_ppm"] for r in sensor.read_many(5)],
                         [400, 1000, 400, 1000, 400])

    def test_equal_range(self):
        self.assertEqual(CO2SensorSimulator(min_ppm=500, max_ppm=500).read()["value_ppm"], 500)

    def test_status_is_defensive_and_does_not_generate(self):
        sensor = CO2SensorSimulator(values=[500, 600])
        reading = sensor.read()
        reading["value_ppm"] = -1
        status = sensor.get_status()
        self.assertEqual(status["value_ppm"], 500)
        status["value_ppm"] = -2
        self.assertEqual(sensor.get_status()["value_ppm"], 500)
        self.assertEqual(sensor.read()["value_ppm"], 600)

    def test_invalid_configuration(self):
        for kwargs in ({"sensor_id": ""}, {"sensor_id": " "}, {"sensor_id": None},
                       {"min_ppm": -1}, {"min_ppm": 1001}, {"max_ppm": float("inf")},
                       {"min_ppm": float("nan")}, {"min_ppm": True},
                       {"max_ppm": "900"}, {"values": []}, {"values": [399]},
                       {"values": [1001]}, {"values": [True]}, {"values": [float("nan")]}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                CO2SensorSimulator(**kwargs)

    def test_invalid_count(self):
        for count in (-1, 1.5, True, "2"):
            with self.subTest(count=count), self.assertRaises(ValueError):
                CO2SensorSimulator().read_many(count)

    def test_invalid_clock_preserves_state(self):
        for now in (datetime(2026, 11, 5), "invalid"):
            sensor = CO2SensorSimulator(clock=lambda: now)
            with self.subTest(now=now), self.assertRaises(ValueError):
                sensor.read()
            self.assertIsNone(sensor.get_status())

    def test_injected_clock_advances(self):
        now = datetime(2026, 11, 5, tzinfo=timezone(timedelta(hours=2)))
        times = iter([now, now + timedelta(seconds=1)])
        readings = CO2SensorSimulator(clock=lambda: next(times)).read_many(2)
        self.assertEqual(datetime.fromisoformat(readings[1]["timestamp"])
                         - datetime.fromisoformat(readings[0]["timestamp"]), timedelta(seconds=1))


if __name__ == "__main__":
    unittest.main()
