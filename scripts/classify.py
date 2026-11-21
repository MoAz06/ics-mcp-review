#!/usr/bin/env python3
"""First-pass scope filter, from the README and dependency manifests on disk.

A repo is IN scope when it is an MCP server that talks to a live industrial
device or protocol. This script only sorts candidates into buckets; it reads
no source code and makes no claim about safety:

  likely     an MCP SDK AND an industrial protocol library among the declared
             dependencies
  review     an MCP signal (dependency or README) AND an industrial protocol named
             in the README or description, but no protocol library declared: raw
             sockets, a vendor REST API, docs-only, code generation... needs a look
  out        everything else, including empty repositories

Dependencies are parsed out of each manifest by name, so the project's own name
(say "foo-mcp") or a library named in prose does not count as a dependency.
Every match is written out, so each bucket can be checked by hand.
"""
import csv
import json
import re
import tomllib
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

# Matched against a dependency NAME, whole-name or prefix as noted.
MCP_DEPS = [
    r"^mcp$", r"^mcp\[", r"^fastmcp", r"^@modelcontextprotocol/sdk$", r"mark3labs/mcp-go",
    r"modelcontextprotocol/go-sdk", r"^rmcp$", r"^ModelContextProtocol", r"^io\.modelcontextprotocol",
    r"^spring-ai-.*mcp", r"^mcp-framework$", r"^@mastra/mcp$", r"^fastmcp$", r"^mcp-use$",
    r"^langchain-mcp", r"^pydantic-ai", r"^mcp-server$", r"^mcp-go$", r"^@modelcontextprotocol/",
    r"^modelcontextprotocol$",
]

PROTOCOL_LIBS = {
    "modbus": [r"^pymodbus", r"^pyModbusTCP$", r"^umodbus$", r"^minimalmodbus$", r"^modbus-serial$",
               r"^jsmodbus$", r"goburrow/modbus", r"simonvetter/modbus", r"grid-x/modbus",
               r"^tokio-modbus$", r"^NModbus", r"^FluentModbus$", r"^EasyModbus", r"^j2mod$",
               r"^jlibmodbus$", r"^modbus-tcp$", r"^rodbus$", r"^modbus-stream$", r"^pymodbus3$",
               r"^async-modbus$", r"^tmodbus$", r"^modbus$"],
    "opcua": [r"^asyncua$", r"^opcua$", r"^freeopcua", r"^node-opcua", r"gopcua",
              r"^OPCFoundation", r"^Opc\.Ua", r"eclipse\.milo", r"^opcua-asyncio$", r"^opcua-client$",
              r"^Workstation\.UaClient"],
    "s7": [r"snap7", r"^nodes7$", r"gos7", r"^S7netplus$", r"^S7\.Net", r"^Sharp7", r"^node-snap7$"],
    "cip/ethernet-ip": [r"^pycomm3$", r"^pylogix$", r"libplctag", r"^st-ethernet-ip$", r"^cpppo$",
                        r"^ethernet-ip$", r"^plctag"],
    "ads/twincat": [r"^pyads$", r"^ads-client$", r"^Beckhoff\.TwinCAT\.Ads", r"^node-ads$"],
    "bacnet": [r"^BAC0$", r"^bacpypes", r"^bacstack$", r"^node-bacnet$", r"^bacnet"],
    "dnp3": [r"dnp3"],
    "iec104/61850": [r"^c104$", r"iec104", r"iec61850", r"lib60870"],
    "melsec/fins": [r"^pymcprotocol$", r"^mcprotocol$", r"^pymelsec$", r"^fins$", r"^omron-fins",
                    r"^fins-"],
    "knx": [r"^xknx$", r"^knx", r"^knxnet"],
    "mqtt/sparkplug": [r"sparkplug", r"^tahu"],
    "multi": [r"plc4x", r"plc4j", r"plc4py"],
}

README_PROTOCOL = re.compile(
    r"\b(modbus|opc[ -]?ua|plc|s7-?\d{3,4}|siemens|bacnet|dnp3|iec[ -]?(60870|61850|104)|"
    r"ethernet/ip|controllogix|allen[- ]bradley|twincat|beckhoff|codesys|melsec|omron|knx|"
    r"sparkplug|scada|profinet)\b", re.IGNORECASE)
README_MCP = re.compile(r"model context protocol|\bmcp\b", re.IGNORECASE)


def deps_requirements(text):
    for line in text.splitlines():
        line = line.split("#")[0].strip()
        if line and not line.startswith("-"):
            yield re.split(r"[<>=!~;\s\[@]", line, maxsplit=1)[0]


def deps_pyproject(text):
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return
    project = doc.get("project", {})
    lists = [project.get("dependencies", [])]
    lists += list(project.get("optional-dependencies", {}).values())
    lists += list(doc.get("dependency-groups", {}).values())
    for group in lists:
        for spec in group:
            if isinstance(spec, str):
                yield re.split(r"[<>=!~;\s\[@]", spec, maxsplit=1)[0]
    poetry = doc.get("tool", {}).get("poetry", {})
    yield from poetry.get("dependencies", {}).keys()
    for group in poetry.get("group", {}).values():
        yield from group.get("dependencies", {}).keys()


