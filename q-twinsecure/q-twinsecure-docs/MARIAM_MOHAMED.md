# Mariam Mohamed — CO₂ Sensor Simulator

## Goal
Build a tiny independent Python simulator that produces timestamped CO₂ readings. Do not wait for gateway, key-pool, or Twin code.

## Tasks
1. Implement `CO2SensorSimulator` or equivalent functions.
2. Generate CO₂ values in ppm from a configurable range or fixed sequence.
3. Include a stable sensor ID.
4. Include an ISO-8601 timezone-aware timestamp.
5. Return the shared reading format:
```python
{
    "sensor_id": "co2-simulator-01",
    "value_ppm": 650.0,
    "timestamp": "2026-11-05T12:30:00+00:00"
}
```
6. Support one reading and a sequence of readings.
7. Allow deterministic tests (fixed values/seed or injected clock).
8. Add demo and tests.

## Files
```text
sensor/
├── __init__.py
├── co2_simulator.py
└── demo.py
tests/test_sensor.py
```

## Independent demo
Run without other project modules and print five sample readings in the agreed format.

## Tests
Required fields; stable non-empty sensor ID; numeric value in configured range; parseable timezone-aware timestamp; multiple readings.

## Acceptance
Demo/tests run independently and output matches `INTERFACE_CONTRACT.md`. Record actual results in `IMPLEMENTATION_STATUS.md`.

## Dashboard and integration tasks
- Expose safe sensor status through the shared integration contract in [plan.md](plan.md).
- Build the sensor panel showing current value, sensor ID and timestamp from the real backend; handle unavailable data.
- Test the panel with the integrated runner and verify displayed readings match the backend. Coordinate shared API changes with Nancy.

## Not assigned
Encryption/transmission, key management, Twin freshness, other owners' modules, physical sensor/Modbus hardware.
