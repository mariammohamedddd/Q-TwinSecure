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

## Independence
Sensor/Twin work uses local sample dictionaries; gateway tests use a local test key and fake key provider; key-pool work uses its own demo. No contributor should need another module to run their own demo.
