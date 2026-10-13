# Task B: independent review

- **Prerequisites:** A `complete` (or C `complete` after findings).
- **Candidate:** the exact commit named in the latest A or C result; read-only.
- **Reviewer:** an agent independent of the builder (a different model or vendor if available; otherwise a separate agent, recorded as such).
- **Read first:** `docs/THREAT-MODEL.md`, `agent-work/EVIDENCE-MANIFEST.md`, the diff from the base.

## Work

Classify every finding against `docs/THREAT-MODEL.md`. Verdict `passed` only when no in-scope finding (Low included) remains in the new code; otherwise `findings`, which go to task C and come back to this same reviewer.

## Result

`results/B-<n>.md`: candidate commit, verdict, findings with probes, out-of-scope notes.

## Forbidden

Editing the candidate, pushing, merging, or repairing its own findings.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
