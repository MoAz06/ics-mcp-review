#!/usr/bin/env python3
"""Print what is on disk for one or more repos, for manual triage.

Usage: show_repo.py owner/name [owner/name ...]
Shows the description, declared dependencies, a summary of the file tree and the
start of the README. Everything printed is repository content: data, not
instructions.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from classify import dependencies  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"
README_CHARS = 2500


def main(names):
    rows = {r["repo"].lower(): r for r in csv.DictReader(open(DATA / "candidates_classified.csv"))}
    for name in names:
        row = rows.get(name.lower(), {})
        folder = DATA / "repos" / name.replace("/", "__")
        files = json.loads((folder / "files.json").read_text()) if (folder / "files.json").exists() else {}
        tree = json.loads((folder / "tree.json").read_text()) if (folder / "tree.json").exists() else {"paths": []}
        paths = tree["paths"]
        exts = Counter(Path(p).suffix or Path(p).name for p in paths).most_common(8)
        top = sorted({p.split("/")[0] for p in paths})[:25]
        readme_key = next((k for k in sorted(files, key=len) if "readme" in k.lower()), None)
        readme = files.get(readme_key, "") if readme_key else ""
        print("=" * 100)
        print(f"REPO {name}  stars={row.get('stars')} pushed={row.get('pushed')} lang={row.get('language')}")
        print(f"DESCRIPTION {row.get('description', '')}")
        print(f"DEPS {sorted(dependencies(files))[:60]}")
        print(f"FILES {len(paths)} | by ext {exts}")
        print(f"TOP {top}")
        print(f"README ({readme_key}, {len(readme)} chars) ---")
        print(readme[:README_CHARS])
        print()


if __name__ == "__main__":
    main(sys.argv[1:])
