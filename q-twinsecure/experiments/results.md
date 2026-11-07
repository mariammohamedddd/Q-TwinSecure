# Verification results

## Current Twin integration results (2026-11-07)

Local MARIAM_WAEL branch, existing venv: Python 3.13.3, cryptography 50.0.2.
These results supersede older null-component checkpoints below.

- 71 Python tests passed, including real HTTP and integrated Twin scenarios.
- 4 Twin/shared-app + 1 gateway JavaScript tests passed; Twin rendering uses real runner
  snapshots and preserves the accepted display after tampering.
- Existing sensor JavaScript tests passed four check groups.
- Evidence: evidence/twin-python-tests.txt, evidence/twin-javascript-tests.txt,
  evidence/twin-scenarios.json. Tests disable automatic supply for determinism.

| Automated scenario | Keys available | Connection | Delivered | Freshness | Result |
| --- | ---: | --- | ---: | --- | --- |
| Normal | 0 | CONNECTED | 1 | CURRENT | Pass |
| Interrupted, old epoch active | 0 | CONNECTED | 2 | CURRENT | Pass |
| New epoch without key | 0 | DISCONNECTED | 2 | CURRENT initially | 409 as expected |
| Advance experiment clock to 6s | 0 | DISCONNECTED | 2 | DELAYED | Pass |
| Advance to 16s | 0 | DISCONNECTED | 2 | MISSING | Pass |
| Recovery | 0 | CONNECTED | 3 | CURRENT | Pass |
| Reset | 0 | DISCONNECTED | 0 | MISSING, no observation | Pass |

Additional checks reject tampered and authenticated-but-invalid observations
without changing Twin status or delivered count. Browser visual/interactions
review is NOT VERIFIED: browser host unavailable and native Chrome minimized.
Shared-file review and presenter acceptance remain pending. No screenshots or
team phase acceptance are claimed. Changes are uncommitted.

## Historical Nancy foundation results


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
