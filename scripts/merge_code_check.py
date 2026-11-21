#!/usr/bin/env python3
"""Merge the per-agent code-check parts and the pilot into one private file, and
write only aggregate numbers to data/code_check_summary.json.

Per-server results stay in private/ until every disclosure is handled.
"""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRIV = ROOT / "private" / "code_check"


def low(v):
    return json.dumps(v).lower() if not isinstance(v, str) else v.lower()


def has_gate(e):
    gates = e.get("write_gates") or []
    if isinstance(gates, str):
        gates = [gates]
    real = [g for g in gates if not low(g).startswith("none") and low(g) not in ("n/a", "")]
    return bool(real)


def gate_kinds(e):
    text = low(e.get("write_gates"))
    kinds = {
        "flag (env, cli or config)": r"env_flag|cli_flag|config_flag|profile|flag",
        "allowlist": r"allowlist",
        "value bounds": r"bound|limit|range",
        "human confirmation": r"(?<!_)confirmation|elicit|approval",
        "confirm argument only": r"confirm_arg",
        "dry run": r"dry_run|dry-run",
        "audit log": r"audit",
    }
    return [k for k, rx in kinds.items() if re.search(rx, text)]


def main():
    entries = json.load(open(PRIV / "pilot.json"))
    missing = []
    for i in range(1, 11):
        inp = [l.strip() for l in (PRIV / f"input-{i}.txt").read_text().splitlines() if l.strip()]
        f = PRIV / f"part-{i}.json"
        if not f.exists():
            missing.append(i)
            continue
        part = json.load(open(f))
        assert [e["repo"] for e in part] == inp, f"part {i}: order or set differs from its input"
        entries += part
    (PRIV / "merged.json").write_text(json.dumps(entries, indent=1))

    checked = [e for e in entries if e.get("category") in ("runtime", "engineering")]
    writers = [e for e in checked if low(e.get("write_default")) in ("on", "off")]
    on = [e for e in checked if low(e.get("write_default")) == "on"]
    http = [e for e in checked if "http" in low(e.get("transport"))]
    exposed = [e for e in http if "0.0.0.0" in low(e.get("http_bind")) or "all interfaces" in low(e.get("http_bind"))]
    claims = [e for e in checked if low(e.get("claim_holds")) not in ("no_claim", "n/a", "")]
    summary = {
        "parts_missing": missing,
        "entries": len(entries),
        "checked_in_scope": len(checked),
        "moved_out_during_check": len(entries) - len(checked),
        "by_category": dict(Counter(e["category"] for e in checked)),
        "write_default": dict(Counter(low(e.get("write_default")) for e in checked)),
        "writes_on_by_default_with_no_gate": sum(not has_gate(e) for e in on),
        "write_capable_with_any_gate": sum(has_gate(e) for e in writers),
        "gate_kinds_among_write_capable": dict(Counter(k for e in writers for k in gate_kinds(e))),
        "target_agent_chosen": sum("agent_chosen" in low(e.get("target")) for e in checked),
        "http_capable": len(http),
        "http_all_interfaces": len(exposed),
        "http_all_interfaces_no_auth": sum(low(e.get("http_auth")).startswith("none") for e in exposed),
        "tls_verify_off": sum(low(e.get("tls_verify")).startswith("off") for e in checked),
        "claim_holds": dict(Counter(low(e.get("claim_holds")).split(" ")[0] for e in claims)),
        "traced": dict(Counter(low(e.get("traced")).split(" ")[0] for e in checked)),
        "disclosure_candidates": sum(bool(e.get("disclosure")) for e in entries),
    }
    (ROOT / "data" / "code_check_summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
