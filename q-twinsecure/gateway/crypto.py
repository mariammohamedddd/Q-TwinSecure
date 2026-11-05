"""Protect JSON sensor readings using AES-256-GCM."""

import base64
import binascii
import json
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


_VERSION = 1
_AAD = b'{"version":1}'
_FIELDS = {"sensor_id", "value_ppm", "timestamp"}


def _validate_reading(reading):
    if not isinstance(reading, dict) or not _FIELDS.issubset(reading):
        raise ValueError("reading must contain sensor_id, value_ppm and timestamp")
    if not isinstance(reading["sensor_id"], str) or not isinstance(reading["timestamp"], str):
        raise ValueError("sensor_id and timestamp must be strings")
    if isinstance(reading["value_ppm"], bool) or not isinstance(reading["value_ppm"], (int, float)):
        raise ValueError("value_ppm must be a number")


def _cipher(key):
    if not isinstance(key, bytes) or len(key) != 32:
        raise ValueError("key must be 32 bytes")
    return AESGCM(key)


def encrypt_reading(reading: dict, key: bytes) -> dict:
    """Return a versioned envelope; byte fields are standard base64 strings."""
    cipher = _cipher(key)
    _validate_reading(reading)
    try:
        plaintext = json.dumps(reading, allow_nan=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("reading must contain JSON-compatible values") from exc
    nonce = os.urandom(12)
    ciphertext = cipher.encrypt(nonce, plaintext, _AAD)
    return {"version": _VERSION, "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii")}


def decrypt_reading(envelope: dict, key: bytes) -> dict:
    """Authenticate and decode an envelope; authentication failures are rejected."""
    cipher = _cipher(key)
    if (not isinstance(envelope, dict) or set(envelope) != {"version", "nonce", "ciphertext"}
            or type(envelope["version"]) is not int or envelope["version"] != _VERSION):
        raise ValueError("invalid envelope")
    try:
        nonce = base64.b64decode(envelope["nonce"], validate=True)
        ciphertext = base64.b64decode(envelope["ciphertext"], validate=True)
    except (TypeError, ValueError, binascii.Error) as exc:
        raise ValueError("invalid envelope encoding") from exc
    if len(nonce) != 12 or len(ciphertext) < 16:
        raise ValueError("invalid envelope lengths")
    plaintext = cipher.decrypt(nonce, ciphertext, _AAD)
    try:
        reading = json.loads(plaintext.decode("utf-8"), parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid JSON number")))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("invalid reading encoding") from exc
    _validate_reading(reading)
    return reading
