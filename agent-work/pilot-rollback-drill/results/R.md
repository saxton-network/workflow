# Task R: release readiness

Performed by the coordinator on 2026-10-13. It changed nothing on `main` or in tags and releases.

**Verdict: PASS.** As `CONTRACT.md` defines it, `PASS` means every check passed and the injected file differs from the correct one exactly as declared; it does not mean the batch has no known failure.

- Source: `92c51e6c69d7ed29ee6e879733ad4b801a82814e`
- Frozen batch fingerprint: `f29928f7347068111db6495e702ae4c129f14aca8ff26b0453afe9992b65f52a`

## Checks

| Check | Result |
| --- | --- |
| `origin/main` equals the source | PASS. Checked by `rev-parse` with no inherited `GIT_*` variables, and by `ls-remote`. `gitDivergence` is `identical: true`. |
| `validate-repository.sh` at the source | PASS. Run in a clean detached worktree; exit 0. |
| Validate CI on the source | PASS. Run 38370618291, `head_sha` = source, `success`. |
| Name free | PASS. No `refs/tags/v0.0.0*` in `ls-remote`. `get_release_by_tag v0.0.0-drill.1` returns 404. The authenticated `list_releases` shows twelve releases and no draft. |
| Immutable releases off | PASS: `{"enabled": false, "enforced_by_owner": false}`. |
| No blocking rulesets | PASS. `GET /rulesets` returns `[]`. |
| Draft visibility | Recorded in `R-settings.json`. The connection acts as `caffeinatedcultist`, which has write access: it pushed to `main` and merged PRs #13–#15. GitHub shows drafts to accounts with write access. Not directly observed, because no draft existed. |
| ZIP reproducible | PASS. Two builds are byte-identical (`de299320…a766a715`). |
| Local fault proof | PASS. `sha256sum workflow-v0.0.0-drill.1.zip`, run in the ZIP's directory, gives `de299320ca829e53f990c034603da19a68f5468f30161a79248f21b2a766a715  workflow-v0.0.0-drill.1.zip` and a newline (94 bytes). It matches the required form and equals `R-expected-checksum.txt`. It differs from `R-expected-checksum-INJECTED.txt`, and every differing byte is within bytes 0–63. |
| Baseline | `R-baseline.json`: 12 tags with their targets, and 12 releases with their IDs, flags, publish times, and every asset's name, size and digest. |
| Tools | Run read: proven. Dispatch and cancel: present, not exercised. Release and tag deletion: no tool; the owner deletes. Local git: 2.43.0. |

## Frozen batch

- `deploymentSourceSha`: `92c51e6c69d7ed29ee6e879733ad4b801a82814e`
- `deployableArtifactSha256`: `de299320ca829e53f990c034603da19a68f5468f30161a79248f21b2a766a715`
- `deploymentConfiguration`:
  - `release.yml`
  - `R-dispatch-inputs.json`
  - `R-expected-checksum.txt`
  - `R-expected-checksum-INJECTED.txt`
  - `R-settings.json`
- `validators`, all hashed at the source:
  - `validate-repository.sh`
  - `check-release-version.sh`
  - `agent-task.py`
  - `test_agent_workflow.py`
- `installedScripts`: none.
- `rollbackArtifact`: `github-release-v0.1.0-alpha.12` (`R-rollback-alpha12.md`).
- `deploymentTargets`: the drill release page and its two download URLs, each with `mode: null`.

The hashes are in `evidence.json`.
