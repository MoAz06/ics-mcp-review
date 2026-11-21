#!/usr/bin/env python3
"""Download, for every candidate, its README and its dependency manifests.

Only metadata and manifest files are fetched, through the GitHub API. Nothing is
cloned, built or run. Files land in data/repos/<owner>__<name>/ together with
the file tree, so classify.py can work offline and the evidence stays on disk.
"""
import base64
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = DATA / "repos"

MANIFEST = re.compile(
    r"(^|/)(requirements[^/]*\.txt|pyproject\.toml|setup\.py|setup\.cfg|Pipfile|"
    r"package\.json|go\.mod|Cargo\.toml|[^/]+\.csproj|pom\.xml|build\.gradle(\.kts)?|"
    r"README(\.[a-z]+)?)$",
    re.IGNORECASE,
)
MAX_DEPTH = 3       # manifests deeper than this are vendored or examples
MAX_FILES = 25


def gh_json(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if r.returncode != 0:
        return None, r.stderr.strip()[:300]
    return json.loads(r.stdout), None


def fetch(repo):
    name = repo["fullName"]
    folder = OUT / name.replace("/", "__")
    if (folder / "tree.json").exists():
        return name, "cached"
    folder.mkdir(parents=True, exist_ok=True)
    meta, err = gh_json(f"repos/{name}")
    if meta is None:
        (folder / "error.txt").write_text(err)
        return name, "error"
    tree, err = gh_json(f"repos/{name}/git/trees/{meta['default_branch']}?recursive=1")
    if tree is None:
        (folder / "error.txt").write_text(err)
        return name, "error"
    paths = [t["path"] for t in tree.get("tree", []) if t["type"] == "blob"]
    picked = [p for p in paths if MANIFEST.search(p) and p.count("/") < MAX_DEPTH]
    picked = [p for p in picked if "node_modules/" not in p][:MAX_FILES]
    files = {}
    for p in picked:
        blob, err = gh_json(f"repos/{name}/contents/{p}?ref={meta['default_branch']}")
        if blob and blob.get("encoding") == "base64":
            files[p] = base64.b64decode(blob["content"]).decode("utf-8", "replace")
    (folder / "tree.json").write_text(json.dumps({
        "default_branch": meta["default_branch"],
        "head_sha": tree.get("sha"),
        "truncated": tree.get("truncated", False),
        "paths": paths,
    }))
    (folder / "files.json").write_text(json.dumps(files))
    return name, f"{len(paths)} paths, {len(files)} files"


def main():
    repos = json.loads((DATA / "github_candidates.json").read_text())["repos"]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for name, status in pool.map(fetch, repos):
            if status.startswith("error"):
                print(name, status)
    print("done:", len(repos), "repos")


if __name__ == "__main__":
    main()
