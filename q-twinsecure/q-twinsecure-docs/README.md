# Q-TwinSecure

**Industrial Security Gateway with QKD Emulation and a Trust-Aware Digital Twin**

Q-TwinSecure is a research prototype that explores how constrained, software-emulated key availability can affect secure industrial monitoring and the freshness of Digital Twin observations.

> **Important scope statement:** The current target is a small **10% proof of concept (PoC)** to demonstrate feasibility. It is not a production-ready industrial security platform and does not implement physical quantum communication.

## 1. Project goal

Demonstrate a simple end-to-end flow in which:

1. A simulated CO₂ sensor produces readings.
2. A software key service supplies matching key material to two endpoints.
3. A gateway protects sensor observations before transmission.
4. A receiving endpoint verifies and decrypts the observations.
5. A minimal Digital Twin view displays the latest observation and its freshness.
6. A controlled key-supply interruption demonstrates how key availability can affect a *new* secure connection and, consequently, observation delivery and freshness.

The main question is:

**How does constrained emulated key supply affect secure connection establishment/renewal and the freshness of Digital Twin observations?**

The team is planning one integrated local dashboard for the committee. Each member owns a backend contribution and a visual section; see [plan.md](plan.md). The integrated local runner and all four owner panels are available on branch `Nancy`; automated API scenarios pass, and browser/team review remains pending. See [startup and review instructions](../experiments/scenario_checklist.md).

## 2. Current PoC scope

### In scope
- Python-based CO₂ sensor simulator.
- Software-emulated key supply using Python's cryptographically secure random generator.
- Bounded, in-memory key pools for the device-side and Twin-side endpoints.
- A minimal secure gateway demonstration.
- Authenticated encryption (AES-GCM) for protected messages.
- A shared local dashboard showing sensor, key, gateway, Twin and experiment states.
- A repeatable normal → interruption → recovery experiment.
- Basic tests and clear logs.

### Explicitly out of scope for this PoC
- Physical QKD hardware, photons, or quantum links.
- Claims of quantum security or quantum-generated entropy.
- A full BB84 protocol implementation.
- A physical CO₂ sensor or industrial deployment.
- Production-grade key management, secure hardware storage, or high availability.
- Full ML anomaly detection and LLM-generated incident explanations.
- Cloud-scale deployment, complex orchestration, or production infrastructure.

These may be considered in later project phases only if the team agrees and the schedule permits.

## 3. Core demonstration

| Phase | Key supply | Secure connection | Sensor observations | Twin freshness |
|---|---|---|---|---|
| Normal | Available | Established | Delivered | CURRENT |
| Supply interrupted; existing connection remains active | No new keys | Existing connection continues | May continue on that connection | CURRENT while fresh readings arrive |
| A new connection/connection epoch is required | No available key | Establishment/renewal fails | Delivery stops | DELAYED, then MISSING |
| Recovery | Supply resumes and keys are replenished | New connection can be established | Delivery resumes | CURRENT again |

**Do not model key-supply interruption as automatically killing an already established connection.** The research design distinguishes key consumption for a new protected connection epoch from the multiple measurements that can travel over an established connection.

## 4. Repository map

```text
q-twinsecure/
├── README.md
├── PROJECT_CONTEXT.md
├── ARCHITECTURE.md
├── IMPLEMENTATION_STATUS.md
├── TASKS.md
├── EXPERIMENT_PLAN.md
├── AI_GUIDELINES.md
├── DECISIONS.md
├── requirements.txt
├── qkd/
│   ├── __init__.py
│   └── key_pool.py
├── gateway/
├── sensor/
├── digital_twin/
├── tests/
└── main.py
```

The Markdown documents are the shared source of truth for contributors and AI assistants. Update them whenever scope, architecture, implementation status, or decisions change.

## 5. Getting started

Windows PowerShell example:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If `requirements.txt` has not yet been created, install the current dependency:

```powershell
pip install cryptography
```

Run the application once the entry point is implemented:

```powershell
python main.py
```

Run tests once tests are added:

```powershell
python -m pytest
```

## 6. Team workflow

Before implementing a task:

1. Read `PROJECT_CONTEXT.md`, `ARCHITECTURE.md`, `IMPLEMENTATION_STATUS.md`, and `AI_GUIDELINES.md`.
2. Check `TASKS.md` to avoid duplicating work.
3. Confirm interfaces with the team before changing shared data structures or message formats.
4. Implement the smallest testable increment.
5. Add or update tests.
6. Update `IMPLEMENTATION_STATUS.md` and mark tasks accurately.
7. Record important design changes in `DECISIONS.md`.

Never mark something as implemented merely because code was drafted or generated. It is implemented only after it exists in the repository and has been run or tested successfully.