def deps_setup(text):
    for block in re.findall(r"install_requires\s*=\s*\[(.*?)\]", text, re.S):
        for spec in re.findall(r"['\"]([^'\"]+)['\"]", block):
            yield re.split(r"[<>=!~;\s\[@]", spec, maxsplit=1)[0]


def deps_package_json(text):
    try:
        doc = json.loads(text)
    except json.JSONDecodeError:
        return
    for key in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        yield from (doc.get(key) or {}).keys()


def deps_go_mod(text):
    for line in text.splitlines():
        m = re.match(r"\s*(?:require\s+)?([\w.\-]+\.\w+/[\w.\-/]+)\s+v", line)
        if m:
            yield m.group(1)


def deps_cargo(text):
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return
    for key in ("dependencies", "dev-dependencies"):
        yield from doc.get(key, {}).keys()
    yield from doc.get("workspace", {}).get("dependencies", {}).keys()


def deps_csproj(text):
    yield from re.findall(r'PackageReference\s+Include="([^"]+)"', text)


def deps_pom(text):
    yield from re.findall(r"<artifactId>([^<]+)</artifactId>", text)
    yield from re.findall(r"<groupId>([^<]+)</groupId>", text)


def deps_gradle(text):
    yield from re.findall(r"['\"]([\w.\-]+:[\w.\-]+)(?::[^'\"]*)?['\"]", text)


PARSERS = [
    (re.compile(r"requirements[^/]*\.txt$|Pipfile$", re.I), deps_requirements),
    (re.compile(r"pyproject\.toml$", re.I), deps_pyproject),
    (re.compile(r"setup\.py$|setup\.cfg$", re.I), deps_setup),
    (re.compile(r"package\.json$", re.I), deps_package_json),
    (re.compile(r"go\.mod$", re.I), deps_go_mod),
    (re.compile(r"Cargo\.toml$", re.I), deps_cargo),
    (re.compile(r"\.csproj$", re.I), deps_csproj),
    (re.compile(r"pom\.xml$", re.I), deps_pom),
    (re.compile(r"build\.gradle(\.kts)?$", re.I), deps_gradle),
]


def dependencies(files):
    found = set()
    for path, text in files.items():
        for pattern, parser in PARSERS:
            if pattern.search(path):
                found.update(d.strip() for d in parser(text) if d and d.strip())
    return found


def match(patterns, deps):
    return sorted({d for d in deps for p in patterns if re.search(p, d, re.IGNORECASE)})


def main():
    candidates = json.loads((DATA / "github_candidates.json").read_text())["repos"]
    rows = []
    for repo in candidates:
        folder = DATA / "repos" / repo["fullName"].replace("/", "__")
        files_path = folder / "files.json"
        files = json.loads(files_path.read_text()) if files_path.exists() else {}
        deps = dependencies(files)
        readme = "\n".join(v for k, v in files.items() if re.search(r"(^|/)README", k, re.I))
        text = readme + "\n" + (repo.get("description") or "") + "\n" + repo["fullName"]
        mcp_dep = match(MCP_DEPS, deps)
        protocols = {name: hit for name, pats in PROTOCOL_LIBS.items() if (hit := match(pats, deps))}
        mcp_text = bool(README_MCP.search(text))
        proto_text = sorted({m.lower() for m in README_PROTOCOL.findall(text) if isinstance(m, str)} |
                            {m[0].lower() for m in README_PROTOCOL.findall(text) if isinstance(m, tuple)})
        if not files:
            bucket, why = "out", "empty or unreadable repository"
        elif mcp_dep and protocols:
            bucket, why = "likely", "MCP SDK and protocol library declared"
        elif (mcp_dep or mcp_text) and (protocols or proto_text):
            bucket, why = "review", "MCP signal and an industrial protocol, not both declared"
        else:
            bucket, why = "out", "no MCP signal" if not (mcp_dep or mcp_text) else "no industrial protocol"
        rows.append({
            "repo": repo["fullName"],
            "bucket": bucket,
            "why": why,
            "protocols": ";".join(sorted(protocols)),
            "protocol_libs": ";".join(sorted({h for v in protocols.values() for h in v})),
            "mcp_dep": ";".join(mcp_dep),
            "readme_protocols": ";".join(proto_text[:8]),
            "stars": repo.get("stargazersCount"),
            "pushed": (repo.get("pushedAt") or "")[:10],
            "archived": repo.get("isArchived"),
            "fork": repo.get("isFork"),
            "language": repo.get("language") or "",
            "sources": ";".join(repo.get("sources", []) + (["github-search"] if repo.get("queries") else [])),
            "description": (repo.get("description") or "").replace("\n", " ")[:200],
            "url": repo.get("url") or f"https://github.com/{repo['fullName']}",
        })
    order = {"likely": 0, "review": 1, "out": 2}
    rows.sort(key=lambda r: (order[r["bucket"]], -(r["stars"] or 0)))
    with open(DATA / "candidates_classified.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    counts = {b: sum(r["bucket"] == b for r in rows) for b in order}
    print(counts)


if __name__ == "__main__":
    main()
