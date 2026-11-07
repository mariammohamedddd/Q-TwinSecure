# Marwan's software-emulated QKD key supply

This is an in-memory model of constrained key availability, using classical
cryptographically secure randomness. It does not implement physical QKD, BB84,
quantum secrecy, TLS or connection management. No third-party packages are
needed for this component, its preview or its tests (verified on Python 3.13.4).

## Run independently

From the repository root in Windows PowerShell:

```powershell
cd q-twinsecure
python -B -m qkd.demo
python -B -m unittest discover -s tests -p 'test_key*.py' -v
```

The terminal demo automatically fills a capacity-two pool, allocates matching endpoint material,
interrupts generation, consumes the remaining queued pair, demonstrates empty
allocation failure, resumes generation and allocates a recovery pair. Output
contains only non-secret IDs, booleans and counts.

## Backend contract

```python
from qkd import QKDKeyPool

with QKDKeyPool(capacity=3, generation_interval=1.0) as pool:
    # Supply starts automatically; one pair arrives after each interval.
    # The application may request an epoch later, when a key is available.
    record = pool.consume_key()
    if record is not None:
        # Use internally, never print or serialize these bytes:
        device_key = record.device_key
        twin_key = record.twin_key
        key_id = record.key_id
    safe_status = pool.get_status()
```

- Automatic supply is enabled by default. A background worker generates one pair
  per `generation_interval` seconds (default one second), until capacity is
  reached. It waits while full and automatically refills freed slots. It works
  even with no browser connected and no API requests.
- `capacity` is a hard limit for **each** endpoint pool: capacity three means
  three device keys and three matching Twin keys. A full pool accepts zero new
  pairs, never overwrites stored keys, and generates no extra material. Allocation
  removes one key from each pool, making room for one new matching pair.
- Use a context manager or call `close()` to stop and join the worker. Closing
  permanently stops generation; already allocated and queued material survives.
- `auto_generate=False` disables the worker for controlled experiments/tests.
  The compatible `generate_keys(count)` API remains available for explicit
  seeding: it returns how many pairs were added, capped by free capacity. A
  paused or full pool returns zero. Zero count is valid.
- Capacity must be a positive integer; count must be a non-negative integer.
  Booleans and other types raise `TypeError`; out-of-range integers raise
  `ValueError`.
- `consume_key()` removes one matching pair in FIFO order, returning an immutable
  `KeyRecord(key_id, device_key, twin_key)`, or `None` when empty. Both byte fields
  contain the same 32-byte material. Its `repr` excludes secret fields.
- `interrupt_supply()` and `resume_supply()` are idempotent. Interruption prevents
  generation but preserves queued pairs and previously allocated material.
  Resumption restarts automatic replenishment on the worker's next interval;
  it does not instantly fill the pool or accumulate missed supply during pauses.
- Allocate once per new connection epoch. Multiple readings use the existing
  allocation; the pool does not close or renew connections.
- `get_status()` returns a new JSON-safe dictionary containing only
  `supply_enabled`, `keys_available`, `keys_generated`, `keys_consumed`, and
  `capacity`. Counters count pairs, not the two endpoint copies separately.
  `keys_generated == keys_available + keys_consumed`.
- Pools are process-local, have no persistence, and synchronize public operations
  with the supply worker. The runner must still coordinate multi-step epoch
  establishment across components. This is not production key
  storage and does not promise secure memory erasure.

## Key-panel preview

```powershell
python -B -m qkd.panel_demo
# Optional: generate one pair every two seconds
python -B -m qkd.panel_demo --interval 2
# Optional: allow up to ten keys in each endpoint pool
python -B -m qkd.panel_demo --capacity 10
```

Open `http://127.0.0.1:8765` in a browser. Use `--port 8766` if needed. Stop with
Ctrl+C. Restarting creates a fresh empty pool with capacity three.
The panel shows separate device-side and Twin-side occupancy and a
`Pool full · generation waiting` indicator at capacity. `--capacity` sets the
limit at startup; it cannot grow while the preview is running.

This independent component preview uses the actual `QKDKeyPool`; it does not
implement Nancy's shared runner or committee dashboard. Supply starts when the
server starts, at one pair per second by default. Allocate, interrupt and resume
buttons call a loopback-only standard-library HTTP server; no Generate button is
needed. Closing the server stops its supply worker.
Allocation demonstrates pool consumption without establishing a connection.

Manual panel checks:

1. Start the server: the empty pool begins filling automatically.
2. Wait approximately three seconds: available and generated reach three.
   Leave it running: generation waits at capacity. Allocate once while supply is
   enabled: the freed slot refills automatically on the next interval.
3. Interrupt supply: the indicator changes; generation is blocked. Allocate the
   queued pairs: available becomes zero and consumed increases by the allocations.
4. Allocate again: an explicit empty-pool failure appears; counters stay unchanged.
5. Resume: supply is enabled and available increases automatically again.
6. Stop the server while leaving the page open: the next refresh shows backend
   disconnected and hides live counts. Restart to recover with fresh empty state.

The preview's private routes are `GET /api/key-pool` and
`POST /api/key-pool/actions` with one `action`: `consume`, `interrupt`,
or `resume`. Responses contain safe status and result text, never a key record.
These are preview routes, not changes to the planned shared API.

## Shared dashboard handoff

`web/key-panel.js` exports:

```javascript
import { renderKeyPanel } from "./key-panel.js";

renderKeyPanel(container, null, { state: "loading" });
renderKeyPanel(container, apiStatus.key_pool);
renderKeyPanel(container, null, { state: "disconnected" });
```

The renderer owns only the supplied container, includes scoped styles, handles
missing/malformed data, and renders only explicitly allowed safe fields. It
does not fetch, hold keys, manage epochs or add shared scenario controls. Nancy's
shared app supplies real status and calls the renderer. Final integration and
browser verification remain outstanding.

## Verification on 2026-11-07

- `python -B -m unittest discover -s tests -p 'test_key*.py' -v`: **20 passed**
  (ten manual pool tests, six automatic-supply tests and four local preview
  server tests). Checks cover automatic generation/refill, capacity, pause/resume,
  concurrent consumption, interval validation and worker shutdown. Full-pool
  additions are rejected without generating material or displacing stored keys;
  API tests verify capacity stays unchanged until allocation frees a slot.
- `python -B -m qkd.demo`: exited successfully; empty allocation returned `None`,
  interruption blocked generation, and recovery allocation succeeded. Final
  counts: generated three, consumed three, available zero, supply paused before
  shutdown. Initial and recovery keys were generated automatically.
- `python -B -m qkd.panel_demo`: started successfully on loopback port 8765.
- Interactive browser checks were **not completed**: computer use stopped because
  it could not determine the current Edge URL confidently enough to enforce
  policy. Loading/disconnected rendering and visual layout remain unverified.
- Teammate gateway tests and the integrated scenario were not run for this task.
