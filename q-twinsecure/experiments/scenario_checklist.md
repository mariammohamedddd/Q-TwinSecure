# Integrated demo: run and review

From the repository root in PowerShell:

```powershell
cd q-twinsecure
py -B main.py
```

Open http://127.0.0.1:8000. Use `--port 8001` if occupied. Restart the server after code updates and refresh the page. Ctrl+C stops it. Dependencies: Python and cryptography (install using `py -m pip install -r q-twinsecure-docs/requirements.txt` if missing).

The shared dashboard loads the existing key, sensor, gateway and Twin panels. Standalone owner previews remain available for independent testing; they do not need to run alongside main.py.

## Demonstration configuration

- Real QKDKeyPool, capacity 10 pairs, `auto_generate=False` for repeatability. Click Generate keys explicitly; interruption/resumption changes generation availability. The independent key-pool preview still uses automatic supply.
- Manual experiment clock, starting at the UTC time of reset/start. Wall-clock waiting does not age the Twin. Advance time explicitly; sensor timestamps and Twin queries use the same clock.
- Fixed sensor sequence: 650, 700, 680 ppm, repeating.
- Twin thresholds: CURRENT when age <= 5 seconds; DELAYED when 5 < age <= 15; MISSING when age > 15 or no accepted observation.
- Clock advancement: 1–3600 integer seconds per request, maximum total 86400. Reset recreates the pool, sensor, Twin and clock; closes the active epoch, clears counts/history, and adds a reset event.

## Presenter sequence

1. Reset. Generate exactly **1** key pair, start an epoch, send two readings. Expect generated=2, delivered=2, keys consumed=1, CURRENT.
2. Interrupt supply and send another reading. Expect connected, delivered=3, consumed still 1. The existing epoch remains usable.
3. End epoch. Pool should be empty. Click Start epoch: expect a visible no-key error and disconnected gateway. Send reading is disabled. Direct requests also reject sends without an epoch.
4. Advance time by **6** seconds: DELAYED. Advance another **10** seconds: MISSING. Delivered remains 3; the last accepted observation stays visible.
5. Resume supply, generate **1** key pair, start an epoch and send a reading. Expect consumed=2, delivered=4, CURRENT with a new epoch ID.
6. Reset and repeat from an empty pool.

If more than one pair was generated, interruption can leave buffered keys available for new epochs. That is expected; reset and seed exactly one for the empty-pool demonstration.

Tampering is verified through automated tests, not a dashboard mutation button. The tests modify a protected message and confirm rejection without updating the Twin or delivery count. Status and events contain no keys, nonce, ciphertext or plaintext secret payloads.

## Checks

```powershell
py -B -m unittest discover -s tests -v
$env:PYTHON = 'py'
node --test tests/test_gateway_panel.mjs tests/test_sensor_panel.mjs tests/test_twin_panel.cjs
node --check web/app.js
```

## Browser review pending

- [ ] All four owner panels load with no browser console errors.
- [ ] Run the presenter sequence and compare displayed values/counts with the expectations.
- [ ] Invalid inputs show errors and never change state unexpectedly.
- [ ] Controls prevent duplicate requests while an action is pending.
- [ ] Stop server: all panels show unavailable/disconnected; controls disable. Restart: reconnects with clean state.
- [ ] Verify reset clears sensor chart and Twin observation, and check narrow-window/keyboard usability.
- [ ] Capture safe screenshots and record actual presenter results under evidence/.
- [ ] Team reviews Phase 3 before presentation rehearsal and final evidence work.

HTTP integration and isolated panel tests do not establish visual/browser acceptance. No browser automation tool was available in this session. This is a local in-memory software model using classical randomness and direct AES-GCM; no physical QKD, TLS, production replay protection or guaranteed secure memory erasure is claimed.
