"""Checks that README.md and entries.json agree with the files in the repo.

- Every relative link in README.md points at a file or directory inside the repo that exists.
- Every entry in entries.json has a directory with install.sh, build.sh and start.sh, and that
  directory is linked from README.md.
- Every directory under the challenge folders is in entries.json, and nothing is listed twice.
- Each entry's files are byte for byte the upstream submission: the git tree hash of its directory
  at HEAD equals the upstream tree hash recorded in entries.json (which also covers file modes),
  and the working tree has no uncommitted edits to it.
- The entry and language counts the README states match entries.json.

Usage: python3 scripts/check_docs.py [repo-root]
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

CHALLENGES = ("million-users", "multicore", "twelve-dollar")
# [text](target) or [text](<target> "title")
LINK = re.compile(r"\]\(<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\)")


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)


def check(root):
    root = Path(root).resolve()
    errors = []
    readme = (root / "README.md").read_text()
    entries = json.loads((root / "entries.json").read_text())["entries"]

    linked = set()
    for target in LINK.findall(readme):
        if re.match(r"^[a-z]+:|^#", target):
            continue
        # A leading / is the repo root, as GitHub renders it. normpath, not resolve: links are lexical.
        full = Path(os.path.normpath(root / target.split("#")[0].lstrip("/")))
        if not full.is_relative_to(root):
            errors.append(f"README.md links to {target}, which is outside the repo")
        elif not full.exists():
            errors.append(f"README.md links to {target}, which does not exist")
        else:
            linked.add(full.relative_to(root).as_posix())

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
        tree = git(root, "rev-parse", f"HEAD:{d}")
        if tree.returncode:
            errors.append(f"{d}: cannot read its committed tree ({tree.stderr.strip()})")
            continue
        if tree.stdout.strip() != e["upstream"]["tree"]:
            errors.append(f"{d} differs from upstream {e['upstream']['path']} (committed tree {tree.stdout.strip()}, expected {e['upstream']['tree']})")
        # Untracked files (a .DS_Store) are not counted; they only matter once committed, and then the tree hash catches them.
        if git(root, "diff", "--quiet", "HEAD", "--", d).returncode:
            errors.append(f"{d} has uncommitted changes")

    for n, noun in ((len(entries), "entries"), (len({e["language"] for e in entries}), "languages")):
        if not re.search(rf"(?<![\d,]){n} {noun}\b", readme):
            errors.append(f"README.md should say '{n} {noun}' (counted from entries.json)")
    return errors


if __name__ == "__main__":
    problems = check(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent)
    for p in problems:
        print(f"error: {p}")
    print(f"{len(problems)} problem(s)")
    sys.exit(1 if problems else 0)
