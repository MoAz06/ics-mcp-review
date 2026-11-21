#!/usr/bin/env python3
"""Recount the gate numbers with two fixes over inspect_code_check.py:
1. a gate item that is a negation or not enforced ("none (...)", "not checked",
   "instruction only", "claims only", "per the README") counts as no gate, so
   words like 'limit' or 'confirmation' inside it no longer count;
2. the human-approval result comes from the hand check (HUMAN below), not
   from the regex.
Prints old and new numbers and the servers whose verdict changed."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
E = json.load(open(ROOT / "private" / "code_check" / "merged.json"))

OLD_HARD = r"env_flag|cli_flag|config_flag|profile|allowlist|bound|limit|range|(?<![_a-z])confirmation|elicit|approval|human"
# Hard gates without the human words; human approval is decided by hand.
HARD = r"env_flag|cli_flag|config_flag|profile|allowlist|bound|limit|range|path sandbox|\brole\b|scope check"
SOFT_ITEM = re.compile(r"^\s*(none|not |no |n/a)|instruction only|claims only|per the readme|text only|agent passes itself|agent can pass|agent itself|the agent calls", re.I)

# Hand check, 2026-11-21. A = the server (or its own approval UI) waits for a
# person before real-device writes in the default setup, and the agent cannot
# approve through MCP. B = exists, but optional, off by default, only some
# operations or modes, or enforced in the host app. C = not a human gate.
# D = could not be verified from the repository. Per-server results stay in
# private/ until disclosure is done.
HUMAN = json.load(open(ROOT / "private" / "code_check" / "human_check.json"))


def low(v):
    return v.lower() if isinstance(v, str) else json.dumps(v).lower()


def items(e):
    g = e.get("write_gates")
    if isinstance(g, str):
        return [g]
    return [str(x) for x in (g or [])]


def hard_new(e):
    if HUMAN.get(e["repo"]) == "A":
        return True
    # A rate limit, cooldown or call budget slows writes down; it does not stop
    # one, so its 'limit' no longer counts (found in the blind re-read).
    return any(re.search(HARD, RATE.sub("", i.lower())) and not SOFT_ITEM.search(i) for i in items(e))



RATE = re.compile(r"rate[ _-]?limit\w*|call budget|cooldown|duty[ -]cycle limit")

# Gate kinds per item, with the same negation and rate-limit rules.
KINDS = {
    "operator flag": r"env_flag|cli_flag|config_flag|profile|\bflag\b",
    "allowlist": r"allowlist",
    "value bounds": r"bound|limit|range",
    "confirm_arg": r"confirm_arg|confirm argument|confirm token|confirmation_token|grant_arg",
    "dry_run": r"dry_run|dry-run",
    "audit_log": r"audit",
}


def gate_kinds(e):
    live = [RATE.sub("", i.lower()) for i in items(e) if not SOFT_ITEM.search(i)]
    has = {k for k, rx in KINDS.items() if any(re.search(rx, i) for i in live)}
    # A confirm token the agent fetches and uses itself is still a confirm
    # argument; SOFT_ITEM only keeps it from counting as a hard gate.
    nonneg = [i.lower() for i in items(e) if not re.match(r"\s*(none|not |no |n/a)", i, re.I)]
    if any(re.search(KINDS["confirm_arg"], i) for i in nonneg):
        has.add("confirm_arg")
    return has


def main():
    checked = [e for e in E if e.get("category") in ("runtime", "engineering")]
    writers = [e for e in checked if low(e.get("write_default")).startswith(("on", "off"))]
    on = [e for e in writers if low(e.get("write_default")).startswith("on")]

    old = {e["repo"] for e in writers if re.search(OLD_HARD, low(e.get("write_gates")))}
    new = {e["repo"] for e in writers if hard_new(e)}
    print("write-capable:", len(writers), "| on by default:", len(on))
    print("hard gate  old:", len(old), " new:", len(new))
    print("on, no hard gate  old:", sum(e["repo"] not in old for e in on), " new:", sum(e["repo"] not in new for e in on))
    print("human A/B/C/D:", {k: sum(v == k for v in HUMAN.values()) for k in "ABCD"})
    print("\nlost a hard gate:")
    for r in sorted(old - new):
        e = next(x for x in writers if x["repo"] == r)
        print(" ", r, "| default", e.get("write_default"), "|", json.dumps(items(e))[:230])
    print("\ngained a hard gate:", sorted(new - old))

    counts = {k: sum(k in gate_kinds(e) for e in writers) for k in KINDS}
    confirm_no_hard = [e for e in writers if "confirm_arg" in gate_kinds(e) and e["repo"] not in new]
    print("\ngate kinds among write-capable (per item):", counts)
    print("confirm_arg and no hard gate:", len(confirm_no_hard),
          "| of those on by default:", sum(low(e.get("write_default")).startswith("on") for e in confirm_no_hard))


if __name__ == "__main__":
    main()
