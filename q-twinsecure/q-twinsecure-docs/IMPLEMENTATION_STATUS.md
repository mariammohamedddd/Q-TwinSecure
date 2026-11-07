# Implementation Status

Last updated: 2026-11-07

This file distinguishes **reported setup**, **drafted code**, **verified implementation**, and **not started**. Update it whenever the repository changes.

## 1. Environment and setup

| Item | Status | Evidence / notes |
|---|---|---|
| Windows + PowerShell development environment | Reported | Terminal screenshots/text show PowerShell. |
| Python virtual environment | Reported active during installation | Prompt displayed `(venv)`. Re-activate after opening a new terminal. |
| `cryptography` package | Installed successfully | Terminal output: `Successfully installed ... cryptography-50.0.2`. |
| Repository folder | Partially confirmed | User created/entered a folder named `q-twinsecure`; confirm final repository root and naming. |
| Project subfolders and files | Not yet verified | Commands were provided; user has not yet confirmed final Explorer structure. |

## 2. Component status

| Component | Status | Notes |
|---|---|---|
| CO₂ sensor simulator | Not started | |
| Emulated QKD key pool | In progress | Automatic interval-based supply, backend and demo verified locally on branch `Marwan`: 16 pool tests passed. Hard capacity rejects extra keys without replacing stored records. Changes are uncommitted; shared integration remains outstanding. See `qkd/README.md`. |
| Device gateway | In progress | Standalone encryption implemented and tested locally; integration not started. |
| Twin gateway | In progress | Standalone decryption implemented and tested locally; integration not started. |
| AES-GCM protection | In progress | Standalone demo and tests passed locally; end-to-end integration remains outstanding. |
| TLS 1.3 external PSK | Not started | Optional for this small PoC; do not claim it is implemented. |
| Digital Twin freshness logic | Not started | |
| Main end-to-end flow | Not started | |
| Automated tests | In progress | Six standalone gateway tests previously passed locally. On 2026-11-07, 20 Marwan tests passed (16 pool and four preview API tests); integrated tests remain outstanding. |
| Normal/interruption/recovery experiment | Not started | |
| ML anomaly detection | Out of current PoC scope | Broader research direction only. |
| LLM explanations | Out of current PoC scope | Broader research direction only. |
| Physical QKD / physical sensor | Out of current PoC scope | |

## 3. Definition of "implemented"

A feature may be marked **Implemented and tested** only when:
1. Its code is committed to the repository.
2. It runs in the documented environment.
3. Its expected behavior has been checked manually or by an automated test.
4. Any limitations are documented.

Use these status labels:
- `Not started`
- `In progress`
- `Drafted — not verified`
- `Implemented — not tested`
- `Implemented and tested`
- `Blocked`
- `Out of PoC scope`

## Planned dashboard status

The committee dashboard, shared API and integrated scenario runner remain planned
in [plan.md](plan.md). Marwan's `web/key-panel.js` and independent real-pool preview
exist locally; preview API tests passed, but interactive browser verification and
shared dashboard integration are outstanding. Other owner panels have not been
verified here. Existing component status and the local gateway evidence remain
separate.

## 4. Update log

- 2026-11-07: Verified hard capacity per endpoint, including zero additions at capacity with no key generation or replacement. Added `--capacity` to the preview and separate endpoint occupancy/full-state rendering. `python -B -m unittest discover -s tests -p 'test_key*.py' -v` passed 20 tests; `python -B -m qkd.panel_demo --help` exposes the capacity option. UI changes have not been visually verified.
- 2026-11-07: At the user's request, changed supply to automatic generation by default (one pair per second, configurable). Worker respects capacity, refills freed slots, pauses on interruption and resumes without manual generation. Added synchronized operations and worker shutdown; removed the preview Generate action/button. `python -B -m unittest discover -s tests -p 'test_key*.py' -v` passed 18 tests; `python -B -m qkd.demo` demonstrated automatic initial fill/recovery and exited successfully. Browser verification and shared integration remain outstanding. See D-007.
- 2026-11-07: Marwan's bounded matching FIFO key pools, `secrets.token_bytes(32)` generation, interruption/resumption, safe counters, independent terminal demo, key panel and local preview were added on branch `Marwan`. Python 3.13.4: `python -B -m unittest discover -s tests -p 'test_key*.py' -v` passed 12 tests. `python -B -m qkd.demo` exited successfully with generated=3, consumed=3, available=0. Preview startup succeeded on `127.0.0.1:8765`. Browser verification stopped because computer use could not determine Edge's current URL confidently enough to enforce policy; visual/loading/disconnected behavior remains unverified. Changes are not committed. No integrated connection or freshness experiment was performed.
- 2026-11-05: Kareem's standalone AES-GCM gateway is implemented on branch `kareem`. With Python 3.12 and cryptography 48.0.1, `python -B -m unittest discover -s tests -p test_gateway_crypto.py -v` passed 6 tests, and `python -B -m gateway.demo` recovered a sample reading and rejected modified ciphertext. These checks do not establish end-to-end integration.
- 2026-11-05: Python virtual environment and `cryptography` installation reported successful.
- 2026-11-05: Initial PoC folder structure and key-pool design discussed. Actual files and execution still need confirmation.
