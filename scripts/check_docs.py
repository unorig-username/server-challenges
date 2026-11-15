"""Checks that README.md and entries.json agree with the files in the repo.

- Every relative link in README.md points at a file or directory that exists.
- Every entry in entries.json has a directory with install.sh, build.sh and start.sh, and that
  directory is linked from README.md.
- Every directory under the challenge folders is in entries.json, and nothing is listed twice.
- Each entry's files are byte for byte the upstream submission: the git tree hash of its directory
  equals the upstream tree hash recorded in entries.json (which also covers file modes).
- The entry and language counts the README states match entries.json.

Usage: python3 scripts/check_docs.py [repo-root]
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

CHALLENGES = ("million-users", "multicore", "twelve-dollar")
LINK = re.compile(r"\]\(([^)\s]+)\)")


def tree_hash(root, rel):
    """Git tree hash of a directory as it is on disk (ignored files excluded), without touching the real index."""
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(tmp) / "index")}
        run = lambda *a: subprocess.run(["git", "-C", str(root), *a], env=env, check=True, capture_output=True, text=True).stdout.strip()
        run("add", "--", rel)
        return run("write-tree", f"--prefix={rel}/")


def check(root):
    root = Path(root)
    errors = []
    readme = (root / "README.md").read_text()
    entries = json.loads((root / "entries.json").read_text())["entries"]

    linked = set()
    for target in LINK.findall(readme):
        if re.match(r"^[a-z]+:|^#", target):
            continue
        path = target.split("#")[0].rstrip("/")
        linked.add(path)
        if not (root / path).exists():
            errors.append(f"README.md links to {target}, which does not exist")

    dirs = [e["dir"] for e in entries]
    for d in sorted({d for d in dirs if dirs.count(d) > 1}):
        errors.append(f"entries.json lists {d} more than once")
    on_disk = {f"{c}/{p.name}" for c in CHALLENGES if (root / c).is_dir() for p in (root / c).iterdir() if p.is_dir()}
    for d in sorted(on_disk - set(dirs)):
        errors.append(f"{d} is not in entries.json")

    for e in entries:
        d = e["dir"]
        if d.split("/")[0] != e["challenge"]:
            errors.append(f"{d} is not under its challenge folder {e['challenge']}/")
        if not (root / d).is_dir():
            errors.append(f"entries.json lists {d}, which does not exist")
            continue
        for f in ("install.sh", "build.sh", "start.sh"):
            if not (root / d / f).is_file():
                errors.append(f"{d} has no {f}")
        if d not in linked:
            errors.append(f"README.md does not link {d}")
        got = tree_hash(root, d)
        if got != e["upstream"]["tree"]:
            errors.append(f"{d} differs from upstream {e['upstream']['path']} (tree {got}, expected {e['upstream']['tree']})")

    for claim in (f"{len(entries)} entries", f"{len({e['language'] for e in entries})} languages"):
        if claim not in readme:
            errors.append(f"README.md should say '{claim}' (counted from entries.json)")
    return errors


if __name__ == "__main__":
    problems = check(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent)
    for p in problems:
        print(f"error: {p}")
    print(f"{len(problems)} problem(s)")
    sys.exit(1 if problems else 0)
