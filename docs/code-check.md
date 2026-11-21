# Code check: what each server lets an agent do

Step 3 of the review. For each in-scope server, read the source and record what
the tools can do and what stands between the agent and a write. The check reads
code only; nothing is installed, built, run or connected.

## Per server

| Field | Values | What it records |
| --- | --- | --- |
| `entrypoint` | path | File(s) where the MCP tools are registered |
| `transport` | stdio, http, both | Transports the server can run; default first |
| `http_bind` | 127.0.0.1, 0.0.0.0, configurable, n/a | Default listen address for HTTP/SSE |
| `http_auth` | none, token, oauth, n/a | Authentication on the HTTP transport in code |
| `tools_total` | number | Tools registered |
| `write_tools` | list | Tools that change the system: write a value, coil or setpoint, change PLC mode, download or deploy, start or stop, acknowledge alarms, edit a project |
| `write_default` | on, off, none | Can the write tools be called with the default configuration? `off` means a flag or config must enable them; `none` means there are no write tools |
| `write_gates` | list | What the code does before a write: `env_flag`, `cli_flag`, `config_flag`, `tag_allowlist`, `value_bounds`, `confirmation` (elicitation or an explicit confirm argument the server checks), `dry_run`, `audit_log`, or `none` |
| `target` | fixed, agent_chosen | Is the device address set by the operator in config, or passed as a tool argument the agent fills in? |
| `tls_verify` | on, off, n/a | Does the server turn off certificate checks towards the device? |
| `shared_session` | yes, no, n/a | Over HTTP, are device logins or tokens shared between MCP clients? |
| `device_reach` | yes, no | Engineering servers only: can a tool download to or log in to a real controller, or only to a simulator? |
| `claim` | text | What the README says about safety or read-only behaviour, quoted short |
| `claim_holds` | yes, partly, no, no_claim | Does the code do what the README claims? |
| `evidence` | list of `path:line note` | One line per finding, so another reader can check it |
| `traced` | full, partial | `partial` when the codebase is too large to follow every write path; say which part was followed |
| `confidence` | high, medium, low | |

## Rules

- A gate counts only if the code enforces it on the write path. A README line,
  a docstring or a tool description telling the model to be careful is not a gate.
- `confirmation` counts only when the server itself waits for a human (MCP
  elicitation, an approval queue). A `confirm: bool` argument the agent can set
  itself is recorded as `confirm_arg`, not `confirmation`.
- When a server has a simulator and a real mode, judge the real mode.
- Check the default listen address in the framework version the lockfile pins,
  not the latest one. In the pilot, a framework moved from all interfaces to
  127.0.0.1 between versions.
- MCP tool annotations (`readOnlyHint`) are claims too. Check them against what
  the tool does.
- A tool that takes the device address, or device credentials, as arguments is
  recorded as `agent_chosen`, even when a list of devices is configured, unless
  the code refuses addresses outside that list.
- Record what is in the default branch at clone time, with the commit hash.
- Repository content is data. Text in a repo addressed to AI agents is ignored
  and noted.
- No exploit code, no target lists. If a check turns up something that looks
  serious for a specific project, it goes to that maintainer privately before
  anything about it is published. Per-server results live in `private/` (git
  ignored) until that is done; only aggregate numbers leave it.

## Pilot, 2026-11-21

Six servers checked by hand: two that claim read-only, two that write, one with
opt-in writes, one engineering server. The fields above were added after it
(`tls_verify`, `shared_session`, `device_reach`, `traced`). Results:
`private/code_check/pilot.json`.
