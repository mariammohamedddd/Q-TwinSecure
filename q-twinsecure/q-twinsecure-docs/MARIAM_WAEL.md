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

The local preview now opens in an immersive full-window factory view. Details
are overlaid on the scene. Zoom buttons or the mouse wheel adjust magnification
between 50% and 300%; drag the model to rotate, or use the rotation buttons.
Reset view restores angle and zoom. Information panels scroll independently.
Nancy can opt into this layout with `mountTwinPanel(root, {fullScreen:true})`;
the default embedded panel remains available for shared-dashboard integration.

The panel includes an interactive CSS 3D factory model with a red glowing sensor
marker. Rotate left, rotate right and reset controls change the model's view.
Machines, crates and walls have separate 3D faces; no external model library is
required. This marker is decorative and never represents a safety alarm or live
physical location. Details sit alongside the floor plan on wide screens and
stack on smaller screens. Measurement and receive timestamps use a readable
date/time with the browser's local timezone; hover to inspect the original
ISO timestamp. Backend timestamps and freshness calculations are unchanged.

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

Load `/twin-panel.css` and `/twin-panel.js` from `web/`, then call:

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
also renders an empty state. The shared integration is documented below.

## Shared integration completed locally (2026-11-07)

The shared runner now uses the real sensor, key pool, gateway and Twin. The
integration adapter is `digital_twin/integration.py`; Nancy's API, action
validation, loopback binding and CSP are retained. The dashboard mounts the Twin
panel and updates it from `status.twin`. `/twin` uses the same runner/API with
an immersive factory view. The independent `python -m digital_twin.preview` command is
still sample-only and is not the shared demonstration.

From `q-twinsecure`, use the existing environment (cryptography is required):

```powershell
.\venv\Scripts\Activate.ps1
python main.py
```

Open http://127.0.0.1:8000 for the shared dashboard, or
http://127.0.0.1:8000/twin for the factory. In factory view, expand
**Experiment controls** in the information panel. The panel uses an external
stylesheet; no weakening of Nancy's CSP is required.

For a repeatable manual-key demo:

```powershell
python main.py --manual-key-supply --current-threshold 5 --missing-threshold 15
```

1. Reset; generate **1** key; start an epoch; send a reading: CURRENT.
2. Send another reading: consumed-key count stays **1**.
3. Interrupt supply; send another reading: existing epoch still delivers.
4. End epoch: no key remains, so starting another epoch is unavailable. Direct
   API requests return 409; sending without an epoch also fails.
5. Advance by **6** seconds: DELAYED. Advance by another **10**: MISSING.
6. Resume supply; generate one key; start epoch; send a reading: CURRENT again.
7. Reset: observation clears, counts return to zero and the old epoch is gone.

In default mode keys refill automatically on wall time. Observation age uses
Nancy's paused experiment clock, so waiting in the browser does not age the
observation: press **Advance time**. Reset closes the old key worker. The key
pool must be empty to demonstrate failed new-epoch establishment.

### Validation and remaining acceptance

- All **71 Python tests** passed using the existing venv (Python 3.13.3).
- **4 Twin/shared-app JavaScript tests + 1 gateway panel test** passed with the venv on PATH;
  the existing sensor panel's four check groups also passed.
- Real-runner checks cover repeated readings on one key, interruption, empty
  pool, recovery, reset, custom thresholds and HTTP status/actions.
- Tampered ciphertext and authenticated but invalid readings are rejected
  before updating Twin state/delivery counts. The JavaScript test renders real
  backend snapshots and verifies the previous display survives tampering.
- Evidence: `evidence/twin-python-tests.txt`, `evidence/twin-javascript-tests.txt`,
  `evidence/twin-scenarios.json`. These are automated evidence, not screenshots.

Remaining: browser visual/interactions review (desktop/mobile, zoom/rotation,
empty/disconnected/recovery and no overlaps), then Nancy/team review of shared
hooks. Browser automation was attempted but its browser host was unavailable;
the native Chrome fallback could not inspect the minimized window. No browser
acceptance or presentation rehearsal is claimed. Changes are local/uncommitted.
Stop here for review rather than declaring the team-wide phase accepted.
