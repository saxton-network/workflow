# Task J: live deployment

Performed by the coordinator on 2026-10-14 under `results/J-approval.md`.

**Runtime acceptance: PASS.** Every read was a first read with the client that `CONTRACT.md` "Evidence clients" names. No read was repeated, and no fallback was needed.

- Source: `02c771a7c7d71e2303c186d0c150e903a524e949`
- Frozen batch fingerprint: `2da72c54825b9b6668e958ad72d4dc017b87f229be5920233060c204d04365b1`

## Recheck, 07:19:56Z–07:19:59Z, read clean before dispatch

- **`main`:** `git ls-remote` shows `main` = the source, so the recorded tip is `02c771a…`.
- **Source worktree:** clean, at the source.
- **No alpha.14 tag or release:**
  - `git ls-remote --tags` shows none;
  - the tag ref and the release by tag return 404 through both `curl` and the connection;
  - the authenticated release list has 13 releases, no drafts, and equals the baseline.
- **Settings:** immutable releases are off and there are no rulesets.
- **Tags:** every tag equals `R-baseline.json`.
- **Frozen batch:**
  - the fingerprint, recomputed from the frozen batch with the source helper, equals the approved one;
  - every frozen configuration and validator hash matches;
  - the ZIP rebuilt from the source has the frozen SHA-256.
- **Latest `release.yml` run:** 38508243210, as in the baseline.

## Dispatch

One `run_workflow` call for `release.yml` on `main`, with inputs `version: v0.1.0-alpha.14` and `prerelease: true`, the frozen input file's values. GitHub returned 204. No second dispatch or cancel was made.

## Runtime acceptance (window from 07:20:25Z; finished by about 07:21Z)

1. **The run: PASS** (connection).
   - Exactly one new run, 38527642533 (run 14; the list went from 13 runs to 14).
   - `head_sha` is `02c771a…`, the recorded tip.
   - It ran from 07:20:07Z to 07:20:25Z and concluded `success`.
2. **The release: PASS.**
   - **Release fields** (connection; `curl` read the same values and agrees):
     - ID 412438638, titled `Workflow v0.1.0-alpha.14`;
     - `draft: false`, `prerelease: true`;
     - `published_at` 2026-10-14T07:20:21Z. `created_at` 06:42:41Z is the source commit's time and is not used.
   - **Not latest:** `/releases/latest` returns 404 through the connection, which is evidence that alpha.14 is not latest. Every release is a prerelease.
   - **Exactly two assets:**
     - `workflow-v0.1.0-alpha.14.zip`, 207427 bytes, API digest `sha256:1b87fa4a…8355`;
     - `workflow-v0.1.0-alpha.14.zip.sha256`, 95 bytes, API digest `sha256:54426f84…5f99`.
   - **ZIP bytes** (`curl` download, HTTP 200, full size): SHA-256 `1b87fa4a7034e58efaf0c8479b93bb82d4d3bad2c8fb3b467da4f27627d98355`. This equals the frozen hash and the API digest.
   - **`.sha256` asset bytes** (`curl`): byte-identical to `R-expected-checksum.txt`. Its API digest equals that file's SHA-256.
   - **Contents:** the unpacked ZIP (103 files) equals `git archive` of the source (`diff -r`, no differences).
3. **Refs: PASS.**
   - **The new tag:** the tag ref through the connection gives `object.type` `commit` and `sha` `02c771a…`. `curl` and `git ls-remote` agree. It is a lightweight tag at the source.
   - **Other tags and releases:**
     - every other tag equals the baseline, and the only new tag is alpha.14;
     - the release list holds the 13 baseline releases unchanged, plus alpha.14;
     - alpha.13's assets keep their baseline digests.
   - **`main`:** still equals the source (`git ls-remote`).

## Observations

- The run took 18 seconds. The tag step finished before the release step, as `docs/RELEASING.md` "Timing" says.
- The first-read rule held: no check needed a repeat or the fallback client.

The main freeze ends with this PASS.
