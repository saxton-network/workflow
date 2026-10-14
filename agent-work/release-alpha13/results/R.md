# Task R: release readiness

Performed by the coordinator on 2026-10-14. Read-only with respect to `main`, tags, releases and settings. The main freeze is in effect from this task.

**Verdict: PASS**

- Source: `84d826a40b8f8567439ab15eb270a1a752f92a82`
- Frozen batch fingerprint: `f2c2d628b1aa24e87e93f3afcd392b8f3c0745f10519ab04ba6e1352ed626960`, computed with `batch_fingerprint` from `scripts/agent-task.py` read at the source

## Checks

| Check | Result |
| --- | --- |
| `origin/main` equals the source | PASS. After a fresh fetch, `git --no-replace-objects -c core.commitGraph=false rev-parse origin/main` (no inherited `GIT_*` variables) printed the source; `git rev-parse --is-shallow-repository` is `false`. `gitDivergence` `identical: true`. |
| `validate-repository.sh` at the source | PASS, in a clean detached worktree (empty `git status --porcelain`). |
| Validate CI on the source | PASS: run 38493376355. |
| Name is free | PASS. `GET …/git/ref/tags/v0.1.0-alpha.13` 404; `GET …/releases/tags/v0.1.0-alpha.13` 404; `git ls-remote --tags origin` lists alpha.1–alpha.12 only; the authenticated release list (`list_releases`, 12 releases, no drafts) has no alpha.13. |
| Rollback possible | PASS. Immutable releases `{"enabled": false, "enforced_by_owner": false}`; rulesets `[]` (`results/R-settings.json`). |
| Identity and draft visibility | The GitHub connection acts as `caffeinatedcultist`, an account with write access, so drafts are visible to it. |
| Tools | Proven: workflow run lists (`actions_list`), job-step reads (`list_workflow_jobs`, used in Pilot 5), release reads (`list_releases`, `get_release_by_tag`). Dispatch and cancel (`actions_run_trigger` `run_workflow` / `cancel_workflow_run`) are present; dispatch was used in Pilots 3–5, cancel has not been exercised. No tool here deletes a release or tag; the owner does any deletion. |
| Local git | `git version 2.43.0`. |
| Reproducible ZIP | PASS. Two builds of `git archive --format=zip --prefix=workflow-v0.1.0-alpha.13/ <source>` are byte-identical: SHA-256 `e520b61c3c48572b73001d333b2c79499e33b3e5c19f34988d5be2f3e191d5d4`, 161870 bytes. The independent reviewer computed the same hash separately. The same command at `c7ad3c3` reproduces alpha.12's published digest `8d93a574…a211ba6`. |
| Expected `.sha256` | `results/R-expected-checksum.txt`, made with `sha256sum workflow-v0.1.0-alpha.13.zip` in the ZIP's directory, 95 bytes, matches `^[0-9a-f]{64}  workflow-v0\.1\.0-alpha\.13\.zip\n$`. |
| Baseline | `results/R-baseline.json`: 12 tags with targets, 12 releases (no drafts) with IDs, flags and publish times, alpha.12's asset digests, latest `release.yml` run 38374361610 (run 12). |

## Frozen batch

- `deploymentSourceSha`: `84d826a40b8f8567439ab15eb270a1a752f92a82`
- `deployableArtifactSha256`: `e520b61c3c48572b73001d333b2c79499e33b3e5c19f34988d5be2f3e191d5d4`
- `deploymentConfiguration`:
  - `.github/workflows/release.yml` (source) `57c20477be82406b9053d9945d48ac53e5bad8a11068d38b72c2d25c21da9562`
  - `agent-work/release-alpha13/results/R-dispatch-inputs.json` `a5ffa35ff0fc8f3a9d80630e72c75b73d6242dffb7ba5d7e2071cfaaf5f0d62c`
  - `agent-work/release-alpha13/results/R-expected-checksum.txt` `682c24ea849181807521e89b938cab9bde3e3712daecd4e05233d18ab603c939`
  - `agent-work/release-alpha13/results/R-settings.json` `866a993ebd1026b836ccb02d74567adfdaab7020559d0554f79e9058c6610f22`
  - `agent-work/release-alpha13/CONTRACT.md` `7062981aa73a1e356d4e1399e1bccb294e632f468787f610f7e6e8d8e5155355`
- `validators` (at the source):
  - `scripts/validate-repository.sh` `45eba69bf41f17ca4d1ea646e4d4bc8e3bcd1cf407a8ae3b698effe1032a2ebe`
  - `scripts/check-release-version.sh` `939911f6527179a3171d5e1f1db222b37af2d477ab8d1d396a9ce74426a8c075`
  - `scripts/agent-task.py` `67fa523bd62cf21ad53d969460074982baff1f5b5e1312a086b953e0138f4434`
  - `scripts/tests/test_agent_workflow.py` `0d1fbfbe65739caadd1656e2f75b1ccf9208650f395bf903e16bd23393b8e9d3`
- `installedScripts`: none
- `rollbackArtifact`: `github-release-v0.1.0-alpha.12`, provenance `agent-work/release-alpha13/results/R-rollback-alpha12.md`
- `deploymentTargets` (mode `null`): the release page, the two download URLs, and the tag ref `https://api.github.com/repos/saxton-network/workflow/git/ref/tags/v0.1.0-alpha.13`. All four pass the helper's destination format.

## Plan clarification in effect

The B5 clarification (2026-10-14): acceptance check 2 names both assets, requires "not a draft", and checks the title. It is in the frozen `CONTRACT.md`.
