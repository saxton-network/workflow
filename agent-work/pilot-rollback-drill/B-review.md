# Task B: independent review

- **Prerequisites:** A `complete`.
- **Reviewer:** a separate agent on a different model from the builder. It records independence in words, not as a model identifier.
- **Read first:** `AGENTS.md`, `docs/THREAT-MODEL.md`, `agent-work/WORKFLOW-SPEC.md`, `agent-work/EVIDENCE-MANIFEST.md`, `PLAN.md`, `CONTRACT.md`, `.github/workflows/release.yml`.

## Review

1. The candidate equals `origin/main`, and every commit since `v0.1.0-alpha.12` comes from a reviewed, merged PR.
2. The contract:
   - the declared deviation is honest;
   - the injected fault is isolated to check 4;
   - the expected-failure signature cannot be satisfied by a real defect;
   - the rollback matrix covers every partial state;
   - V's verification proves the exact baseline.
3. Classify each finding against the threat model, with a severity.

## Result

`results/B-1.md` (`B-2.md` after a repair): verdict `passed` or `findings`, the findings, and the checks run.

## Records

Hand the result content to the coordinator. Only the coordinator commits to `pilot/rollback-drill-records`.

## Forbidden

Editing anything; publishing or deleting anything.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
