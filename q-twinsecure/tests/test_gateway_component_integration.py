"""Disposable in-process component checks; not an integrated runner test."""

import base64
from datetime import datetime, timezone
import secrets
import unittest

from cryptography.exceptions import InvalidTag
from digital_twin import TwinMonitor
from gateway.crypto import encrypt_reading
from gateway.status import GatewayStatus
from sensor import CO2SensorSimulator


class GatewayComponentIntegrationTests(unittest.TestCase):
    def test_verified_reading_updates_twin_and_tampering_does_not(self):
        now = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
        sensor = CO2SensorSimulator(values=[650, 700], clock=lambda: now)
        twin = TwinMonitor(clock=lambda: now)
        gateway = GatewayStatus()
        key = secrets.token_bytes(32)
        gateway.start_epoch("test-epoch")

        first = sensor.read()
        verified = gateway.verify_reading(encrypt_reading(first, key), key)
        twin.update_observation(verified, received_at=now)
        before = twin.get_status(now)
        self.assertEqual(before["value_ppm"], 650)
        self.assertEqual(before["freshness"], "CURRENT")

        envelope = encrypt_reading(sensor.read(), key)
        ciphertext = bytearray(base64.b64decode(envelope["ciphertext"]))
        ciphertext[0] ^= 1
        envelope["ciphertext"] = base64.b64encode(ciphertext).decode("ascii")
        with self.assertRaises(InvalidTag):
            # The runner must forward only a successfully returned reading.
            twin.update_observation(gateway.verify_reading(envelope, key), received_at=now)
        self.assertEqual(twin.get_status(now), before)
        self.assertEqual(gateway.get_status()["verification"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
