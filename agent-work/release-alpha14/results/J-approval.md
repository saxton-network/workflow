# Task J: owner approval

This record follows `agent-work/COORDINATOR.md` "Approval records". The approval was given in chat, so this record is the coordinator's own account of it. The platform offers no link to the message.

- **When:** 2026-10-14, after readiness `PASS` (`results/R.md`), in the coordinator session.
- **Preview shown:** a plain-language preview. It covered:
  - what is published: from `02c771a`, with the package and batch fingerprints, packaging PRs #22, #24 and #25;
  - the single run, which cannot be recalled;
  - the effects:
    - a public tag;
    - a public prerelease with two files;
    - generated notes;
    - notifications;
    - not "Latest";
  - the exposure, including the pilot records with the owner's public username;
  - the checks:
    - the named evidence tools;
    - the 10-minute rule, under which a read outage fails the check even for a correct release;
  - the rollback, by the owner through exact links, with check-ins at 30 minutes and 24 hours;
  - the retry limit and alpha.15 naming;
  - the requests not to merge into `main`, not to touch other releases or tags, and to leave immutable releases off;
  - the three possible outcomes;
  - the plan clarification in force (`curl` is authenticated by the session's proxy).
- **Question asked:** "Approve, and are you available to delete the release and tag within 30 minutes if it fails? (y/n)"
- **Answer, as given:** `y`

## Approved batch

- Source: `02c771a7c7d71e2303c186d0c150e903a524e949`
- Frozen batch fingerprint: `2da72c54825b9b6668e958ad72d4dc017b87f229be5920233060c204d04365b1`

## Approved actions

1. One dispatch of `.github/workflows/release.yml` on `main` with `agent-work/release-alpha14/results/R-dispatch-inputs.json` (`version: v0.1.0-alpha.14`, `prerelease: true`), SHA-256 `4c28473f304ccdd3ee2ab63a9abbd8adcc2fd3957bd5e29a2caed41cc5ef90e3`.
2. A run cancel, only when one of these holds:
   - the run built the wrong commit and is still before its "Create release tag" step;
   - it is still running after 12 minutes;
   - V finds it not `completed`.

## Owner actions under this approval

The owner makes the deletions in `CONTRACT.md` "Rollback (V)", one at a time, through the links the coordinator gives. This applies only if J fails with `liveStateChanged` not `false`.

## Not covered

- A retry, of any kind.
- Another version, source or batch.
- Any settings change.
- Any deletion by the coordinator.

## Clarification in force

- 2026-10-14, during R: `curl` is authenticated by the session's proxy. This is a correction of fact; no rule changes.
