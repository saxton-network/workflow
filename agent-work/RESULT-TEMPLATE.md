# Agent task result

Use this template unless the task defines a stricter result format.

This file is a human/coordinator-readable handoff format. `scripts/agent-task.py` does not parse or enforce every prose field in this template. Machine-enforced deployment gating comes from the workflow manifest and coordinator-owned `evidence.json`; the coordinator/reviewer remains responsible for verifying claims recorded here.

## Identity

- Workflow/task:
- Branch:
- Worktree:
- Candidate commit:
- Base commit:
- Exact reviewed implementation/deployment-source commit, if applicable:
- Result/evidence commit, if different:

## Scope completed

- [Describe only work actually performed.]

## Claim/evidence matrix

| Claim | Fresh evidence | Result |
| --- | --- | --- |
| [Example: repository validation passes] | `scripts/validate-repository.sh` at candidate commit | PASS / FAIL / NOT RUN |

Rules:

- Every success/completion claim needs fresh evidence from the candidate being handed off.
- Include exact commands or inspections and the meaningful exit/result summary; do not paste secrets or a redundant full command diary.
- A previous run is stale after relevant candidate changes.
- A deterministic result may be reused only with identical candidate,
  source/config, dependency, validator, material toolchain, and fixture inputs.
  Mutable host, network, permission, and remote-ref checks need fresh evidence.
- A subagent report is not proof of its own claim; coordinators/reviewers verify the diff and required checks independently.
- Repository evidence does not prove deployment authority or live deployment.

## Git state

- Intended files changed:
- Unexpected/unrelated changes:
- Working state:
- Deployment-authoritative state:
- Live deployed state:

Use `unknown` when a state was not verified. Do not infer authority/deployment from GitHub.

## Validation evidence

- Baseline before edits:
- Final repository validation:
- Feature-specific validation:
- Live/read-only validation, if applicable:
- Checks not run and why:

For v3 release readiness, also report `readinessVerdict` (`PASS`, `FAIL`, or
`UNKNOWN`) separately from task status. Record any contract-accepted unknown
check by name and reason; an unresolved required unknown blocks the overall
PASS. Include the canonical frozen-batch input and SHA-256 fingerprint, exact
source/artifact/config/script/validator identities, rollback provenance,
the explicit deployment target destination/mode metadata (plus owner/group when
applicable), prevalidated check results, live-only checks, proposed batch, and
evidence links. `complete` alone does not permit a live approval preview. For a live
attempt, record the approval reference tied to that fingerprint, immediate
drift recheck, runtime acceptance, and rollback result when needed.

Link detailed evidence and provide SHA-256 hashes for the coordinator's
`evidence.json` index; do not edit the index from a child task. Use `unknown`
or `null` for unavailable metrics and approvals rather than inferring them.
Keep secrets and unnecessary complete response bodies out of results.

## Findings / limitations

- [Known caveats, failures, unknowns, or intentionally deferred work.]

## Recovery / rollback

- [Only when the task changed something that requires recovery instructions.]

## Stop boundary

Task work stops here and returns to the coordinator/user. Do not silently continue into another task.
