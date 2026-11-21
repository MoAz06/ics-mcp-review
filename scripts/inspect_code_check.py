#!/usr/bin/env python3
"""Print a closer breakdown of private/code_check/merged.json for review.

Separates gates the agent cannot satisfy itself (operator flag, allowlist, value
bounds, human confirmation) from ones it can (a confirm argument, a dry-run
switch, an audit log, which records but does not stop). Lists the disclosure
candidates and the claims that do not hold.
"""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
E = json.load(open(ROOT / "private" / "code_check" / "merged.json"))


def low(v):
    return v.lower() if isinstance(v, str) else json.dumps(v).lower()


HARD = r"env_flag|cli_flag|config_flag|profile|allowlist|bound|limit|range|(?<![_a-z])confirmation|elicit|approval|human"
checked = [e for e in E if e.get("category") in ("runtime", "engineering")]
writers = [e for e in checked if low(e.get("write_default")).startswith(("on", "off"))]
hard = [e for e in writers if re.search(HARD, low(e.get("write_gates")))]
on = [e for e in writers if low(e.get("write_default")).startswith("on")]
on_no_hard = [e for e in on if e not in hard]
human = [e for e in writers if re.search(r"(?<![_a-z])confirmation|elicit|approval|human", low(e.get("write_gates")))]

print("write-capable:", len(writers), "| on by default:", len(on))
print("with a gate the agent cannot pass itself:", len(hard))
print("on by default and no such gate:", len(on_no_hard))
print("any human-in-the-loop gate (as recorded, check by hand):", len(human))
print("device_reach for engineering:", dict(Counter(low(e.get("device_reach"))[:12] for e in checked if e["category"] == "engineering")))
print()
print("CLAIMS THAT DO NOT HOLD")
for e in checked:
    if low(e.get("claim_holds")).startswith(("no", "not")) and not low(e.get("claim_holds")).startswith("no_claim"):
        print(" ", e["repo"], "|", str(e.get("claim"))[:90])
print()
print("DISCLOSURE CANDIDATES")
for e in E:
    if e.get("disclosure"):
        print(" ", e["repo"], "|", e["disclosure"][:150].replace("\n", " "))
