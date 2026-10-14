# Experimental AItism runtime

Python 3.11+; standard library only. Run from the repository root on
`experimental/features`. Only deterministic mock dispatch is enabled. No
credentials, external API calls, shell execution tools, source writes, Git ref
mutations, or live deployments are available.

See the [provisional architecture](../docs/experimental/TASK-001-DESIGN.md),
[trust boundaries](../docs/experimental/TASK-001-THREATS.md), and
[review packet](../docs/experimental/TASK-001-REVIEW.md).

## Deterministic demonstration

Use a fresh store and workflow ID. The demo records a clearly **synthetic**
approval, executes three mock tasks, and prints the plan, final Mission Control
state, and event hashes. It is not an independent review of this implementation
and its approval is not human/live evidence. The fixed demo clock makes the
output identical for an identical source, objective, ID, and fresh store.

~~~bash
python3 -B -m aitism_runtime --store /tmp/aitism-task001.sqlite demo task001 \
  --objective "Demonstrate a bounded development workflow" --simulate-approval
python3 -B -m aitism_runtime --store /tmp/aitism-task001.sqlite inspect task001
python3 -B -m aitism_runtime --store /tmp/aitism-task001.sqlite journal task001
~~~

Expected final state: workflow `completed`, build `complete`, review `passed`,
validation `complete`, 11 events, 45 reserved mock tokens, 30 reported input
tokens, 15 output tokens, and zero simulated cost. Repeated `advance` performs
no additional dispatch on a completed workflow. Repeated `demo` rejects the
existing ID rather than overwriting its history.

## Inspect and approve before execution

All `--actor` values are trusted local operator assertions, **not authenticated
sessions**. Human approves/enrolls; coordinator advances/recovers; assigned agents
heartbeat/checkpoint. No actor can delegate or change its role. A reference is
the operator's account of approval, not cryptographic evidence of a human action.

~~~bash
python3 -B -m aitism_runtime propose example --objective "Mock a feature" > /tmp/proposal.json
python3 -B -m aitism_runtime --store /tmp/example.sqlite create /tmp/proposal.json --actor human
python3 -B -m aitism_runtime --store /tmp/example.sqlite inspect example
~~~

Read the proposal and copy its `plan_hash` from creation/inspection. After the
human approves that exact simulation proposal, record it explicitly:

~~~bash
python3 -B -m aitism_runtime --store /tmp/example.sqlite approve example \
  --actor human --plan-hash <exact-plan-hash> --reference <approval-record-reference>
python3 -B -m aitism_runtime --store /tmp/example.sqlite enroll example \
  --actor human --agent builder --role builder --task build
python3 -B -m aitism_runtime --store /tmp/example.sqlite enroll example \
  --actor human --agent reviewer --role reviewer --task review
python3 -B -m aitism_runtime --store /tmp/example.sqlite enroll example \
  --actor human --agent validator --role validator --task validate
python3 -B -m aitism_runtime --store /tmp/example.sqlite advance example --actor coordinator
python3 -B -m aitism_runtime --store /tmp/example.sqlite advance example --actor coordinator
python3 -B -m aitism_runtime --store /tmp/example.sqlite advance example --actor coordinator
~~~

One advance runs one eligible task. Failed/unknown results block successors;
review binds the build artifact and source. Proposal source must still match
HEAD and branch at creation, claim, and acceptance. A source commit change blocks
the old run; create a new proposal/run rather than editing its source identity.
The default store `.aitism/runtime.sqlite` is ignored by Git. Prefer a shared
operator-owned store outside the repository when managing several mock runs.

## Interruption and inspection

`claim <id> --actor coordinator --task build` persists a lease without dispatch,
allowing deliberate interruption tests. `heartbeat` and `checkpoint` require
`--task`, `--lease`, and the assigned agent's `--actor`; checkpoint also reads a
JSON object with `--data <path>`. Expired leases cannot be revived by heartbeat.

`recover <id> --actor coordinator` preserves expired attempts as failed and stops
their actors. It never dispatches. `retry <id> --actor coordinator --task build`
explicitly resets a failed mock task within its approved attempt/token ceiling.
The next claim gets a new fence. Old results remain invalid. Unknown consumption
is recorded as null, and each claimed attempt retains a fixed token reservation.
`cancel <id> --actor human` fences current work and prevents future dispatch.
Completed tasks cannot be cancelled or retried.

Journal events are versioned, sequenced, hash-chained full checkpoints. State and
event append commit together. Interrupted transactions roll back; committed
claims survive restart. Projection, journal, or checkpoint corruption returns
`BLOCKED` (exit 2). Do not edit database files to force progress. Preserve the
damaged store for investigation. Back up SQLite with its backup API or with all
runtime processes stopped, not by copying a file during a transaction.

## Interfaces and compatibility

`Runtime` methods require an explicit actor; `Store` is internal trusted
persistence, not a public authorization boundary. `Provider` declares discovery
metadata and `dispatch(request, timeout_seconds=...)`; request/result JSON
schemas are versioned separately from Workflow manifests. The bus only enables
the bounded mock adapter. Real provider cancellation/timeouts and handoff are
design requirements for later tasks.

Machine-readable schemas live in `schemas/`; named schemas reference
`contracts-v1.json`. The runtime validates their used subset plus semantic graph,
ownership, approval, evidence, and checkpoint rules. Unknown fields/versions and
duplicate JSON keys are rejected. `schema_version=1` and SQLite `user_version=1`
are explicit contracts. Existing v2/v3 manifests and historical evidence remain
byte-compatible and are not imported or rewritten.

~~~bash
bash scripts/validate-repository.sh
python3 -B -m unittest discover -s scripts/tests -p 'test_aitism_runtime.py'
~~~

The repository gate discovers these runtime tests alongside the existing suite.
No result here proves live behavior or independent architectural acceptance.
