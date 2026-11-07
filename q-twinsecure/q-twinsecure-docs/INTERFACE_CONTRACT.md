# Shared Interface Contract

This contract allows everyone to implement independently with sample data and mocks.

## Sensor reading
```python
{
    "sensor_id": "co2-simulator-01",
    "value_ppm": 650.0,
    "timestamp": "2026-11-05T12:30:00+00:00"
}
```
Required fields: `sensor_id`, `value_ppm`, `timestamp`.

## Key pool
Equivalent public behavior:
- `generate_keys(count: int) -> int`
- `consume_key() -> key_record | None`
- `interrupt_supply() -> None`
- `resume_supply() -> None`
- `get_status() -> dict`

A key record provides a non-secret `key_id` and 32-byte material for both simulated endpoints. Never log key bytes.

Marwan's implementation returns an immutable `KeyRecord` with `key_id: str`,
`device_key: bytes`, and `twin_key: bytes`. Both endpoint byte fields match and
are excluded from the record's `repr`. Use these fields internally only.
`QKDKeyPool(capacity=10)` starts empty with supply enabled. `get_status()` returns
`supply_enabled`, `keys_available`, `keys_generated`, `keys_consumed`, and
`capacity`; it never returns key records. By default a background worker generates
one pair every `generation_interval` seconds (default 1.0), waiting when full and
refilling freed slots automatically. Interruption stops generation, preserving
queued and allocated pairs; resumption restarts automatic supply. The explicit
`generate_keys` API remains for seeding; use `auto_generate=False` for deterministic
experiments. Public operations are synchronized; the runner still coordinates
multi-component epoch establishment. Use the pool as a context manager or call
`close()` to stop/join its worker. See [the key-pool run guide](../qkd/README.md).

Capacity is the maximum number of available keys **per endpoint**. Both pools
fill together and never exceed that limit. A full pool adds zero keys and keeps
its stored keys unchanged; allocation frees one slot in each pool, which supply
can refill. The key panel derives both endpoint occupancies and its full state
from the synchronized `keys_available` and `capacity` fields.

## Gateway
Equivalent public behavior:
- `encrypt_reading(reading: dict, key: bytes) -> dict`
- `decrypt_reading(envelope: dict, key: bytes) -> dict`

Document byte encoding. Use AES-GCM with a fresh 12-byte nonce per encryption under a given key. Reject tampering. Direct AES-GCM is not a full TLS implementation.

## Digital Twin
Equivalent public behavior:
- `update_observation(reading: dict, received_at=None) -> None`
- `get_freshness(now=None) -> str`
- `get_status(now=None) -> dict`

States: `CURRENT`, `DELAYED`, `MISSING`. Thresholds must be configurable.

## Planned dashboard integration

The versioned status and scenario-control contract for the shared local dashboard is specified in [plan.md](plan.md). Each component supplies real state to the integration runner; no raw key material is sent to the browser. Existing component interfaces above remain the starting point.

## Independence
Sensor/Twin work uses local sample dictionaries; gateway tests use a local test key and fake key provider; key-pool work uses its own demo. No contributor should need another module to run their own demo.

## Current integration extension (2026-11-07, local branch for review)

This extension supersedes the historical Phase 2 unavailable/null behavior below.
Existing routes, action payload validation, limits and error shapes are retained.
Status now has `phase: 3`, `scenario: "MANUAL"`, `integration_ready: true`.
These indicate code availability, not team/browser acceptance. `/twin` is the
immersive factory view using the same API as `/`.

- `key_pool`: safe QKDKeyPool.get_status() fields, never raw key material.
- `sensor`: latest generated reading or null; generating is not delivery.
- `gateway`: connection state, non-secret epoch ID and verification outcome.
- `twin`: sensor_id, value_ppm, timestamp, received_at, age_seconds, freshness,
  current_threshold, missing_threshold. Observation fields are null initially.
  Age uses observation time; timestamps are timezone-aware ISO strings.
- `readings_generated`, `readings_delivered`, `readings_rejected`: integer counts.
  Authentication or Twin validation rejection never increments delivered count.
- `clock.timestamp`: paused experiment datetime used by both sensor and Twin.
  Limits and elapsed_seconds retain their Phase 2 semantics.
