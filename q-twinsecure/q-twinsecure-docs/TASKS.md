# Tasks and Work Plan

## Revised committee-demo plan

The phased full-stack plan and ownership are in [plan.md](plan.md). Every owner implements a backend contribution and a dashboard contribution; Nancy coordinates the shared runner and shell. The phases below remain component checklists, not an indication that the dashboard or integration is complete.

## Guiding rule

Build the smallest complete demonstration first. Do not add advanced features until the normal → interruption → recovery scenario works end to end.

## Phase 0 — Repository and environment

- [ ] Confirm one shared repository root and naming convention.
- [ ] Add the Markdown project documents.
- [ ] Confirm Python version and activate the virtual environment.
- [ ] Add `requirements.txt`.
- [ ] Confirm package imports work.
- [x] Add a `.gitignore` for `venv/`, `__pycache__/`, `.pytest_cache/`, `.env`, and local log files.

## Phase 1 — Emulated key supply

- [x] Implement key record structure (`key_id`, key material).
- [x] Implement bounded matching device-side and Twin-side pools.
- [x] Generate 32-byte key material using `secrets.token_bytes(32)`.
- [x] Implement key consumption that returns matching endpoint records.
- [x] Implement supply interruption and recovery.
- [x] Generate automatically at a configurable interval; wait at capacity and refill freed slots.
- [x] Expose safe status metrics; never expose raw key material.
- [x] Test capacity limits, empty pool, interruption, recovery, and endpoint synchronization.

Marwan's independent backend is locally verified on 2026-11-07: 16 pool tests
and four preview API tests passed, including full-pool rejection without replacing
stored keys and automatic refill only after allocation. See [run instructions](../qkd/README.md).
Changes await commit; the key panel's browser checks and shared integration
remain outstanding. These checks do not complete the integrated plan's phases.

**Acceptance criteria:** The pool never exceeds configured capacity; both endpoints receive matching key IDs/material; no key can be consumed when the pool is empty; interruption prevents new generation; recovery allows generation again.

## Phase 2 — Sensor simulator

- [x] Create a CO₂ reading model with value, sensor ID, and timestamp.
- [x] Generate repeatable readings.
- [x] Test timestamp and reading serialization.

**Acceptance criteria:** The simulator produces valid timestamped readings without requiring hardware.

Local verification on 2026-11-05: 10 sensor tests passed and the independent demo printed five shared-contract readings using Python 3.14. See `sensor/README.md`. Reusable sensor dashboard panel and standalone Python-backed preview are now saved. Follow-up validation passed 13 Python tests and four JavaScript check groups. Shared sensor runner integration is now tested: real status, manual-clock generation, reset and disconnected/recovery rendering. Final checks on 2026-11-07 passed 66 Python tests, sensor JavaScript checks plus a shared-app snapshot check, and three gateway/Twin JavaScript tests. Browser visual verification and protected-delivery integration remain pending.

## Phase 3 — Secure message / gateway

- [ ] Agree on a small message schema.
- [ ] Implement AES-256-GCM encryption and decryption for PoC messages.
- [ ] Generate a fresh unique 12-byte nonce for each encryption under a key.
- [ ] Authenticate required metadata.
- [ ] Reject tampered ciphertext or metadata.
- [ ] Separate connection-epoch key allocation from per-reading encryption.
- [ ] Document that direct AES-GCM is a PoC simplification if TLS 1.3 external PSK is not implemented.

**Acceptance criteria:** A valid protected reading decrypts correctly; a modified message fails authentication; nonce reuse under the same key is prevented by design.

## Phase 4 — Twin receiver and freshness

Mariam Wael component update (2026-11-05): monitor, configurable thresholds,
status snapshot, terminal demo and owner panel implemented locally. Ten Python
tests and one JavaScript DOM-harness test passed. Run instructions and panel
handoff are in `MARIAM_WAEL.md`. Shared dashboard integration and authenticated
pipeline checks remain pending; component review is next. Prepared for component review.

- [ ] Accept only successfully authenticated readings.
- [ ] Store the latest valid reading and receive timestamp.
- [ ] Calculate observation age.
- [ ] Implement `CURRENT`, `DELAYED`, and `MISSING`.
- [ ] Make thresholds configurable.
- [ ] Test transitions between freshness states.

**Acceptance criteria:** Freshness changes correctly as observations arrive or stop; invalid messages do not update the Twin.

## Phase 5 — End-to-end experiment

- [ ] Run normal operation and verify readings reach the Twin.
- [ ] Interrupt key supply while an existing connection epoch is active.
- [ ] Verify the existing epoch is not automatically terminated by key-supply interruption.
- [ ] Request a new connection epoch while no key is available; verify failure.
- [ ] Verify readings stop after the active epoch is closed/ended and no new epoch can be established.
- [ ] Verify Twin status transitions from `CURRENT` to `DELAYED` to `MISSING`.
- [ ] Restore key supply and replenish the pool.
- [ ] Establish a new epoch and verify readings resume and Twin returns to `CURRENT`.
- [ ] Save logs/results and record configuration.

**Acceptance criteria:** The demonstration clearly shows the causal chain from constrained key availability to new-connection failure, observation interruption, and Twin freshness degradation, followed by recovery.

## Phase 6 — Polish and evidence

- [ ] Implement and test the shared dashboard and each owner's real-data panel as specified in [plan.md](plan.md).
- [ ] Add a concise run guide.
- [ ] Add architecture diagram and experiment table to the report/slides.
- [ ] Capture reproducible terminal/dashboard evidence.
- [ ] Record limitations and avoid unsupported security claims.
- [ ] Update `IMPLEMENTATION_STATUS.md`.

## Not part of the current 10% PoC

- [ ] Physical QKD or BB84 over quantum hardware.
- [ ] Physical CO₂ sensor integration.
- [ ] Full industrial Modbus/TCP deployment.
- [ ] Production TLS/mTLS infrastructure unless specifically selected and time permits.
- [ ] ML anomaly detection.
- [ ] LLM incident explanations.
- [ ] Cloud deployment and production hardening.

## Nancy — dashboard Phase 1 (2026-11-07)

- [x] Create branch `Nancy` and add loopback-only standard-library runner.
- [x] Add page shell with component ownership boundaries, explicit empty states and disabled controls.
- [x] Add foundation status API and HTTP tests.
- [x] Prepare run instructions, scenario checklist, results table and evidence folder.
- [ ] Review loading/disconnected states and responsive layout in a browser.
- [ ] Confirm ownership and contract with team; review Phase 1 before Phase 2.

Component integration and scenario controls remain pending. See [Nancy's checklist](../experiments/scenario_checklist.md).

## Nancy — Phase 2 control foundation (2026-11-07)

- [x] Record user's Phase 1 confirmation and proceed to Phase 2.
- [x] Provide validated action API, availability metadata and bounded safe event history.
- [x] Implement reset and bounded manual clock independently of unfinished components.
- [x] Add controls, busy/disconnected states, action errors and event display.
- [x] Verify 16 tests and JavaScript syntax; document API and owner handoff.
- [ ] Review Phase 2 controls in a browser.
- [ ] Owners complete independent components, safe-status interfaces and real-data panels.
- [ ] Pass team Phase 2 review before Phase 3 integration.
