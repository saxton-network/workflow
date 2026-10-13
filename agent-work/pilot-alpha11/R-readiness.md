# Task R: release readiness

- **Prerequisites:** B `passed`, P `complete`.
- **Read-only** with respect to `main`, tags and releases.

## Checks

- `origin/main` equals the source, checked with no inherited `GIT_*` variables and `git --no-replace-objects -c core.commitGraph=false`; record `gitDivergence` with `identical: true`.
- `bash scripts/validate-repository.sh` passes at the source; Validate CI green on the source.
- No tag and no release (including a draft) named `v0.1.0-alpha.11`.
- Immutable releases still off.
- Tools: workflow dispatch and run read available through the GitHub connection; run cancel available but not exercised; local git version recorded.
- Baseline: every tag and release, and alpha.10's asset digests.

## Frozen batch

Build the ZIP with exactly `git archive --format=zip --prefix=workflow-v0.1.0-alpha.11/ <source> -o workflow-v0.1.0-alpha.11.zip` (a different prefix gives a different hash). As listed in `PLAN.md` under "Release readiness checks": source, local ZIP hash, `release.yml`, `results/R-dispatch-inputs.json`, `results/R-expected-checksum.txt`, four validators, no installed scripts, alpha.10 as rollback identity, three deployment targets.

## Result

`results/R.md` with `readinessVerdict` `PASS`, `FAIL` or `UNKNOWN`, the frozen batch, its fingerprint, and the baseline, plus these files: `results/R-dispatch-inputs.json`, `results/R-expected-checksum.txt`, `results/R-baseline.json` (all tags and releases, alpha.10's asset digests), and `results/R-rollback-alpha10.md` (rollback provenance).

## Records

Hand the result content to the coordinator. Only the coordinator commits to `pilot/alpha11-records`, and nothing under `agent-work/pilot-alpha11/` is ever committed to the implementation or fix branch.

## Forbidden

Dispatching the release, creating tags or releases, or changing `main`.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
