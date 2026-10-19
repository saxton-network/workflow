from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "publication-scan.py"

# Built from pieces so this file passes the scan it tests.
PERSONAL_EMAIL = "someone" + "@" + "mail.co"
NO_REPLY = "agent" + "@" + "noreply.co"
TOKEN = "ghp" + "_" + "A1b2" * 9
KEY_HEADER = "-----BEGIN " + "RSA PRIVATE KEY-----"
HOME_PATH = "/ho" + "me/alice/notes.txt"
TERM = "zebrafinch"


class PublicationScanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.repo = base / "repo"
        self.repo.mkdir()
        home = base / "home"
        home.mkdir()
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        self.env.update(HOME=str(home), XDG_CONFIG_HOME=str(home), GIT_CONFIG_NOSYSTEM="1")
        self.git("init", "-q", "--object-format=sha1", "-b", "main")
        self.git("config", "user.name", "Agent")
        self.git("config", "user.email", NO_REPLY)
        self.terms = base / "terms.txt"
        self.terms.write_text(f"# private words\n\n{TERM}\n", encoding="utf-8")
        self.base = self.commit("README.md", "start\n", "Start")

    def git(self, *args: str, cwd: Path | None = None) -> str:
        return subprocess.run(["git", *args], cwd=cwd or self.repo, env=self.env, check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout.strip()

    def commit(self, path: str, content: str | bytes, message: str) -> str:
        file = self.repo / path
        file.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            file.write_bytes(content)
        else:
            file.write_text(content, encoding="utf-8")
        self.git("add", path)
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")

    def scan(self, *args: str, base: str | None = None, head: str = "HEAD", cwd: Path | None = None,
             env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(SCRIPT), base or self.base, head, "--terms", str(self.terms),
                   "--allow-email", NO_REPLY, *args]
        return subprocess.run(command, cwd=cwd or self.repo, env=env or self.env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def assertFound(self, result: subprocess.CompletedProcess[str], *needles: str) -> None:
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        for needle in needles:
            self.assertIn(needle, result.stdout)

    def test_clean_range_passes(self) -> None:
        self.commit("notes.md", "Ordinary text, a zebra and a finch.\n", "Add notes")
        result = self.scan()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS: no findings (1 commits, 1 listed terms, 0 extra files)", result.stdout)

    def test_slip_fixed_later_is_still_found(self) -> None:
        # Pilot 9: a later commit removed the word, but a --no-ff merge publishes the earlier one too.
        slip = self.commit("R.md", f"The account {TERM} read it.\n", "Record R")
        self.commit("R.md", "The account read it.\n", "Reword R")
        self.assertNotIn(TERM, (self.repo / "R.md").read_text(encoding="utf-8"))
        result = self.scan()
        self.assertFound(result, f"FOUND {slip[:12]} R.md:1: listed term #1")
        self.assertIn("FAIL: 1 findings", result.stdout)

    def test_terms_match_whole_words_ignoring_case(self) -> None:
        self.commit("a.md", f"x\nnot {TERM}es or pre{TERM}\nSee {TERM.upper()}.\n", "Add a")
        result = self.scan()
        self.assertFound(result, "a.md:3: listed term #1")
        self.assertNotIn("a.md:2", result.stdout)

    def test_output_names_no_matched_text_unless_asked(self) -> None:
        self.commit("a.md", f"{TERM} {PERSONAL_EMAIL}\n", "Add a")
        quiet = self.scan()
        self.assertFound(quiet, "listed term #1", "email address")
        self.assertNotIn(TERM, quiet.stdout)
        self.assertNotIn(PERSONAL_EMAIL, quiet.stdout)
        shown = self.scan("--show")
        self.assertIn(PERSONAL_EMAIL, shown.stdout)

    def test_emails(self) -> None:
        reserved = "a@example.com b@x.example c@host.invalid d@sub.example.org e@site.test"
        self.commit("a.md", f"{NO_REPLY} {reserved}\n{PERSONAL_EMAIL.upper()}\n", "Add a")
        result = self.scan()
        self.assertFound(result, "a.md:2: email address")
        self.assertNotIn("a.md:1", result.stdout)

    def test_identity_and_message_are_scanned(self) -> None:
        self.git("config", "user.name", TERM)
        self.git("config", "user.email", PERSONAL_EMAIL)
        self.commit("a.md", "fine\n", f"Add a\n\nThanks {TERM}.\nCo-Authored-By: Agent <{NO_REPLY}>")
        result = self.scan()
        self.assertFound(result, "author: listed term #1", "author: email address",
                         "committer: email address", "message:3: listed term #1")
        self.assertNotIn("message:4", result.stdout)

    def test_credentials_and_home_paths(self) -> None:
        self.commit("a.md", f"token {TOKEN}\n{KEY_HEADER}\nsaved to {HOME_PATH}\n/tmp/x and /root/y\n", "Add a")
        result = self.scan()
        self.assertFound(result, "a.md:1: credential GitHub token", "a.md:2: credential private key",
                         "a.md:3: home directory path")
        self.assertNotIn("a.md:4", result.stdout)

    def test_line_numbers_follow_the_new_file(self) -> None:
        self.commit("a.md", "one\ntwo\nthree\nfour\n", "Add a")
        self.commit("a.md", f"one\ntwo\n{TERM}\nthree\nfour\n", "Insert")
        self.assertFound(self.scan(), "a.md:3: listed term #1")

    def test_merge_reports_only_its_own_new_lines(self) -> None:
        # Already published on main: not this range's to report.
        self.commit("old.md", f"{TERM}\n", "Old slip")
        published = self.git("rev-parse", "HEAD")
        self.git("checkout", "-q", "-b", "work", self.base)
        self.commit("new.md", "work\n", "Work")
        self.git("merge", "-q", "--no-edit", "main")
        clean = self.scan(base=published)
        self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)
        # A merge that adds a line in neither parent (an "evil merge") is reported.
        self.git("checkout", "-q", "-b", "evil", self.base)
        self.commit("new.md", "work\n", "Work again")
        self.git("merge", "-q", "--no-commit", "main")
        (self.repo / "new.md").write_text(f"work\n{TERM}\n", encoding="utf-8")
        self.git("add", "new.md")
        self.git("commit", "-q", "--no-edit")
        merge = self.git("rev-parse", "HEAD")
        self.assertFound(self.scan(base=published), f"FOUND {merge[:12]} new.md:2: listed term #1")

    def test_root_commit_range_from_another_branch(self) -> None:
        self.git("checkout", "-q", "--orphan", "fresh")
        self.git("rm", "-q", "-rf", ".")
        root = self.commit("a.md", f"{TERM}\n", "Fresh root")
        self.assertFound(self.scan(head=root), f"FOUND {root[:12]} a.md:1: listed term #1")

    def test_binary_files_are_noted_not_scanned(self) -> None:
        binary = self.commit("image.bin", b"\x00\x01" + TERM.encode() + b"\x00", "Add image")
        result = self.scan()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f"NOTE binary file not scanned, check it by hand: {binary[:12]} image.bin", result.stdout)

    def test_extra_text_files(self) -> None:
        body = Path(self.tmp.name) / "pr-body.md"
        body.write_text(f"Summary\n\nThanks {TERM}\n", encoding="utf-8")
        self.assertFound(self.scan("--text", str(body)), "FOUND text pr-body.md:3: listed term #1")

    def test_hostile_configuration_and_environment(self) -> None:
        self.commit("a.md", f"{TERM}\n", "Add a")
        for key, value in [("diff.noprefix", "true"), ("diff.mnemonicPrefix", "true"), ("diff.relative", "true"),
                           ("diff.external", "false"), ("core.quotePath", "true"), ("color.ui", "always")]:
            self.git("config", key, value)
        other = Path(self.tmp.name) / "other"
        other.mkdir()
        self.git("init", "-q", cwd=other)
        env = {**self.env, "GIT_DIR": str(other / ".git"), "GIT_WORK_TREE": str(other)}
        (self.repo / "sub").mkdir()
        result = self.scan(env=env, cwd=self.repo / "sub")
        self.assertFound(result, "a.md:1: listed term #1")

    def test_refuses_terms_file_inside_the_repository(self) -> None:
        inside = self.repo / "terms.txt"
        inside.write_text(f"{TERM}\n", encoding="utf-8")
        command = [sys.executable, str(SCRIPT), self.base, "HEAD", "--terms", str(inside)]
        result = subprocess.run(command, cwd=self.repo, env=self.env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("outside the repository", result.stderr)

    def test_refuses_shallow_clone_and_unknown_refs(self) -> None:
        self.commit("a.md", "x\n", "Add a")
        self.commit("b.md", "y\n", "Add b")
        clone = Path(self.tmp.name) / "shallow"
        self.git("clone", "-q", "--depth", "1", f"file://{self.repo}", str(clone), cwd=Path(self.tmp.name))
        shallow = self.scan(base="HEAD", cwd=clone)
        self.assertEqual(shallow.returncode, 2)
        self.assertIn("shallow clone", shallow.stderr)
        latin1 = Path(self.tmp.name) / "latin1.txt"
        latin1.write_bytes(b"caf\xe9\n")
        unreadable = self.scan("--text", str(latin1))
        self.assertEqual(unreadable.returncode, 2, unreadable.stdout + unreadable.stderr)
        missing = self.scan(base="no-such-ref")
        self.assertEqual(missing.returncode, 2)
        self.assertIn("ERROR", missing.stderr)


if __name__ == "__main__":
    unittest.main()
