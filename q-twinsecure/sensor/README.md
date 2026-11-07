# CO2 sensor simulator

From the `q-twinsecure` directory (Python 3.10+, standard library only):

```powershell
python -B -m sensor.demo
python -B -m unittest discover -s tests -p test_sensor.py -v
```

The demo prints five JSON readings using fixed values and live UTC timestamps.
`CO2SensorSimulator().read()` returns one shared-contract dictionary;
`read_many(count)` returns a list. Configure `sensor_id`, `min_ppm`, `max_ppm`,
`seed`, `values`, and an optional timezone-aware `clock` callable. Fixed values
cycle in order and must be within the inclusive configured range. Seeded random
values and injected clocks allow repeatable experiments. Equal bounds are valid.
Invalid configuration, counts or clock results raise `ValueError`.

`get_status()` returns a copy of the latest generated reading, or `None` before
any reading. Nancy can place this directly in the planned API's `sensor` field.
Calling status does not generate data. Batch reads are immediate; scheduling
belongs to the runner. This simulator performs no transmission, protection,
key allocation or freshness calculation, and models no physical sensor.

The shared experiment runner/API do not yet exist. The sensor panel now has
its own standalone preview, using real data from this Python simulator.

Verified locally on 2026-11-05 with Python 3.14: 10 tests passed and the demo
printed five readings. On this Windows setup, `python` is a Store alias; use:

```powershell
py -3.14 -B -m sensor.demo
py -3.14 -B -m unittest discover -s tests -p test_sensor.py -v
```

## Sensor dashboard

From `q-twinsecure/`, start the local preview:

```powershell
py -3.14 -B -m sensor.dashboard
```

Open **http://127.0.0.1:8765**. Stop with Ctrl+C. If the port is busy, use
`py -3.14 -B -m sensor.dashboard --port 8766` and open that port instead.
No packages, internet connection or build step are required.

The responsive navy/mint panel includes decorative sensor drawings, the latest
CO2 value, sensor ID, UTC timestamp, a chart of the last 30 observed samples,
and min/max values for that chart. The page polls every two seconds. Its data
comes from `CO2SensorSimulator`, not generated browser values. The range marker
shows the preview simulator's 400–1000 ppm range; it is not a health indicator.
Samples are produced on status requests, at most once per two seconds. This is
an independent sensor preview, not the integrated secure-delivery experiment.

The panel shows connecting, awaiting-reading, receiving, invalid-data and
disconnected states. During a disconnect the current value is hidden; the
timestamp and history describe previously observed readings. Polling retries
automatically. History is local to the current page and clears on reload or
when the API returns `sensor: null`.

### Nancy's integration

The owner-specific files are `web/sensor-panel.js` and `web/sensor-panel.css`.
Import the module and place `<co2-sensor-panel></co2-sensor-panel>` in the shared
page. The element loads scoped styles automatically. Pass the existing shared
status into the panel; no extra poller is necessary if the runner already polls:

```javascript
import './sensor-panel.js';
const panel = document.querySelector('co2-sensor-panel');
panel.update(status.sensor); // shared-contract reading or null
// On a failed status request:
panel.unavailable();
```

Alternatively, import `startSensorPolling` and call `startSensorPolling(panel)`
against the shared `/api/status`; it returns a function that stops polling.
The sensor-only preview implements just GET status and static assets. It does
not replace Nancy's main runner, actions, shared shell or other owners' panels.

### Verification

```powershell
py -3.14 -B -m unittest discover -s tests -p 'test_sensor*.py' -v
node tests/test_sensor_panel.mjs
```

13 Python tests passed (including HTTP asset serving, backend data agreement,
sample rate limiting and unknown-route rejection). Four JavaScript check groups
passed for validation, rendering, chart bounds, reset, disconnection, recovery
and polling cleanup using a minimal DOM adapter. These are not browser rendering
tests. Browser appearance, responsive layout and integration with Nancy's runner
still require manual verification. To check recovery, stop the preview, wait for
Disconnected, then restart it and confirm readings resume.
