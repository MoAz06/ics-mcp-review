#!/usr/bin/env python3
"""List the servers recorded with a human-in-the-loop gate, with the gate text
and the evidence lines that mention it, for checking by hand."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
E = json.load(open(ROOT / "private" / "code_check" / "merged.json"))
PAT = r"(?<![_a-z])confirmation|elicit|approval|human"
KEY = re.compile(r"confirm|elicit|approv|human|pending|operator", re.I)


def low(v):
    return v.lower() if isinstance(v, str) else json.dumps(v).lower()


writers = [e for e in E if e.get("category") in ("runtime", "engineering")
           and low(e.get("write_default")).startswith(("on", "off"))]
human = [e for e in writers if re.search(PAT, low(e.get("write_gates")))]
for n, e in enumerate(human, 1):
    print(f"## {n}. {e['repo']} @ {e.get('commit', '?')[:7]} | default={e.get('write_default')} | transport={str(e.get('transport'))[:30]}")
    print("gates:", json.dumps(e.get("write_gates"))[:400])
    ev = e.get("evidence") or []
    if isinstance(ev, str):
        ev = [ev]
    for line in ev:
        if KEY.search(str(line)):
            print("  -", str(line)[:260])
    print()
print(len(human), "servers")
