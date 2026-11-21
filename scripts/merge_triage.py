#!/usr/bin/env python3
"""Merge the manual triage parts with the first-pass classification.

Checks that every 'review' and 'likely' repo was triaged exactly once, then
writes data/in_scope.csv with every repo triaged as runtime or engineering.
"""
import csv
import json
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
TRIAGE = DATA / "triage"

# Manual corrections after a second look at the low-confidence verdicts, and the
# repos that are in scope by what they claim but hold no server source (docs,
# releases or installer only). Kept in data/triage/overrides.json with the rest
# of the per-repo data.
_MANUAL = json.load(open(TRIAGE / "overrides.json"))
OVERRIDES = _MANUAL["overrides"]
NO_SOURCE = set(_MANUAL["no_source"])

# bucket -> (input file pattern, part file pattern, number of parts)
PASSES = {
    "review": ("input-{}.txt", "part-{}.json", 4),
    "likely": ("likely-input-{}.txt", "likely-part-{}.json", 3),
}


def load_pass(bucket, rows):
    inp, part_pat, n = PASSES[bucket]
    triaged = []
    for i in range(1, n + 1):
        expected = [l.strip() for l in (TRIAGE / inp.format(i)).read_text().splitlines() if l.strip()]
        part = json.loads((TRIAGE / part_pat.format(i)).read_text())
        assert [e["repo"] for e in part] == expected, f"{bucket} part {i}: does not match its input list"
        triaged += part
    names = [e["repo"] for e in triaged]
    wanted = {r for r, v in rows.items() if v["bucket"] == bucket}
    assert len(names) == len(set(names)) and set(names) == wanted, f"{bucket}: triage does not cover the bucket exactly"
    for e in triaged:
        e.update(OVERRIDES.get(e["repo"], {}))
        e["bucket"] = bucket
    return triaged


def summary(label, triaged):
    print(f"{label} verdicts:", dict(Counter(e["verdict"] for e in triaged)))
    print("  out reasons:", dict(Counter(e["out_reason"] for e in triaged if e["verdict"] == "out")))
    print("  confidence:", dict(Counter(e["confidence"] for e in triaged)))


def main():
    rows = {r["repo"]: r for r in csv.DictReader(open(DATA / "candidates_classified.csv"))}
    triaged = []
    for bucket in PASSES:
        part = load_pass(bucket, rows)
        summary(bucket, part)
        triaged += part
    (TRIAGE / "merged.json").write_text(json.dumps(triaged, indent=1))

    out = []
    for e in triaged:
        if e["verdict"] in ("runtime", "engineering"):
            r = rows[e["repo"]]
            out.append({"repo": e["repo"], "category": e["verdict"], "first_pass": e["bucket"],
                        "protocols": ";".join(e["protocols"]), "write_claim": e["write_claim"],
                        "confidence": e["confidence"], "source": "no" if e["repo"] in NO_SOURCE else "yes",
                        "note": e["note"], "stars": r["stars"], "pushed": r["pushed"], "url": r["url"]})
    out.sort(key=lambda o: (o["category"], -int(o["stars"] or 0)))
    with open(DATA / "in_scope.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(out[0]))
        writer.writeheader()
        writer.writerows(out)
    print("in_scope.csv:", dict(Counter(o["category"] for o in out)), "total", len(out),
          "| no source:", sum(o["source"] == "no" for o in out),
          "| write claim:", dict(Counter(o["write_claim"] for o in out)))


if __name__ == "__main__":
    main()
