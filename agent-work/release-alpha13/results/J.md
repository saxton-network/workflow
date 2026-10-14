# Task J: live deployment

Performed by the coordinator on 2026-10-14 under `results/J-approval.md`, for source `84d826a40b8f8567439ab15eb270a1a752f92a82` and frozen batch `f2c2d628b1aa24e87e93f3afcd392b8f3c0745f10519ab04ba6e1352ed626960`.

**Runtime acceptance: PASS**

## Pre-dispatch recheck (2026-10-14T03:49:24Z), read clean before dispatching

- `git ls-remote origin refs/heads/main` = the source; recorded as the `main` tip.
- Source worktree clean, at the source.
- No `v0.1.0-alpha.13` tag (`git ls-remote`; API ref 404) and no release (API by tag 404; authenticated list: 12 releases, no drafts, no alpha.13).
- Immutable releases `{"enabled": false, "enforced_by_owner": false}`; rulesets `[]`.
- Every frozen file hash matches; the fingerprint recomputed from the frozen data equals the approved one.
- The ZIP rebuilt from the source has the frozen SHA-256 `e520b61c…d5d4`.
- Tags equal `R-baseline.json`; alpha.12's asset digests unchanged; latest `release.yml` run still 38374361610.

## Dispatch

One `run_workflow` call, on its own after the recheck: `release.yml`, ref `main`, `{version: v0.1.0-alpha.13, prerelease: true}`; answered `204 No Content` (about 03:49:35Z). No other dispatch, and no cancel.

## Check 1: the run — PASS

- Exactly one new `release.yml` run since 38374361610: 38508243210 (run 13).
- `head_sha` = `84d826a40b8f8567439ab15eb270a1a752f92a82`, the recorded `main` tip.
- `completed`, conclusion `success`, about 16 seconds (03:49:35Z–03:49:51Z).

## Check 2: the release — PASS

- Release 412320357, `v0.1.0-alpha.13`, title `Workflow v0.1.0-alpha.13`, `draft: false`, `prerelease: true`, published 03:49:47Z. `GET /releases/latest` returns 404, so it is not "Latest".
- Exactly two assets: `workflow-v0.1.0-alpha.13.zip` (161870 bytes, API digest `sha256:e520b61c…d5d4`) and `workflow-v0.1.0-alpha.13.zip.sha256` (95 bytes, API digest `sha256:682c24ea…c939`).
- Downloaded ZIP SHA-256 = the frozen `deployableArtifactSha256`.
- Downloaded `.sha256` asset bytes equal `results/R-expected-checksum.txt` (`cmp`).
- The unpacked ZIP equals `git archive` of the source (`diff -r`, no differences).
- Generated notes list PRs #15–#21 with a compare link from alpha.12.

## Check 3: refs — PASS

- `refs/tags/v0.1.0-alpha.13` → `84d826a…`; the API ref's object type is `commit` (a lightweight tag at the source).
- Every other tag equals `R-baseline.json`; the only new tag is alpha.13. The release list holds the 12 baseline releases unchanged plus alpha.13. alpha.12 (411440138) and its asset digests are unchanged.
- `main` = `84d826a…`, unchanged (03:50:15Z).

## Observations

- The run took about 16 seconds, as the plan expected; no cancel was needed.
- The release's API `created_at` is 01:00:48Z, earlier than the dispatch. That matches the source commit's time, not the run; `published_at` 03:49:47Z is the run.

The main freeze ends with this acceptance; the records PR follows as an ordinary reviewed merge.
