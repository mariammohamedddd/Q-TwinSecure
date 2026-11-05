# Marwan — Emulated QKD Key Pool

## Goal
Build a small, independently runnable software model of constrained key supply. It uses classical cryptographically secure randomness; it is not physical QKD, BB84, or quantum-secure communication.

## Tasks
1. Implement a `QKDKeyPool` class.
2. Generate 32-byte key material with `secrets.token_bytes(32)`.
3. Give each key a unique non-secret `key_id`.
4. Maintain matching in-memory device-side and Twin-side pools.
5. Enforce configurable maximum capacity.
6. Consume one matching key pair, or return `None` when empty.
7. Support supply interruption and resumption.
8. Expose safe status: supply enabled, available count, generated count, consumed count.
9. Never print/log raw key bytes.
10. Add independent tests and a runnable demo.

## Files
```text
qkd/
├── __init__.py
├── key_pool.py
└── demo.py
tests/test_key_pool.py
```

## Independent demo
Without importing other project modules: generate keys to capacity, consume one and show matching IDs (not key material), test empty pool, interrupt supply, verify generation is blocked, resume and generate again.

## Tests
Capacity bound; matching endpoint records; empty pool; interruption; recovery; counters.

## Acceptance
Demo and tests run independently and match `INTERFACE_CONTRACT.md`. Record actual results in `IMPLEMENTATION_STATUS.md`.

## Not assigned
Gateway encryption, sensor simulator, Twin freshness, end-to-end integration, physical QKD/BB84.
