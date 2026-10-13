# Threat model

## Status

Approved by the repository owner. This document decides which review findings are defects to fix and which are recorded as out of scope. Changing it is a scope decision for the owner, not a repair a builder or reviewer may make.

## What Workflow protects

Workflow's gates exist so that a live change happens only when all of these hold:

- the deployed source is the exact commit an independent reviewer passed;
- release readiness passed for that source;
- the frozen batch (artifact, configuration, validators, scripts, rollback, destinations) is the one readiness recorded, proven by its fingerprint;
- any newer commit on the authority ref was proven to be an additive descendant that leaves deployment inputs unchanged;
- a human approved that exact source and fingerprint.

`scripts/agent-task.py` is a read-only checker of evidence the coordinator records. It is not an enforcement boundary: the coordinator still verifies real approval and rechecks live state before acting.

## The problem it is built for

The project grew out of multi-agent work where the failures were honest mistakes, not attacks: stale assumptions, validators that checked the wrong thing, confusion over which commit was which, Git divergence, and deployment steps drifting from what was approved. See `docs/PILOT-HISTORY.md`.

## Who is trusted, and how far

| Actor | Trust |
| --- | --- |
| Repository owner | Trusted. Approves scope, releases, and live changes. Not expected to read or review code. |
| Coordinator agent | Honest but fallible. May misread state, reuse stale evidence, run the wrong command, record the wrong value, or skip a step. |
| Builder and repair agents | Honest but fallible. May report success that did not happen. |
| Reviewer agents | Honest but fallible. Independence comes from being a different agent from the builder, preferably a different model or vendor. |
| Authority remote (for example GitHub) | Trusted source of truth for refs. Objects fetched from it are verified by Git as they arrive. |
| Local machine and checkout | Trusted not to be deliberately tampered with. May carry accidental configuration (user or system Git settings, mirror-clone replace refs, odd environment variables left by other tools). |

## In scope: must fail closed

A finding is in scope when an honest but fallible actor, without intending harm, could cause one of these:

1. **Wrong-source or wrong-batch approval.** The gate reports `PREVIEW` or `READY`, or allows final reconciliation, for a source, fingerprint, or approval that does not match the reviewed and readied ones. This includes stale records, out-of-order records, and evidence from another workflow.
2. **Ambiguous evidence accepted.** Evidence that could reasonably mean two different things (two spellings of one location, conflicting hashes, duplicate keys) is accepted instead of rejected.
3. **Crash instead of a verdict.** Malformed or unexpected input makes the helper raise an exception rather than report `GATED`.
4. **Accidental environment changes the facts.** Ordinary configuration a coordinator might really have (Git settings such as `diff.relative` or ignored submodules, replace refs from a mirror clone) changes what the documented commands report.
5. **Documentation that misleads.** The documented procedure, followed exactly, produces wrong evidence, or the docs and the code disagree on what is accepted.

## Out of scope

These are recorded when found, not fixed, unless the owner changes this document:

- **Deliberate tampering with the local repository or machine.** Rewriting object files, forging commit-graph or graft files, planting test-only Git environment variables such as `GIT_TEST_*`, or swapping binaries. The existing graft and commit-graph hardening stays as cheap defense in depth, not as a guarantee.
- **A malicious or colluding agent.** An agent that lies on purpose, or a builder and reviewer acting together.
- **Compromise outside the repository.** A compromised forge, CI runner, credentials, or network.
- **Breaking cryptography.** Hash collisions in Git or SHA-256.
- **Understanding every possible spelling.** The helper does not have to work out that two unusual spellings of a URL or path name the same place. It must reject spellings outside its accepted format instead (in-scope item 2). See "Proposed follow-up" below.

## How reviews use this

- **Classify.** A reviewer labels every finding in scope (naming the item above) or out of scope (naming the bullet above).
- **Severity.**
  - High: an in-scope path to `READY` or final reconciliation with the wrong source, fingerprint, or approval.
  - Medium: an in-scope path to `READY` through ambiguous evidence; a crash on input a coordinator could plausibly produce; a documented procedure that yields wrong evidence.
  - Low: rejecting legitimate evidence; docs and code disagreeing without a path to `READY`; weak tests.
