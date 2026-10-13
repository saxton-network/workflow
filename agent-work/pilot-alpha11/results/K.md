# Task K: final reconciliation

## Final refs and release (checked 2026-10-13, after runtime acceptance)

- `origin/main` = `d568c5f18986ea122018bde2d1badb257346dd92` (deployed source).
- `refs/tags/v0.1.0-alpha.11` = the same commit, as a lightweight tag.
- Release 411336897 `v0.1.0-alpha.11`: published prerelease with two assets whose digests equal the frozen hashes (`results/J.md`).
- `v0.1.0-alpha.10` and every other tag and release match `results/R-baseline.json`.

The main freeze ended when runtime acceptance passed.

## Secrets check

The records were scanned for GitHub tokens (`ghp_`, `gho_`, `ghu_`, `ghs_`, `ghr_`, `github_pat_`), private-key blocks, bearer tokens and AWS key IDs; none were found. The records hold no response bodies beyond public release metadata.

## Records divergence from the deployed source

Run with no inherited `GIT_*` variables, against the records head before this file (`f22ddf612f1f10900c78a80eed29b4c4f64508e5`):

- `GIT_GRAFT_FILE=/dev/null git --no-replace-objects -c core.commitGraph=false -c advice.graftFileDeprecated=false merge-base --is-ancestor d568c5f… f22ddf6…` exited 0.
- `git --no-replace-objects -c core.commitGraph=false diff --no-renames --no-relative --ignore-submodules=none --name-only -z d568c5f… f22ddf6…` lists 24 paths, all under `agent-work/pilot-alpha11/`.
- This commit adds `results/K.md` and the `docs/PILOT-HISTORY.md` entry, so the records PR changes those 26 paths and nothing else. The PR description carries the check on its final head.
- `classify_divergence`, with the frozen batch's paths as protected inputs, returns `protected_change`, because the records add `results/R-dispatch-inputs.json` and `results/R-expected-checksum.txt`. This is expected after deployment and recorded as a pilot finding. These files only document the batch, and the release is already published from the source, so the records change no deployment input of `v0.1.0-alpha.11`.

## Records PR

The records PR from `pilot/alpha11-records` to `main` is reviewed independently, then merged by the coordinator on the owner's go-ahead, after which `main` is rechecked. The merge and that recheck come after this file, so they are reported in the coordinator session and visible in the merge commit (pilot finding 9 in `docs/PILOT-HISTORY.md`). Record K's `complete` status covers work steps 1–3 only.

## Pilot findings

Collected in the Pilot 3 entry of `docs/PILOT-HISTORY.md` (findings 1 to 10).

## Gate behaviour observed

| When | Helper | Expected |
| --- | --- | --- |
| Before readiness | J `GATED` | yes |
| After R `PASS` | J `PREVIEW` | yes |
| After the approval record | J `READY` | yes |
| After J complete with `runtimeAcceptance` `PASS` | J `PREVIEW`, K `READY` | yes (known quirk for J) |
| No repair needed | C `BLOCKED conditional` | yes |
