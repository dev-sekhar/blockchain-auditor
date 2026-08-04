from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path

from ..config import AuditConfig
from ..provenance import IGNORED_PARTS
from .properties import Property


LOCATION = re.compile(r"(?P<file>[^\s:]+\.sol):(?P<line>\d+):(?P<column>\d+):")


def parse_smt_output(output: str, properties: list[Property], return_code: int) -> tuple[list[dict], list[dict]]:
    diagnostics=[]
    for block in re.split(r"\n(?=[^\s].*\.sol:\d+:\d+:)", output):
        location=LOCATION.search(block)
        lower=block.lower()
        if "assertion violation happens" in lower or "counterexample" in lower: outcome="violated"
        elif "assertion violation might happen" in lower or "might not happen" in lower: outcome="inconclusive"
        elif "proved safe" in lower: outcome="proved"
        else: continue
        diagnostics.append({"outcome":outcome,"file":location.group("file") if location else None,"line":int(location.group("line")) if location else None,"message":block.strip()[:4000]})
    outcomes=[]
    solver_problem=any(marker in output.lower() for marker in ("solver was not found","no horn solver","analysis was not possible","unsupported"))
    for prop in properties:
        match=next((item for item in diagnostics if prop.source_file and item["file"] and item["file"].endswith(prop.source_file) and item["line"]==prop.source_line),None)
        if match: status=match["outcome"]
        elif prop.kind!="smt-assertion" or not prop.source_file or not prop.linked: status="declared_unlinked"
        elif return_code!=0 or solver_problem: status="inconclusive"
        else: status="no_counterexample"
        outcomes.append({**prop.to_dict(),"status":status})
    return outcomes,diagnostics


def run_solidity_smt(project: Path, properties: list[Property], config: AuditConfig) -> dict:
    solidity=[p for p in project.rglob("*.sol") if p.is_file() and not any(part in IGNORED_PARTS for part in p.relative_to(project).parts)]
    if not solidity: return {"engine":"solidity-smtchecker","status":"not_applicable","version":"unknown","outcomes":[],"diagnostics":[],"error":None,"duration_ms":0}
    relative=[p.relative_to(project).as_posix() for p in solidity]; base=["--model-checker-engine","all","--model-checker-targets","assert","--model-checker-timeout",str(min(config.timeout_seconds*1000,60000)),*relative]
    if config.execution_mode=="native":
        if not config.allow_native_execution or not shutil.which("solc"): return {"engine":"solidity-smtchecker","status":"skipped","version":"unknown","outcomes":[{**p.to_dict(),"status":"unverified"} for p in properties],"diagnostics":[],"error":"Native solc is unavailable or native execution is not allowed","duration_ms":0}
        command=["solc",*base]; version="native-solc"
    else:
        if not config.solc_image or not shutil.which("docker"): return {"engine":"solidity-smtchecker","status":"skipped","version":config.solc_image or "unconfigured","outcomes":[{**p.to_dict(),"status":"unverified"} for p in properties],"diagnostics":[],"error":"A locally available, reviewed solc_image is required","duration_ms":0}
        try: inspected=subprocess.run(["docker","image","inspect",config.solc_image],capture_output=True,timeout=10)
        except (OSError,subprocess.TimeoutExpired): inspected=None
        if not inspected or inspected.returncode: return {"engine":"solidity-smtchecker","status":"skipped","version":config.solc_image,"outcomes":[{**p.to_dict(),"status":"unverified"} for p in properties],"diagnostics":[],"error":"Configured solc image is not present locally; images are never pulled implicitly","duration_ms":0}
        command=["docker","run","--rm","--network","none","--read-only","--security-opt","no-new-privileges","--cap-drop","ALL","--memory",config.max_memory,"--cpus",config.max_cpus,"--pids-limit","256","--tmpfs","/tmp:rw,noexec,nosuid,size=128m","-v",f"{project}:/src:ro","-w","/src",config.solc_image,*base]; version=config.solc_image
    started=time.monotonic()
    try:
        result=subprocess.run(command,cwd=project if config.execution_mode=="native" else None,capture_output=True,text=True,timeout=config.timeout_seconds)
        output=(result.stdout+"\n"+result.stderr).strip(); outcomes,diagnostics=parse_smt_output(output,properties,result.returncode)
        status="completed" if result.returncode==0 else "failed"; error=None if status=="completed" else output[-4000:]
    except (OSError,subprocess.TimeoutExpired) as exc:
        status,error,outcomes,diagnostics="failed",str(exc),[{**p.to_dict(),"status":"unverified"} for p in properties],[]
    return {"engine":"solidity-smtchecker","status":status,"version":version,"outcomes":outcomes,"diagnostics":diagnostics,"error":error,"duration_ms":int((time.monotonic()-started)*1000)}
