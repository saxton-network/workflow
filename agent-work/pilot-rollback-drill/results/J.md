# Task J: drill release and runtime acceptance

`drill: true`. **Runtime acceptance: FAIL**, as designed: the injected check failed with the exact expected signature.

- Source: `92c51e6c69d7ed29ee6e879733ad4b801a82814e`
- Fingerprint: `f29928f7347068111db6495e702ae4c129f14aca8ff26b0453afe9992b65f52a`
- Approval: `results/J-approval.md`. The owner answered `y`, including availability to delete within 30 minutes.

## Rechecks immediately before dispatch (2026-10-13T09:09:51Z)

All matched readiness:

- `origin/main` = source.
- No `v0.0.0*` tag. The tag list equals the baseline.
- `get_release_by_tag v0.0.0-drill.1` returns 404, and the authenticated `list_releases` shows the same twelve releases, none of them drafts.
- Immutable releases: `{"enabled": false, "enforced_by_owner": false}`. Rulesets: `[]`.
- Every frozen file hash and the local ZIP hash are unchanged. The dispatch inputs are `{"version": "v0.0.0-drill.1", "prerelease": true}`.
- The latest `release.yml` run before dispatch was run 11 (alpha.12).

## Dispatch

One `actions_run_trigger` `run_workflow` call (`release.yml`, `main`, the frozen inputs) returned 204. Exactly one new dispatch run followed:

- run 38374361610 (run number 12), created 09:10:01Z;
- `head_sha` = source, so it was not cancelled;
- it reported `completed`, conclusion `success`, before the state was read.

Two one-shot, read-only check-ins were scheduled, firing at 09:41Z and 2026-10-14T09:11Z.

## Runtime acceptance, in contract order

| # | Check | Result |
| --- | --- | --- |
| 1 | The run succeeded, `head_sha` = source | PASS |
| 2 | The release is published, a prerelease, not a draft, with exactly the two expected assets | PASS. Release 411488786, published 09:10:16Z. `workflow-v0.0.0-drill.1.zip` (104401 bytes) and `workflow-v0.0.0-drill.1.zip.sha256` (94 bytes). |
| 3 | The ZIP digest and downloaded bytes equal the frozen hash | PASS. Digest `de299320…a766a715`; the downloaded ZIP is byte-identical to the frozen local build. |
| 4 | The `.sha256` asset equals `R-expected-checksum-INJECTED.txt` | **FAIL** (the injected check) |

## Expected-failure signature

- The published `.sha256` asset equals `R-expected-checksum.txt` byte for byte: yes. Its digest is `sha256:343640f3…d9a64`, the frozen hash of the correct file.
- It differs from the INJECTED file only within bytes 0–63: yes. 59 bytes differ, all within the hash; the other 5 hash characters happen to be `0`.

**Signature matched.** The failure is the injected one and no real defect was found. The coordinator stopped at check 4 and recorded J `failed`, before any deletion.

## Notes

- The release notes compare `v0.1.0-alpha.12...v0.0.0-drill.1` and list PR #15 (accepted unknown 2).
- The release API reports `created_at` 08:38:16Z, which is the source commit's time.
