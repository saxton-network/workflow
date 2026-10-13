# Task A: implementation

- **Prerequisites:** none.
- **Base:** `b2316d116d09d91788b9b653a126cb3edd702281`. **Branch:** `pilot/alpha11-impl`, in its own worktree.
- **Owned paths:** `scripts/agent-task.py`, `scripts/tests/test_agent_workflow.py`, `agent-work/EVIDENCE-MANIFEST.md`.
- **Read first:** `AGENTS.md`, `docs/THREAT-MODEL.md`, `agent-work/EVIDENCE-MANIFEST.md` (accepted format).

## Work

1. Protected-pattern bracket rule follows `fnmatch`: a `[` opens a class that may start with `!` and then `]` as a member, and ends at the next `]`. `[]` and `[!]` are unclosed and rejected; `[]a]` and `[!]a]` are valid classes and accepted.
2. Test that `ssh:///srv/app` (hostless, non-web scheme) is accepted.
3. Add default ports `scp` 22, `ftps` 990, `smb` 445, and list them in the docs.

## Validation

- Baseline `bash scripts/validate-repository.sh` at the base, before edits.
- New tests fail on the base and pass on the candidate (Python 3.12).
- `bash scripts/validate-repository.sh` passes on Python 3.11, 3.12 and 3.13; Validate CI green on the pushed candidate.
- Fingerprint functions unchanged.

## Result

`results/A.md` using `agent-work/RESULT-TEMPLATE.md`: candidate commit, base, changed paths, checks.

## Forbidden

Changes outside the owned paths; any change to fingerprint computation, the threat model, the spec, or the release workflow.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
