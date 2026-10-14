# Task 001 review packet

Status: implementation prepared for independent review. The implementation is
experimental and repository-only. This packet does not self-certify review or
grant release/deployment authority. Review results and exact candidate identity
will be recorded separately after a read-only review.

## Scope and decisions

Baseline `6b7016f3f2cd150469b71ce62ccd23e147d1f659`, branch
`experimental/features`. The owner authorized Task 001 and cloning this existing
branch. Only this isolated checkout has a mutating agent. Local commits use the
task's no-reply identity; no push, PR, merge, release, or deploy is part of the task.

The [architecture](TASK-001-DESIGN.md) and [threat notes](TASK-001-THREATS.md)
record the repository assessment, provisional status, state machines, approval
semantics, trust boundaries, compatibility, and roadmap. Independent review must
classify findings against the unchanged owner-approved `docs/THREAT-MODEL.md`.

Key choices: Python standard library; strict versioned JSON contracts; a SQLite
transaction per transition; append-only hash-chained full checkpoints and verified
projection; mock-only claims before dispatch; fencing before result acceptance;
explicit retry with frozen reservations; distinct assigned review actor/model;
exact branch/HEAD observation; no provider/session credentials or shell tools.

## Changed files

| Files | Purpose |
| --- | --- |
| `aitism_runtime/contracts.py`, `schemas/*.json` | Plan, state, event, request/result schema v1 plus semantic checks |
| `aitism_runtime/planner.py` | Inspectable objective-to-mock-proposal template |
| `aitism_runtime/store.py` | Durable transactional journal and consistency checks |
| `aitism_runtime/permissions.py`, `runtime.py` | Roles, assignment, scheduling, leases, checkpoints, cancellation/recovery |
| `aitism_runtime/providers.py` | Neutral adapter protocol, capability discovery, deterministic bounded mock |
| `aitism_runtime/git_state.py` | Read-only Git identity checks with accidental environment isolation |
| `aitism_runtime/cli.py`, `__main__.py`, `__init__.py` | JSON Mission Control and local demo |
| `aitism_runtime/README.md`, `docs/experimental/TASK-001-*.md` | Usage, architecture, threats, migration, roadmap, review evidence |
| `scripts/tests/test_aitism_runtime.py` | Mock integration and adversarial regressions |
| `scripts/validate-repository.sh` | Compile runtime; existing discovery includes new tests |
| `.gitignore`, `README.md` | Ignore local state and link the opt-in subsystem |

Unchanged: `scripts/agent-task.py`, its 67-test suite, all v2/v3 manifests, adoption
control files, owner-approved threat model, historical pilot evidence, and release
workflows. New runtime schemas do not supply v3 deployment evidence.

## Verification and reviewer focus

Before editing, the existing repository gate passed 67 tests. The implemented
foundation's first full gate passed 100 tests (67 existing + 33 runtime), and the
mock demonstration completed with 11 durable events. Final candidate verification
and deterministic output hashes belong in the result record.

Run `bash scripts/validate-repository.sh` on the exact candidate. Inspect the demo
with a fresh temporary store:

~~~bash
python3 -B -m aitism_runtime --store /tmp/task001-review.sqlite demo review \
  --objective "Review mock runtime integration" --simulate-approval
~~~

Focus on: no draft/foreign approval dispatch; success-only dependencies; reviewer
ownership; resource aliases across runs; unauthorized role/delegation operations;
late results after expiry/retry/cancel; journal rollback after abrupt process exit;
corrupt projections/checkpoints; unknown telemetry; provider failure and bounded
timeouts; evidence/source mismatch; unchanged existing gate behavior. Verify
errors actually block successors or preserve an unchanged journal.

## Known limitations and unresolved risks

- Proposal compilation and approval are simulation contracts. No independent
  AI plan review or automatic Workflow v3 importer is implemented.
- Local actor names are operator assertions. Authentication is required before
  multi-user or adversarial use; malicious actors remain outside existing scope.
- Branch/worktree ownership is reserved simulation labels in one store, not
  actual provisioning or isolation. Separate stores have no shared ownership lock.
- The provider adapter contract is synchronous; only the bounded mock is enabled.
  Real timeout enforcement, process termination, cancellation, safe handoff,
  external quota reservations, and tool confinement require later work.
- Checkpoints are verified and preserved; retry starts a new deterministic attempt
  rather than resuming arbitrary provider execution. Failed evidence stays failed.
- Unknown provider consumption remains null. Fixed per-attempt mock reservations
  bound retry admission; they do not estimate real provider spend.
- Recovery requires an explicit CLI/API call; there is no background reaper,
  server/UI, authenticated approval service, repair/re-review loop, or memory store.
- Full journal checkpoints and verification are deliberately simple and may be
  expensive for large histories. Schema/database migrations are not implemented;
  unknown versions block. Retention and multi-host SQLite are not supported.
- Git checks pin local exact HEAD/branch, not remote authority or real mutation
  isolation. No live mutation, rollback, release or reconciliation is performed.

These are boundaries for subsequent experimental tasks, not successful proofs
of a full autonomous runtime. The owner-approved threat scope is unchanged.
