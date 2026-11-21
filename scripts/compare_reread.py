#!/usr/bin/env python3
"""Compare the blind re-read of the 20-server sample (private/code_check/
reread-1..4.json) with the original code check, field by field. Prints the
agreement per field and every disagreement, for settling by hand."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CC = ROOT / "private" / "code_check"
sys.path.insert(0, str(ROOT / "scripts"))
from recount_gates import hard_new  # noqa: E402  (same gate rule as the article numbers)

orig = {e["repo"]: e for e in json.load(open(CC / "merged.json"))}
sample = json.load(open(CC / "sample-20.json"))
rr = {}
for i in range(1, 5):
    p = CC / f"reread-{i}.json"
    if p.exists():
        for x in json.load(open(p)):
            rr[x["repo"]] = x


def low(v):
    return v.lower() if isinstance(v, str) else json.dumps(v).lower()


def o_fields(e):
    wd = low(e.get("write_default"))
    wd = "on" if wd.startswith("on") else "off" if wd.startswith("off") else "none" if wd.startswith("none") else wd[:12]
    tr = low(e.get("transport"))
    http = "yes" if re.search(r"http|sse|both", tr) else "no"
    hb = low(e.get("http_bind"))
    hb = ("n/a" if http == "no" or hb.startswith("n/a") else "all_interfaces" if "0.0.0.0" in hb or "all" in hb
          else "localhost" if "127.0.0.1" in hb or "localhost" in hb else "configurable" if "config" in hb else hb[:14])
    ha = low(e.get("http_auth"))
    ha = "n/a" if http == "no" or ha.startswith("n/a") else "none" if ha.startswith("none") else "token" if "token" in ha or "key" in ha else "oauth" if "oauth" in ha else ha[:12]
    tg = low(e.get("target"))
    tg = "agent_chosen" if tg.startswith("agent") else "fixed" if tg.startswith("fixed") else "n/a" if tg.startswith("n/a") else tg[:12]
    hard = "n/a" if wd == "none" else ("yes" if hard_new(e) else "no")
    return {"write_default": wd, "hard_gate": hard, "target": tg, "http_capable": http, "http_bind": hb, "http_auth": ha}


def r_fields(x):
    wd = low(x.get("write_default"))[:5].strip()
    gates = {g.lower() for g in x.get("gates") or []}
    hard = "n/a" if wd == "none" else ("yes" if gates & {"operator_flag", "allowlist", "value_bounds", "human_approval"} else "no")
    return {"write_default": wd, "hard_gate": hard, "target": low(x.get("target")), "http_capable": low(x.get("http_capable")),
            "http_bind": low(x.get("http_bind")), "http_auth": low(x.get("http_auth"))}


FIELDS = ["write_default", "hard_gate", "target", "http_capable", "http_bind", "http_auth"]
agree = {f: [0, 0] for f in FIELDS}
missing = [r for r in sample if r not in rr]
diffs = []
for r in sample:
    if r not in rr:
        continue
    a, b = o_fields(orig[r]), r_fields(rr[r])
    for f in FIELDS:
        if f.startswith("http_b") or f == "http_auth":
            if a["http_capable"] == "no" and b["http_capable"] == "no":
                continue
        agree[f][1] += 1
        if a[f] == b[f]:
            agree[f][0] += 1
        else:
            diffs.append((r, f, a[f], b[f]))
print("re-read:", len(rr), "of", len(sample), "| missing:", missing)
tot = [sum(v[0] for v in agree.values()), sum(v[1] for v in agree.values())]
for f, (m, n) in agree.items():
    print(f"  {f:14} {m}/{n}")
print(f"  {'all fields':14} {tot[0]}/{tot[1]}")
print("\nDISAGREEMENTS (repo | field | original | re-read)")
for d in diffs:
    print("  " + " | ".join(d))
