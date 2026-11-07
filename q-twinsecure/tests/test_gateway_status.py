import base64
import json
import secrets
import unittest

from cryptography.exceptions import InvalidTag
from gateway.crypto import encrypt_reading
from gateway.status import GatewayStatus


class GatewayStatusTests(unittest.TestCase):
    def setUp(self):
        self.gateway = GatewayStatus()
        self.key = secrets.token_bytes(32)
        self.reading = {"sensor_id": "test-sensor", "value_ppm": 650,
                        "timestamp": "2026-11-05T12:30:00+00:00"}

    def test_epoch_and_verified_reading(self):
        self.assertEqual(self.gateway.get_status()["connection_state"], "DISCONNECTED")
        self.gateway.start_epoch("epoch-1")
        envelope = encrypt_reading(self.reading, self.key)
        self.assertEqual(self.gateway.verify_reading(envelope, self.key), self.reading)
        self.assertEqual(self.gateway.get_status(), {"connection_state": "CONNECTED",
                         "connection_epoch": "epoch-1", "verification": "VERIFIED"})
        self.gateway.end_epoch()
        self.assertEqual(self.gateway.get_status(), {"connection_state": "DISCONNECTED",
                         "connection_epoch": None, "verification": None})

    def test_rejection_never_returns_a_reading(self):
        self.gateway.start_epoch("epoch-1")
        envelope = encrypt_reading(self.reading, self.key)
        ciphertext = bytearray(base64.b64decode(envelope["ciphertext"]))
        ciphertext[0] ^= 1
        envelope["ciphertext"] = base64.b64encode(ciphertext).decode("ascii")
        with self.assertRaises(InvalidTag):
            self.gateway.verify_reading(envelope, self.key)
        self.assertEqual(self.gateway.get_status()["verification"], "REJECTED")
        with self.assertRaises(ValueError):
            self.gateway.verify_reading({}, self.key)
        self.assertEqual(self.gateway.get_status()["verification"], "REJECTED")

    def test_disconnected_and_overlapping_epochs_rejected(self):
        with self.assertRaises(ValueError):
            self.gateway.verify_reading({}, self.key)
        self.gateway.start_epoch("epoch-1")
        with self.assertRaises(ValueError):
            self.gateway.start_epoch("epoch-2")
        self.assertEqual(self.gateway.get_status()["connection_epoch"], "epoch-1")

    def test_status_is_independent_and_contains_no_message_or_key(self):
        self.gateway.start_epoch("epoch-1")
        self.gateway.verify_reading(encrypt_reading(self.reading, self.key), self.key)
        snapshot = self.gateway.get_status()
        self.assertNotIn(self.key.hex(), json.dumps(snapshot))
        self.assertNotIn("test-sensor", json.dumps(snapshot))
        snapshot["verification"] = "REJECTED"
        self.assertEqual(self.gateway.get_status()["verification"], "VERIFIED")


if __name__ == "__main__":
    unittest.main()
