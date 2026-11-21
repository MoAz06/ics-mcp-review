#!/usr/bin/env python3
"""Check each Glama seed against GitHub and merge the ones that exist into the
candidate list. A seed that is not a GitHub repo at that path is recorded as
unresolved, not dropped silently."""
import json
import subprocess
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
SEEDS = DATA / "glama_seeds.txt"
CANDIDATES = DATA / "github_candidates.json"


def repo_info(path):
    jq = ("{fullName: .full_name, description, url: .html_url, stargazersCount: .stargazers_count,"
          " pushedAt: .pushed_at, updatedAt: .updated_at, isArchived: .archived, isFork: .fork,"
          " language, license: .license}")
    r = subprocess.run(["gh", "api", f"repos/{path}", "--jq", jq], capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 else None


def main():
    data = json.loads(CANDIDATES.read_text())
    repos = {r["fullName"].lower(): r for r in data["repos"]}
    seeds = [line.strip() for line in SEEDS.read_text().splitlines()
             if line.strip() and not line.startswith("#")]
    new, known, unresolved = 0, 0, []
    for seed in seeds:
        key = seed.lower()
        if key in repos:
            repos[key].setdefault("sources", []).append("glama")
            known += 1
            continue
        info = repo_info(seed)
        if info is None:
            unresolved.append(seed)
            continue
        key = info["fullName"].lower()  # follows renames
        entry = repos.setdefault(key, {**info, "queries": []})
        entry.setdefault("sources", []).append("glama")
        new += 1
    data["repos"] = list(repos.values())
    data["glama_unresolved"] = unresolved
    CANDIDATES.write_text(json.dumps(data, indent=1))
    print(f"seeds {len(seeds)}: already found {known}, added {new}, unresolved {len(unresolved)}")
    for s in unresolved:
        print("  unresolved:", s)
    print(f"total candidates now {len(repos)}")


if __name__ == "__main__":
    main()
