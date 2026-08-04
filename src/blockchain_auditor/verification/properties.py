from __future__ import annotations

import hashlib
import re
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

from ..provenance import IGNORED_PARTS


@dataclass
class Property:
    id: str
    description: str
    severity: str
    language: str
    kind: str
    source_file: str | None = None
    source_line: int | None = None
    expression: str | None = None
    origin: str = "declared"
    linked: bool = False

    def to_dict(self): return asdict(self)


def load_properties(project: Path, filename: str) -> tuple[list[Property], str | None]:
    path = Path(filename)
    if not path.is_absolute(): path = project / path
    if not path.exists(): return [], None
    try:
        with path.open("rb") as stream: data = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc: raise ValueError(f"Invalid property specification {path}: {exc}") from exc
    items = data.get("properties", [])
    if not isinstance(items, list): raise ValueError("Property specification must use [[properties]] entries")
    properties=[]; ids=set()
    for item in items:
        required={"id","description","severity","language","kind"}; missing=required-set(item)
        if missing: raise ValueError(f"Property is missing fields: {', '.join(sorted(missing))}")
        if not re.fullmatch(r"[a-z][a-z0-9-]{2,80}", str(item["id"])): raise ValueError(f"Invalid property ID: {item['id']}")
        if item["id"] in ids: raise ValueError(f"Duplicate property ID: {item['id']}")
        if item["severity"] not in {"critical","high","medium","low"}: raise ValueError(f"Invalid property severity: {item['severity']}")
        source_file=item.get("source_file"); source_line=item.get("source_line"); expression=item.get("expression")
        linked=False
        if item["kind"]=="smt-assertion" and source_file and source_line:
            source_path=(project/source_file).resolve()
            try:
                source_path.relative_to(project.resolve()); lines=source_path.read_text(encoding="utf-8",errors="replace").splitlines()
                source_text=lines[int(source_line)-1] if 0<int(source_line)<=len(lines) else ""
                linked="assert" in source_text and (not expression or "".join(str(expression).split()) in "".join(source_text.split()))
            except (OSError,ValueError): linked=False
        ids.add(item["id"]); properties.append(Property(
            str(item["id"]),str(item["description"]),str(item["severity"]),str(item["language"]),str(item["kind"]),
            source_file,source_line,expression,"declared",linked,
        ))
    return properties, str(path)


def discover_solidity_assertions(project: Path) -> list[Property]:
    properties=[]
    for path in sorted(project.rglob("*.sol")):
        relative=path.relative_to(project)
        if any(part in IGNORED_PARTS for part in relative.parts): continue
        try: lines=path.read_text(encoding="utf-8",errors="replace").splitlines()
        except OSError: continue
        for number,line in enumerate(lines,1):
            match=re.search(r"\bassert\s*\((.+)\)\s*;",line)
            if not match: continue
            rel=relative.as_posix(); digest=hashlib.sha256(f"{rel}:{number}:{match.group(1)}".encode()).hexdigest()[:12]
            properties.append(Property(f"assert-{digest}","Discovered Solidity assertion","high","Solidity","smt-assertion",rel,number,match.group(1).strip(),"discovered",True))
    return properties
