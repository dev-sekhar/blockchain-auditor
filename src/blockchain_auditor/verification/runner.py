from __future__ import annotations

from pathlib import Path

from ..config import AuditConfig
from .properties import discover_solidity_assertions, load_properties
from .solidity import run_solidity_smt


def run_verification(project: Path, config: AuditConfig) -> dict:
    declared,path=load_properties(project,config.properties_file); discovered=discover_solidity_assertions(project)
    known={(item.source_file,item.source_line,item.expression) for item in declared}; properties=declared+[item for item in discovered if (item.source_file,item.source_line,item.expression) not in known]
    if not config.formal_verification:
        engine={"engine":"solidity-smtchecker","status":"not_requested","version":"unconfigured","outcomes":[{**p.to_dict(),"status":"unverified"} for p in properties],"diagnostics":[],"error":None,"duration_ms":0}
    elif not properties:
        engine={"engine":"solidity-smtchecker","status":"no_properties","version":config.solc_image or "unconfigured","outcomes":[],"diagnostics":[],"error":"No declared properties or Solidity assert obligations were found","duration_ms":0}
    else: engine=run_solidity_smt(project,properties,config)
    counts={status:sum(item["status"]==status for item in engine["outcomes"]) for status in ("proved","no_counterexample","violated","inconclusive","unverified","declared_unlinked")}
    return {"schema_version":"1.0","requested":config.formal_verification,"properties_file":path,"property_count":len(properties),"engine":engine,"summary":counts,"limitations":["No-counterexample is not equivalent to a mathematical proof.","Only source-linked Solidity assert obligations are submitted to the SMT checker in this phase."]}
