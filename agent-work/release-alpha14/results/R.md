# Task R: release readiness

Performed by the coordinator on 2026-10-14. Read-only with respect to `main`, tags, releases and settings. The main freeze is in effect from this task.

**Verdict: PASS**

- Source: `02c771a7c7d71e2303c186d0c150e903a524e949`
- Frozen batch fingerprint: `2da72c54825b9b6668e958ad72d4dc017b87f229be5920233060c204d04365b1`, computed with `batch_fingerprint` from `scripts/agent-task.py` read at the source

## Checks

| Check | Result |
| --- | --- |
| `origin/main` equals the source | PASS. In a fresh, non-shallow clone, with every inherited `GIT_*` variable removed (a count inside printed 0), `git --no-replace-objects -c core.commitGraph=false rev-parse origin/main` printed the source. `gitDivergence` is `identical: true`. |
| `validate-repository.sh` at the source | PASS, in a clean detached worktree (empty `git status --porcelain`). |
| Validate CI on the source | PASS: run 38523817053. |
| Name is free | PASS. The tag ref for `v0.1.0-alpha.14` returns 404 through the connection and through `curl`. The release by tag returns 404 through both. `git ls-remote --tags` lists alpha.1 to alpha.13 only. The authenticated release list (13 releases, no drafts) has no alpha.14. |
| Rollback possible | PASS. Immutable releases `{"enabled": false, "enforced_by_owner": false}`; rulesets `[]` (`results/R-settings.json`). |
| Identity and draft visibility | The GitHub connection acts as `caffeinatedcultist`, an account with write access, so drafts are visible to it. |
| Evidence access (new) | PASS. Every row of `CONTRACT.md` "Evidence clients" was read on run 38508243210 (alpha.13) and the alpha.13 release. See below. |
| Tools | Workflow dispatch and run cancel are present in the connection, but neither was exercised. Dispatch was used in Pilots 3–6. No tool here deletes a release or tag; the owner does any deletion. |
| Local git | `git version 2.43.0`. |
| Reproducible ZIP | PASS. Two builds of `git archive --format=zip --prefix=workflow-v0.1.0-alpha.14/ <source>` are byte-identical: SHA-256 `1b87fa4a7034e58efaf0c8479b93bb82d4d3bad2c8fb3b467da4f27627d98355`, 207427 bytes. The independent reviewer computed the same hash separately in B-1. The same command at `84d826a` reproduces alpha.13's published digest `e520b61c…d5d4`. |
| Expected `.sha256` | `results/R-expected-checksum.txt`, made with `sha256sum workflow-v0.1.0-alpha.14.zip` in the ZIP's directory, 95 bytes, matches `^[0-9a-f]{64}  workflow-v0\.1\.0-alpha\.14\.zip\n$`. |
| Baseline | `results/R-baseline.json`: 13 tags with targets; 13 releases (no drafts) with IDs, flags and `published_at`; no latest release; alpha.13's asset digests; latest `release.yml` run 38508243210 (run 13 of 13). |

## Evidence access

Each item was read with the client the contract names:

| Item | Primary (connection) | Fallback (`curl`) | Agree |
| --- | --- | --- | --- |
| Run list, `head_sha`, conclusion | Run 38508243210: `completed`, `success`, `head_sha` `84d826a…` | none | — |
| Job-step list | Job 115670580747: 13 steps, including "Create release tag at the validated commit" (`success`) | none | — |
| Release by tag (alpha.13) | ID 412320357, title, `draft: false`, `prerelease: true`, `published_at` 03:49:47Z, two assets | The same values | yes |
| Not latest | `/releases/latest` 404 (the connection's error names the 404 status) | 404 | yes |
| Release list, drafts included | 13 releases, no drafts | none | — |
| Asset `digest` fields | `sha256:e520b61c…d5d4` (ZIP), `sha256:682c24ea…c939` (`.sha256`) | (`curl` returned the same values in the release read) | yes |
| Asset bytes | — | Both downloads 200. The ZIP is 161870 bytes with SHA-256 `e520b61c…`. The `.sha256` is 95 bytes with SHA-256 `682c24ea…`. Both equal the `digest` fields. | yes |
| Tag ref and `object.type` | `refs/tags/v0.1.0-alpha.13`, `commit`, `84d826a…` | The same | yes |
| Tags, `refs/heads/main` | — | `git ls-remote`: 13 tags; main `02c771a…` | — |
| Absent alpha.14 tag ref and release | 404, 404 | 404, 404 | yes |
| Job log (diagnostic only) | Read successfully (the job's final lines) | none | — |

- **`curl` is authenticated by the proxy.** `curl`'s requests go through the session's network proxy, which adds the session's GitHub credentials: the rate limit is 15,000 per hour, with 14,962 remaining at these reads, and an authenticated-only endpoint answers. Acceptance makes at most about 10 `curl` requests per round. The plan described `curl` as unauthenticated. That is corrected as a dated clarification, and the contract's wording was fixed before it was hashed. No rule changes.
- **404 is evidence.** The connection reports a 404 as an error that names the status. So a 404 is evidence, not a missing read.

## Frozen batch

- `deploymentSourceSha`: `02c771a7c7d71e2303c186d0c150e903a524e949`
- `deployableArtifactSha256`: `1b87fa4a7034e58efaf0c8479b93bb82d4d3bad2c8fb3b467da4f27627d98355`
- `deploymentConfiguration`:
  - `.github/workflows/release.yml` (at the source; unchanged since alpha.13): `57c20477be82406b9053d9945d48ac53e5bad8a11068d38b72c2d25c21da9562`
  - `agent-work/release-alpha14/results/R-dispatch-inputs.json`: `4c28473f304ccdd3ee2ab63a9abbd8adcc2fd3957bd5e29a2caed41cc5ef90e3`
  - `agent-work/release-alpha14/results/R-expected-checksum.txt`: `54426f84ac978f86c18dafe06fc21346ec4838e75f9742b65b466c2fa5305f99`
  - `agent-work/release-alpha14/results/R-settings.json`: `61abd035b63518eb1d2fbc0fff10b607f7b7fe9cf869b48da95cc5daf9fe44d3`
  - `agent-work/release-alpha14/CONTRACT.md`: `5bdda18bde8839e1f79f4a788a61a7174a559962d3eea2dbb7d3375837b3f765`
- `validators` (at the source):
  - `scripts/validate-repository.sh`: `45eba69bf41f17ca4d1ea646e4d4bc8e3bcd1cf407a8ae3b698effe1032a2ebe`
  - `scripts/check-release-version.sh`: `939911f6527179a3171d5e1f1db222b37af2d477ab8d1d396a9ce74426a8c075`
  - `scripts/agent-task.py`: `8ec1b22cd97d10e1873ed9dfa83a37fa58f036914452f1af6508564215748f3c`
  - `scripts/tests/test_agent_workflow.py`: `d4c60b087a1ab5717303f7c13c6b8d5384dade9c30d686c4d15a6fbe2cf4ceb4`
- `installedScripts`: none
- `rollbackArtifact`: `github-release-v0.1.0-alpha.13`, provenance `agent-work/release-alpha14/results/R-rollback-alpha13.md`
- `deploymentTargets` (mode `null`): the release page, the two download URLs, and the tag ref `https://api.github.com/repos/saxton-network/workflow/git/ref/tags/v0.1.0-alpha.14`

## Plan clarification in effect

2026-10-14, during R: `curl` is authenticated by the session's proxy. This is a correction of fact; nothing is weakened.
