# Task K: final reconciliation

## Refs and release (checked 2026-10-14T03:50:15Z, after runtime acceptance)

- `origin/main` = `84d826a40b8f8567439ab15eb270a1a752f92a82`, the deployed source.
- `refs/tags/v0.1.0-alpha.13` = the source, a lightweight tag (API object type `commit`).
- Release 412320357 `v0.1.0-alpha.13`: published prerelease, not a draft, not "Latest", two assets whose bytes equal the frozen hashes (`results/J.md`).
- Every other tag and release, and alpha.12's asset digests, equal `results/R-baseline.json`.

The main freeze ended with runtime acceptance.

## Secrets and privacy check

- No GitHub tokens, private-key blocks, bearer tokens or AWS key IDs in `agent-work/release-alpha13/` or the `docs/PILOT-HISTORY.md` change.
- No email addresses, IP addresses, local machine paths, session links or model names in the workflow directory.
- Private repository names, checked through the authenticated connection: the only matches are ordinary English words in existing history text. No private name is printed here.
- The records name the owner's public GitHub username in `results/R-settings.json`, as Pilot 4's records do; the plan disclosed this and the owner accepted it (owner decision 7).

## Records divergence from the deployed source

Run with no inherited `GIT_*` variables, against the records head before this file (`87665ae4fb0ea38cac34b562f435b90fe81f0dd8`):

- `GIT_GRAFT_FILE=/dev/null git --no-replace-objects -c core.commitGraph=false -c advice.graftFileDeprecated=false merge-base --is-ancestor 84d826a… 87665ae…` exited 0.
- `git --no-replace-objects -c core.commitGraph=false diff --no-renames --no-relative --ignore-submodules=none --name-only -z 84d826a… 87665ae…` lists 25 paths: 24 under `agent-work/release-alpha13/` and `docs/PILOT-HISTORY.md`.
- This commit adds `results/K.md`, so the records PR changes 26 paths.
- `classify_divergence`, with the frozen batch's configuration and validator paths, returns `protected_change`. The protected paths are exactly `CONTRACT.md`, `results/R-dispatch-inputs.json`, `results/R-expected-checksum.txt` and `results/R-settings.json`, all frozen configuration files under the workflow directory, as `K-reconcile.md` expects after runtime acceptance passed.

## Records PR

The records PR from `pilot/alpha13-records` to `main` is reviewed independently, then landed by the coordinator on the owner's go-ahead with a local `git merge --no-ff` pushed as a fast-forward, following `COORDINATOR.md` "Commands that move refs". The merge and the fresh check of `main` and the release afterwards are reported outside the records. Record K's `complete` covers the work above.

## Gate behaviour observed

| When | Helper | Expected |
| --- | --- | --- |
| Before R | J `GATED` | yes |
| After R `PASS` | J `PREVIEW` | yes |
| After the approval record | J `READY` | yes |
| After J complete with `runtimeAcceptance` `PASS` | J `DONE`, K `READY` | yes |
| No repair needed | C `BLOCKED conditional` | yes |
| No failed attempt | V `BLOCKED` | yes |
