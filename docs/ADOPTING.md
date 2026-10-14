# Adopting Workflow in another repository

This guide is for a repository that wants to use Workflow's coordination rules and helper. It fills the gaps the first newcomer adoption hit (Pilot 5 in `docs/PILOT-HISTORY.md`). Workflow is experimental; read `README.md` "Core invariants" first.

## 1. Copy these files

Copy them byte for byte from one Workflow commit, and do not edit them. Local rules go in your own files.

| File | Why |
| --- | --- |
| `agent-work/README.md` | Directory conventions for workflows. |
| `agent-work/WORKFLOW-SPEC.md` | The workflow contract the helper enforces. |
| `agent-work/COORDINATOR.md` | The coordinator's procedure. |
| `agent-work/EVIDENCE-MANIFEST.md` | The `evidence.json` format. |
| `agent-work/RESULT-TEMPLATE.md` | The task result format. |
| `scripts/agent-task.py` | The read-only helper. It needs Python 3.11 or newer (`tomllib`). |
| `docs/THREAT-MODEL.md` | Classifies helper and gate findings; see section 4. |
| `docs/agent-worktrees.md` | Cited by `COORDINATOR.md`. |

Do **not** copy these. They serve Workflow's own development and releases:

- `scripts/validate-repository.sh`;
- `scripts/check-release-version.sh`;
- `scripts/tests/`;
- `.github/workflows/release.yml`;
- `docs/PILOT-HISTORY.md`;
- `docs/RELEASING.md`;
- the `agent-work/pilot-*` directories;
- Workflow's own `README.md`, `CONTRIBUTING.md`, `.gitignore` and `.github/workflows/validate.yml`. Write your own; section 5 has a gate template.

Background reading, not copied: `docs/DESIGN.md`, `docs/AGENT-LIFECYCLE-AND-OBSERVABILITY.md` and `examples/`. Some copied files mention documents that are not copied; those references point back to Workflow, not to your repository. Where a copied file shows `scripts/validate-repository.sh` as an example check (for example `RESULT-TEMPLATE.md`), substitute your own gate.

## 2. Record provenance

Add an `ADOPTION.md` with one table row per copied file:

~~~text
| `agent-work/README.md` | `<40-hex Workflow commit>` | `<64-hex SHA-256>` |
~~~

