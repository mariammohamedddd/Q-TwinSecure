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

## Phase 2 control API — Nancy's implemented portion (2026-11-07)

The local runner currently exposes `api_version: 1`, `phase: 2`, `scenario: "NOT_STARTED"`, and `integration_ready: false`. All four component fields and generated/delivered counts remain null until real integration. Existing component interfaces above are unchanged.

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

The lines above are separate request examples. `seconds` must be an integer from 1 to 3600 and total elapsed time cannot exceed 86400. `count` must be an integer from 1 to 100; generation remains unavailable. Other known actions (`interrupt_supply`, `resume_supply`, `start_epoch`, `end_epoch`, `send_reading`) accept only the action field and remain unavailable. Extra/missing fields, unknown actions, and booleans as integers are rejected. Reset clears runner clock/history and adds a reset event; it performs no component operations yet.

Success returns status directly (200). Validation errors return `{error, status}` (400); known unavailable actions return the same shape (409) and add an unavailable event. Unsupported content type (415), excessive/empty body (413), unsupported transfer encoding (400), bad origin (403), timeout (408), and unknown route (404) return clear errors, but may omit status. If the browser sends Origin, it must exactly match the printed loopback origin. The server binds to 127.0.0.1 and serializes requests; there is no production authentication or network deployment.

The frontend disables controls during requests and disconnection, reports action errors separately, and does not automatically retry mutations after a timeout. Domain integration and real-data panels remain owner follow-up work; phase metadata must not be mistaken for completion of the team-wide review gate.

## Gateway runner coordination — 2026-11-07

This section supersedes the earlier `gateway: null` placeholder and epoch-action availability notes. Nancy's runner uses Kareem's existing `GatewayStatus` adapter and `renderGatewayPanel` unchanged from origin/kareem. The sensor contribution from current origin/main is preserved; full sensor/Twin wiring is outside this change.

### Responsibility and call sequence

- Nancy owns the active epoch, key-provider consumption and private device/Twin key references. Kareem owns cryptographic protection/verification and safe gateway state.
- Construct `RunnerState(key_pool=provider)` for internal integration. The default application still has no provider; it never substitutes sample keys.
- `POST /api/actions` with `{"action":"start_epoch"}` calls runner `start_epoch()`. An existing epoch is rejected before consuming a key. Otherwise consume one matching pair; an empty pool returns 409 and stays disconnected. Validate the pair, assign a new UUID epoch ID, call `GatewayStatus.start_epoch(epoch_id)` and retain keys privately. A rejected malformed record is consumed/discarded, not returned to the provider.
- `protect_reading(reading)` internally calls `encrypt_reading(reading, device_key)`; `verify_reading(envelope)` calls `GatewayStatus.verify_reading(envelope, twin_key)`. Multiple messages reuse the active epoch without consuming more pool keys. Verification returns a reading only after authentication succeeds. These are Python methods, not public HTTP routes. Key bytes are never accepted from the browser.
- `POST /api/actions` with `{"action":"end_epoch"}` calls `end_epoch()` and clears gateway state and both key references. HTTP requests without an active epoch return 409. Reset also ends the epoch. Clearing references is not guaranteed secure memory erasure.
- Supply interruption must not call end_epoch or clear active keys. After ending an epoch, establishing another still requires an available pair; interrupted supply may still leave buffered pairs available.

### Proposed provider adapter format

`consume_key()` returns `None` or a dictionary with `key_id` (nonempty non-secret string), `device_key` (32-byte bytes), and `twin_key` (equal 32-byte bytes). This is the runner's proposed internal adapter format, pending confirmation with Marwan. Adapt his public record shape at that boundary rather than changing his internals. The runner does not expose key_id or either key through status/events. The only included provider is test-only; real pool wiring remains outstanding.

### Gateway JSON and panel

```json
{
  "gateway": {
    "connection_state": "DISCONNECTED",
    "connection_epoch": null,
    "verification": null
  }
}
```

An active epoch reports `CONNECTED` with its non-secret UUID. Verification is null, `VERIFIED`, or `REJECTED`. Starting/ending an epoch clears the previous verification outcome. `VERIFIED` does not mean Twin delivery: Twin status and delivery counts remain unavailable until Twin acceptance is wired.

The shared page loads app.js as an ES module; app.js imports `/gateway-panel.js` and calls `renderGatewayPanel(container, status.gateway)` on every successful status/action response. On runner disconnection it passes null so the panel shows unavailable rather than stale connected state. The server explicitly serves the module with JavaScript MIME type.

`actions.start_epoch` is enabled only when a provider is attached and no epoch is active. The actual action checks the pool for a key. `actions.end_epoch` is enabled only while connected. With the default empty key-pool implementation, start remains disabled. The page displays real DISCONNECTED gateway state even without a pool.

The existing direct AES-GCM envelope and its random nonce scheme are unchanged. This is not TLS or a replay-resistant network protocol; no production security or full end-to-end acceptance is claimed.
