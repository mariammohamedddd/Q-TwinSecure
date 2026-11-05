"""Run with: python -m gateway.demo"""

import base64
import secrets

from cryptography.exceptions import InvalidTag
from gateway.crypto import decrypt_reading, encrypt_reading


def main():
    key = secrets.token_bytes(32)
    reading = {"sensor_id": "co2-simulator-01", "value_ppm": 650.0,
               "timestamp": "2026-11-05T12:30:00+00:00"}
    envelope = encrypt_reading(reading, key)
    print("Recovered reading:", decrypt_reading(envelope, key))
    modified = dict(envelope)
    ciphertext = bytearray(base64.b64decode(modified["ciphertext"]))
    ciphertext[0] ^= 1
    modified["ciphertext"] = base64.b64encode(ciphertext).decode("ascii")
    try:
        decrypt_reading(modified, key)
    except InvalidTag:
        print("Modified ciphertext rejected.")
    else:
        raise RuntimeError("Modified ciphertext was not rejected")


if __name__ == "__main__":
    main()
