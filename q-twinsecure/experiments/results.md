# Verification results

2026-11-07, branch Nancy, Python 3.14.3.

- `py -B -m unittest discover -s tests -p test_dashboard.py -v`: PASS, 5 tests. Real HTTP requests verified page/assets, null component status, disabled controls markup, explicit unavailable actions, restricted file routes and loopback binding. Server shut down during test teardown.
- `py -B -m unittest discover -s tests -p test_gateway_crypto.py -v`: PASS, 6 existing gateway tests.
- `py -B -m unittest discover -s tests -v`: PASS, 11 tests. `node --check web/app.js`: PASS. `git diff --check`: PASS (line-ending conversion warnings only).
- Browser visual review, loading/disconnected rendering, presenter Ctrl+C and team ownership/contract confirmation: NOT VERIFIED; checklist prepared.

| Scenario | Keys available | Connection state | Readings delivered | Twin freshness | Result |
| --- | --- | --- | --- | --- | --- |
| Normal | — | — | — | — | Not run |
| Interrupted, old epoch active | — | — | — | — | Not run |
| New epoch, no key | — | — | — | — | Not run |
| Recovery | — | — | — | — | Not run |

Phase 1 is a shell, not an end-to-end experiment. No physical QKD or TLS implementation is claimed. No screenshots or integrated results have been captured.


## Phase 2 — Nancy's controls (2026-11-07)

- User reported Phase 1 working and authorized Phase 2.
- `py -B -m unittest discover -s tests -v`: PASS, 16 tests (10 dashboard/state, 6 unchanged gateway).
- `node --check web/app.js`: PASS.
- HTTP checks exercised reset, repeated clock advancement, malformed/invalid/oversized requests, cross-origin rejection, unavailable domain actions, static routing and real loopback server startup/shutdown.
- State checks exercised 86400-second clock limit, reset recovery and 100-event retention.
- Phase 2 visual/browser interaction review: pending; see scenario_checklist.md.
- No integrated sensor/key-pool/Twin results, owner panel acceptance or end-to-end scenarios claimed. Phase 2 team gate remains pending owner work.

## Gateway runner coordination — 2026-11-07

`py -B -m unittest discover -s tests -v`: PASS, 39 tests. JavaScript syntax checks for app.js and gateway-panel.js passed. With `$env:PYTHON = 'py'`, `node --test tests/test_gateway_panel.mjs tests/test_sensor_panel.mjs`: PASS, both files. Runner tests exercise Kareem's actual crypto/status code with a test-only matching key provider, including HTTP lifecycle/status/module loading. Default runner still has no real key provider. Browser review and end-to-end Twin evidence remain pending.

## Latest main merge verification — 2026-11-07

Merged origin/main d846b6d into Nancy, retaining runner coordination and including Kareem's actual sensor/gateway/Twin rejection test. Full Python suite: 50 passed. JavaScript gateway, sensor and Twin test files: 4 test entries passed. Shared app/gateway module syntax checks passed. Actual key-pool integration and browser review remain pending.

## Current integrated-runner results — 2026-11-07

All older unavailable/not-run entries above are historical. The following results use the real components in Nancy's integrated runner after merging Kareem PR #5.

- Full Python suite: `py -B -m unittest discover -s tests -v` — 69 passed.
- With `$env:PYTHON = 'py'`, `node --test tests/test_gateway_panel.mjs tests/test_sensor_panel.mjs tests/test_twin_panel.cjs` — 4 test entries passed.
- `node --check web/app.js` and `node --check web/key-panel.js` — passed.
- API story tested over real loopback HTTP with capacity 10, manual generation, fixed readings and one shared clock (thresholds 5/15 seconds):

| API checkpoint | Available keys | Consumed pairs | Delivered | Freshness | Result |
| --- | ---: | ---: | ---: | --- | --- |
| Generate 1, start epoch, send 1 | 0 | 1 | 1 | CURRENT | PASS |
| Interrupt supply, send on active epoch | 0 | 1 | 2 | CURRENT | PASS |
| End epoch, request new epoch | 0 | 1 | 2 | CURRENT until time advances | 409 as expected |
| Advance 6 seconds | 0 | 1 | 2 | DELAYED | PASS |
| Advance another 10 seconds | 0 | 1 | 2 | MISSING | PASS |
| Resume, generate 1, start epoch, send | 0 | 2 | 3 | CURRENT | PASS |
| Reset | 0 | 0 | 0 | MISSING; no observation | PASS |

Tampering and invalid Twin readings leave observation/delivery count unchanged; repeated protected readings use one pool allocation; buffered keys survive interruption; pool capacity is respected. Status checks exclude key bytes and protected envelope fields.

Browser visual acceptance, console/network inspection in an actual browser, screenshots and team presenter rehearsal remain pending. HTTP and isolated panel tests do not establish those checks. No browser automation tool was available. The presenter checklist uses two initial readings (one more than this automated scenario) and consequently expects final delivered=4.
