# Manual mode — exact run and verification guide

Stop any running server with Ctrl+C. From PowerShell:

```powershell
cd "C:\Users\nancy\Desktop\Graduation project\Q-TwinSecure\q-twinsecure"
py -B main.py
```

Open http://127.0.0.1:8000, press Ctrl+F5, and select **Experiment controls**.
No automatic/presentation flag is used. The page must say **Manual demonstration**.
Time, generation, sending and epoch changes happen only when you click their controls.

| Step | Action | Expected result |
| --- | --- | --- |
| 1 | Reset | Empty pool, disconnected gateway, zero readings, Twin MISSING with no observation. |
| 2 | Generate 1 key pair | Available=1, generated=1, consumed=0. |
| 3 | Start epoch | Connected with epoch ID; available=0, consumed=1. |
| 4 | Send reading twice | Latest value=700 ppm; delivered=2, consumed still 1, Twin CURRENT. |
| 5 | Interrupt supply, send reading | Latest value=680 ppm; delivered=3, same epoch, consumed still 1. |
| 6 | Try Generate keys | Error: supply interrupted; no new pair. |
| 7 | End epoch, then Start epoch | Expected no-key error; gateway stays disconnected, Send reading disabled. |
| 8 | Advance time by 6 seconds | Twin DELAYED; delivered stays 3. |
| 9 | Advance another 10 seconds | Twin MISSING at age 16s; last accepted value remains 680 ppm. |
| 10 | Resume supply, generate 1, start epoch, send | New epoch, value=650 ppm, delivered=4, consumed=2, CURRENT. |
| 11 | Open Factory view | Same backend observation/counters; expanding Experiment controls allows the same operations. |
| 12 | Reset | Keys/readings/clock/epoch/observation clear; sensor chart clears. |

**The clock staying still is expected in manual mode.** Advance time controls observation age. Use --automatic for real-time continuous monitoring, or --presentation for the scenario walkthrough.

The key pool is bounded at 10 in default manual mode; generating extra keys leaves buffered pairs usable even after supply interruption. Generate exactly one pair for the empty-pool scenario. Invalid counts/time steps and invalid actions are rejected. Tampering is tested through backend tests and demonstrated visibly by presentation mode.

## Verification performed on 2026-11-07

- Complete Python suite: 89 passed, covering all modes and component tests.
- Six Node test files: 8 entries passed; app.js syntax passed.
- Real Chrome CDP walkthrough: 9 check groups passed for manual controls, separate navigation, visible validation/failure errors, real reading delivery, interruption, freshness transitions, recovery, factory-state sharing/reset, 390px layout/control operation and no unexpected browser JavaScript exceptions (layout/no-exceptions are recorded separately in the console output).
- Server stop: real page detected disconnection and disabled controls.
- Server restart: same page reconnected automatically to clean manual state.
- Screenshot reviewed: evidence/manual-browser-mobile.png.

The browser script is `tests/browser_manual_review.mjs`. It uses a separate loopback manual server at 18945 and a headless Chrome debugging endpoint at 18946 by default (override REVIEW_APP/REVIEW_BROWSER). It operates its own test page/server state and uses actual browser controls, API, component snapshots and rendering. --expect-offline and --expect-reconnected check the retained page across test-server stop/restart. No external package installation is required.

All executed checks passed on this machine. This establishes tested behavior, not proof against every untested environment or failure. The software model/security limitations in the project documentation still apply.
