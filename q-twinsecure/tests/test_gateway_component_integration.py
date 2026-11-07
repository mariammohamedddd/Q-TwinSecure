"""Disposable in-process component checks; not an integrated runner test."""

import base64
from datetime import datetime, timezone
import secrets
import unittest

from cryptography.exceptions import InvalidTag
from digital_twin import TwinMonitor
from gateway.crypto import encrypt_reading
from gateway.status import GatewayStatus
from qkd import QKDKeyPool
from sensor import CO2SensorSimulator


class GatewayComponentIntegrationTests(unittest.TestCase):
    def test_key_pool_epoch_interruption_and_recovery(self):
        now = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
        sensor = CO2SensorSimulator(values=[650, 700, 750], clock=lambda: now)
        twin = TwinMonitor(clock=lambda: now)
        gateway = GatewayStatus()

        with QKDKeyPool(capacity=1, auto_generate=False) as pool:
            self.assertEqual(pool.generate_keys(1), 1)
            allocation = pool.consume_key()
            self.assertIsNotNone(allocation)
            gateway.start_epoch(allocation.key_id)
            pool.interrupt_supply()

            # An interrupted supply does not close the current epoch: two
            # readings use the same allocated endpoint keys, not new keys.
            for expected in (650, 700):
                protected = encrypt_reading(sensor.read(), allocation.device_key)
                verified = gateway.verify_reading(protected, allocation.twin_key)
                twin.update_observation(verified, received_at=now)
                self.assertEqual(twin.get_status(now)["value_ppm"], expected)
            self.assertEqual(pool.get_status()["keys_consumed"], 1)
            self.assertEqual(gateway.get_status()["connection_state"], "CONNECTED")

            gateway.end_epoch()
            self.assertIsNone(pool.consume_key())
            self.assertEqual(gateway.get_status()["connection_state"], "DISCONNECTED")
            self.assertEqual(pool.generate_keys(1), 0)

            pool.resume_supply()
            self.assertEqual(pool.generate_keys(1), 1)
            recovery = pool.consume_key()
            self.assertIsNotNone(recovery)
            self.assertNotEqual(recovery.key_id, allocation.key_id)
            gateway.start_epoch(recovery.key_id)
            protected = encrypt_reading(sensor.read(), recovery.device_key)
            twin.update_observation(gateway.verify_reading(protected, recovery.twin_key), received_at=now)
            self.assertEqual(twin.get_status(now)["value_ppm"], 750)
            self.assertEqual(pool.get_status()["keys_consumed"], 2)

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
