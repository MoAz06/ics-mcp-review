#!/usr/bin/env python3
"""Every number the article uses, from one place, with the corrections found by
the hand checks and the blind re-read (private/code_check/reread-adjudication.md):

- known first-pass errors from the re-read are applied (FIXES);
- HTTP-capable means the transport offers HTTP, SSE or both (the first count
  only looked for the word 'http' and missed 'both' and SSE-only entries);
- 'all interfaces' is judged on the default bind, not on any mention of
  0.0.0.0 (e.g. '127.0.0.1 default; the Docker image uses 0.0.0.0' is not);
- gates come from recount_gates.py."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from recount_gates import hard_new, gate_kinds, KINDS, HUMAN  # noqa: E402

E = [e for e in json.load(open(ROOT / "private" / "code_check" / "merged.json"))
     if e.get("category") in ("runtime", "engineering")]

# First-pass errors the blind re-read proved, per server (private until
# disclosure is done).
FIXES = json.load(open(ROOT / "private" / "code_check" / "reread_fixes.json"))
NOT_HTTP = {"stdio (sse raises notimplementederror)"}


def low(v):
    return v.lower() if isinstance(v, str) else json.dumps(v).lower()


for e in E:
    e.update(FIXES.get(e["repo"], {}))

writers = [e for e in E if low(e.get("write_default")).startswith(("on", "off"))]
on = [e for e in writers if low(e.get("write_default")).startswith("on")]
hard = [e for e in writers if hard_new(e)]
http = [e for e in E if re.search(r"http|sse|both", low(e.get("transport"))) and low(e.get("transport")) not in NOT_HTTP]


def all_if(e):
    b = low(e.get("http_bind"))
    return (("0.0.0.0" in b or "all interfaces" in b) and not re.match(r"(127\.0\.0\.1|n/a)", b)
            and "not the mcp transport" not in b)


exposed = [e for e in http if all_if(e)]
noauth = [e for e in exposed if low(e.get("http_auth")).startswith("none") or "optional" in low(e.get("http_auth"))[:20]]
eng = [e for e in E if e["category"] == "engineering"]

print("checked:", len(E), "| runtime", sum(e["category"] == "runtime" for e in E), "| engineering", len(eng))
print("write-capable:", len(writers), "| on by default:", len(on))
print("with a gate the agent can't pass:", len(hard), "| on by default with none:", sum(e not in hard for e in on))
print("human approval (hand check) A/B/C/D:", {k: sum(v == k for v in HUMAN.values()) for k in "ABCD"})
print("agent-chosen target:", sum(low(e.get("target")).startswith("agent") for e in E))
print("HTTP-capable:", len(http), "| all interfaces by default:", len(exposed), "| ...with no auth by default:", len(noauth),
      "| bind not checked:", sum(low(e.get("http_bind")).startswith("not checked") for e in http))

# Aggregates only, no repository names: this file is published.
claims = [e for e in E if low(e.get("claim_holds")) not in ("no_claim", "n/a", "", "not checked")]
sev = {}
for line in (ROOT / "private" / "disclosures.md").read_text().splitlines():
    m = re.match(r"\| (high|medium|low) \|", line)
    if m:
        sev[m.group(1)] = sev.get(m.group(1), 0) + 1
hard_names = {e["repo"] for e in hard}
aggregates = {
    "snapshot": "default branch of each repository on 2026-11-21",
    "checked_servers": len(E),
    "runtime": sum(e["category"] == "runtime" for e in E),
    "engineering": len(eng),
    "write_capable": len(writers),
    "writes_on_by_default": len(on),
    "with_a_gate_the_agent_cannot_pass": len(hard),
    "writes_on_by_default_with_no_such_gate": sum(e not in hard for e in on),
    "gate_kinds_among_write_capable": {k: sum(k in gate_kinds(e) for e in writers) for k in KINDS},
    "confirm_argument_is_the_only_gate": sum("confirm_arg" in gate_kinds(e) and e["repo"] not in hard_names for e in writers),
    "human_approval_hand_check": {
        "waits_for_a_person_by_default": sum(v == "A" for v in HUMAN.values()),
        "optional_partial_or_in_host_app": sum(v == "B" for v in HUMAN.values()),
        "not_human_approval": sum(v == "C" for v in HUMAN.values()),
        "not_verifiable": sum(v == "D" for v in HUMAN.values()),
    },
    "agent_chooses_device": sum(low(e.get("target")).startswith("agent") for e in E),
    "http_capable": len(http),
    "http_all_interfaces_by_default": len(exposed),
    "http_all_interfaces_no_auth_by_default": len(noauth),
    "http_bind_not_determined": sum(low(e.get("http_bind")).startswith("not checked") for e in http),
    "engineering_reaching_a_controller": sum(low(e.get("device_reach")).startswith("yes") for e in eng),
    "readme_safety_claims_checked": len(claims),
    "claims_not_fully_kept": sum(low(e.get("claim_holds")).startswith(("partly", "no")) for e in claims),
    "claims_not_kept_at_all": sum(low(e.get("claim_holds")).startswith("no") for e in claims),
    "traced_only_in_part": sum(low(e.get("traced")).startswith("partial") for e in E),
    "disclosure_candidates": sev,
    "blind_reread_sample": {"servers": 20, "seed": 20261121, "answers": 104, "held_up": 97, "wrong": 5, "skipped": 2},
}
(ROOT / "data" / "aggregates.json").write_text(json.dumps(aggregates, indent=1) + "\n")
print("wrote data/aggregates.json")
