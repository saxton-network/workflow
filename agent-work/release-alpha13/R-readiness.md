# Task R: release readiness

- **Prerequisites:** B `passed`.
- **Read first:** `AGENTS.md`, `PLAN.md` "Readiness checks (R)", `CONTRACT.md`.
- **Read-only** with respect to `main`, tags, releases and settings. The main freeze starts here.

## Checks

As `PLAN.md` "Readiness checks (R)" lists them:

- source equals `origin/main` (`gitDivergence` `identical: true`, in a non-shallow clone, no inherited `GIT_*` variables); `validate-repository.sh` passes at the source in a clean worktree; Validate CI green;
- no `v0.1.0-alpha.13` tag (API ref and `git ls-remote`) and no release or draft with that name; record the identity that read drafts;
- `results/R-settings.json`: immutable releases off; rulesets empty;
- tools: workflow dispatch, run reads and job-step reads (`list_workflow_jobs`) proven available; run cancel present but not exercised; the GitHub identity and local git version recorded;
- ZIP built twice, byte-identical; alpha.12's published ZIP reproduced from `c7ad3c3`;
- `results/R-expected-checksum.txt` made as `release.yml` makes it, matching `^[0-9a-f]{64}  workflow-v0\.1\.0-alpha\.13\.zip\n$`;
- `results/R-baseline.json`: every tag with target, every release (drafts included) with ID, tag, flags and publish time, alpha.12's asset digests, the latest `release.yml` run ID.

## Frozen batch

Exactly as `PLAN.md` lists it. Validators are hashed as read at the source, not from the records branch. `results/R-rollback-alpha12.md` holds alpha.12's tag target and verified asset digests. Commit the `agent-work/release-alpha13/results/R-*` files on the records branch before hashing them. Compute the fingerprint with `batch_fingerprint` from `scripts/agent-task.py` at the source.

## Result

`results/R.md` (verdict, checks, frozen batch, fingerprint), `R-baseline.json`, `R-settings.json`, `R-rollback-alpha12.md`, `R-dispatch-inputs.json`, `R-expected-checksum.txt`.

## Records

Hand the result content to the coordinator. Only the coordinator commits to `pilot/alpha13-records`.

## Forbidden

Dispatching; changing `main`, tags, releases or settings.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
