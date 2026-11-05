import base64
import secrets
import unittest

from cryptography.exceptions import InvalidTag
from gateway.crypto import decrypt_reading, encrypt_reading


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.key = secrets.token_bytes(32)
        self.reading = {"sensor_id": "co2-simulator-01", "value_ppm": 650.0,
                        "timestamp": "2026-11-05T12:30:00+00:00"}

    def test_round_trip(self):
        self.assertEqual(decrypt_reading(encrypt_reading(self.reading, self.key), self.key), self.reading)

    def test_fresh_nonce(self):
        self.assertNotEqual(encrypt_reading(self.reading, self.key)["nonce"],
                            encrypt_reading(self.reading, self.key)["nonce"])

    def test_tampered_ciphertext_and_nonce(self):
        for field in ("ciphertext", "nonce"):
            with self.subTest(field=field):
                envelope = encrypt_reading(self.reading, self.key)
                data = bytearray(base64.b64decode(envelope[field]))
                data[0] ^= 1
                envelope[field] = base64.b64encode(data).decode("ascii")
                with self.assertRaises(InvalidTag):
                    decrypt_reading(envelope, self.key)

    def test_modified_metadata_rejected(self):
        envelope = encrypt_reading(self.reading, self.key)
        envelope["version"] = 2
        with self.assertRaises(ValueError):
            decrypt_reading(envelope, self.key)

    def test_malformed_envelopes_rejected(self):
        for envelope in ({}, {"version": 1, "nonce": "!", "ciphertext": ""},
                         {"version": 1, "nonce": "", "ciphertext": ""}):
            with self.subTest(envelope=envelope), self.assertRaises(ValueError):
                decrypt_reading(envelope, self.key)

    def test_invalid_key_and_reading_rejected(self):
        with self.assertRaises(ValueError):
            encrypt_reading(self.reading, b"short")
        with self.assertRaises(ValueError):
            encrypt_reading({"sensor_id": "x"}, self.key)


if __name__ == "__main__":
    unittest.main()
