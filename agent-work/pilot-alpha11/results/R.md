# Task R: release readiness

Performed by the coordinator on 2026-10-13. Read-only with respect to `main`, tags and releases.

**Verdict: PASS**

- Source: `d568c5f18986ea122018bde2d1badb257346dd92`
- Frozen batch fingerprint: `a4724dc9718a7bf3cc11a4dd0de9139d2e660001ae59ddf75c8443c68818d83b`, computed with `batch_fingerprint` from `scripts/agent-task.py` at the source

## Checks

| Check | Result |
| --- | --- |
| `origin/main` equals the source | PASS. After `git fetch origin`, `git --no-replace-objects -c core.commitGraph=false rev-parse origin/main` (every inherited `GIT_*` variable removed) printed the source. `gitDivergence` is `identical: true`. |
| `validate-repository.sh` at the source | PASS. Run in a clean detached worktree at the source; exit 0, ending `PASS: workflow repository validation`. |
| Validate CI on the source | PASS. Run 38344216421 (push to `main`, `head_sha` = source), conclusion `success`. Also run 38343503323 on `pilot/alpha11-impl`. |
| No `v0.1.0-alpha.11` tag | PASS. `git ls-remote origin 'refs/tags/v0.1.0-alpha.11*'` prints nothing; the tag list has ten tags, alpha.1 to alpha.10. |
| No `v0.1.0-alpha.11` release, draft included | PASS. `get_release_by_tag` returns 404; `list_releases` (which includes drafts for a writer) lists ten published releases, no draft. |
| Immutable releases off | PASS. `GET /repos/saxton-network/workflow/immutable-releases` returned `{"enabled": false, "enforced_by_owner": false}`; alpha.10 reports `immutable: false`. |
| Tools | Run read: proven (`actions_list`, `get_check_run`). Dispatch and cancel: `actions_run_trigger` with `run_workflow` and `cancel_workflow_run` is present in this session's GitHub connection; neither was exercised, as both act on live state. Release and tag deletion: no tool; the owner does it (owner decision 4). |
| Local git | `git version 2.43.0`. |
| ZIP is reproducible | PASS. Two builds of the source ZIP are byte-identical, and the same command at `b2316d1` reproduces alpha.10's published digest `3e6dab07…0da097`. |
| Baseline | Recorded in `R-baseline.json`: every tag and target, every release, alpha.10's asset digests, the immutable-releases setting. |

## Frozen batch

- `deploymentSourceSha`: `d568c5f18986ea122018bde2d1badb257346dd92`
- `deployableArtifactSha256`: `b8c4c8c0a4ce76bd6851ae18a161e556a95f8c765639a62ab064ed3c2bd6c2f1`, which is `workflow-v0.1.0-alpha.11.zip` (66734 bytes) built with `git archive --format=zip --prefix=workflow-v0.1.0-alpha.11/ d568c5f… -o workflow-v0.1.0-alpha.11.zip`
- `deploymentConfiguration`:
  - `.github/workflows/release.yml` `57c20477be82406b9053d9945d48ac53e5bad8a11068d38b72c2d25c21da9562`
  - `agent-work/pilot-alpha11/results/R-dispatch-inputs.json` `2d6ae426fafd6378d2d8b4fba1317f076cf3732c35fd7a8330d7df1d0ee39d90`
  - `agent-work/pilot-alpha11/results/R-expected-checksum.txt` `5dccd42e1288202991278e56f84b1bcc84575d6004c10d525c31524f3241921f`
- `validators`:
  - `scripts/validate-repository.sh` `45eba69bf41f17ca4d1ea646e4d4bc8e3bcd1cf407a8ae3b698effe1032a2ebe`
  - `scripts/check-release-version.sh` `939911f6527179a3171d5e1f1db222b37af2d477ab8d1d396a9ce74426a8c075`
  - `scripts/agent-task.py` `fadb61b1bd081bb72f337e973ec648d36baff39623cc1b08c602a59cccfd1559`
  - `scripts/tests/test_agent_workflow.py` `408aad5d1952fcb2adb2cef32b6b3cf1227458af3fc80d617872b3cdcfdd5360`
- `installedScripts`: none
- `rollbackArtifact`: `github-release-v0.1.0-alpha.10`, provenance `R-rollback-alpha10.md`
- `deploymentTargets` (mode `null`): the release page `…/releases/tag/v0.1.0-alpha.11` and the two download URLs `…/releases/download/v0.1.0-alpha.11/workflow-v0.1.0-alpha.11.zip` and `….zip.sha256`

## Accepted unknowns (CONTRACT.md)

- Runner tools: the runner's git and zlib build the published ZIP. If its hash is not `b8c4c8c0…bd6c2f1`, runtime acceptance fails (owner decision 6).
- Release notes: not previewed. The generate-notes API needs a token, and this session has no tool for it. Accepted as unfrozen (owner decision 7).
- Action versions: pinned by tag; covered by the ZIP hash check.

## Pilot findings

- R1. The frozen configuration files `R-dispatch-inputs.json` and `R-expected-checksum.txt` live on the records branch, not at the source, so the batch mixes paths from two trees. The spec does not say which tree a batch path refers to.
- R2. Repository settings (immutable releases) are read without a token here; nothing in the spec covers settings that are not files.
