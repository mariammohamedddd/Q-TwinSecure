# Nancy — Experiment Validation, Reproducibility, Evidence + Small Integration Subtask

## Goal
Own the experiment procedure, validation checklist, reproducibility, and evidence for the 10% PoC. This is not a full implementation role. Start independently by writing scenario steps and expected results using mock events.

## Main tasks
1. Write the normal, interruption, and recovery experiment procedure.
2. Define expected connection, key, reading-delivery, and freshness states.
3. Prepare a manual checklist to validate each person's independent demo.
4. Prepare a results table.
5. Organize screenshots/logs under an `evidence/` folder.
6. Prepare final run instructions and a short limitations statement.
7. Update `IMPLEMENTATION_STATUS.md` only from actual evidence.
8. Record approved scope/architecture changes in `DECISIONS.md`.

## Small integration subtask
After the four component demos run independently:
- Wire the agreed public interfaces through a minimal `main.py`.
- Connect sample sensor reading -> gateway encrypt/decrypt -> Twin update, and use key-pool output for new connection-epoch establishment.
- Run the three agreed scenarios.
- Fix only small wiring/interface issues or report component defects to the owner.

This is a **subtask**, not your whole assignment. Do not rewrite another person's module, take over all debugging, or build a large orchestration framework. Each owner remains responsible for their component.

## Files
```text
experiments/
├── scenario_checklist.md
└── results.md
evidence/README.md
main.py  # minimal integration subtask only
```

## Scenario expectations

### A — Normal
Key supply available; allocate a key for a new epoch; send multiple readings over that epoch; Twin reports CURRENT.

### B — Interruption
Interrupt new key generation; existing epoch remains active; readings can continue on it. End the epoch and request a new one; if no key is available, establishment fails. Once the active epoch ends, delivery stops; Twin becomes DELAYED then MISSING according to configured thresholds.

### C — Recovery
Resume supply, replenish pool, establish a new epoch, resume readings, Twin returns to CURRENT.

## Results table
| Scenario | Keys available | Connection state | Readings delivered | Twin freshness | Pass/Fail |
|---|---:|---|---:|---|---|
| Normal | | | | | |
| Supply interrupted; old epoch active | | | | | |
| New epoch requested with no key | | | | | |
| Recovery | | | | | |

## Acceptance
Procedure exists; each component is independently tested by its owner; minimal integration demonstrates all scenarios; evidence/results are saved; limitations are clear.

## Not assigned
Implementing key-pool, sensor, AES-GCM, or Twin internals; owning all component debugging; building a large dashboard.
