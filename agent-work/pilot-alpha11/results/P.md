# Task P: authority promotion

Performed by the coordinator on 2026-10-13, under owner decision 3 (non-force fast-forward of `main`).

## Before the push

- `git fetch origin`; `origin/main` = `b2316d116d09d91788b9b653a126cb3edd702281` (the phase baseline), confirmed with `git ls-remote origin refs/heads/main`.
- Candidate: `d568c5f18986ea122018bde2d1badb257346dd92`, the commit B passed.
- Validate CI on the candidate: run 38343503323 (push, `pilot/alpha11-impl`, `head_sha` = the candidate), conclusion `success`; job `validate` (check run 115119553191) `success`.
- Ancestry, run with every inherited `GIT_*` variable removed (git 2.43.0):
  `GIT_GRAFT_FILE=/dev/null git --no-replace-objects -c core.commitGraph=false -c advice.graftFileDeprecated=false merge-base --is-ancestor b2316d116d09d91788b9b653a126cb3edd702281 d568c5f18986ea122018bde2d1badb257346dd92` exited 0.
- `git log --oneline b2316d1..d568c5f` lists one commit, the candidate.

## Push

```
$ git push origin d568c5f18986ea122018bde2d1badb257346dd92:refs/heads/main
To https://github.com/saxton-network/workflow
   b2316d1..d568c5f  d568c5f18986ea122018bde2d1badb257346dd92 -> main
```

Exit 0; a fast-forward, no force.

## After the push

- `git fetch origin`; `origin/main` = `d568c5f18986ea122018bde2d1badb257346dd92`, and `git ls-remote origin refs/heads/main` reports the same.
- `origin/main` was merged into `pilot/alpha11-records` without force. The helper there now has SHA-256 `fadb61b1bd081bb72f337e973ec648d36baff39623cc1b08c602a59cccfd1559`, identical to `scripts/agent-task.py` at the candidate.

Main freeze (owner decision 2) is in effect from this point.

## Pilot findings

- P1. The session's git configuration comes partly from `GIT_CONFIG_*` environment variables (proxy URL rewrites and a CA bundle), so "no inherited `GIT_*` variables" cannot apply to commands that talk to the remote. The local proof commands ran without them; fetch and push ran with them. The docs could say which commands the rule is for.
- P2. Record B named the reviewer's model identifier, which this repository keeps out of committed files. The coordinator replaced it with `null` in `evidence.json` and with "the same model as the builder" in `B-1.md`, and updated B-1.md's hash in record B. The workflow docs do not say what the `model` field should hold when that rule applies.
