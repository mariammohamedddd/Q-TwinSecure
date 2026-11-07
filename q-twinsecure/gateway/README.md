# Gateway demo

From the `q-twinsecure` directory, with `cryptography` installed:

```powershell
python -m gateway.demo
python -m unittest discover -s tests -p test_gateway_crypto.py -v
python -m unittest discover -s tests -p test_gateway_status.py -v
node --test tests/test_gateway_panel.mjs
```

`encrypt_reading(reading, key)` and `decrypt_reading(envelope, key)` use a 32-byte key. The envelope contains version 1, a standard Base64-encoded 12-byte random nonce, and standard Base64-encoded ciphertext with the 16-byte authentication tag appended. The version is authenticated as associated data; the reading is inside the authenticated ciphertext. Invalid authentication raises `cryptography.exceptions.InvalidTag`; malformed input raises `ValueError`.

The nonce is randomly generated for each encryption. A key must never be used with the same nonce twice; this demonstration does not persist or coordinate nonces across processes or enforce a per-key usage limit.

The intended integration allocates one key per new protected connection epoch and can use it for multiple readings. Interrupting supply does not itself end an active epoch; establishing a new epoch requires an available key. This module does not manage epochs or the key pool. Direct AES-GCM is a proof-of-concept simplification, not TLS 1.3 or a complete network protocol.

## Status adapter and panel

The future runner owns key allocation and calls `GatewayStatus.start_epoch(non_secret_epoch_id)` only after establishing an epoch, and `end_epoch()` when it closes. Call `verify_reading(envelope, key)` and forward its return value to the Twin only if it succeeds. Rejected or malformed messages raise an exception and return no reading. `get_status()` returns only `connection_state`, `connection_epoch`, and `verification` (`VERIFIED`, `REJECTED`, or null). The runner must pass only a non-secret identifier; this adapter does not allocate keys or communicate with the Twin.

The shared dashboard imports `renderGatewayPanel` from `web/gateway-panel.js` and calls it with a container and the `gateway` object from its status response, or `null` if unavailable. The panel displays verification, not Twin delivery. Node is only needed for the panel test. The runner does not yet supply live gateway status.

The shared dashboard now loads the gateway panel and passes it `status.gateway`; the runner currently returns null, so it displays unavailable until integration. Nancy's runner should allocate a real key pair before calling `start_epoch`, use the receiving key with `verify_reading`, and forward only the returned reading to the Twin. On authentication or parsing failure it must not call `update_observation`. Never send key bytes or protected payloads in status. Close the epoch via `end_epoch`; key supply interruption alone must not close it.

To check the real sensor, gateway and Twin together with a disposable in-memory key (without starting a server or using the key pool):

```powershell
python -B -m unittest discover -s tests -p test_gateway_component_integration.py -v
```

The isolated tests also exercise the actual `QKDKeyPool` with automatic generation disabled: allocate matching endpoint keys, send multiple readings during interrupted supply, observe an empty pool after closing the epoch, and allocate a fresh key after recovery. This is not evidence that the shared runner, dashboard, or complete timed end-to-end scenario works.
