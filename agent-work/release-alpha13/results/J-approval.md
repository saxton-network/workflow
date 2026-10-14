# Task J: owner approval

This record follows `agent-work/COORDINATOR.md` "Approval records". The approval was given in chat, so this record is the coordinator's own account of it; the platform offers no link to the message.

- **When:** 2026-10-14, after readiness `PASS` (`results/R.md`), in the coordinator session.
- **Preview shown:** a plain-language preview covering:
  - what is published, from `84d826a`, with the package and batch fingerprints;
  - the single run and that it cannot be recalled;
  - the effects (public tag, public prerelease with two files, generated notes listing PRs #15–#21, notifications, not "Latest");
  - the exposure, including the pilot records with the owner's public username and the public site repository;
  - the checks, including the B5 clarification;
  - the rollback by the owner through exact links;
  - the retry limit and alpha.14 naming;
  - the requests not to touch other releases or tags and to leave immutable releases off, and the main freeze;
  - the three possible outcomes.
- **Question asked:** "Approve, and are you available to delete the release and tag within 30 minutes if it fails? (y/n)"
- **Answer, as given:** `y`

## Approved batch

- Source: `84d826a40b8f8567439ab15eb270a1a752f92a82`
- Frozen batch fingerprint: `f2c2d628b1aa24e87e93f3afcd392b8f3c0745f10519ab04ba6e1352ed626960`

## Approved actions

1. One dispatch of `.github/workflows/release.yml` on `main` with `agent-work/release-alpha13/results/R-dispatch-inputs.json` (`version: v0.1.0-alpha.13`, `prerelease: true`), SHA-256 `a5ffa35ff0fc8f3a9d80630e72c75b73d6242dffb7ba5d7e2071cfaaf5f0d62c`.
2. A run cancel, only when:
   - the run built the wrong commit and is still before its "Create release tag" step;
   - it is still running after 12 minutes; or
   - V finds it not `completed`.

## Owner actions under this approval

The deletions in `CONTRACT.md` "Rollback (V)", one at a time through the links the coordinator gives, only if J fails with `liveStateChanged` not `false`.

## Not covered

- A retry, of any kind.
- Another version, source or batch.
- Any settings change.
- Any deletion by the coordinator.
