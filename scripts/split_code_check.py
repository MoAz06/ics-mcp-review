#!/usr/bin/env python3
"""Split the in-scope repos that still need a code check into N input lists.

Skips the pilot repos and the repos with no server source. Sorts by source size
and deals round-robin, so each part gets a mix of large and small repos.
"""
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "private" / "code_check"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 10


def source_files(repo):
    d = ROOT / "data" / "src" / repo.replace("/", "__")
    r = subprocess.run(["git", "-C", str(d), "ls-files"], capture_output=True, text=True)
    exts = (".py", ".ts", ".js", ".mjs", ".go", ".cs", ".rs", ".java", ".kt")
    return sum(1 for p in r.stdout.splitlines() if p.endswith(exts))


def main():
    rows = list(csv.DictReader(open(ROOT / "data" / "in_scope.csv")))
    pilot = {e["repo"] for e in json.load(open(OUT / "pilot.json"))}
    todo = [r["repo"] for r in rows if r["source"] == "yes" and r["repo"] not in pilot]
    todo.sort(key=source_files, reverse=True)
    for i in range(N):
        part = todo[i::N]
        (OUT / f"input-{i + 1}.txt").write_text("\n".join(part) + "\n")
    print(f"{len(todo)} repos to check, {N} parts of {len(todo) // N}-{-(-len(todo) // N)}")


if __name__ == "__main__":
    main()
