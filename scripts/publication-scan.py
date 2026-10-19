#!/usr/bin/env python3
"""Scan every commit about to be published for content that must not be published.

Read-only. For each commit in BASE..HEAD it checks the lines the commit adds,
its message, and its author and committer, so a slip that a later commit
removed is still found: a --no-ff merge publishes every commit, not only the
final tree. See docs/ADOPTING.md section 3 and COORDINATOR.md "Publication scan".
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
# RFC 2606 and RFC 6761 names that can never belong to a real person.
RESERVED_DOMAINS = {"example.com", "example.net", "example.org"}
RESERVED_TLDS = {"example", "invalid", "localhost", "test"}
# Common credential shapes. This catches honest slips; it is not a complete secret scanner.
SECRETS = [
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("GitHub token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}")),
    ("Anthropic key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("AWS key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}")),
    ("private key", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    ("bearer value", re.compile(r"\b[Bb]earer\s+[A-Za-z0-9._~+/-]{20,}=*")),
]
# A home directory names the person who owns the machine. Split so this file passes its own scan.
HOME_PATHS = re.compile(r"(?:/ho" r"me/|/Us" r"ers/|[A-Za-z]:\\Us" r"ers\\)[^/\\\s'\"`]+")


@dataclass(frozen=True)
class Finding:
    commit: str
    where: str
    category: str
    detail: str
    text: str


def _terms(path: Path | None) -> list[str]:
    if path is None:
        return []
    terms = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            terms.append(line)
    return terms


def _term_pattern(term: str) -> re.Pattern[str]:
    # Whole word, ignoring case: a private name inside a longer ordinary word is not a match.
    return re.compile(r"(?<![A-Za-z0-9_])" + re.escape(term) + r"(?![A-Za-z0-9_])", re.IGNORECASE)


class Scanner:
    def __init__(self, terms: list[str], allowed_emails: list[str]) -> None:
        self.terms = [(index, _term_pattern(term)) for index, term in enumerate(terms, 1)]
        self.allowed = {email.lower() for email in allowed_emails}
        self.findings: list[Finding] = []

    def _email_allowed(self, email: str) -> bool:
        email = email.lower()
        domain = email.rsplit("@", 1)[1]
        return (email in self.allowed or domain.rsplit(".", 1)[-1] in RESERVED_TLDS
                or any(domain == name or domain.endswith("." + name) for name in RESERVED_DOMAINS))

    def check(self, commit: str, where: str, text: str) -> None:
        def add(category: str, detail: str = "") -> None:
            self.findings.append(Finding(commit, where, category, detail, text))

        for index, pattern in self.terms:
            if pattern.search(text):
                # Report the term's number, not the term, so the output is safe to record.
                add("listed term", f"#{index}")
        for match in EMAIL.finditer(text):
            if not self._email_allowed(match.group()):
                add("email address")
        for name, pattern in SECRETS:
            if pattern.search(text):
                add("credential", name)
        if HOME_PATHS.search(text):
            add("home directory path")


def _error(message: str) -> SystemExit:
    # Exit 2, so an error is never mistaken for a pass (0) or a list of findings (1).
    print(f"ERROR: {message}", file=sys.stderr)
    return SystemExit(2)


def _git(repo: Path, *args: str) -> bytes:
    # Inherited GIT_* variables could point git at another repository or change what it reports.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    command = ["git", "--no-replace-objects", "-c", "core.quotePath=false", "-c", "core.commitGraph=false", *args]
    result = subprocess.run(command, cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise _error(f"git {' '.join(args)} failed: {message}")
    return result.stdout


def _text(data: bytes) -> str:
    return data.decode("utf-8", "replace")


def _added_lines(repo: Path, commit: str, parents: int) -> tuple[list[tuple[str, int, str]], list[str]]:
    """Return (path, line number, text) for every line the commit adds, and its binary paths.

    A merge is read as a combined diff (--cc): only lines that match none of its parents
    are new, since lines from a parent were scanned in that parent's own commit.
    """
    patch = _text(_git(repo, "diff-tree", "-p", "--cc", "--root", "-U0", "--no-color", "--no-ext-diff",
                       "--no-textconv", "--no-renames", "--no-relative", "--ignore-submodules=none",
                       "--src-prefix=a/", "--dst-prefix=b/", "--no-commit-id", commit))
    width = max(parents, 1)
    added: list[tuple[str, int, str]] = []
    binary: list[str] = []
    path = ""
    header_path = ""
    line_number = 0
    in_hunk = False
    hunk_start = "@" * (width + 1) + " "
    for line in patch.split("\n"):
        if line.startswith(("diff --git ", "diff --cc ", "diff --combined ")):
            in_hunk = False
            header_path = line.split(" b/", 1)[1] if line.startswith("diff --git ") else line.split(" ", 2)[2]
            path = header_path
        elif line.startswith(hunk_start):
            in_hunk = True
            new_range = [part for part in line.split(" ") if part.startswith("+")][-1]
            line_number = int(new_range[1:].split(",")[0])
        elif not in_hunk:
            if line.startswith("+++ "):
                target = line[4:]
                path = target[2:] if target.startswith("b/") else target
            elif line.startswith("Binary files "):
                binary.append(header_path)
        elif line.startswith("\\"):
            continue  # "\ No newline at end of file"
        else:
            markers, content = line[:width], line[width:]
            if len(markers) < width or "-" in markers:
                continue
            if "+" in markers:
                added.append((path, line_number, content))
            line_number += 1
    return added, binary


def scan(repo: Path, base: str, head: str, scanner: Scanner, extra_files: list[Path]) -> tuple[int, list[str]]:
    if _text(_git(repo, "rev-parse", "--is-shallow-repository")).strip() != "false":
        raise _error("shallow clone; fetch full history first (git fetch --unshallow)")
    head_sha = _text(_git(repo, "rev-parse", "--verify", "--end-of-options", f"{head}^{{commit}}")).strip()
    base_sha = _text(_git(repo, "rev-parse", "--verify", "--end-of-options", f"{base}^{{commit}}")).strip()
    commits = _text(_git(repo, "rev-list", "--reverse", "--parents", head_sha, f"^{base_sha}")).split("\n")
    binaries: list[str] = []
    count = 0
    for entry in filter(None, commits):
        commit, *parents = entry.split(" ")
        count += 1
        short = commit[:12]
        names = _text(_git(repo, "show", "-s", "--format=%an%x00%ae%x00%cn%x00%ce", commit)).rstrip("\n").split("\0")
        scanner.check(short, "author", f"{names[0]} <{names[1]}>")
        scanner.check(short, "committer", f"{names[2]} <{names[3]}>")
        message = _text(_git(repo, "show", "-s", "--format=%B", commit))
        for number, line in enumerate(message.split("\n"), 1):
            scanner.check(short, f"message:{number}", line)
        added, binary = _added_lines(repo, commit, len(parents))
        for path, number, line in added:
            scanner.check(short, f"{path}:{number}", line)
        binaries.extend(f"{short} {path}" for path in binary)
    for extra in extra_files:
        for number, line in enumerate(extra.read_text(encoding="utf-8").split("\n"), 1):
            scanner.check("text", f"{extra.name}:{number}", line)
    return count, binaries


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("base", help="the published commit or ref the new commits build on, for example origin/main")
    parser.add_argument("head", help="the commit or ref about to be published")
    parser.add_argument("--terms", type=Path, metavar="FILE",
                        help="file of words that must not be published, one per line, kept outside the repository")
    parser.add_argument("--allow-email", action="append", default=[], metavar="ADDRESS",
                        help="an address the repository's rules allow, such as a mandated no-reply identity")
    parser.add_argument("--text", action="append", default=[], type=Path, metavar="FILE",
                        help="also scan this text file, for example a draft pull request description")
    parser.add_argument("--show", action="store_true",
                        help="print each matching line; the default output names no matched text, so it can be recorded")
    args = parser.parse_args(argv)

    repo = Path.cwd()
    top = Path(_text(_git(repo, "rev-parse", "--show-toplevel")).strip()).resolve()
    if args.terms is not None:
        terms_path = args.terms.resolve()
        if terms_path == top or top in terms_path.parents:
            # Inside the work tree, the list of private words is one `git add` away from being published.
            raise _error("keep the --terms file outside the repository")
        if not terms_path.is_file():
            raise _error(f"--terms file not found: {args.terms}")
    for extra in args.text:
        if not extra.is_file():
            raise _error(f"--text file not found: {extra}")

    terms = _terms(args.terms)
    scanner = Scanner(terms, args.allow_email)
    count, binaries = scan(top, args.base, args.head, scanner, args.text)

    for finding in scanner.findings:
        detail = f" {finding.detail}" if finding.detail else ""
        print(f"FOUND {finding.commit} {finding.where}: {finding.category}{detail}")
        if args.show:
            print(f"    {finding.text}")
    for binary in binaries:
        print(f"NOTE binary file not scanned, check it by hand: {binary}")
    summary = f"{count} commits, {len(terms)} listed terms, {len(args.text)} extra files"
    if scanner.findings:
        print(f"FAIL: {len(scanner.findings)} findings ({summary})")
        return 1
    print(f"PASS: no findings ({summary})")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, UnicodeDecodeError) as exc:
        # Python's own exit code for a crash is 1, which would read as findings.
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
