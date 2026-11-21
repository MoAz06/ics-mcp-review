#!/usr/bin/env python3
"""Shallow-clone every in-scope repo into data/src/<owner>__<name> for reading.

Read only: nothing in these clones is installed, built or run. Blobs over 1 MB
are skipped (firmware, binaries, datasets). data/src/ is git-ignored: it is other
people's code and is not redistributed.
"""
import csv
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
SRC = DATA / "src"


def clone(repo):
    dest = SRC / repo.replace("/", "__")
    if dest.exists():
        return repo, "exists"
    try:
        r = subprocess.run(["git", "clone", "--quiet", "--depth", "1", "--filter=blob:limit=1m",
                            "--no-tags", f"https://github.com/{repo}.git", str(dest)],
                           capture_output=True, text=True, timeout=600,
                           env={"GIT_TERMINAL_PROMPT": "0", "PATH": "/usr/bin:/bin"})
    except subprocess.TimeoutExpired:
        return repo, "error: timeout"
    return repo, "ok" if r.returncode == 0 else "error: " + r.stderr.strip()[-200:]


def main():
    SRC.mkdir(exist_ok=True)
    repos = [r["repo"] for r in csv.DictReader(open(DATA / "in_scope.csv"))]
    with ThreadPoolExecutor(6) as pool:
        results = list(pool.map(clone, repos))
    errors = [(r, s) for r, s in results if s.startswith("error")]
    print(f"{len(repos)} repos, {len(errors)} errors")
    for r, s in errors:
        print(" ", r, s)
    (DATA / "clone_errors.txt").write_text("".join(f"{r}\t{s}\n" for r, s in errors))


if __name__ == "__main__":
    main()
