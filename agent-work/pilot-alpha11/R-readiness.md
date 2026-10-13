# Task R: release readiness

- **Prerequisites:** B `passed`, P `complete`.
- **Read-only** with respect to `main`, tags and releases.

## Checks

- `origin/main` equals the source; record `gitDivergence` with `identical: true`.
- `bash scripts/validate-repository.sh` passes at the source; Validate CI green on the source.
- No tag and no release (including a draft) named `v0.1.0-alpha.11`.
- Immutable releases still off.
- Tools: workflow dispatch and run read available through the GitHub connection; run cancel available but not exercised; local git version recorded.
- Baseline: every tag and release, and alpha.10's asset digests.

## Frozen batch

As listed in `PLAN.md` under "Release readiness checks": source, local ZIP hash, `release.yml`, `results/R-dispatch-inputs.json`, `results/R-expected-checksum.txt`, four validators, no installed scripts, alpha.10 as rollback identity, three deployment targets.

## Result

`results/R.md` with `readinessVerdict` `PASS`, `FAIL` or `UNKNOWN`, the frozen batch, its fingerprint, and the baseline.

## Forbidden

Dispatching the release, creating tags or releases, or changing `main`.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
