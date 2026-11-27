# Coding Agent guidance

When asked to work on a ByteMe Phase 2 task:

1. Find the task by Task ID in [`docs/phase2/TASK_TRACKER.md`](docs/phase2/TASK_TRACKER.md). Check its dependencies, scope, owner and acceptance criteria before changing anything. Do not start dependent work whose prerequisites are incomplete. For sequential G4-B work on the same branch, a prerequisite may be treated as locally complete when its deliverable has a local Task-ID commit and its technical acceptance evidence is recorded in the tracker; this only opens the next local implementation task and does not change the prerequisite to `DONE` before the Git workflow conditions are met.
2. Follow [`docs/phase2/GIT_WORKFLOW.md`](docs/phase2/GIT_WORKFLOW.md) for branch, commit, review and tracker conventions. Do not commit or push unless explicitly requested.
3. For G4 tasks, read the corresponding implementation plan
   and ADR in `docs/phase2/03_ARCHITECTURE_DECISIONS.md`:
   - G4-A: `implementation/G4-A_CONCURRENCY.md`, ADR-001.
   - G4-B: `implementation/G4-B_DATA_ACCESS.md`, ADR-002.
   - G4-C: `implementation/G4-C_DEPENDENCY_BOUNDARIES.md`, ADR-003.
   - G4-D: `implementation/G4-D_FAIL_CLOSED_AUTHORIZATION.md`, ADR-004.
   Read only the relevant sections.
4. Follow the agreed method/file ownership, task dependencies,
   implementation scope and merge order in the project documents.
   Do not modify another workstream's owned methods or tests
   without explicit approval. Do not broaden scope or start
   another task unless requested.
5. Read only source code, tests and documentation directly relevant to the requested task. Consult Requirements, System Assessment, Baseline Benchmark or evidence only when needed to resolve that task. Do not repeat completed work or perform a project-wide audit.
6. Run only the tests and verification gates required for the task's acceptance criteria.
7. Report briefly: changed files/behavior, tests and verification results, acceptance status, and any blockers.
