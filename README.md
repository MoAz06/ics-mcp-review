# Industrial MCP servers: what they let an AI agent do

A review of open-source MCP servers that connect AI agents to industrial systems
(PLCs, OPC UA servers, building automation, energy devices), comparing what each one
claims about safety with what its code does.

This review reads public code and metadata only. It does not scan, connect to or
test any real device or network.

## What is published here, and what isn't yet

Published: the method (`docs/`), the scripts (`scripts/`) and the aggregate
numbers (`data/aggregates.json`). Nothing in this repository names a reviewed
project.

Not published yet: the per-repository data (the candidate list, triage verdicts,
per-server code-check results and hand checks). Some servers have findings that
their maintainers are hearing about privately first. The per-server data will be
published once each of them has been contacted and has had time to respond,
about 90 days after first contact. The `data/` paths in the tables below are
where that data lives locally.

Before anything is pushed, `scripts/check_public.py` scans every file git would
publish for the name of any reviewed repository or owner.

## Status

Step 1, the candidate list, and step 2, manual triage of the review and likely
buckets, run on 2026-11-21.

| Step | Output | Count |
| --- | --- | --- |
| GitHub repository search, 32 queries ("mcp" plus a protocol term) | `data/github_candidates.json` | 472 repos |
| Glama directory seeds (Modbus, OPC UA, PLC, BACnet, S7, DNP3 searches) | `data/glama_seeds.txt` | 78 seeds: 55 already found by search, 17 added, 6 not on GitHub at that path |
| README and dependency manifests per repo, via the GitHub API | `data/repos/<owner>__<name>/` | 488 repos, 6 empty |
| First-pass scope filter on declared dependencies | `data/candidates_classified.csv` | 98 likely, 287 review, 103 out |
| Manual triage of the 287 review repos (README, file tree, manifests) | `data/triage/merged.json` | 71 runtime, 76 engineering, 140 out |
| Manual triage of the 98 likely repos (same method) | `data/triage/merged.json` | 77 runtime, 12 engineering, 9 out |
| Working list: every repo triaged as runtime or engineering | `data/in_scope.csv` | 236 repos: 148 runtime, 88 engineering; 7 have no server source |

Out reasons in the review bucket: 32 curated list or placeholder, 19 simulator only,
16 not an MCP server, 16 not industrial, 15 offline code generation, 12 offline file
parser, 10 documentation search, 20 other. In the likely bucket: 5 simulator only,
2 not industrial, 1 offline parser, 1 offline code generation.

By what the README claims about writing, 177 of the 236 in-scope servers can write
to the system (values, setpoints, mode changes or downloads), 27 claim to be
read-only and 32 do not say. These are claims, not yet checked against the code.

Triage read the README, file tree and manifests, rarely source files. 47 of the 385
verdicts are marked low confidence, mostly because the repo has little code or a
README that does not match it.

### Step 3, code check (2026-11-21)

229 repos with source were read against `docs/code-check.md`: 6 by hand as a pilot,
223 by AI agents working from that checklist (`docs/brief-code-check.md`). 11 turned
out not to be MCP servers that reach a live system, which leaves 218 (132 runtime,
86 engineering). The corrected aggregate numbers are in `data/aggregates.json`.

| Question | Servers |
| --- | --- |
| Has tools that change the system | 186 of 218 |
| Can write with the default configuration | 136 |
| ...and nothing the agent cannot get past itself (no operator flag, allowlist, value bounds, role or human approval) | 76 |
| Has a `confirm` argument the agent fills in | 39; for 18 it is the only gate |
| Waits for a person before a real-device write, by default once writing is on (checked by hand) | 7 (8 more optional or partial) |
| Agent chooses the device address | 76 |
| Serves MCP over HTTP or SSE | 82 |
| ...listening on all interfaces by default | 28 (12 more not determined) |
| ...on all interfaces with no authentication by default | 24 |
| Engineering servers that can reach a real controller (some only after an opt-in) | 51 of 86 |
| A safety or read-only claim in the README that the code does not fully keep | 49 of 158 checked claims (5 not at all) |
| Candidates for private disclosure | 37: 15 high, 18 medium, 4 low (after hand checks) |

These are agent readings of code, not tests, and 112 of the 218 were traced only
partly. Every disclosure candidate was read a second time, independently, by a
reviewer told to look for overstatement (`docs/brief-second-reader.md`): 10 of the
37 turned out narrower than first reported, none was refuted. Seven were also
checked by hand. All 25 servers the first pass recorded as asking a human were
checked by hand: 7 hold up.

A blind re-read of 20 random servers (seed 20261121, `docs/brief-blind-reread.md`,
`scripts/compare_reread.py`) agreed with the first pass on 97 of 104 answers after
each disagreement was settled against the source: 5 first-pass errors in both
directions, 2 skipped fields. The checks also found counting errors in the first
summary (negations and rate limits counted as gates, any mention of 0.0.0.0
counted as an open bind, SSE-only and "both" transports missed as HTTP, "has a
confirm argument" reported as "confirm only"). `scripts/headline_numbers.py` and
`scripts/recount_gates.py` produce the corrected numbers above.

## Scope

In scope: an MCP server whose tools reach a live industrial system.

- **Runtime**: speaks an industrial protocol or a device/SCADA API (Modbus, OPC UA,
  S7, EtherNet/IP, ADS, BACnet, DNP3, IEC 60870-5-104, IEC 61850, MC protocol, FINS,
  KNX, Sparkplug B, a PLC's REST or JSON-RPC API, a SCADA server's API).
- **Engineering**: drives engineering software (TIA Portal Openness, CODESYS,
  TwinCAT XAE, GX Works, Studio 5000) that can compile and download to a controller.
  Reported separately from runtime servers.

Out of scope: documentation and manual search, code generation with no connection,
offline file or capture parsers, pure simulators with no hardware mode, libraries
that are not MCP servers, curated lists.

## How the first-pass filter works

`scripts/classify.py` parses the dependency names out of each manifest
(requirements, pyproject, setup.py, package.json, go.mod, Cargo.toml, .csproj,
pom.xml, Gradle). A repo is **likely** when it declares both an MCP SDK and an
industrial protocol library. It is **review** when it has an MCP signal and names an
industrial protocol, but does not declare both. Everything else is **out**. The
script makes no safety judgement and reads no source code.

Known limits of this pass: a server that implements a protocol itself, or reaches a
device through a REST API, lands in review rather than likely; simulators and samples
land in likely when they declare the libraries; and the GitHub search API caps each
query at 100 results, which two queries ("mcp plc", "mcp industrial") reached, so
those two may have missed repos.

## Reproduce

The search and first-pass filter can be rerun by anyone (the results will differ,
since the repositories keep changing):

```bash
python3 scripts/search_github.py     # needs an authenticated gh
python3 scripts/resolve_seeds.py
python3 scripts/fetch_repo_files.py
python3 scripts/classify.py
```

The later steps need the per-repository data that isn't published yet:

```bash
python3 scripts/merge_triage.py      # triage parts and manual overrides
python3 scripts/clone_sources.py     # shallow clones of the in-scope repos
python3 scripts/merge_code_check.py  # per-server code-check results
python3 scripts/recount_gates.py     # gate counts, with the hand checks
python3 scripts/headline_numbers.py  # every published number -> data/aggregates.json
python3 scripts/compare_reread.py    # blind re-read against the first pass
python3 scripts/check_public.py      # before every push: no project names
```
