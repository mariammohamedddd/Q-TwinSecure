# Q-TwinSecure — 10% PoC Team Assignments

## Purpose
This is a small, simple, effective proof of concept—not the full research implementation. Each person must be able to start and demonstrate their component independently, using local sample data or mocks. Nobody should wait for another person's code.

## Assignments

| Person | Independent task | Output |
|---|---|---|
| Marwan | Emulated QKD key pool | Runnable key-pool demo and tests |
| Mariam Mohamed | CO₂ sensor simulator | Runnable timestamped-reading demo |
| Mariam Wael | Digital Twin freshness monitor | Runnable monitor demo using sample readings |
| Kareem | AES-256-GCM gateway demonstration | Runnable encrypt/decrypt and tamper-rejection demo |
| Nancy | Integration, scenario controls and evidence | Integrated runner, dashboard controls and reproducible results |

## Committee demo: full-stack ownership

The team will build one local dashboard backed by the real Python components. Each owner implements their domain logic, safe status interface and corresponding visual panel. Nancy owns shared orchestration and the dashboard shell; coordinate shared changes before editing them. See [plan.md](plan.md) for phases, paths, contracts and review gates. The dashboard is planned, not yet implemented.

| Person | Backend responsibility | Frontend responsibility |
|---|---|---|
| Marwan | Key-pool status and supply operations | Key supply, counts and interruption indicator |
| Mariam Mohamed | Sensor readings and safe status | Sensor value, ID and timestamp |
| Kareem | Encryption/decryption and safe gateway status | Protection, verification and connection status |
| Mariam Wael | Twin observation and freshness status | Latest accepted reading, age and freshness |
| Nancy | Integrated scenario runner, local API and evidence | Dashboard shell, scenario controls and event/result display |

## Independence rules
- Start immediately; do not wait for another component.
- Do not import unfinished teammate code to complete your own task.
- Use `INTERFACE_CONTRACT.md` as the shared contract.
- Every component must have its own demo and basic tests.
- Use local mock/sample data where necessary.
- No circular imports.
- Each owner fixes their own component; Nancy only coordinates/wires the agreed interfaces.

## PoC scope
**Included:** simulated CO₂ readings; software-emulated key supply using `secrets`; bounded matching in-memory pools; AES-256-GCM message protection; Twin freshness states; normal/interruption/recovery experiment.

**Excluded:** physical QKD, photons, quantum channel, BB84, physical sensor, production deployment, cloud/Docker, full ML anomaly detection, LLM explanations, production key management. Full TLS 1.3 external-PSK integration is not assumed unless the assessment explicitly requires it and the team approves it.

## Behaviour that must be preserved
1. Key material is generated with classical cryptographically secure randomness; do not claim physical QKD or quantum secrecy.
2. Allocate a key for a new protected connection epoch, not for every sensor reading.
3. Multiple readings may travel over an established epoch.
4. Key-supply interruption does not automatically terminate an active connection.
5. A new epoch request fails if no key is available.
6. AES-GCM must use a unique 12-byte nonce per encryption under the same key.
7. Never print or commit raw keys, PSKs, or secrets.

## Definition of done
Code is saved in the agreed path, runs independently, has normal and relevant failure/boundary tests, has short run instructions, and has actual test results recorded. Drafted code is not automatically implemented code.

## Integration ownership
Nancy's main task is experiment validation and evidence. Nancy owns the shared integration runner, local API, dashboard shell and scenario controls. Each owner connects and tests their own panel and fixes their own component. See [plan.md](plan.md).
