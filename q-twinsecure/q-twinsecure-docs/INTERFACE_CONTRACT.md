# Shared Interface Contract

This contract allows everyone to implement independently with sample data and mocks.

## Sensor reading
```python
{
    "sensor_id": "co2-simulator-01",
    "value_ppm": 650.0,
    "timestamp": "2026-11-05T12:30:00+00:00"
}
```
Required fields: `sensor_id`, `value_ppm`, `timestamp`.

## Key pool
Equivalent public behavior:
- `generate_keys(count: int) -> int`
- `consume_key() -> key_record | None`
- `interrupt_supply() -> None`
- `resume_supply() -> None`
- `get_status() -> dict`

A key record provides a non-secret `key_id` and 32-byte material for both simulated endpoints. Never log key bytes.

Marwan's implementation returns an immutable `KeyRecord` with `key_id: str`,
`device_key: bytes`, and `twin_key: bytes`. Both endpoint byte fields match and
are excluded from the record's `repr`. Use these fields internally only.
`QKDKeyPool(capacity=10)` starts empty with supply enabled. `get_status()` returns
`supply_enabled`, `keys_available`, `keys_generated`, `keys_consumed`, and
`capacity`; it never returns key records. By default a background worker generates
one pair every `generation_interval` seconds (default 1.0), waiting when full and
refilling freed slots automatically. Interruption stops generation, preserving
queued and allocated pairs; resumption restarts automatic supply. The explicit
`generate_keys` API remains for seeding; use `auto_generate=False` for deterministic
experiments. Public operations are synchronized; the runner still coordinates
multi-component epoch establishment. Use the pool as a context manager or call
`close()` to stop/join its worker. See [the key-pool run guide](../qkd/README.md).

Capacity is the maximum number of available keys **per endpoint**. Both pools
fill together and never exceed that limit. A full pool adds zero keys and keeps
its stored keys unchanged; allocation frees one slot in each pool, which supply
can refill. The key panel derives both endpoint occupancies and its full state
from the synchronized `keys_available` and `capacity` fields.

## Gateway
Equivalent public behavior:
- `encrypt_reading(reading: dict, key: bytes) -> dict`
- `decrypt_reading(envelope: dict, key: bytes) -> dict`

Document byte encoding. Use AES-GCM with a fresh 12-byte nonce per encryption under a given key. Reject tampering. Direct AES-GCM is not a full TLS implementation.

## Digital Twin
Equivalent public behavior:
- `update_observation(reading: dict, received_at=None) -> None`
- `get_freshness(now=None) -> str`
- `get_status(now=None) -> dict`

States: `CURRENT`, `DELAYED`, `MISSING`. Thresholds must be configurable.

## Planned dashboard integration

The versioned status and scenario-control contract for the shared local dashboard is specified in [plan.md](plan.md). Each component supplies real state to the integration runner; no raw key material is sent to the browser. Existing component interfaces above remain the starting point.

## Independence
Sensor/Twin work uses local sample dictionaries; gateway tests use a local test key and fake key provider; key-pool work uses its own demo. No contributor should need another module to run their own demo.
