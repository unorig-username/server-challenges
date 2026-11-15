"""Tests for check_docs.py. Run: python3 -m unittest discover -s scripts"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import check_docs

ROOT = Path(__file__).resolve().parent.parent
ENTRY = "twelve-dollar/c-epoll-unorig-username"
README = "1 entries in 1 languages: [c-epoll](twelve-dollar/c-epoll-unorig-username).\n"


class Fixture:
    """A tiny committed repo: one challenge folder with one entry, a README that links it, and entries.json."""

    def __init__(self, tmp):
        self.root = Path(tmp)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        for f in ("install.sh", "build.sh", "start.sh"):
            self.write_file(f"{ENTRY}/{f}", "#!/usr/bin/env bash\n")
        self.write_file("README.md", README)
        self.entries = [{
            "challenge": "twelve-dollar",
            "entry": "c-epoll",
            "language": "C",
            "dir": ENTRY,
            "upstream": {"path": "submissions/c-epoll-unorig-username", "tree": None},
        }]
        self.commit()
        self.entries[0]["upstream"]["tree"] = self.tree(ENTRY)
        self.write()

    def write_file(self, rel, text):
        (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
        (self.root / rel).write_text(text)

    def write(self):
        self.write_file("entries.json", json.dumps({"entries": self.entries}))

    def commit(self, *add):
        git = ["git", "-C", str(self.root), "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false"]
        subprocess.run([*git, "add", "-A"], check=True)
        if add:
            subprocess.run([*git, "add", "-f", *add], check=True)
        subprocess.run([*git, "commit", "-q", "--no-verify", "-m", "x"], check=True)

    def tree(self, rel):
        return check_docs.git(self.root, "rev-parse", f"HEAD:{rel}").stdout.strip()


class CheckDocsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def check(self):
        return check_docs.check(self.fx.root)

    def test_consistent_fixture_passes(self):
        self.assertEqual(self.check(), [])

    def test_broken_readme_link(self):
        self.fx.write_file("README.md", README + "[gone](multicore/gone), [web](https://example.com), [top](#top).\n")
        self.assertEqual(self.check(), ["README.md links to multicore/gone, which does not exist"])

    def test_link_with_title_is_checked(self):
        self.fx.write_file("README.md", README + '[gone](multicore/gone "t"), [ok](<entries.json> "t").\n')
        self.assertEqual(self.check(), ["README.md links to multicore/gone, which does not exist"])

    def test_leading_slash_is_the_repo_root(self):
        self.fx.write_file("README.md", "1 entries in 1 languages: [c-epoll](/twelve-dollar/c-epoll-unorig-username/), [x](/usr/bin).\n")
        self.assertEqual(self.check(), ["README.md links to /usr/bin, which does not exist"])

    def test_link_outside_the_repo(self):
        self.fx.write_file("README.md", README + "[x](../../..), [y](twelve-dollar/../README.md).\n")
        self.assertEqual(self.check(), ["README.md links to ../../.., which is outside the repo"])

    def test_counts_must_match_whole_numbers(self):
        self.fx.write_file("README.md", "11 entries in 21 languages: [c-epoll](twelve-dollar/c-epoll-unorig-username).\n")
        self.assertEqual(self.check(), ["README.md should say '1 entries' (counted from entries.json)",
                                        "README.md should say '1 languages' (counted from entries.json)"])

    def test_directory_missing_from_entries_json(self):
        (self.fx.root / "twelve-dollar" / "zsh-ztcp-unorig-username").mkdir()
        self.assertEqual(self.check(), ["twelve-dollar/zsh-ztcp-unorig-username is not in entries.json"])

    def test_entry_without_directory(self):
        self.fx.entries.append({**self.fx.entries[0], "entry": "go-epoll", "dir": "twelve-dollar/go-epoll"})
        self.fx.write()
        self.assertEqual(self.check(), ["entries.json lists twelve-dollar/go-epoll, which does not exist",
                                        "README.md should say '2 entries' (counted from entries.json)"])

    def test_duplicate_entry(self):
        self.fx.entries.append(dict(self.fx.entries[0]))
        self.fx.write()
        self.assertIn(f"entries.json lists {ENTRY} more than once", self.check())

    def test_entry_under_the_wrong_challenge(self):
        self.fx.entries[0]["challenge"] = "multicore"
        self.fx.write()
        self.assertEqual(self.check(), [f"{ENTRY} is not under its challenge folder multicore/"])

    def test_missing_start_sh(self):
        (self.fx.root / ENTRY / "start.sh").unlink()
        self.fx.commit()
        self.fx.entries[0]["upstream"]["tree"] = self.fx.tree(ENTRY)
        self.fx.write()
        self.assertEqual(self.check(), [f"{ENTRY} has no start.sh"])

    def test_entry_not_linked_from_readme(self):
        self.fx.write_file("README.md", "1 entries in 1 languages.\n")
        self.assertEqual(self.check(), [f"README.md does not link {ENTRY}"])

    def test_uncommitted_and_committed_edits_are_caught(self):
        self.fx.write_file(f"{ENTRY}/build.sh", "#!/usr/bin/env bash\nexit 0\n")
        self.assertEqual(self.check(), [f"{ENTRY} has uncommitted changes"])
        self.fx.commit()
        [error] = self.check()
        self.assertTrue(error.startswith(f"{ENTRY} differs from upstream"), error)

    def test_committed_ignored_file_is_caught(self):
        self.fx.write_file(".gitignore", "bin/\n")
        self.fx.write_file(f"{ENTRY}/bin/extra.sh", "echo extra\n")
        self.fx.commit(f"{ENTRY}/bin/extra.sh")
        [error] = self.check()
        self.assertTrue(error.startswith(f"{ENTRY} differs from upstream"), error)

    def test_untracked_file_is_not_an_error(self):
        self.fx.write_file(f"{ENTRY}/.DS_Store", "\0\0\0\1Bud1")
        self.assertEqual(self.check(), [])

    def test_lost_exec_bit_is_caught(self):
        script = self.fx.root / ENTRY / "start.sh"
        script.chmod(0o755)
        self.fx.commit()
        self.fx.entries[0]["upstream"]["tree"] = self.fx.tree(ENTRY)
        self.fx.write()
        self.assertEqual(self.check(), [])
        script.chmod(0o644)
        self.assertEqual(self.check(), [f"{ENTRY} has uncommitted changes"])
        self.fx.commit()
        [error] = self.check()
        self.assertTrue(error.startswith(f"{ENTRY} differs from upstream"), error)

    def test_uncommitted_entry_directory_is_reported(self):
        self.fx.entries.append({**self.fx.entries[0], "entry": "go-epoll", "dir": "twelve-dollar/go-epoll"})
        self.fx.write()
        (self.fx.root / "twelve-dollar" / "go-epoll").mkdir()
        self.fx.write_file("README.md", "2 entries in 1 languages: [c](twelve-dollar/c-epoll-unorig-username) [go](twelve-dollar/go-epoll).\n")
        errors = self.check()
        self.assertTrue(any(e.startswith("twelve-dollar/go-epoll: cannot read its committed tree") for e in errors), errors)

    def test_outside_a_git_checkout_is_reported(self):
        shutil.rmtree(self.fx.root / ".git")
        [error] = self.check()
        self.assertTrue(error.startswith(f"{ENTRY}: cannot read its committed tree"), error)

    def test_exit_code(self):
        def run():
            return subprocess.run([sys.executable, str(ROOT / "scripts" / "check_docs.py"), str(self.fx.root)], capture_output=True, text=True)
        ok = run()
        self.assertEqual((ok.returncode, ok.stdout), (0, "0 problem(s)\n"))
        (self.fx.root / ENTRY / "start.sh").unlink()
        self.assertEqual(run().returncode, 1)

    def test_this_repo_is_consistent(self):
        self.assertEqual(check_docs.check(ROOT), [])


if __name__ == "__main__":
    unittest.main()
