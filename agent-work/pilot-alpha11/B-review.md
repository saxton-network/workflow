# Task B: independent review

- **Prerequisites:** A `complete` (or C `complete` after findings).
- **Candidate:** the exact commit named in the latest A or C result; read-only.
- **Reviewer:** an agent independent of the builder (a different model or vendor if available; otherwise a separate agent, recorded as such). The reviewer works read-only and commits to no branch.
- **Read first:** `docs/THREAT-MODEL.md`, `agent-work/EVIDENCE-MANIFEST.md`, `agent-work/pilot-alpha11/CONTRACT.md`, the diff from the base, and the full changed files.

## Work

Run `bash scripts/validate-repository.sh` on the candidate as fresh evidence. Classify every finding against `docs/THREAT-MODEL.md`. Verdict `passed` only when no in-scope finding (Low included) remains in the new code; otherwise `findings`, which go to task C and come back to this same reviewer.

## Result

`results/B-<n>.md`: the reviewer's model, the exact candidate SHA reviewed, its own validation result, verdict, findings with probes, out-of-scope notes.

## Records

Hand the result content to the coordinator. Only the coordinator commits to `pilot/alpha11-records`, and nothing under `agent-work/pilot-alpha11/` is ever committed to the implementation or fix branch.

## Forbidden

Editing the candidate, pushing, merging, or repairing its own findings.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
