# Task R: release readiness

- **Prerequisites:** B `passed`.
- **Read first:** `AGENTS.md`, `PLAN.md`, `CONTRACT.md`.
- **Read-only** with respect to `main`, tags and releases.

## Checks

- **Source:** `origin/main` equals the source, checked with no inherited `GIT_*` variables; record `gitDivergence` `identical: true`.
- **Validation:** `bash scripts/validate-repository.sh` passes at the source in a clean worktree; Validate CI is green on the source.
- **Name is free:** no `v0.0.0-drill.1` tag, and no release with that tag, drafts included.
- **Settings:** immutable releases are off, recorded in `results/R-settings.json`.
- **Baseline:** `results/R-baseline.json`, holding:
  - the full tag list with targets;
  - the full release list, drafts included, with IDs, tags, flags and publish times;
  - alpha.12's asset digests.
- **ZIP:** `git archive --format=zip --prefix=workflow-v0.0.0-drill.1/ <source>`; two builds must be byte-identical.
- **Fault:** the local proof of the injected fault, as `CONTRACT.md` defines it.

## Frozen batch

- `deploymentSourceSha`: the source.
- `deployableArtifactSha256`: the local ZIP hash.
- `deploymentConfiguration`:
  - `.github/workflows/release.yml`
  - `agent-work/pilot-rollback-drill/results/R-dispatch-inputs.json`
  - `agent-work/pilot-rollback-drill/results/R-expected-checksum.txt`
  - `agent-work/pilot-rollback-drill/results/R-expected-checksum-INJECTED.txt`
  - `agent-work/pilot-rollback-drill/results/R-settings.json`
- `validators` (hashed at the source):
  - `scripts/validate-repository.sh`
  - `scripts/check-release-version.sh`
  - `scripts/agent-task.py`
  - `scripts/tests/test_agent_workflow.py`
- `installedScripts`: none.
- `rollbackArtifact`: identity `github-release-v0.1.0-alpha.12`, provenance `agent-work/pilot-rollback-drill/results/R-rollback-alpha12.md`, which holds the release ID, tag SHA `c7ad3c3b1ae3e0a07d7af0322f0688e7d4533c9f` and asset digests.
- `deploymentTargets`, each with `mode: null`:
  - `https://github.com/saxton-network/workflow/releases/tag/v0.0.0-drill.1`
  - `https://github.com/saxton-network/workflow/releases/download/v0.0.0-drill.1/workflow-v0.0.0-drill.1.zip`
  - `https://github.com/saxton-network/workflow/releases/download/v0.0.0-drill.1/workflow-v0.0.0-drill.1.zip.sha256`

Only data files live under `agent-work/pilot-rollback-drill/`; validators come from the source.

## Result

`results/R.md`: the verdict, frozen batch, fingerprint, fault proof and baseline summary. Plus these files:
- `R-dispatch-inputs.json`
- `R-expected-checksum.txt`
- `R-expected-checksum-INJECTED.txt`
- `R-settings.json`
- `R-baseline.json`
- `R-rollback-alpha12.md`

## Records

Hand the result content to the coordinator. Only the coordinator commits to `pilot/rollback-drill-records`.

## Forbidden

Dispatching, creating or deleting tags or releases, changing `main`.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
