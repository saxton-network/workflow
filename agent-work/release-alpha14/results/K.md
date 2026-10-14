# Task K: final reconciliation

Performed by the coordinator on 2026-10-14 at 07:22Z, after J's runtime acceptance PASS.

## Refs and the release

These reads come after acceptance, so the repeat window does not apply to them.

- **`main`:** equals the source `02c771a7c7d71e2303c186d0c150e903a524e949` (`git ls-remote`). It is unchanged since readiness, and the main freeze has ended.
- **The tag:** `v0.1.0-alpha.14` is a lightweight ref at the source (`git ls-remote`; the connection and `curl` agreed in J).
- **The release:** 412438638 is published (not a draft) and is a prerelease. Its two assets have the frozen digests: `sha256:1b87fa4a…8355` for the ZIP and `sha256:54426f84…5f99` for the `.sha256` file.
- **Everything else:** every other tag and release equals `R-baseline.json` (checked in J at 07:20:53Z).

## Secrets and privacy scan

The scan covered the added lines of every changed file between the source and the records head: 25 files.

- **Secrets:** none. No token patterns (classic and fine-grained GitHub tokens), private keys or cloud keys.
- **Personal data:** no email addresses other than the no-reply co-author trailer, no local machine paths, and no session links.
- **Names:** no private repository names, and no personal names other than the owner's public username. The records name `caffeinatedcultist` as the connection's identity, as the alpha.13 records did.
- **Ordinary English words:** the only hits are ordinary words already present in earlier releases.

## Divergence proof (records head against the source)

Run in a non-shallow clone with every inherited `GIT_*` variable removed:

- **Ancestry:** `GIT_GRAFT_FILE=/dev/null git --no-replace-objects -c core.commitGraph=false merge-base --is-ancestor <source> <records head>` exits 0.
- **Changed paths:** `git --no-replace-objects -c core.commitGraph=false diff --no-renames --no-relative --ignore-submodules=none --name-only -z` lists the records directory plus `docs/PILOT-HISTORY.md` (25 paths before this result file).
- **Classification:** `classify_divergence`, with the frozen configuration, validator and installed-script paths, returns `protected_change`. The protected paths that changed are exactly the frozen files under `agent-work/release-alpha14/`: `CONTRACT.md`, `results/R-dispatch-inputs.json`, `results/R-expected-checksum.txt` and `results/R-settings.json`. That is what the plan expects for a records landing. No deployment code or validator changed.

## Records PR

The PR adds only `agent-work/release-alpha14/` and the `docs/PILOT-HISTORY.md` Pilot 8 entry, with the follow-up note B-1 L1 asked for. It lands after independent review and the owner's go-ahead:

- a local `git merge --no-ff` under the coordinator's no-reply identity;
- pushed as a fast-forward of an asserted literal SHA, under `COORDINATOR.md` "Commands that move refs";
- never through GitHub's merge API.

K is recorded `complete` before that merge, because records cannot prove their own merge. The merge and a fresh check of `main` and the release are reported afterwards, outside these records.
