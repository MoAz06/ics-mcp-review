#!/usr/bin/env python3
"""Pre-publication check: scan the files git would publish for the name of any
reviewed repository or its owner. Names come from the local, git-ignored data
at run time, so this script itself names no project.

Usage: python3 scripts/check_public.py   (run from the repository root)
Exit code 1 if anything is found."""
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

names = set()
cand = json.load(open(ROOT / "data" / "github_candidates.json"))
for full in [c["fullName"] for c in cand["repos"]] + list(cand.get("glama_unresolved", [])):
    if "/" in full:
        names.update(full.split("/", 1))
for row in csv.DictReader(open(ROOT / "data" / "in_scope.csv")):
    names.update(row["repo"].split("/", 1))
for d in (ROOT / "data" / "repos").iterdir():
    names.update(d.name.split("__", 1))

# Generic words that are also repo or owner names would drown the check.
GENERIC = {"mcp", "plc", "modbus", "opcua", "opc", "scada", "industrial", "server", "tools",
           "bridge", "gateway", "agent", "agents", "codesys", "twincat", "bacnet", "knx", "iot",
           "siemens", "docs", "test", "demo", "mqtt", "edge", "core", "lab", "python", "github"}
# Protocol libraries and words the scripts name on purpose, which also happen
# to be the name of some owner or repo.
LIBRARIES = {"node-opcua", "opcfoundation", "mcprotocol", "controllogix", "releases"}
names = {n for n in names if len(n) >= 5 and n.lower() not in GENERIC | LIBRARIES}
pattern = re.compile(r"(?<![A-Za-z0-9_-])(" + "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True)) + r")(?![A-Za-z0-9_-])", re.I)

files = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                       cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
hits = 0
for f in files:
    try:
        text = (ROOT / f).read_text(errors="ignore")
    except (IsADirectoryError, FileNotFoundError):
        continue
    for n, line in enumerate(text.splitlines(), 1):
        for m in pattern.finditer(line):
            hits += 1
            print(f"{f}:{n}: {m.group(0)}  |  {line.strip()[:120]}")
print(f"{len(files)} files to publish, {len(names)} names checked, {hits} hits")
sys.exit(1 if hits else 0)
