# Architecture and Scope Decisions

Record agreed decisions here. Add a date, decision, rationale, and consequences whenever the team changes an important project choice.

## D-001 — Current deliverable is a 10% feasibility PoC
- **Date:** 2026-11-05
- **Decision:** Build a small working demonstration rather than the full research architecture.
- **Rationale:** The immediate objective is to demonstrate feasibility within a limited schedule.
- **Consequences:** Prioritize the sensor-to-Twin path, emulated key supply, secure message protection, freshness status, and one repeatable experiment. Advanced features remain outside the current PoC.

## D-002 — QKD is software-emulated, not physical
- **Date:** 2026-11-05
- **Decision:** Model key supply with classical cryptographically secure random key generation.
- **Rationale:** The project PoC emulates key availability and operational constraints; it does not implement a quantum channel.
- **Consequences:** Do not claim physical QKD, BB84, photons, or quantum secrecy.

## D-003 — Use a simulated CO₂ sensor initially
- **Date:** 2026-11-05
- **Decision:** Generate CO₂ readings in software for the PoC.
- **Rationale:** Avoid hardware integration so the end-to-end behavior can be demonstrated quickly and reproducibly.
- **Consequences:** Physical sensor integration is not required for the current PoC.

## D-004 — Model key allocation per connection epoch
- **Date:** 2026-11-05
- **Decision:** A fresh key is allocated when establishing a new protected connection epoch; multiple readings can travel over that established epoch.
- **Rationale:** This preserves the connection/key lifecycle described in the research design.
- **Consequences:** Do not consume one new key per sensor reading. Key-supply interruption does not automatically terminate an existing connection.

## D-005 — AES-GCM may be used as a PoC simplification
- **Date:** 2026-11-05
- **Decision:** A direct AES-256-GCM protected-message demonstration is acceptable if full TLS 1.3 external-PSK integration is too large for the initial PoC.
- **Rationale:** Demonstrate authenticated protection without allowing TLS integration complexity to block the feasibility prototype.
- **Consequences:** Clearly label direct AES-GCM as a simplification. Do not claim it is a full TLS 1.3 implementation. If the team later implements TLS 1.3 external PSKs, record the library, configuration, and verification evidence here.

## D-006 — Keep ML and LLM features out of the first PoC
- **Date:** 2026-11-05
- **Decision:** Do not implement anomaly detection or LLM explanations in the initial 10% PoC.
- **Rationale:** The key-supply / connection / freshness chain is the minimum useful feasibility result.
- **Consequences:** These remain broader research directions, not current acceptance criteria.

## Pending decisions
- Confirm final repository folder name.
- Confirm Python version used by all contributors.
- Agree exact freshness thresholds.
- Agree whether the first demo is terminal-based or includes a minimal web/dashboard interface.
- Agree whether direct AES-GCM is sufficient for the assessed PoC or whether TLS 1.3 external PSK is mandatory.
