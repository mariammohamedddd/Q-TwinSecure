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

## Integrated runner contract — current on Nancy (2026-11-07)

This section supersedes the earlier placeholder and proposed adapter notes. The runner uses the actual `QKDKeyPool`, `CO2SensorSimulator`, `GatewayStatus` and `TwinMonitor`. `consume_key()` returns Marwan's immutable `KeyRecord`; the runner reads its attributes directly and never serializes the record. One record is consumed per epoch; repeated readings reuse the active matching keys privately.

`GET /api/status` keeps api_version=1 and now reports phase=3 and integration_ready=true (components wired; not browser acceptance). `key_pool` is the safe get_status() snapshot. `sensor` is the latest generated reading or null. `gateway` is Kareem's safe snapshot. `twin` is Mariam Wael's get_status(now) dictionary, including age_seconds, freshness, observation fields and thresholds. Counts begin at zero and delivery increments only after authentication and Twin acceptance both succeed.

All eight documented actions are implemented. start_epoch is available while disconnected, and may fail 409 if the pool is empty. end_epoch and send_reading are disabled without an epoch and reject direct requests too. generate_keys accepts count=1..100, bounded by pool capacity (default 10); zero additions due to interruption/full pool return 409. Partial capacity returns the actual generated count in a safe event. Interrupt/resume preserves active epochs and buffered keys.

The shared runner deliberately uses `auto_generate=False`; the standalone key preview retains its automatic mode. Advance_time moves one UTC experiment clock used by sensor generation, Twin receipt and age, and event timestamps. Clock does not advance on polling or wall time. Default thresholds are 5 and 15 seconds; these are demonstration settings. Reset recreates all components with a fresh manual pool, no active epoch, zero counts, no observations and one reset event.

Events contain success/failure outcomes and fixed safe messages (including non-secret numeric counts). Invalid request-schema inputs do not mutate state or echo payloads. Failure status reflects current backend state. No secret bytes or protected envelope are exposed. Browser action timeout results remain uncertain until status refresh; mutations are not retried automatically.

app.js imports all four owner modules and fetches status once centrally. Sensor receives update(status.sensor), Twin receives update(status.twin), and key/gateway renderers receive their corresponding safe objects. Disconnection clears live claims across panels. Panel styles use existing inline styles; the local server CSP permits inline styling while scripts remain same-origin only. No production hosting/authentication is provided.

## Current merged behavior (2026-11-07)

Both latest Mariam contributions are included. Send reading remains the sensor generation/delivery action; clock advancement does not generate data. New status fields: readings_rejected counts authentication/Twin-validation rejections, and key_supply_mode is manual/automatic. Reset clears rejections too. Manual key generation remains default; `--automatic-key-supply` enables Marwan's wall-time worker. Observation clock remains manual in both modes. CLI `--current-threshold` and `--missing-threshold` configure Twin thresholds and survive reset. Server close terminates supply and ends the epoch.

`/twin` serves the factory view; `/twin-panel.css` and `/twin-live.css` are explicit assets. Shared app mounts the Twin fullScreen option only for that view, and moves scenario controls into its details area. It keeps one state/API poller and the same runner as the dashboard; no standalone preview server is needed. Owner TwinPipeline is retained as an independent adapter, not a second state owner inside Nancy's runner. Browser review remains pending.

## Automatic monitoring contract (2026-11-07)

`RunnerState(automatic=True, reading_interval=2, epoch_duration=10, generation_interval=1, pool_capacity=...)` creates one scheduler and enables the real pool worker. `create_server` accepts the same options. CLI flags `--automatic` / `--automatic-key-supply` both select full automation. Manual constructor/server defaults preserve existing reproducible tests; automatic CLI capacity defaults to 3 (manual 10).

`clock.mode` is `realtime` in automatic mode and elapsed_seconds is a real number based on monotonic elapsed time anchored to UTC. Sensor timestamps, Twin receipt/query and events share that clock. No manual advancement or 86400-second cap applies to real-time operation. `monitoring` contains mode, running, reading_interval_seconds, epoch_duration_seconds, epoch_remaining_seconds (null without an epoch), and error (null or fixed safe text).

New action-only requests: start_monitoring and stop_monitoring. Stop closes the epoch and pauses sampling/delivery while real time and key supply continue. Start retries establishment and schedules a reading. Automatic mode rejects generate_keys/start_epoch/end_epoch/send_reading/advance_time with 409 because the scheduler owns them. Interrupt/resume supply and reset remain presenter controls. Reset clears state, preserves configuration, stops the old key worker, retains one scheduler and resumes monitoring automatically.

The scheduler runs independently of status requests, serializing operations with HTTP state access. Keys are consumed once per epoch; expiry closes the old epoch before trying a fresh allocation. Supply interruption never directly ends the epoch or drops buffered keys. Empty-pool retries and generated-but-undeliverable readings never update the Twin/delivery count. No catch-up message burst is replayed after a scheduler delay. Unexpected internal exceptions stop monitoring, end the epoch and expose a fixed safe error, requiring reset. Authentication/Twin-validation rejection retains the prior observation and does not stop future valid sampling.

The browser polls every second, labels clock/mode accurately and displays only start/stop plus supply/reset overrides in automatic mode. Each accepted reading resets observation age, so a healthy 2-second stream naturally oscillates around 0–2 seconds; Stop monitoring makes real-time aging easy to observe. The state remains in-memory, not a production network service.

## Presentation mode contract (2026-11-07)

CLI --presentation selects guided scenario operation. RunnerState/create_server accept presentation=True and presentation_hold=4. This enables the real-time scheduler but fixes a real capacity-one pool with auto generation disabled; PresentationSequence owns generation, interruption, explicit epoch closure and recovery using actual component calls. Its constructor requires no injected pool and current_threshold > reading_interval so CURRENT can be shown reliably. The continuous automatic and deterministic manual modes remain available.

GET /api/status adds presentation=null outside presentation mode, or {run_id, step, total_steps, stage, title, description, complete, error, steps, results}. Steps are pending/active/passed; verified results are bounded by the finite nine-check sequence and include label, passed and elapsed_seconds. Observed backend conditions gate transitions. No key, protected envelope or raw error payload is returned. The new action-only replay_presentation request recreates state and restarts the sequence with a new run_id; reset does the same. All other mutating actions reject with 409 in presentation mode. Availability metadata enforces the same behavior in both frontend and API. Replay is disabled while an HTTP request is pending.

Presentation lifecycle: POOL_FULL -> NORMAL -> TAMPER_REJECTED -> INTERRUPTED_ACTIVE -> NO_KEY -> DELAYED -> MISSING -> RECOVERY -> COMPLETE. Real age gates stale transitions. Completion retains results and continues accepted readings on the recovery epoch; no further automatic epoch renewal or replay occurs. The presentation overrides the generic epoch-duration timer; monitoring countdown is replaced with guided-sequence information in the UI. Expected authentication/empty-pool failures are demonstrated and recorded, while unexpected/check failures halt visibly through monitoring.error.