- **Guard validators.** This rule covers a project's own content guards, such as a site check that a page names nothing private. It does not cover the helper's evidence parsing, which in-scope items 1–4 govern.
  - These guards check content that trusted builders write, and guard against honest mistakes.
  - **Out of scope:** a finding that needs content deliberately crafted to slip past the guard, written in a way no one would write it for an honest reason. Examples are an entity-encoded name, or a name split across markup to hide it. This falls under "A malicious or colluding agent". Record it in the PR description; do not extend the guard round after round. A later batch may extend it at the owner's discretion.
  - **In scope, and fixed:** a guard that misses an ordinary way of writing the forbidden content (item 5 by analogy). That includes copy-paste artifacts such as a non-breaking hyphen, a soft hyphen or a smart quote, which are ordinary.
  - **When unsure** whether an honest author could plausibly produce the content (for example, a look-alike letter from an input method or a pasted web page), record it as a Low in the PR description and ask the owner.
- **When to stop.** A review round is clean when it has no in-scope High or Medium finding. Low findings are fixed in batches. Out-of-scope findings go in the PR description, not into code.
- **When to release.** A release follows a clean review, not every fix.

## The owner's role

The owner decides what this document says, approves releases, and approves each live change from its plain-language preview. Code review is done by agents that are independent of the builder; the owner is not asked to review code.

## Findings open at the time of writing

From the independent review of PR #10 (`329f5ff`, `v0.1.0-alpha.9`):

| Finding | Classification |
| --- | --- |
| Rewritten loose objects or an inherited `GIT_TEST_COMMIT_GRAPH` fool the documented Git commands | Out of scope: deliberate tampering. The docs now say to run the commands with no inherited `GIT_*` variables, which covers accidental leftovers (in scope, item 4). |
| `file:///C%3A/srv/app` and `file:///srv/%61pp` alias plain paths | In scope, item 2 (Low). Resolved: `file:` URLs and `%` are outside the accepted format. |
| `https://:@host` aliases `https://host` | In scope, item 2 (Low). Resolved: user info is outside the accepted format. |
| `ssh://[0:0::1]` and `ssh://[::1]` get different keys | In scope, item 2 (Low). Resolved: every URL's IPv6 host must be in compressed form. |
| Docs describe the `//` prefix only as UNC | In scope, item 5 (Low). Resolved: the accepted-format rules list every accepted form. |
| Commit-graph test helper assumes SHA-1 repositories | Low: test robustness. Resolved: the git-backed tests create SHA-1 repositories explicitly. |

## One accepted format

Approved by the owner and implemented. Instead of recognising every way of writing the same destination or path, the helper accepts one plain format and rejects everything else. The exact rules are in `agent-work/EVIDENCE-MANIFEST.md`; in summary:

- **Destinations** are one of: an absolute POSIX path, a Windows drive path (`C:\...`), a UNC path (`\\server\share\...`), a URL written `scheme://host[:port]/path`, or a hostless URL written `scheme:///path` (such as `unix:///run/app.sock`). The scheme and host are lowercase ASCII, an IPv6 host is in compressed form, and a port is written only when it is not the scheme's default. Every path segment uses only letters, digits, `.`, `_`, `-` and `~`, and is not `.` or `..`. No user info, percent-encoding, query, fragment, whitespace, or trailing separator.
- **Batch paths, changed paths, and protected-input patterns** follow the same character rule, with the glob characters `*`, `?`, `[`, `]` and `!` allowed only in protected-input patterns.
- **Anything else is `GATED`** with a message saying which rule it broke, so the coordinator can rewrite it in the accepted form.

Trade-offs:

- The URL normalisation, Unicode handling and alias-resolution code was removed. Windows device-name and trailing-dot checks remain, because those aliases use plain characters.
- Destinations or files whose real names use other characters (spaces, non-ASCII) cannot be deployed through the gate until the owner widens the format.
- scp-style destinations (`host:/path`) are written as `ssh://host/path`, and `file:///path` as the plain path. Trailing slashes are not written, so an S3 prefix is `s3://bucket/releases`, not `s3://bucket/releases/`.
- Fingerprints are unchanged; only which evidence is accepted changes.