Write each row in exactly this form, with a lower-case SHA-256. Any line that carries a backticked 64-character hex value is read as a hash row, so other tables (for example a "not copied" list) must not contain one. Your gate (section 5) fails when a copied file drifts from its row. If your gate already uses another row form (Pilot 7's adopter required a source-path column), keep it and note the difference in `ADOPTION.md` rather than changing a working gate. To upgrade, copy the files from a newer commit, update every row, and review the change like any other.

## 3. Write `AGENTS.md`

Start from Workflow's `AGENTS.md`:

- Replace its first paragraph, which describes Workflow itself.
- Keep the general rules (preserve work, the three repository states, approval, secrets, repository-native workflows, verification) in substance.
- Replace "Deployment authority" with your own authority remote and ref, and name your live changes.
- Drop Workflow's sentence about its own `release.yml`.

Add your repository's rules, for example a content rule for a public site. If a content rule forbids naming people or email addresses, say whether the mandated commit identity and `Co-Authored-By` trailers are exempt. Pilot 5 had to ask the owner.

- **Write the answer next to the rule, in `AGENTS.md`.** An owner decision that interprets a rule belongs beside that rule. Pilot 5 recorded its answer only in the adoption log; in Pilot 7 a reviewer read the rule as written, reported the trailers as a violation, and the repair worked against the owner's decision. If decisions also live in `ADOPTION.md`, list them in every review briefing.
- **Say which commit identity to use, without naming anyone.** For example: "the configured no-reply identity, never a personal one". "Whatever identity is configured" depends on the machine: in Pilot 7 a coordinator handover changed the author identity on a public repository. Whoever takes over checks `git config user.name` and `user.email` against the rule before the first commit.

Changing repository or hosting settings (turning on GitHub Pages, branch protection, secrets) is a live change. It needs its own bounded preview and explicit approval.

## 4. Threat model

The copied `docs/THREAT-MODEL.md` covers Workflow's helper and gates, not your project. Say in `AGENTS.md` how project defects are classified. For example: a breach of a project content rule is always a defect to fix, reported as a site-rule violation, even though the copied threat model has no item for it. If you want a full project threat model, write your own and have the owner approve it.

For guard-style validators, such as a check that a page contains nothing forbidden, decide in advance when a review loop stops. Pilot 5's HTML check kept finding new encodings to cover. The loop ended once the remaining findings needed deliberately crafted content; `docs/THREAT-MODEL.md` "Guard validators" now states that rule, including which odd spellings are still ordinary.

## 5. A repository gate

Write your own gate. This template checks the copied files against `ADOPTION.md` and runs the helper over every workflow; add your project's checks at the end. It fails on a missing, duplicated, malformed or extra row, and on a workflow directory without a manifest.

<!-- adopter-gate:start -->
~~~bash
#!/usr/bin/env bash
# Repository gate for a Workflow adopter.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

python3 - <<'PY'
import hashlib
import re
import sys
from pathlib import Path

# Every copied Workflow file, exactly once each.
VENDORED = [
    "agent-work/README.md",
    "agent-work/WORKFLOW-SPEC.md",
    "agent-work/COORDINATOR.md",
    "agent-work/EVIDENCE-MANIFEST.md",
    "agent-work/RESULT-TEMPLATE.md",
    "scripts/agent-task.py",
    "docs/THREAT-MODEL.md",
    "docs/agent-worktrees.md",
]
ROW = re.compile(r"\| `([^`]+)` \| `([0-9a-f]{40})` \| `([0-9a-f]{64})` \|")
DIGEST = re.compile(r"`[0-9A-Fa-f]{64}`")
rows = {}
for line in Path("ADOPTION.md").read_text(encoding="utf-8").splitlines():
    if not DIGEST.search(line):
        continue
    match = ROW.fullmatch(line.rstrip())
    if match is None:
        sys.exit(f"FAIL: malformed ADOPTION.md row: {line}")
    path, _commit, digest = match.groups()
    if path in rows:
        sys.exit(f"FAIL: duplicate ADOPTION.md row: {path}")
    rows[path] = digest
if sorted(rows) != sorted(VENDORED):
    sys.exit(f"FAIL: ADOPTION.md rows {sorted(rows)} do not match the vendored list")
for path, digest in rows.items():
    file = Path(path)
    if file.is_symlink() or not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != digest:
        sys.exit(f"FAIL: {path} differs from its ADOPTION.md hash")
print(f"PASS: {len(rows)} vendored file hashes match ADOPTION.md")
PY

# Each workflow directory needs a valid manifest; zero workflows is fine.
shopt -s nullglob
for dir in agent-work/*/; do
  id="$(basename "$dir")"
  if [[ ! -f "$dir/manifest.toml" ]]; then
    echo "FAIL: agent-work/$id has no manifest.toml" >&2
    exit 1
  fi
  python3 scripts/agent-task.py "$id" --all > /dev/null
  echo "PASS: agent-work/$id/manifest.toml"
done

# Project checks go here.

echo "PASS: repository validation"
~~~
<!-- adopter-gate:end -->

Run it in CI on every push and pull request with read-only permissions. Pin actions to exact tags, or to commit SHAs if your policy requires it.

## 6. Order of work

Quick start lists the pieces; this is the order they happen in:

1. **Adopt.** Copy the files, write `ADOPTION.md`, `AGENTS.md` and the gate. Have the adoption reviewed independently, and record the review as one pull-request comment (`COORDINATOR.md` "Durable review records").
2. **Plan.** Write a plan and have it reviewed independently; the owner approves it.
3. **Compile.** Only then create `agent-work/<workflow-id>/` with `PLAN.md`, `manifest.toml`, the task files and `results/`. Before an approved plan exists, the gate accepts zero workflow directories.

If the coordinator cannot create the repository (an organisation may refuse it), the owner creates it. A starter commit that the host adds, such as a README, may be kept; record it as owner-accepted rather than rewriting history.

## 7. Static-site and Pages-style targets

Workflow's examples are written around releases and hosts. For a site published by a deploy workflow (such as GitHub Pages):

- **Deployable artifact.** The SHA-256 of each published file at the source, for example `site/index.html`.
- **Destination.** Write it without a trailing separator, for example `https://<owner>.github.io/<repo>`, with `mode` `null`.
- **Rollback identity.**
  - Before the first launch: "unpublished, 404".
  - After a launch: the previous deployed commit, for example `git:<sha>`, redeployed by the same deploy workflow.
  - The deploy workflow must accept that commit. A first-parent guard on `main` does, if the earlier commit stays on `main`'s first-parent line.
- **Runtime acceptance.**
  - Fetch the live bytes with a cache-busting query (`curl -sS --compressed '<url>/?cb=<nonce>'`) and compare SHA-256. Retry for a bounded window to cover CDN propagation.
  - Never use a tool that returns converted text instead of bytes.
- **Evidence of what is live.** Have the deploy job log the checked-out commit and the file hash. At readiness, prove that the coordinator can read a recent deploy job's log with the client it will use at acceptance, and say in the contract whether a second read-only client may be used within the acceptance window (decided before approval, not after a failure). In Pilot 7 one client got `Forbidden` on the log and another could read it; acceptance failed and a correct deploy was rolled back. Reading the same evidence again is not a retry of the live batch, but evidence read after a failed check never turns the failed attempt into a pass. Host deployment labels may name the triggering ref's tip rather than the deployed input. On GitHub Pages, `pages_build_version` is `main`'s tip on a dispatch, so it is not evidence of the live commit.
- **Turning on the host feature** is a settings change with its own preview and approval (section 3).
