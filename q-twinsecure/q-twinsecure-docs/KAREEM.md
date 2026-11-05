# Kareem — Minimal Security Gateway / AES-256-GCM

## Goal
Build an independent authenticated-encryption demo for a sensor-reading payload. Use a locally generated test key; do not depend on Marwan's key-pool code.

Direct AES-256-GCM is a proposed PoC simplification, not a full TLS 1.3 external-PSK implementation.

## Tasks
1. Use `cryptography` and its `AESGCM` API.
2. Accept a reading matching `INTERFACE_CONTRACT.md`.
3. Serialize and encrypt it with a 32-byte test key.
4. Generate a fresh 12-byte nonce for every encryption.
5. Return an envelope containing non-secret metadata, nonce, and ciphertext/tag.
6. Decrypt and deserialize valid envelopes.
7. Reject modified ciphertext, nonce, or authenticated metadata.
8. Document the encoding (e.g. base64 for byte fields).
9. Never print/log the key.
10. Add independent tests and demo.

## Files
```text
gateway/
├── __init__.py
├── crypto.py
└── demo.py
tests/test_gateway_crypto.py
```

## Independent demo
Create a sample reading locally, generate a temporary test key, encrypt/decrypt, alter ciphertext and show rejection. Do not import sensor/key-pool modules or print the key.

## Tests
Valid round-trip; fresh nonce; tampered ciphertext rejected; tampered authenticated metadata rejected if used as AAD; malformed envelope rejected.

## Lifecycle note
Document intended semantics: one key per new protected connection epoch; multiple readings may use that epoch; interruption does not itself terminate an active epoch; a new epoch needs an available key.

## Acceptance
Demo/tests run independently and follow `INTERFACE_CONTRACT.md`. Record actual results in `IMPLEMENTATION_STATUS.md`.

## Not assigned
Key-pool internals, sensor generation, Twin freshness, full experiment, production TLS/mTLS.
