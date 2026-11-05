# Mariam Wael — Digital Twin Freshness Monitor

## Goal
Build a minimal independent monitor that accepts sample readings and reports `CURRENT`, `DELAYED`, or `MISSING`. Use local sample data; do not wait for sensor or gateway code.

## Tasks
1. Implement `TwinMonitor` or equivalent functions.
2. Accept readings with `sensor_id`, `value_ppm`, `timestamp`.
3. Store the latest valid observation and receive time.
4. Calculate observation age.
5. Implement:
   - `CURRENT`: age is within the configured current threshold.
   - `DELAYED`: age exceeds current threshold but not missing threshold.
   - `MISSING`: no valid observation, or age exceeds missing threshold.
6. Make thresholds configurable.
7. Expose latest value, timestamp, age, and freshness in a status dictionary.
8. Add terminal demo and tests using sample readings and a controllable clock.

## Files
```text
digital_twin/
├── __init__.py
├── twin_monitor.py
└── demo.py
tests/test_twin_monitor.py
```

## Independent demo
Feed a local sample reading, show `CURRENT`, then simulate elapsed time to show `DELAYED` and `MISSING`.

## Tests
No reading -> MISSING; fresh -> CURRENT; older -> DELAYED; expired -> MISSING; invalid reading does not replace valid reading; threshold boundaries.

## Acceptance
Demo/tests run independently and follow `INTERFACE_CONTRACT.md`. Record actual results in `IMPLEMENTATION_STATUS.md`.

## Not assigned
Sensor generation, encryption/decryption, key/connection management, integration, large web dashboard.
