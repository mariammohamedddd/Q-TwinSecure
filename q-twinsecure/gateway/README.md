# Gateway demo

From the `q-twinsecure` directory, with `cryptography` installed:

```powershell
python -m gateway.demo
python -m unittest discover -s tests -p test_gateway_crypto.py -v
```

`encrypt_reading(reading, key)` and `decrypt_reading(envelope, key)` use a 32-byte key. The envelope contains version 1, a standard Base64-encoded 12-byte random nonce, and standard Base64-encoded ciphertext with the 16-byte authentication tag appended. The version is authenticated as associated data; the reading is inside the authenticated ciphertext. Invalid authentication raises `cryptography.exceptions.InvalidTag`; malformed input raises `ValueError`.

The nonce is randomly generated for each encryption. A key must never be used with the same nonce twice; this demonstration does not persist or coordinate nonces across processes or enforce a per-key usage limit.

The intended integration allocates one key per new protected connection epoch and can use it for multiple readings. Interrupting supply does not itself end an active epoch; establishing a new epoch requires an available key. This module does not manage epochs or the key pool. Direct AES-GCM is a proof-of-concept simplification, not TLS 1.3 or a complete network protocol.
