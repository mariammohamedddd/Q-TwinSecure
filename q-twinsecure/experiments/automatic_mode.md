# Q-TwinSecure — automatic monitoring

From the repository root:

```powershell
cd q-twinsecure
py -B main.py --automatic
```

The earlier command `py -B main.py --automatic-key-supply` now aliases the same complete automatic mode. Stop any older server with Ctrl+C before restarting. Open http://127.0.0.1:8000 and press Ctrl+F5. Use `--port 8001` if your old server still occupies port 8000.

## What happens without clicking

- Keys replenish in the background every 1 second, up to 3 buffered pairs by default.
- The runner waits for a key and establishes an epoch automatically.
- Sensor readings are generated every 2 seconds, authenticated with the epoch's matching keys and forwarded to the Twin only after verification.
- Epochs last 10 seconds and renew with a fresh allocation. Multiple readings reuse one epoch allocation.
- One monotonic real-time clock drives UTC sensor/receive timestamps, observation age and epoch lifetime. The display refreshes every second. Measurement age grows between readings and resets when a fresh reading is accepted.
- Sampling and delivery continue when the browser is closed. Polling does not drive the worker.
- If no key is available, sampling continues but delivery does not; the runner retries automatically. No unprotected reading reaches the Twin.

## Presenter controls

In Experiment controls or the factory view's controls disclosure:

- **Interrupt supply:** stops new key generation, preserving the active epoch and buffered keys. Delivery continues until renewal exhausts available allocations. Then the gateway waits for keys and the Twin becomes DELAYED after 5 seconds and MISSING after 15 seconds since its last observation.
- **Resume supply:** replenishment restarts; the runner reconnects and delivers automatically. Twin returns to CURRENT.
- **Stop monitoring:** pauses sensor sampling/delivery and closes the epoch. Key supply and the real clock continue, so measurement age grows. **Start monitoring** resumes connection/sampling automatically.
- **Reset experiment:** clears all components, observations, counters, clock origin and events, then automatically resumes monitoring. The worker is reused; the old key worker is stopped.

Generate keys, start/end epoch, send reading and advance time are managed internally and hidden in automatic mode. Their direct API requests return 409. They remain available in manual mode (`py -B main.py`).

To demonstrate interruption quickly, use a small pool:

```powershell
py -B main.py --automatic --pool-capacity 1
```

With one buffered pair, interruption may still permit another epoch. Wait for the active/buffered allocations to expire before expecting delivery to stop. The controls show epoch lifetime and remaining time. You can use Stop monitoring to observe real-time aging immediately, independently of key exhaustion.

## Configuration

```powershell
py -B main.py --automatic --reading-interval 2 --epoch-duration 10 --pool-capacity 3 --key-interval 1 --current-threshold 5 --missing-threshold 15
```

Intervals must be finite positive numbers; thresholds require 0 <= current < missing. Manual mode defaults to capacity 10; automatic CLI defaults to capacity 3. Reset preserves mode, capacity, intervals and thresholds. The fixed sensor sequence remains 650/700/680 ppm for a reproducible software demonstration.

## Verification

```powershell
py -B -m unittest discover -s tests -v
$env:PYTHON = 'py'
node --test tests/test_gateway_panel.mjs tests/test_sensor_panel.mjs tests/test_sensor_shared.mjs tests/test_twin_panel.cjs tests/test_twin_app.cjs
```

Current results: 85 Python tests and 7 Node test entries passed. Nine new automatic-monitor tests cover background progression without requests, real-time aging, active-epoch survival, renewal/exhaustion/recovery, stop/start, reset, tampering, failure visibility, configuration and worker shutdown. Browser snapshots also confirmed active automatic controls and an aged DELAYED Twin. Full interactive/mobile presenter review remains pending.

This is still software-emulated QKD key supply using classical randomness and direct AES-GCM, not physical QKD, TLS, or production monitoring. Threads are local/in-memory and stop with the process. If an unexpected scheduler error occurs, it stops sending and reports a safe error; reset is required to recover. Keys and exception payloads are not exposed.
