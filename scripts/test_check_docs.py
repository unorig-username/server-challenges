"""Tests for check_docs.py. Run: python3 -m unittest discover -s scripts"""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import check_docs

ROOT = Path(__file__).resolve().parent.parent


class Fixture:
    """A tiny repo: one challenge folder with one entry, a README that links it, and entries.json."""

    def __init__(self, tmp):
        self.root = Path(tmp)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        entry = self.root / "twelve-dollar" / "c-epoll-unorig-username"
        entry.mkdir(parents=True)
        for f in ("install.sh", "build.sh", "start.sh"):
            (entry / f).write_text("#!/usr/bin/env bash\n")
        (self.root / "README.md").write_text("1 entries in 1 languages: [c-epoll](twelve-dollar/c-epoll-unorig-username).\n")
        self.entries = [{
            "challenge": "twelve-dollar",
            "entry": "c-epoll",
            "language": "C",
            "dir": "twelve-dollar/c-epoll-unorig-username",
            "upstream": {"path": "submissions/c-epoll-unorig-username",
                         "tree": check_docs.tree_hash(self.root, "twelve-dollar/c-epoll-unorig-username")},
        }]
        self.write()

    def write(self):
        (self.root / "entries.json").write_text(json.dumps({"entries": self.entries}))


class CheckDocsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_consistent_fixture_passes(self):
        self.assertEqual(check_docs.check(self.fx.root), [])

    def test_broken_readme_link(self):
        (self.fx.root / "README.md").write_text("1 entries in 1 languages: [c-epoll](twelve-dollar/c-epoll-unorig-username), [gone](multicore/gone), [web](https://example.com).\n")
        self.assertEqual(check_docs.check(self.fx.root), ["README.md links to multicore/gone, which does not exist"])

    def test_directory_missing_from_entries_json(self):
        (self.fx.root / "twelve-dollar" / "zsh-ztcp-unorig-username").mkdir()
        self.assertEqual(check_docs.check(self.fx.root), ["twelve-dollar/zsh-ztcp-unorig-username is not in entries.json"])

    def test_entry_without_directory_or_link(self):
        self.fx.entries.append({**self.fx.entries[0], "entry": "go-epoll", "dir": "twelve-dollar/go-epoll"})
        self.fx.write()
        errors = check_docs.check(self.fx.root)
        self.assertIn("entries.json lists twelve-dollar/go-epoll, which does not exist", errors)
        self.assertIn("README.md should say '2 entries' (counted from entries.json)", errors)

    def test_edited_entry_file_is_caught(self):
        (self.fx.root / "twelve-dollar" / "c-epoll-unorig-username" / "build.sh").write_text("#!/usr/bin/env bash\nexit 0\n")
        [error] = check_docs.check(self.fx.root)
        self.assertTrue(error.startswith("twelve-dollar/c-epoll-unorig-username differs from upstream"), error)

    def test_lost_exec_bit_is_caught(self):
        script = self.fx.root / "twelve-dollar" / "c-epoll-unorig-username" / "start.sh"
        script.chmod(0o755)
        self.fx.entries[0]["upstream"]["tree"] = check_docs.tree_hash(self.fx.root, self.fx.entries[0]["dir"])
        self.fx.write()
        self.assertEqual(check_docs.check(self.fx.root), [])
        script.chmod(0o644)
        self.assertEqual(len(check_docs.check(self.fx.root)), 1)

    def test_this_repo_is_consistent(self):
        self.assertEqual(check_docs.check(ROOT), [])


if __name__ == "__main__":
    unittest.main()
