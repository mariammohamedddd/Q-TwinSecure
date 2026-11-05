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
| Nancy | Experiment validation and evidence | Scenario checklist, results, evidence; small integration subtask |

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

## Integration subtask
Nancy's main task is experiment validation and evidence. As a **small subtask only**, after the components work independently, she wires their agreed public interfaces through a minimal `main.py` and runs the three scenarios. She does not rewrite or own the other components.
