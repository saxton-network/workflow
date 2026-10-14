# AItism Experimental Development: Task 001 result

Implemented the isolated mock-only Workshop/runtime/Mission Control foundation
on `experimental/features`. No push, PR, merge, release, deployment, real provider
call, credentials, unrestricted execution, or existing gate mutation occurred.

## Identity and scope

- Inspected clean baseline: `6b7016f3f2cd150469b71ce62ccd23e147d1f659`.
- Origin: `https://github.com/saxton-network/workflow.git`.
- Final reviewed source candidate: `cf0f19d9b12c7a1bf95d63decff57e548e013f9c`.
- Architecture commit: `937c8b4`.
- Foundation implementation/test commit: `2ea338c`.
- Separate repair commit: `cf0f19d`.
- This result and review-packet update are a later documentation/evidence commit,
  distinct from the reviewed source and simulated run source.

Delivered the [provisional architecture and roadmap](TASK-001-DESIGN.md),
[component threat notes](TASK-001-THREATS.md), [review packet](TASK-001-REVIEW.md),
and [runtime package/CLI guide](../../aitism_runtime/README.md). The package contains
versioned plan/state/event/request/result schemas, strict semantic validation,
durable agent/workflow state, append-only SQLite journal, provider-neutral
contracts and mock adapter, ownership-aware dependency scheduler, explicit role
checks, lease fences/heartbeats/checkpoints, cancellation, explicit recovery/retry,
resource reservations and nullable telemetry, and JSON Mission Control.

The demonstrated sequence is objective -> inspectable simulation proposal ->
explicitly synthetic demo approval -> build -> separate mock review -> evidence
validation -> completion. The manual CLI path also requires a separate exact-hash
approval operation; draft claims were verified to fail without changing history.

## Fresh verification

Baseline repository validation passed 67 tests. The same separate reviewer ran
`bash scripts/validate-repository.sh` on final candidate `cf0f19d`: **102 tests
passed** (67 unchanged existing tests and 35 runtime tests), plus example-manifest,
shell syntax, Python compilation, and release-version checks. `git diff --check`
passed. The reviewer observed a clean tracked checkout and exact candidate HEAD.

Critical regressions prove: failed/unknown evidence blocks successors; agents
cannot approve/delegate/expand roles; conflicting worktree/branch claims cannot
dispatch; cancellation/expiry/retry fence old results; provider exceptions do not
retry or expose exception text; malformed approvals, source mismatch, corrupt
checkpoints/projections/journals and unknown versions fail closed; process exit
before commit rolls back state and event together; completed results are
idempotent; failed attempts and unknown telemetry remain inspectable.

Coordinator demonstration at final reviewed source, two fresh stores:

~~~bash
python3 -B -m aitism_runtime --store <fresh-store> demo task001 \
  --objective "Demonstrate a bounded development workflow" --simulate-approval
~~~

Both stdout byte streams were identical. SHA-256:
`eb66ce1dd531d47357751d6a152c097506bcdf10cfd037f3a8ba5415898d1ef4`.
Final workflow `completed`; build `complete`, review `passed`, validation
`complete`; 11 durable events; 45 reserved mock tokens; reported input/output
tokens 30/15; simulated cost zero. Final journal hash:
`581fe09ae0f239ca3fcfd5dfeeb93167ff3a6526d0e0cbeeaeda53211b2c089e`.

The reviewer independently repeated the documented demo twice using ID `review`
and objective `Review mock runtime integration`, with byte-identical stdout
SHA-256 `cb26c28c86d03cb737816d0d7d2a8135da7a98adff675894230f360c8908bb5b`
and the same terminal states/event counts/usage. A changed Git HEAD produces a
different source-bound output hash; it does not invalidate the runnable demo.

## Actual source review and repair

Reviewer `/root/independent_review` was a separate read-only non-builder agent.
Its initial review of `2ea338c` found zero High/Medium and two Low findings, both
in scope under threat-model item 5 (contract/documentation disagreement):

1. Unanchored published schema patterns accepted substrings while runtime spelling
   validation required whole strings.
2. The actor concurrency guarantee did not clearly state workflow-scoped identity.

Separate repair agent `/root/contract_repair` changed only the shared schema,
runtime tests, design document, and runtime guide. All 33 published patterns now
use strict whole-string anchors; parity tests cover prefixes/suffixes, lengths,
SHA alternatives, and newlines. Documentation defines `(workflow_id, agent_id)`
and distinguishes workflow-local actor ownership from store-wide resource labels;
a concurrent regression verifies same-label actors in different runs.

The same reviewer re-reviewed `cf0f19d` and reported **PASS**, both Lows resolved,
and no remaining High/Medium/Low findings within the provisional mock-only scope.
Its initial review also exercised 1,344 malformed-state substitutions without an
unexpected exception class. The coordinator records these as the reviewer's
reported observations, not as self-certification.

The reviewer was requested on a different model, but its exact observed model
identifier was unavailable. Separate-agent/non-builder identity is established;
different-model/vendor independence is **not certified**. No review here grants
human architectural approval for production or live work. Synthetic demo review
and approval never satisfy an existing Workflow v3 gate.

## Compatibility, limitations, and next boundary

The existing read-only helper, its tests, v2/v3 manifests, frozen deployment
fingerprints, approval/source semantics, owner-approved threat model, release
workflows and historical pilot evidence remain unchanged. Runtime schema v1 is
separate; there is no importer, evidence migration, or deployment integration.

Local actor names are trusted operator assertions; real authentication is
deferred. Ownership is of simulation labels in one store, not actual worktree or
process provisioning. The mock adapter is bounded and synchronous; real backend
timeouts, safe provider handoff, process reaping, and external spend controls are
deferred. Recovery preserves checkpoints and failures but retries a new mock
attempt rather than resuming a real session. No background reaper, full UI,
repair graph, or institutional memory store is claimed.

Next work should review/freeze compatibility, then add authenticated identities,
policy-backed delegation and global resource ownership before enabling isolated
workers or real providers. Live mutation remains a separately scoped approval
boundary. The architecture remains provisional for production use.
