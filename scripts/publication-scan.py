#!/usr/bin/env python3
"""Scan every commit about to be published for content that must not be published.

Read-only. For each commit in BASE..HEAD it checks the lines the commit adds, the
paths it adds or changes, its message, and its author and committer, so a slip that
a later commit removed is still found: a --no-ff merge publishes every commit, not
only the final tree. In a merge, a line counts only when it matches none of the
parents, since lines from a parent were scanned in that parent's own commit.
See docs/ADOPTING.md section 3 and COORDINATOR.md "Publication scan".
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import unicodedata
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path

# The lookbehind starts a match only at the start of a run of address characters; without it
# every position in a long run is a new start and a long line takes quadratic time.
EMAIL = re.compile(r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
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
    ("private key", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY(?: BLOCK)?-----")),
    ("bearer value", re.compile(r"\b[Bb]earer\s+[A-Za-z0-9._~+/-]{20,}=*")),
]
# A home directory names the person who owns the machine. Split so this file passes its own scan.
# Not after a host or word character, so a URL path such as https://host/home/page is not one.
HOME_PATHS = re.compile(r"(?<![\w.%~-])(?:/ho" r"me/|/Us" r"ers/|[A-Za-z]:\\{1,2}Us" r"ers\\{1,2})[^/\\\s'\"`]+")
HUNK = re.compile(r"@+ (?:-\S+ )+\+(\d+)(?:,\d+)? @+")
# Copy-paste artifacts are ordinary spellings (docs/THREAT-MODEL.md "Guard validators").
FOLD = {**dict.fromkeys(map(ord, "­​‌‍⁠﻿")),
        **dict.fromkeys(range(0x2010, 0x2016), "-"), 0x2212: "-",
        0x2018: "'", 0x2019: "'", 0x02BC: "'", 0x201C: '"', 0x201D: '"'}
ESCAPES = {b"a": b"\a", b"b": b"\b", b"t": b"\t", b"n": b"\n", b"v": b"\v", b"f": b"\f", b"r": b"\r"}


@dataclass(frozen=True)
class Finding:
    commit: str
    where: str
    category: str
    detail: str
    text: str
    path: str = ""


def _normalise(text: str) -> str:
    return unicodedata.normalize("NFKC", text).translate(FOLD)


def _terms(path: Path) -> list[str]:
    terms = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            terms.append(line)
    if not terms:
        raise _error(f"no terms in {path}; pass --no-terms to scan without a list")
    return terms


def _term_pattern(term: str) -> re.Pattern[str]:
    words = _normalise(term).split()
    if not words:
        raise _error("a term is empty once invisible characters are removed")
    # Whole word, ignoring case: a private name inside a longer ordinary word is not a match.
    body = r"\s+".join(map(re.escape, words))
    return re.compile(r"(?<![A-Za-z0-9_])" + body + r"(?![A-Za-z0-9_])", re.IGNORECASE)


class Scanner:
    def __init__(self, terms: list[str], allowed_emails: list[str]) -> None:
        self.terms = [(index, _term_pattern(term)) for index, term in enumerate(terms, 1)]
        self.allowed = {email.lower() for email in allowed_emails}
        self.findings: list[Finding] = []
        self._seen: set[tuple[str, str, str, str, str]] = set()

    def _email_allowed(self, email: str, after: str) -> bool:
        email = email.lower()
        local, domain = email.rsplit("@", 1)
        if local == "git" and after[:1] in (":", "/"):
            return True  # an SSH remote such as git@host:owner/repo, not a mailbox
        return (email in self.allowed or domain.rsplit(".", 1)[-1] in RESERVED_TLDS
                or any(domain == name or domain.endswith("." + name) for name in RESERVED_DOMAINS))

    def matches(self, text: str) -> list[tuple[str, str]]:
        text = _normalise(text)
        # Report a term's number, not the term, so the output is safe to record.
        found = [("listed term", f"#{index}") for index, pattern in self.terms if pattern.search(text)]
        found += [("email address", "") for match in EMAIL.finditer(text)
                  if not self._email_allowed(match.group(), text[match.end():match.end() + 1])]
        found += [("credential", name) for name, pattern in SECRETS if pattern.search(text)]
        if HOME_PATHS.search(text):
            found.append(("home directory path", ""))
        return found

    def _add(self, finding: Finding) -> None:
        key = (finding.commit, finding.where, finding.category, finding.detail, finding.path)
        if key not in self._seen:
            self._seen.add(key)
            self.findings.append(finding)

    def check(self, commit: str, where: str, text: str, path: str = "") -> None:
        for category, detail in self.matches(text):
            self._add(Finding(commit, where, category, detail, text, path))

    def check_path(self, commit: str, path: str) -> None:
        # The leading slash lets a home directory copied in at the top (home/<name>/...) match.
        for category, detail in self.matches("/" + path):
            self._add(Finding(commit, "path", category, detail, path, path))

    def path_fails(self, path: str) -> bool:
        return bool(self.matches("/" + path))

    def check_lines(self, commit: str, label: str, lines: list[tuple[int, str]], path: str = "") -> None:
        """Check numbered lines, and terms wrapped across consecutive lines."""
        runs: list[list[tuple[int, str]]] = []
        for number, text in lines:
            self.check(commit, f"{label}:{number}", text, path)
            if runs and runs[-1][-1][0] + 1 == number:
                runs[-1].append((number, text))
            else:
                runs.append([(number, text)])
        for run in runs:
            if len(run) < 2 or not self.terms:
                continue
            parts = [_normalise(text) for _, text in run]
            starts = [0]
            for part in parts[:-1]:
                starts.append(starts[-1] + len(part) + 1)
            joined = " ".join(parts)
            for index, pattern in self.terms:
                for match in pattern.finditer(joined):
                    first = bisect_right(starts, match.start()) - 1
                    last = bisect_right(starts, match.end() - 1) - 1
                    if first != last:  # a match within one line was reported above
                        text = " ".join(text for _, text in run[first:last + 1])
                        self._add(Finding(commit, f"{label}:{run[first][0]}", "listed term", f"#{index}", text, path))


def _error(message: str) -> SystemExit:
    # Exit 2, so an error is never mistaken for a pass (0) or a list of findings (1).
    print(f"ERROR: {message}", file=sys.stderr)
    return SystemExit(2)


def _git(repo: Path, *args: str) -> bytes:
    # Inherited GIT_* variables could point git at another repository or change what it reports.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    # Defence in depth against configuration; plumbing commands ignore most of it anyway.
    command = ["git", "--no-replace-objects", "-c", "core.quotePath=false", "-c", "core.commitGraph=false", *args]
    result = subprocess.run(command, cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise _error(f"git {' '.join(args)} failed: {message}")
    return result.stdout


def _text(data: bytes) -> str:
    return data.decode("utf-8", "replace")


def _unquote(name: str) -> str:
    # Git writes a path holding '"', '\', a tab or another non-printing character as a C string.
    if len(name) < 2 or not (name.startswith('"') and name.endswith('"')):
        return name

    def unescape(match: re.Match[bytes]) -> bytes:
        code = match.group(1)
        return bytes([int(code, 8) & 0xFF]) if len(code) == 3 else ESCAPES.get(code, code)

    return _text(re.sub(rb"\\([0-7]{3}|.)", unescape, name[1:-1].encode("utf-8")))


def _changed_paths(repo: Path, commit: str, parents: int) -> list[str]:
    # For a merge, -c lists only paths that differ from every parent.
    combined = ["-c"] if parents > 1 else []
    names = _git(repo, "diff-tree", "-r", "-z", "--name-only", "--no-renames", "--root", "--diff-filter=d",
                 "--ignore-submodules=none", "--no-commit-id", *combined, commit)
    return [_text(name) for name in names.split(b"\0") if name]


def _added_lines(repo: Path, commit: str, parents: int) -> tuple[dict[str, list[tuple[int, str]]], list[str]]:
    """Return the numbered lines the commit adds, by path, and the paths that hold binary content.

    A merge is read as a combined diff (--cc): a line is new only when it is marked as added
    against every parent.
    """
    # --text reads files that attributes mark -diff; a NUL byte still marks real binary content.
    patch = _text(_git(repo, "diff-tree", "-p", "--cc", "--root", "-U0", "--text", "--no-color", "--no-ext-diff",
                       "--no-textconv", "--no-renames", "--no-relative", "--ignore-submodules=none",
                       "--src-prefix=a/", "--dst-prefix=b/", "--no-commit-id", commit))
    width = max(parents, 1)
    added: dict[str, list[tuple[int, str]]] = {}
    binary: list[str] = []
    path = ""
    line_number = 0
    in_hunk = False
    hunk_start = "@" * (width + 1) + " "
    for line in patch.split("\n"):
        if line.startswith("diff "):
            in_hunk = False
            path = ""
        elif line.startswith(hunk_start):
            match = HUNK.match(line)
            if match is None:
                raise ValueError(f"unexpected hunk header in {commit}")
            in_hunk = True
            line_number = int(match.group(1))
        elif not in_hunk:
            if line.startswith("+++ "):
                # The name ends in a tab when it holds a space; an unquoted name never holds a tab.
                target = _unquote(line[4:].removesuffix("\t"))
                path = target[2:] if target.startswith("b/") else target
        elif line.startswith("\\"):
            continue  # "\ No newline at end of file"
        else:
            markers, content = line[:width], line[width:]
            if len(markers) < width or "-" in markers:
                continue
            if markers == "+" * width:
                if "\0" in content:
                    if path not in binary:
                        binary.append(path)
                else:
                    added.setdefault(path, []).append((line_number, content))
            line_number += 1
    return {name: lines for name, lines in added.items() if name not in binary}, binary


def scan(repo: Path, base: str, head: str, scanner: Scanner, extra_files: list[Path]) -> tuple[int, list[tuple[str, str]]]:
    if _text(_git(repo, "rev-parse", "--is-shallow-repository")).strip() != "false":
        raise _error("shallow clone; fetch full history first (git fetch --unshallow)")
    head_sha = _text(_git(repo, "rev-parse", "--verify", "--end-of-options", f"{head}^{{commit}}")).strip()
    base_sha = _text(_git(repo, "rev-parse", "--verify", "--end-of-options", f"{base}^{{commit}}")).strip()
    commits = [entry for entry in _text(_git(repo, "rev-list", "--reverse", "--parents", head_sha,
                                             f"^{base_sha}")).split("\n") if entry]
    if not commits:
        raise _error("nothing to scan: check base and head")
    show = ["show", "-s", "--no-show-signature", "--no-notes", "--encoding=UTF-8"]
    binaries: list[tuple[str, str]] = []
    for entry in commits:
        commit, *parents = entry.split(" ")
        short = commit[:12]
        names = _text(_git(repo, *show, "--format=%an%x00%ae%x00%cn%x00%ce", commit)).rstrip("\n").split("\0")
        scanner.check(short, "author", f"{names[0]} <{names[1]}>")
        scanner.check(short, "committer", f"{names[2]} <{names[3]}>")
        message = _text(_git(repo, *show, "--format=%B", commit))
        scanner.check_lines(short, "message", list(enumerate(message.split("\n"), 1)))
        for path in _changed_paths(repo, commit, len(parents)):
            scanner.check_path(short, path)
        added, binary = _added_lines(repo, commit, len(parents))
        for path, lines in added.items():
            scanner.check_lines(short, path, lines, path)
        binaries.extend((short, path) for path in binary)
    for extra in extra_files:
        lines = list(enumerate(extra.read_text(encoding="utf-8").split("\n"), 1))
        scanner.check_lines("text", extra.name, lines)
    return len(commits), binaries


def _main(argv: list[str] | None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("base", help="the published commit or ref the new commits build on, for example origin/main")
    parser.add_argument("head", help="the commit or ref about to be published")
    words = parser.add_mutually_exclusive_group(required=True)
    words.add_argument("--terms", type=Path, metavar="FILE",
                       help="file of words that must not be published, one per line, kept outside the repository")
    words.add_argument("--no-terms", action="store_true", help="scan without a list of words")
    parser.add_argument("--allow-email", action="append", default=[], metavar="ADDRESS",
                        help="an address the repository's rules allow, such as a mandated no-reply identity")
    parser.add_argument("--allow-binary", action="store_true",
                        help="pass even though binary files were not scanned, after checking them by hand")
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

    terms = [] if args.no_terms else _terms(args.terms)
    scanner = Scanner(terms, args.allow_email)
    count, binaries = scan(top, args.base, args.head, scanner, args.text)

    unsafe: dict[str, bool] = {}

    def shown(path: str) -> str:
        # A path that itself fails a check is not printed, so the default output stays safe to record.
        if path not in unsafe:
            unsafe[path] = scanner.path_fails(path)
        return "<path withheld>" if unsafe[path] else path

    for finding in scanner.findings:
        where = finding.where
        if finding.path and where != "path":
            where = shown(finding.path) + where[len(finding.path):]
        detail = f" {finding.detail}" if finding.detail else ""
        print(f"FOUND {finding.commit} {where}: {finding.category}{detail}")
        if args.show:
            print(f"    {finding.text}")
    for commit, path in binaries:
        print(f"NOTE binary file not scanned, check it by hand: {commit} {shown(path)}")
    summary = f"{count} commits, {len(terms)} listed terms, {len(args.text)} extra files"
    problems = [f"{len(scanner.findings)} findings"] if scanner.findings else []
    if binaries and not args.allow_binary:
        problems.append(f"{len(binaries)} binary files not scanned (--allow-binary once checked by hand)")
    if problems:
        print(f"FAIL: {', '.join(problems)} ({summary})")
        return 1
    print(f"PASS: no findings ({summary})")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except Exception as exc:
        # Python's own exit code for a crash is 1, which would read as findings.
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
