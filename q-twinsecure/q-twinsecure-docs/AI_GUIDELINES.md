# Instructions for AI Assistants and Coding Agents

This file is mandatory context for any AI assistant or coding agent used by the team in this repository.

## 1. Start with the project context

Before proposing or changing code, read:

1. `README.md`
2. `PROJECT_CONTEXT.md`
3. `ARCHITECTURE.md`
4. `IMPLEMENTATION_STATUS.md`
5. `TASKS.md`
6. `DECISIONS.md`

Use these files as the current project source of truth. If a task conflicts with them, identify the conflict and ask for clarification rather than silently changing the architecture.

## 2. Preserve the actual project scope

- The current deliverable is a small 10% feasibility PoC.
- Optimize for a working, reproducible end-to-end demonstration.
- Do not turn the PoC into a production system.
- Do not add physical QKD, BB84, physical sensors, ML, LLM explanations, cloud infrastructure, or unrelated features unless the team explicitly approves a scope change.
- Prefer the simplest implementation that proves the stated behavior.

## 3. Be scientifically accurate

- Always call the key mechanism **software-emulated QKD key supply** or **QKD emulation**.
- The emulated key material is generated using classical cryptographically secure randomness.
- Never claim that the PoC performs physical quantum communication, uses photons, implements BB84, or provides quantum secrecy.
- Distinguish the broader research architecture from what is actually implemented in this repository.
- Never claim TLS 1.3 external PSK is implemented if the code only uses direct AES-GCM encryption.
- Explain assumptions, simplifications, and limitations.

## 4. Preserve key lifecycle semantics

- Allocate fresh key material for a new protected connection epoch.
- Allow multiple readings over an established connection epoch.
- Do not consume a new pool key for every reading unless the team explicitly changes and documents the design.
- Interrupting key supply must not automatically terminate an already established connection in the intended model.
- If a new epoch is requested while no key is available, establishment must fail.
- Recovery means key supply resumes, keys are replenished, and a new epoch can be established.

## 5. Security coding rules

- Never print, commit, or expose raw key material, PSKs, credentials, or secrets.
- Use Python `secrets` for cryptographically secure random key generation in the emulator.
- For AES-GCM, never reuse a nonce with the same key.
- Prefer the library's well-reviewed cryptographic APIs; do not implement cryptographic primitives manually.
- Authenticate relevant metadata.
- Reject authentication failures; do not silently accept corrupted or tampered messages.
- Keep key material out of logs, exceptions, screenshots, and sample output.
- Do not invent security guarantees beyond the mechanism actually implemented.
- Keep secrets out of Git. Add `.env` and local secret files to `.gitignore`.

## 6. Engineering rules

- Use small modules with one clear responsibility.
- Keep configuration separate from implementation where practical.
- Use clear names, type hints, and docstrings for non-obvious logic.
- Avoid unnecessary dependencies.
- Add tests for normal, boundary, failure, and recovery cases.
- Do not silently swallow exceptions.
- Do not add large frameworks for a small PoC.
- Preserve existing interfaces unless a change is coordinated.
- Do not overwrite teammates' work without reviewing it.
- Keep commits small and descriptive.

## 7. Collaboration rules for AI-generated changes

When asked to implement a task:

1. State which files will be created or changed.
2. Check existing code before replacing anything.
3. Implement only the requested task.
4. Explain how to run the change.
5. Add or update tests.
6. Report what was actually tested and the exact result.
7. Update `IMPLEMENTATION_STATUS.md` and `TASKS.md` if status changed.
8. List known limitations and follow-up work.

Never say a task is complete merely because code was generated. Do not invent test results, files, commands, or repository state.

## 8. Output expectations

Prefer:
- A short explanation of the design.
- Complete code with exact file paths.
- Exact commands for Windows PowerShell where relevant.
- A small test or reproducible manual check.
- Clear distinction between implemented, proposed, and not tested.

Avoid:
- Long unrelated tutorials.
- Large speculative architecture expansions.
- Unrequested refactoring.
- Fabricated references or unsupported claims.
