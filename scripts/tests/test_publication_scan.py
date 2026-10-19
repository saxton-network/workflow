from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "publication-scan.py"

# Built from pieces so this file passes the scan it tests.
PERSONAL_EMAIL = "someone" + "@" + "mail.co"
NO_REPLY = "agent" + "@" + "noreply.co"
TOKEN = "ghp" + "_" + "A1b2" * 9
KEY_HEADER = "-----BEGIN " + "RSA PRIVATE KEY-----"
PGP_HEADER = "-----BEGIN " + "PGP PRIVATE KEY BLOCK-----"
HOME_PATH = "/ho" + "me/someuser/notes.txt"
JSON_HOME_PATH = "C:\\\\Us" + "ers\\\\someuser"
TERM = "zebrafinch"


def load_module():
    spec = importlib.util.spec_from_file_location("publication_scan", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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
             env: dict[str, str] | None = None, terms: Path | None = None,
             timeout: float | None = None) -> subprocess.CompletedProcess[str]:
        words = ["--no-terms"] if "--no-terms" in args else ["--terms", str(terms or self.terms)]
        command = [sys.executable, str(SCRIPT), base or self.base, head, *words, "--allow-email", NO_REPLY,
                   *(arg for arg in args if arg != "--no-terms")]
        return subprocess.run(command, cwd=cwd or self.repo, env=env or self.env, timeout=timeout,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def write_terms(self, *terms: str, prefix: str = "") -> Path:
        path = Path(self.tmp.name) / "more-terms.txt"
        path.write_text(prefix + "\n".join(terms) + "\n", encoding="utf-8")
        return path

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
        url = "https://x.org/ho" + "me/page and https://x.org/Us" + "ers/list"
        remote = "git" + "@" + "github.com:owner/repo.git and ssh://git" + "@" + "github.com/owner/repo"
        self.commit("a.md", f"token {TOKEN}\n{KEY_HEADER}\nsaved to {HOME_PATH}\n/tmp/x and /root/y\n"
                            f"{PGP_HEADER}\n\"path\": \"{JSON_HOME_PATH}\"\n{url}\n{remote}\n", "Add a")
        result = self.scan()
        self.assertFound(result, "a.md:1: credential GitHub token", "a.md:2: credential private key",
                         "a.md:3: home directory path", "a.md:5: credential private key",
                         "a.md:6: home directory path")
        for line in ("a.md:4", "a.md:7", "a.md:8"):
            self.assertNotIn(line, result.stdout)

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

    def test_binary_files_fail_unless_allowed(self) -> None:
        binary = self.commit("image.bin", b"\x00\x01\xff\xfe\n\x89PNG" + TERM.encode() + b"\x00\n", "Add image")
        note = f"NOTE binary file not scanned, check it by hand: {binary[:12]} image.bin"
        result = self.scan()
        self.assertFound(result, note, "FAIL: 1 binary files not scanned")
        self.assertNotIn("FOUND", result.stdout)
        allowed = self.scan("--allow-binary")
        self.assertEqual(allowed.returncode, 0, allowed.stdout + allowed.stderr)
        self.assertIn(note, allowed.stdout)

    def test_files_marked_not_diffable_are_still_read(self) -> None:
        self.commit(".gitattributes", "*.txt -diff\n", "Attributes")
        marked = self.commit("secret.txt", f"plain {TERM}\n", "Add secret")
        self.assertFound(self.scan(), f"FOUND {marked[:12]} secret.txt:1: listed term #1")

    def test_extra_text_files(self) -> None:
        self.commit("a.md", "fine\n", "Add a")
        body = Path(self.tmp.name) / "pr-body.md"
        body.write_text(f"Summary\n\nThanks {TERM}\n", encoding="utf-8")
        self.assertFound(self.scan("--text", str(body)), "FOUND text pr-body.md:3: listed term #1")

    def test_hostile_configuration_and_environment(self) -> None:
        self.commit("a.md", f"{TERM}\n", "Add a")
        # A signed commit under log.showSignature=true: the signature check's output must not shift
        # the message's line numbers. The signature is fake; gpg reports it to stdout all the same.
        raw = self.git("cat-file", "commit", "HEAD")
        header = raw.split("\n\n", 1)[0]
        signature = "gpgsig -----BEGIN PGP SIGNATURE-----\n \n iQEzBAABCAAdFiEE\n -----END PGP SIGNATURE-----"
        signed = subprocess.run(["git", "hash-object", "-t", "commit", "-w", "--stdin"], cwd=self.repo, env=self.env,
                                input=f"{header}\n{signature}\n\nAdd a\n\nThanks {TERM}.\n", check=True,
                                stdout=subprocess.PIPE, text=True).stdout.strip()
        self.git("update-ref", "refs/heads/main", signed)
        self.git("config", "log.showSignature", "true")
        other = Path(self.tmp.name) / "other"
        other.mkdir()
        self.git("init", "-q", cwd=other)
        env = {**self.env, "GIT_DIR": str(other / ".git"), "GIT_WORK_TREE": str(other)}
        (self.repo / "sub").mkdir()
        result = self.scan(env=env, cwd=self.repo / "sub")
        self.assertFound(result, "a.md:1: listed term #1", f"FOUND {signed[:12]} message:3: listed term #1")

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

    def test_hunk_heading_with_a_plus_token(self) -> None:
        # Git puts the nearest heading line after the hunk range; it may hold " +x" or " +7".
        self.commit("build.sh", "chmod +x build.sh\n  old\nrun +7 times\n  old\n", "Add script")
        self.commit("build.sh", f"chmod +x build.sh\n  {TERM}\nrun +7 times\n  {TERM}\n", "Edit script")
        self.assertFound(self.scan(), "build.sh:2: listed term #1", "build.sh:4: listed term #1")

    def test_unexpected_error_exits_2(self) -> None:
        module = load_module()
        stderr = io.StringIO()
        with mock.patch.object(module, "_git", side_effect=ValueError("boom")), contextlib.redirect_stderr(stderr):
            code = module.main([self.base, "HEAD", "--no-terms"])
        self.assertEqual(code, 2)
        self.assertIn("ERROR: ValueError: boom", stderr.getvalue())

    def test_long_line_is_fast(self) -> None:
        self.commit("long.txt", "x" * 200_000 + " a.b" * 20_000 + "\n", "Add long line")
        started = time.monotonic()
        result = self.scan(timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertLess(time.monotonic() - started, 5)

    def test_copy_paste_spellings_match(self) -> None:
        terms = self.write_terms("pale lantern", "quill-maker", "crow\u2019s nest", TERM)
        text = ("pale\u00a0lantern\nquill\u2011maker\ncrow\u2019s nest\nzebra\u00adfinch\npale  lantern\n"
                "crow's\tnest\npale lanterns and a quill maker\n")
        self.commit("a.md", text, "Add a")
        result = self.scan(terms=terms)
        self.assertFound(result, "a.md:1: listed term #1", "a.md:2: listed term #2", "a.md:3: listed term #3",
                         "a.md:4: listed term #4", "a.md:5: listed term #1", "a.md:6: listed term #3")
        self.assertNotIn("a.md:7", result.stdout)

    def test_term_wrapped_across_lines(self) -> None:
        terms = self.write_terms("pale lantern")
        wrapped = self.commit("a.md", "x\nunder the pale\nlantern\npale lantern and pale\nlantern\n",
                              "Add a\n\nSeen under the pale\nlantern.")
        result = self.scan(terms=terms)
        self.assertFound(result, f"FOUND {wrapped[:12]} a.md:2: listed term #1", "a.md:4: listed term #1",
                         "message:3: listed term #1")
        self.assertEqual(result.stdout.count("a.md:4:"), 1)
        self.assertNotIn("a.md:3", result.stdout)

    def test_terms_file_with_byte_order_mark(self) -> None:
        terms = self.write_terms("# private words", TERM, prefix="\ufeff")
        self.commit("a.md", "fine\n", "Add a")
        result = self.scan(terms=terms)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("1 listed terms", result.stdout)

    def test_paths_are_scanned_and_withheld(self) -> None:
        named = self.commit(f"notes-{TERM}.md", f"x\n{PERSONAL_EMAIL}\n", "Add notes")
        home = self.commit("ho" + "me/someuser/.profile", "fine\n", "Add profile")
        result = self.scan()
        self.assertFound(result, f"FOUND {named[:12]} path: listed term #1",
                         f"FOUND {named[:12]} <path withheld>:2: email address",
                         f"FOUND {home[:12]} path: home directory path")
        self.assertNotIn(TERM, result.stdout)
        self.assertIn(f"notes-{TERM}.md", self.scan("--show").stdout)

    def test_quoted_and_spaced_paths(self) -> None:
        quoted = self.commit('say "hi".md', f"{TERM}\n", "Add quoted")
        spaced = self.commit("two words.md", f"{TERM}\n", "Add spaced")
        result = self.scan()
        self.assertFound(result, f'FOUND {quoted[:12]} say "hi".md:1: listed term #1',
                         f"FOUND {spaced[:12]} two words.md:1: listed term #1")
        self.assertNotIn("\t", result.stdout)

    def test_merge_counts_only_lines_new_against_every_parent(self) -> None:
        self.commit("c.md", "a\n", "Add c")
        start = self.git("rev-parse", "HEAD")
        self.commit("c.md", f"a\nmain {TERM}\n", "Main side")
        published = self.git("rev-parse", "HEAD")
        self.git("checkout", "-q", "-b", "work", start)
        self.commit("c.md", "a\nwork side\n", "Work side")
        subprocess.run(["git", "merge", "-q", "main"], cwd=self.repo, env=self.env,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (self.repo / "c.md").write_text(f"a\nwork side\nmain {TERM}\nevil {TERM}\n", encoding="utf-8")
        self.git("add", "c.md")
        self.git("commit", "-q", "--no-edit")
        merge = self.git("rev-parse", "HEAD")
        result = self.scan(base=published)
        self.assertFound(result, f"FOUND {merge[:12]} c.md:4: listed term #1")
        self.assertNotIn("c.md:3", result.stdout)

    def test_requires_a_word_list_choice_and_a_range(self) -> None:
        self.commit("a.md", "fine\n", "Add a")
        command = [sys.executable, str(SCRIPT), self.base, "HEAD"]
        neither = subprocess.run(command, cwd=self.repo, env=self.env, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True)
        self.assertEqual(neither.returncode, 2, neither.stdout + neither.stderr)
        self.assertIn("--no-terms", neither.stderr)
        empty = self.scan(terms=self.write_terms("# only a comment"))
        self.assertEqual(empty.returncode, 2, empty.stdout + empty.stderr)
        self.assertIn("no terms", empty.stderr)
        nothing = self.scan(base="HEAD")
        self.assertEqual(nothing.returncode, 2, nothing.stdout + nothing.stderr)
        self.assertIn("nothing to scan", nothing.stderr)
        without = self.scan("--no-terms")
        self.assertEqual(without.returncode, 0, without.stdout + without.stderr)
        self.assertIn("0 listed terms", without.stdout)


if __name__ == "__main__":
    unittest.main()
