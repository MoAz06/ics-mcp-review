#!/usr/bin/env python3
"""Find candidate MCP servers for industrial protocols on GitHub.

Runs one repository search per query, through the authenticated `gh` CLI, and
writes every hit with the queries that found it to data/github_candidates.json.
This is the wide net: nothing here decides whether a repo is in scope.
"""
import json
import shlex
import subprocess
import time
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "github_candidates.json"

# Each protocol is searched together with "mcp" in name, description or README.
PROTOCOLS = [
    "modbus", "opcua", "opc-ua", "\"opc ua\"", "plc", "s7", "snap7", "s7comm",
    "siemens plc", "bacnet", "dnp3", "iec104", "\"iec 60870\"", "iec61850",
    "ethernet/ip", "pycomm3", "allen-bradley", "controllogix", "twincat", "ads beckhoff",
    "fins omron", "melsec", "mitsubishi plc", "codesys", "scada", "profinet",
    "knx", "sparkplug", "industrial", "\"operational technology\"", "hmi plc", "rtu",
]

FIELDS = "fullName,description,url,stargazersCount,pushedAt,updatedAt,isArchived,isFork,language,license"


def search(query):
    # gh quotes an argument that contains a space, which turns "mcp modbus" into
    # one exact phrase. Pass each term as its own argument; keep quoted phrases.
    terms = ["mcp", *shlex.split(query, posix=False)]
    cmd = ["gh", "search", "repos", *terms, "--limit", "100", "--json", FIELDS]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None, result.stderr.strip()
    return json.loads(result.stdout), None


def main():
    repos = {}
    log = []
    for protocol in PROTOCOLS:
        hits, err = search(protocol)
        if err:
            log.append({"query": protocol, "error": err})
            print(f"{protocol!r}: ERROR {err}")
        else:
            log.append({"query": protocol, "hits": len(hits)})
            print(f"{protocol!r}: {len(hits)}")
            for repo in hits:
                entry = repos.setdefault(repo["fullName"].lower(), {**repo, "queries": []})
                entry["queries"].append(protocol)
        time.sleep(2.5)  # search API: 30 requests per minute
    OUT.write_text(json.dumps({"log": log, "repos": list(repos.values())}, indent=1))
    print(f"\n{len(repos)} distinct repos -> {OUT}")


if __name__ == "__main__":
    main()
