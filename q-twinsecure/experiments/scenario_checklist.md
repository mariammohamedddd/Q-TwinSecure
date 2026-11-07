# Nancy's local dashboard — Phase 2

From the repository root in PowerShell:

```powershell
cd q-twinsecure
py -B main.py
```

Open http://127.0.0.1:8000. If occupied, use `py -B main.py --port 8001` and the printed URL. Stop with Ctrl+C. Restart after code changes; the old server does not reload automatically. The control runner needs only Python's standard library; gateway tests need `cryptography`.

## Automated checks

```powershell
py -B -m unittest discover -s tests -v
node --check web/app.js
```

## Phase 2 review checklist

Phase 1 was reported working by Nancy on 2026-11-07. The following checks cover the new controls:

- [ ] Open the page; confirm Phase 2 and the runner-connected message.
- [ ] Advance the clock by 5 seconds twice; confirm 10 seconds and two success events.
- [ ] Reset; confirm 0 seconds and only the new reset event.
- [ ] Confirm all component actions remain disabled, with unavailable reasons on hover.
- [ ] Confirm the sensor starts empty, advance_time generates one reading with the experiment timestamp, and reset clears it. Other components and delivery remain unavailable.
- [ ] Enter an invalid time step; confirm it cannot advance the clock.
- [ ] At the cumulative clock limit of 86400 seconds, try advancing again; confirm a visible action error. Reset and try again to confirm recovery.
- [ ] Stop the server; confirm disconnected state and disabled controls. Restart; confirm automatic reconnection and clean in-memory state.
- [ ] Check a narrow window, keyboard controls, and visible focus indicators.

Browser rendering, duplicate-click prevention and disconnected behavior are implemented but not browser-automated. HTTP tests cover API validation and server lifecycle. Do not treat manual checks above as passed until performed.

## Owner handoff and review gate

Nancy owns `main.py`, the shared HTML/CSS/JavaScript, API, controls and event area. Domain owners retain their component directories and panel files: Marwan `web/key-panel.js`, Mariam Mohamed `web/sensor-panel.js`, Kareem `web/gateway-panel.js`, Mariam Wael `web/twin-panel.js`. The existing panel IDs remain `key-panel`, `sensor-panel`, `gateway-panel`, `twin-panel`.

Current checkout includes independent sensor, key pool, gateway and Twin components. The sensor is wired into the shared runner: advance_time generates one reading, status exposes it, and reset clears it. The shared page updates the sensor panel using its existing polling loop. Other component status and delivery remain unavailable. The isolated gateway component tests do not establish shared secure-delivery integration. See INTERFACE_CONTRACT.md and IMPLEMENTATION_STATUS.md for current verification.

Each owner must run their independent demo and focused tests, expose safe status, and implement/test their panel. When those are ready, agree shared wiring with Nancy. Do not begin Phase 3 epoch establishment or reading delivery until the Phase 2 team review gate passes.

## Later scenario acceptance (not executed)

| Step | Expected evidence |
| --- | --- |
| Normal | Generate one key, establish epoch, deliver multiple verified readings; one key consumed and Twin CURRENT. |
| Interrupted, epoch active | Interrupt generation; readings still arrive over the existing epoch. |
| Epoch ended, pool empty | New epoch fails; no additional readings delivered; controlled clock yields DELAYED then MISSING. |
| Recovery | Resume supply, generate a key, establish a new epoch, deliver a reading; Twin CURRENT. |

Record actual commands, configuration and results; verify no key material appears. Direct AES-GCM is a PoC simplification. Software-emulated QKD uses classical randomness, not physical quantum communication.
