# Committee presentation: automatic scenario walkthrough

Stop the old server with Ctrl+C, then run from q-twinsecure:

```powershell
py -B main.py --presentation
```

Open http://127.0.0.1:8000 and press Ctrl+F5. Open the page before presenting, then click **Replay all scenarios** so the committee sees the sequence from its beginning. No individual supply, send or clock clicks are needed. The sequence also appears on /twin, and navigation never starts a second runner.

## What the audience sees

| Step | Demonstration | Real result to explain |
| --- | --- | --- |
| 1 | Bounded key supply | One pair fills a capacity-one pool; additional generation returns zero. |
| 2 | Normal delivery | Multiple authenticated readings arrive using exactly one epoch allocation; Twin CURRENT. |
| 3 | Tampered message | A real encrypted message is modified; gateway REJECTED, rejected count increases, Twin observation/delivery count unchanged. |
| 4 | Interrupted supply, active epoch | Generation stops while readings still arrive over the same epoch. |
| 5 | New epoch with no key | Runner explicitly ends the epoch; empty-pool establishment fails, gateway disconnected. |
| 6 | DELAYED | Real age crosses the configured current threshold without a new observation. |
| 7 | MISSING | Real age exceeds the missing threshold; the last accepted value stays visible. |
| 8 | Recovery | Supply resumes; one fresh pair establishes a different epoch and readings return the Twin to CURRENT. |
| 9 | Complete | Verified outcomes remain available; healthy recovered readings continue on that epoch. |

The banner displays the current step, explanation, progress, and completed checks under **Verified outcomes**. Activity records the real actions and expected failures. A failed check stops the sequence visibly; no fake passing status is substituted.

Default pacing is about 50 seconds: the full pool is shown for 4 seconds, normal/interrupted/recovery delivery for about 8 seconds each, rejection for 4 seconds, then actual 5/15-second freshness boundaries and a 4-second MISSING hold. Some timing varies with sampling/scheduling. The gap takes real time; it is not a frontend animation.

Optional slower pacing:

```powershell
py -B main.py --presentation --presentation-hold 6
```

Pool and MISSING holds use that value; delivery phases use twice that value. The rejection hold is capped below the current threshold so an unrelated stale-data transition does not obscure rejection. DELAYED/MISSING transitions always wait for actual configured age. The presentation requires current_threshold > reading_interval.

## Operating behavior

- The scenario owns key generation and epoch lifecycle using real component methods. It fixes the pool at one pair and disables autonomous replenishment so the empty-pool failure is guaranteed.
- A shared monotonic real clock drives readings and freshness. Epoch closure is scripted at the named checkpoint, rather than the continuous-monitor epoch timer.
- On completion, recovered readings continue using the established recovery epoch. The scenario does not automatically loop or renew it; the results remain readable. Replay recreates all components and begins again.
- Reset also replays. Other action endpoints reject individual interventions in this mode to keep results reproducible.
- `--automatic` remains continuous monitoring. No flag selects manual operation. These are three distinct modes.

The sensor and factory are simulated; QKD supply is software-emulated with classical randomness. Message protection uses direct AES-GCM, not TLS or physical QKD. This walkthrough covers the agreed PoC scenarios, not every production failure/security condition.

## Verification

89 Python tests and 8 Node test entries passed. Presentation tests observed all nine stages, real rejection, unchanged delivery/observation during the gap, new-epoch recovery, replay isolation and background progression without API polling. A real default-speed browser preview displayed the no-key stage with a disconnected gateway, one rejection, preserved observation and live age; screenshot in evidence/guided-presentation.png. Full mobile/presenter rehearsal remains pending.
