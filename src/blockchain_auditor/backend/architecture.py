from __future__ import annotations

import re
from pathlib import Path

from ..provenance import IGNORED_PARTS


CONTRACT = re.compile(r"\b(contract|interface|library|abstract\s+contract)\s+(\w+)(?:\s+is\s+([^\{]+))?")
FUNCTION = re.compile(r"\b(function|constructor|fallback|receive)\s*(\w+)?\s*\([^)]*\)\s*([^\{;]*)")
IMPORT = re.compile(r"\bimport\s+(?:[^'\"]+from\s+)?['\"]([^'\"]+)['\"]")
EXTERNAL_CALL = re.compile(r"\b([A-Za-z_]\w*)\.([A-Za-z_]\w*)\s*(?:\{|\()")
PRIVILEGE_MARKERS = {"onlyOwner", "onlyAdmin", "requiresAuth", "auth", "onlyRole"}


def analyze_architecture(project: Path) -> dict:
    nodes, edges, entry_points, privileged, upgrade_signals = [], [], [], [], []
    source_files = []
    for path in sorted(project.rglob("*.sol")):
        relative = path.relative_to(project)
        if any(part in IGNORED_PARTS for part in relative.parts):
            continue
        try: lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError: continue
        rel = relative.as_posix(); source_files.append(rel)
        current, depth, contract_depth = None, 0, 0
        for number, line in enumerate(lines, 1):
            clean = line.split("//", 1)[0]
            for target in IMPORT.findall(clean):
                edges.append({"type": "import", "source": rel, "target": target, "line": number})
            match = CONTRACT.search(clean)
            if match:
                current = match.group(2); contract_depth = depth + clean[:match.end()].count("{") - clean[:match.end()].count("}")
                nodes.append({"id": current, "type": match.group(1).replace(" ", "_"), "file": rel, "line": number})
                for parent in (match.group(3) or "").split(","):
                    parent = parent.strip().split("(", 1)[0].strip()
                    if parent: edges.append({"type": "inheritance", "source": current, "target": parent, "line": number})
            function = FUNCTION.search(clean)
            if function and current:
                name = function.group(2) or function.group(1)
                qualifiers = function.group(3)
                item = {"contract": current, "function": name, "file": rel, "line": number, "qualifiers": qualifiers.strip()}
                if re.search(r"\b(public|external)\b", qualifiers): entry_points.append(item)
                if any(marker in qualifiers for marker in PRIVILEGE_MARKERS): privileged.append(item)
            for receiver, method in EXTERNAL_CALL.findall(clean):
                if receiver not in {"require", "assert", "revert", "super", "this"} and current:
                    edges.append({"type": "call", "source": current, "target": receiver, "method": method, "line": number, "file": rel})
            if re.search(r"\b(upgradeTo|upgradeToAndCall|_authorizeUpgrade|implementation)\b", clean):
                upgrade_signals.append({"contract": current, "file": rel, "line": number, "evidence": clean.strip()[:200]})
            depth += clean.count("{") - clean.count("}")
            if current and depth < contract_depth: current = None
    centralization = "high" if len(privileged) >= 5 else "medium" if privileged else "low"
    return {
        "schema_version": "1.0", "source_files": source_files, "nodes": nodes, "edges": edges,
        "entry_points": entry_points, "privileged_operations": privileged, "upgrade_signals": upgrade_signals,
        "risk_indicators": {"centralization": centralization, "public_entry_points": len(entry_points), "privileged_operations": len(privileged), "upgrade_signals": len(upgrade_signals)},
        "limitations": ["Source-level heuristic graph; confirm dispatch and call edges with compiler AST/Slither before relying on completeness."],
    }


def mermaid_graph(architecture: dict) -> str:
    lines = ["flowchart LR"]
    known = {node["id"] for node in architecture["nodes"]}
    for node in architecture["nodes"]:
        safe = re.sub(r"\W", "_", node["id"]); lines.append(f'  {safe}["{node["id"]}"]')
    emitted = set()
    for edge in architecture["edges"]:
        if edge["type"] not in {"inheritance", "call"} or edge["source"] not in known: continue
        source, target = re.sub(r"\W", "_", edge["source"]), re.sub(r"\W", "_", edge["target"])
        key = (source, target, edge["type"])
        if key in emitted: continue
        emitted.add(key); label = "inherits" if edge["type"] == "inheritance" else "calls"
        lines.append(f"  {source} -->|{label}| {target}")
    return "\n".join(lines) + "\n"
