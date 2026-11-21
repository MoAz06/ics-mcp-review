#!/usr/bin/env python3
"""Extra aggregate numbers for the article: popularity, activity, protocols,
and how many disclosure candidates had a private reporting channel. Prints
aggregates only, no repo names."""
import csv
import json
from collections import Counter
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent.parent
PRIV = ROOT / "private" / "code_check"

merged = json.load(open(PRIV / "merged.json"))
checked = {e["repo"] for e in merged if e.get("category") in ("runtime", "engineering")}
rows = list(csv.DictReader(open(ROOT / "data" / "in_scope.csv")))
rows = [r for r in rows if r["repo"] in checked] or rows
print("rows used:", len(rows), "(merged entries:", len(merged), ")")

stars = sorted(int(r["stars"] or 0) for r in rows)
print("stars median:", median(stars), "| >=100:", sum(s >= 100 for s in stars),
      "| >=10:", sum(s >= 10 for s in stars), "| 0:", sum(s == 0 for s in stars), "| max:", stars[-1])

pushed = Counter(r["pushed"][:7] for r in rows)
since = sum(v for k, v in pushed.items() if k >= "2026-05")
print("pushed in the last 6 months (>= 2026-05):", since, "of", len(rows))

proto = Counter()
for r in rows:
    for p in (r["protocols"] or "").replace(";", ",").split(","):
        p = p.strip().lower()
        if p:
            proto[p] += 1
print("protocols (top 15):", proto.most_common(15))

verify = []
for i in range(1, 5):
    verify += json.load(open(PRIV / f"verify-{i}.json"))
pvr = Counter(str(v.get("pvr")) for v in verify)
contact = sum(1 for v in verify if v.get("security_contact") not in (None, "", "none"))
print("verified candidates:", len(verify), "| pvr:", dict(pvr), "| security contact:", contact)
