# Project Context and Shared Understanding

## 1. Project identity

**Name:** Q-TwinSecure  
**Working title:** Industrial Security Gateway with QKD Emulation and a Trust-Aware Digital Twin.

The project studies a secure monitoring path between an industrial device/sensor and a Digital Twin. It combines a security gateway, software-emulated QKD key supply, secure transport/protected messages, observation-freshness monitoring, and (in the broader research concept) anomaly detection and evidence-grounded explanations.

## 2. Problem being explored

Industrial monitoring depends on observations reaching the Digital Twin reliably and securely. The project investigates what happens when the supply of key material is constrained, delayed, or interrupted.

The PoC should make the relationship observable:

**key availability → ability to establish a new protected connection → observation delivery → Digital Twin freshness.**

This is a feasibility demonstration, not proof that every component of the full research architecture has been production validated.

## 3. Terminology

- **Device / sensor:** The source of industrial measurements. For the PoC, use a software CO₂ sensor simulator.
- **Device-side gateway/proxy:** Protects outgoing sensor observations.
- **Twin-side gateway/proxy:** Receives and verifies protected observations before forwarding them to the Twin.
- **Key service:** Supplies authorized key material to an endpoint. In the PoC this is a local software component, not a real quantum network service.
- **Emulated QKD key supply:** A software model that generates cryptographically random key material and simulates supply rate, pool capacity, delay, interruption, and recovery. It is not physical QKD.
- **Key pool:** A bounded store of available key records.
- **Connection epoch:** A protected connection instance for which fresh external PSK material is required by the research design.
- **Digital Twin (Twin):** The receiving monitoring representation that displays the latest accepted observation and its freshness.
- **Freshness:** Whether the latest received observation is recent enough according to a configured threshold.

## 4. QKD-emulation clarification

The project uses **software emulation**. Key material is generated with a classical cryptographically secure random generator (for example, Python `secrets`). The prototype may model key supply rate, batch availability, pool capacity, delays, interruptions, and recovery.

Do not describe this as physical QKD, quantum key distribution over a quantum channel, BB84 implementation, or quantum-secure communication. Do not claim that the generated keys have quantum properties or quantum secrecy.

The emulation models the operational effect of a constrained key source; it does not reproduce the physics of quantum communication.

## 5. Security and connection-lifecycle understanding

The research design considers TLS 1.3 with externally supplied PSKs. The key service supplies PSK material to the TLS implementation; the TLS library performs the handshake and derives traffic keys.

For a minimal PoC, AES-256-GCM can be used to demonstrate authenticated encryption of observations if implementing TLS 1.3 external PSKs would make the prototype too large. If AES-GCM is used directly, document that it is a **PoC simplification** and do not claim that it is equivalent to a complete TLS 1.3 deployment.

Important lifecycle rule:

- Fresh key material is required for a new protected connection epoch.
- Multiple sensor measurements may travel over an already established connection.
- Interrupting key supply does **not** automatically terminate an existing connection.
- If a new connection/epoch is needed while no key is available, establishment/renewal should fail.
- When key supply resumes and a key is available, a new connection can be established.

## 6. Broader research vision vs. current PoC

The broader concept includes secure device-to-Twin communication, freshness monitoring, anomaly detection, and evidence-validated LLM explanations. The current 10% PoC intentionally focuses on the smallest demonstrable chain:

**sensor simulation → emulated key pool → protected gateway message → Twin receiver → freshness status.**

Do not quietly expand the PoC to include ML, LLMs, real hardware, or deployment infrastructure.
