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

## Dashboard and integration tasks
- Expose latest accepted observation, age, thresholds and freshness through the shared contract in [plan.md](plan.md).
- Build the Twin panel with clear CURRENT, DELAYED and MISSING states and an empty state.
- Test that real backend updates appear and invalid messages do not update the panel. Coordinate shared API changes with Nancy.

## Not assigned
Sensor generation, encryption/decryption and key/connection management.

## Local implementation and preview (2026-11-05)

The preview now uses a responsive dashboard layout with large measurement and
age values, colour-coded status, plain-language state explanations, and a
three-step demonstration guide. No external fonts or frontend dependencies are
required. Refresh the page after restarting the preview server to see changes.

Run from the `q-twinsecure` folder:

```powershell
python -m digital_twin.preview
```

Open http://127.0.0.1:8765. Click **Send new sample reading**. The panel
shows CURRENT initially, DELAYED after 5 seconds, and MISSING after 15 seconds.
Click again to demonstrate recovery. Ctrl+C stops the server. This is an
independent component preview with local samples, not the integrated experiment.
The displayed value comes from the real Python monitor; the browser polls it.

Other commands:

```powershell
python -m digital_twin.demo
python -m unittest discover -s tests -p 'test_twin*.py' -v
node --test tests/test_twin_panel.cjs
```

`TwinMonitor(current_threshold=5, missing_threshold=15, clock=...)` exports the
agreed update/freshness/status methods. Defaults are demonstration settings,
not finalized experiment thresholds. Age uses observation time, and receive
time is stored separately. The injected clock, `now`, and `received_at` use
timezone-aware datetime objects; reading timestamps use ISO-8601 strings.

Use one monitor per sensor. Invalid, future, or older observations raise
ValueError without changing the previous valid observation. Equal timestamps
are allowed. CO2 values must be finite, non-negative numbers. Clocks are assumed
synchronized. The gateway must authenticate before passing readings to the Twin.

### Nancy integration handoff

Load `/twin-panel.js` from `web/twin-panel.js` and call:

```javascript
const panel = mountTwinPanel(document.getElementById('twin'));
panel.update(apiStatus.twin); // runner supplies monitor.get_status(now)
// On API failure:
panel.disconnected();
```

The component owns only its supplied container. It does not fetch data or
simulate time. Nancy's app owns polling, shared controls, and API actions.
Status fields: `sensor_id`, `value_ppm`, `timestamp`, `received_at`,
`age_seconds`, `freshness`, `current_threshold`, `missing_threshold`.
Observation fields are null before the first reading. `panel.update(null)`
also renders an empty state. No shared API was changed.

Verified locally: 10 Python tests and 1 JavaScript DOM-harness test passed.
Browser visual review, shared-runner integration, and authenticated-message
rejection through the complete pipeline remain pending. The preview is not a
replacement for Nancy's runner. Stop here for the
component review before end-to-end integration, as required by `plan.md`.