- `key_supply_mode`: automatic (default wall-time worker) or manual (explicit
  `--manual-key-supply` option for seeded scenarios).

Actions are enabled according to real state. Disabled requests return 409 with
a safe reason and an unavailable event. Start consumes one key for a new epoch;
send reuses that allocation, authenticates/decrypts, then validates/stores in the
Twin. Interruption preserves active epochs and queued keys. Reset closes the
old worker and clears components, clock, counts and events before a reset event.
Events additionally support `outcome: "rejected"`. No arbitrary reading,
envelope or tamper payload is exposed through HTTP; tampering is injected in tests.

The runner adapter is `digital_twin/integration.py`. The page loads external
`/twin-panel.css` and script, retaining `default-src 'self'`. Shared hooks await
Nancy/team review. CLI `--current-threshold` and `--missing-threshold` configure
seconds; status records actual values. `create_server(auto_generate=False)`
provides deterministic test setup. Server shutdown closes the key-pool worker.

## Historical Phase 2 checkpoint

## Phase 2 control API — Nancy's implemented portion (2026-11-07)

The local runner currently exposes `api_version: 1`, `phase: 2`, `scenario: "NOT_STARTED"`, and `integration_ready: false`. The sensor field starts null and exposes the latest real simulator reading after advance_time. readings_generated starts at zero; key_pool, gateway, twin and readings_delivered remain null. Full secure-delivery integration remains pending. Existing component interfaces above are unchanged.

`GET /api/status` also supplies:
- `clock`: `elapsed_seconds`, `max_step_seconds` (3600), `max_elapsed_seconds` (86400). This is a manual elapsed experiment clock, paused between actions; event timestamps separately use UTC wall time.
- `actions`: each documented action maps to `{enabled: bool, reason: string | null}`. Clients must respect availability. Only reset and advance_time are enabled now.
- `events`: newest 100 events in chronological order, each with UTC `timestamp`, `elapsed_seconds`, known `action`, `outcome` (`success` or `unavailable`) and a fixed safe `message`. No request payloads or component secrets are stored.

`POST /api/actions` requires `Content-Type: application/json`, a body of 1–4096 bytes, and one JSON object:

```json
{"action": "reset"}
{"action": "advance_time", "seconds": 5}
{"action": "generate_keys", "count": 1}
```

The lines above are separate request examples. `seconds` must be an integer from 1 to 3600 and total elapsed time cannot exceed 86400. `count` must be an integer from 1 to 100; generation remains unavailable. Other known actions (`interrupt_supply`, `resume_supply`, `start_epoch`, `end_epoch`, `send_reading`) accept only the action field and remain unavailable. Extra/missing fields, unknown actions, and booleans as integers are rejected. Reset clears runner clock/history and adds a reset event; it also resets the sensor, generated count and observation history.

Success returns status directly (200). Validation errors return `{error, status}` (400); known unavailable actions return the same shape (409) and add an unavailable event. Unsupported content type (415), excessive/empty body (413), unsupported transfer encoding (400), bad origin (403), timeout (408), and unknown route (404) return clear errors, but may omit status. If the browser sends Origin, it must exactly match the printed loopback origin. The server binds to 127.0.0.1 and serializes requests; there is no production authentication or network deployment.

The frontend disables controls during requests and disconnection, reports action errors separately, and does not automatically retry mutations after a timeout. Domain integration and real-data panels remain owner follow-up work; phase metadata must not be mistaken for completion of the team-wide review gate.

## Sensor integration — 2026-11-07

Each successful advance_time generates exactly one reading, timestamped at reset-time UTC origin plus elapsed experiment seconds. GET status does not generate observations. Sensor generation is independent of protected delivery: send_reading remains disabled and readings_delivered remains null. The shared status loop updates the sensor custom element, including reset/empty and disconnected states. No separate sensor poller runs on the shared page.

Latest main compatibility: advance_time retains the sensor owner behavior of generating one reading at the new experiment timestamp, without delivery. Only send_reading authenticates and delivers. Status polling generates no readings. The sensor owner custom element and HTTP rejected-body draining behavior are preserved.
