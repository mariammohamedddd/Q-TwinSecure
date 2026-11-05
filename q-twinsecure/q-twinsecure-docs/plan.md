# Committee demo — integrated implementation plan

## Goal and decisions

Build one local, browser-based dashboard showing the real Python proof of concept, from a simulated CO₂ reading through authenticated encryption to Digital Twin freshness. Each member owns both backend work and a visible frontend contribution. The dashboard and integration described here are **planned**, not existing functionality.

- Use the existing Python project, a small standard-library local HTTP server and plain HTML/CSS/JavaScript; avoid a separate frontend framework, database or new dependency unless the team later agrees it is needed.
- Use one in-memory application state owned by a single runner. Serve the page and API from the same local origin; bind to `127.0.0.1` only. This is a local demonstration, not production hosting.
- The key service is a classical software emulator, and direct AES-GCM is a PoC simplification, not physical QKD or TLS. Never expose key material in API responses, browser state, logs or evidence.
- Fresh key material is consumed for a new connection epoch, not each reading. An interruption stops new supply, not an existing epoch; an empty pool is required to demonstrate failed establishment.
- Each member may build and test their component independently with local samples. A finished integrated panel must use real runner state, not hard-coded or simulated frontend values. Temporary teammate-interface stubs must be clearly marked and removed before integration acceptance.
- Do one phase at a time and stop for team review before starting the next. Each owner fixes their own component and panel. Nancy coordinates shared files and interface changes; no database schema is planned.

## Ownership and proposed files

| Owner | Backend | Frontend | Proposed owner-specific files |
|---|---|---|---|
| Marwan | Key pool, safe status and supply operations | Supply state and generated/available/consumed counts | `qkd/`, `web/key-panel.js` |
| Mariam Mohamed | Sensor simulator and safe reading status | Sensor value, ID and timestamp | `sensor/`, `web/sensor-panel.js` |
| Kareem | AES-GCM protection, verification and safe gateway status | Epoch/connection and message verification | `gateway/`, `web/gateway-panel.js` |
| Mariam Wael | Twin state, configurable freshness and age | Latest accepted reading, age and freshness | `digital_twin/`, `web/twin-panel.js` |
| Nancy | Runner, local API, scenario execution, validation and evidence | Shared page, scenario controls, event/result area | `main.py`, `web/index.html`, `web/app.js`, `web/style.css`, `experiments/` |

These paths are a proposed coordination convention, not a claim they already exist. Nancy owns shared runner, API, page and common styles; panel owners own their files and coordinate shared edits. Each owner adds focused tests for their own work. Nancy maintains the integration tests and run instructions with input from owners.

## Proposed integration contract

Keep the existing sensor and component interfaces in `INTERFACE_CONTRACT.md`. The runner serializes access to state, supplies matching key material internally to the two endpoints, and passes only successfully decrypted readings to the Twin. If an owner needs an interface change, agree on it and update the contract before implementation.

The same-origin local API should expose:

- `GET /api/status`: JSON containing `scenario`, safe `key_pool` (supply enabled and generated/available/consumed counts), `sensor` (latest generated reading or null), `gateway` (connection state, non-secret epoch ID or null, latest verification outcome), `twin` (latest accepted reading or null, observation age, configured thresholds and freshness), and generated/delivered counts. Include a bounded, non-secret event list with timestamps and clear failure reasons.
- `POST /api/actions`: accept one documented action at a time: `reset`, `generate_keys`, `interrupt_supply`, `resume_supply`, `start_epoch`, `end_epoch`, `send_reading`, or `advance_time`. Return updated status or a clear error; reject invalid actions and inputs. Use a controllable experiment clock for deterministic freshness transitions, including sensible bounds. Do not expose arbitrary file or command operations.
- The browser periodically refreshes status and sends actions through the API. Show loading, disconnected and action-error states; disable duplicate actions while a request is pending. Status must not claim a message was delivered unless the Twin accepted it.

The reset creates a clean **in-memory demonstration** state, with no production data. At minimum, controls must let the presenter follow the scenario below. Labels should explain the model; avoid implying an actual network or quantum hardware is running.

## Phase 1 — shared dashboard foundation

Nancy sets up the local runner entry point, static page shell, basic layout and empty/loading/disconnected states; component owners agree panel boundaries and contract. No simulated result should look like a live result. Backend component integrations can follow in later phases.

**Review gate:** start the local page using documented commands; confirm it loads locally, shows clearly labelled empty states, and stops cleanly. Confirm shared-file ownership and contract with the team. Stop for review.

## Phase 2 — independent components and panels

Each member completes their existing independent backend tests and their panel: Marwan key supply, Mariam Mohamed sensor, Kareem gateway, Mariam Wael Twin, Nancy scenario controls and event area. Integrate each panel with its real safe status as the runner exposes it. Nancy provides the shared API and each owner tests their own panel.

**Review gate:** each independent demo and focused tests pass; each panel displays real backend values, handles missing data and contains no key material. Record actual commands and results. Stop for review.

## Phase 3 — end-to-end connection

Nancy wires key pool, sensor, gateway and Twin through the runner. Each owner supports integration and fixes their own module or panel. Implement the connection epoch and control actions. Ensure only verified readings reach the Twin; expose clear errors and avoid key leakage. Test empty pool, unavailable connection, tampering and repeated readings in one epoch.

**Review gate:** a new epoch consumes one available key; multiple protected readings arrive and update the Twin; a modified message is rejected without updating it. The dashboard accurately reflects runner state. Stop for review.

## Phase 4 — scenarios and presentation rehearsal

Implement and verify a repeatable, presenter-controlled sequence:

1. Reset, generate a known small number of keys, establish an epoch, send readings and show `CURRENT`.
2. Interrupt supply and show that the existing epoch still delivers readings. End it, ensure the pool is empty, and show that a new epoch request fails.
3. With no active epoch, show delivery stopping; advance the experiment clock across the configured thresholds to show `DELAYED` then `MISSING`.
4. Resume supply, generate a key, establish a new epoch, send a reading and show `CURRENT` again.

Nancy records configuration, actual results, screenshots and limitations; all members rehearse their portions. Add a concise startup, reset and troubleshooting guide and record actual verification in `IMPLEMENTATION_STATUS.md`.

**Review gate:** run all four steps from a clean state, compare displayed counts and statuses with backend evidence, verify error and disconnected states, and confirm no secrets appear in screenshots or logs. Record pass/fail and any unresolved issues. Stop for review.

## Phase 1 kickoff prompt

```text
Read q-twinsecure/q-twinsecure-docs/plan.md and the shared interface contract.
Implement Phase 1 only. Respect the existing project structure and preserve unrelated work.
Document the commands used and verify the local page and empty/disconnected states.
Stop after Phase 1 so the team can review before Phase 2.
```
