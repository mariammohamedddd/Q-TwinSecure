# PoC Architecture

## Planned committee dashboard

One local Python runner will connect the real components and serve a shared dashboard; the proposed status and control contract and ownership are in [plan.md](plan.md). Panels display safe backend state and never receive raw keys. The dashboard and integration are planned, not yet verified as implemented.

## 1. Logical flow

```text
┌─────────────────┐
│ CO₂ Sensor      │
│ Simulator       │
└────────┬────────┘
         │ reading
         ▼
┌─────────────────┐       requests fresh key for a new
│ Device Gateway  │◄──────connection epoch
└────────┬────────┘
         │ protected observation
         ▼
   [Secure channel /
    AES-GCM PoC mode]
         │
         ▼
┌─────────────────┐       matching key material
│ Twin Gateway    │◄──────from Twin-side key pool
└────────┬────────┘
         │ verified reading
         ▼
┌─────────────────┐
│ Digital Twin    │
│ CURRENT /       │
│ DELAYED / MISSING│
└─────────────────┘

        ┌─────────────────────────┐
        │ Emulated Key Supply     │
        │ bounded matching pools │
        │ rate / interruption /  │
        │ recovery                │
        └─────────────────────────┘
          supplies both endpoints
```

## 2. Components and responsibilities

### Sensor simulator (`sensor/`)
- Produces timestamped CO₂ readings.
- Uses deterministic or configurable values for repeatable tests.
- Does not require physical sensor hardware.

### Emulated key service (`qkd/`)
- Generates key material using a cryptographically secure random generator.
- Maintains matching device-side and Twin-side key records.
- Enforces a maximum pool capacity.
- Supports supply interruption and recovery.
- Exposes status such as available key count, generated count, and consumed count.
- Must never log raw key material.

### Device gateway (`gateway/`)
- Requests/consumes a key when a new protected connection epoch is established.
- Protects sensor observations.
- Uses a unique nonce for every AES-GCM encryption under a given key.
- Sends the protected payload and the metadata needed for verification.

### Twin gateway (`gateway/`)
- Receives protected data.
- Uses the corresponding Twin-side key material.
- Authenticates and decrypts the message.
- Rejects messages that fail authentication.
- Passes verified readings to the Digital Twin.

### Digital Twin (`digital_twin/`)
- Stores the latest accepted observation and its timestamp.
- Calculates age of the latest observation.
- Displays `CURRENT`, `DELAYED`, or `MISSING` based on configurable thresholds.
- Does not invent missing measurements.

### Application entry point (`main.py`)
- Wires components together.
- Runs the normal, interruption, and recovery scenario.
- Exposes safe state to a shared dashboard showing key status, connection state, observation delivery, and Twin freshness.

## 3. Suggested message structure

Use a small, versioned message structure. Example fields:

```json
{
  "version": 1,
  "connection_epoch": "example-epoch-id",
  "message_id": "unique-message-id",
  "sensor_id": "co2-simulator-01",
  "timestamp": "ISO-8601 timestamp",
  "nonce": "base64-encoded-nonce",
  "ciphertext": "base64-encoded-ciphertext",
  "tag": "base64-encoded-authentication-tag"
}
```

This is a conceptual schema. The implementation may use the `cryptography` library's AESGCM API, which returns ciphertext with the authentication tag appended. Document the exact encoding and parsing convention chosen.

Do not include raw AES keys or PSKs in the message.

## 4. AES-GCM requirements

If AES-GCM is used in the PoC:

- Use a 256-bit key (32 bytes).
- Use a 96-bit nonce (12 bytes) unless the library/API explicitly documents another safe choice.
- **Never reuse a nonce with the same key.**
- Authenticate relevant metadata as associated data (AAD), or include it inside the authenticated plaintext.
- Treat authentication failure as a rejected message.
- Do not print keys, plaintext secrets, or sensitive key material in logs.
- Keep encryption/decryption tests, including a tampering test.

AES-GCM provides authenticated encryption for the message. It is not by itself a complete network protocol, TLS implementation, key-exchange protocol, or production gateway.

## 5. Connection and key lifecycle

Model connection establishment separately from individual sensor messages:

1. A new connection epoch is requested.
2. The endpoint requests a matching key record from the emulated key service.
3. If no key is available, the new connection cannot be established.
4. If a key is available, the protected connection epoch becomes active.
5. Multiple readings can be protected and sent over that established epoch.
6. A later new epoch/renewal requires fresh key material.
7. If supply is interrupted, an already active epoch remains active in this simplified lifecycle model; a new epoch cannot be established without a key.

Do not consume one new pool key for every sensor reading unless the team explicitly changes the research model and documents the change.

## 6. Freshness states

Choose thresholds in configuration, not scattered magic numbers.

Suggested initial semantics:
- `CURRENT`: latest valid observation age is at or below the current threshold.
- `DELAYED`: latest valid observation is older than the current threshold but not beyond the missing threshold.
- `MISSING`: no valid observation has ever arrived, or its age exceeds the missing threshold.

The exact time thresholds are experimental parameters and must be recorded in the experiment output.
