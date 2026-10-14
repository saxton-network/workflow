# Task B: release review

- **Prerequisites:** A `complete`.
- **Reviewer:** a separate agent, pinned to a different model from the one that built every change under review. The coordinator checks the model observed in the reviewer's own transcript in every round and records it in words in `results/B-n.md` (`model: null` in the evidence). A same-model review is a deviation, not independence.
- **Read first:** `AGENTS.md`, `docs/THREAT-MODEL.md`, `agent-work/WORKFLOW-SPEC.md`, `agent-work/COORDINATOR.md`, `PLAN.md`, `CONTRACT.md`, and the diff `84d826a..<candidate>`.

## Review

This review is on top of the per-PR reviews already done.

1. **The candidate.** It is exactly `origin/main`, and every commit since `84d826a` belongs to a merged PR (#22, #24 and #25).
2. **The release as a whole,** against `docs/THREAT-MODEL.md`:
   - the helper after #25 (a manifest `failed` status closes the live gate), replayed on the earlier pilot records under `agent-work/`;
   - the full test suite on Python 3.11, 3.12 and 3.13;
   - docs consistent with each other and with the code.
3. **Nothing private in the ZIP** (`git archive` of the candidate): no tokens or keys, no real email addresses other than the no-reply trailer, no personal names other than the owner's public username, no local machine paths, no session links in shipped files, no private repository names.
4. **`CONTRACT.md`:** the evidence clients and the acceptance window, the dispatch rules, acceptance checks, the `liveStateChanged` proof, the rollback matrix, and the retry boundary.

Classify each finding against the threat model, with a severity. If the review is not clean after two repair rounds, the run stops. Verdict `passed` (no in-scope High or Medium) or `findings`.

## Evidence

A `passed` record carries `deploymentSourceSha` equal to the latest candidate: A's `candidateSha`, or C's after a repair.

## Result

`results/B-1.md`, and `B-2.md` after a repair.

## Records

Hand the result content to the coordinator. Only the coordinator commits to `pilot/alpha14-records`.

## Forbidden

Editing anything; dispatching; commenting on GitHub.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
