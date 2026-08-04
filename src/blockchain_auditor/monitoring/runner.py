from __future__ import annotations

import hashlib
import json
import re
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from ..provenance import safe_project_path
from ..storage import write_json


SUPPORTED={"contract_upgrade","treasury_transfer","governance_execution","oracle_staleness"}


def load_monitoring_rules(project: Path, filename: str) -> tuple[list[dict],str|None]:
    path=Path(filename)
    if not path.is_absolute(): path=project/path
    if not path.exists(): return [],None
    try:
        with path.open("rb") as stream: data=tomllib.load(stream)
    except (OSError,tomllib.TOMLDecodeError) as exc: raise ValueError(f"Invalid monitoring specification {path}: {exc}") from exc
    rules=data.get("rules",[]); ids=set()
    if not isinstance(rules,list): raise ValueError("Monitoring file must use [[rules]] entries")
    for rule in rules:
        if not rule.get("id") or rule.get("type") not in SUPPORTED or rule.get("severity") not in {"critical","high","medium","low","informational"}: raise ValueError("Every monitoring rule requires a unique id, supported type, and severity")
        if rule["id"] in ids: raise ValueError(f"Duplicate monitoring rule ID: {rule['id']}")
        ids.add(rule["id"])
    return rules,str(path)


def _matches(rule: dict,event: dict) -> tuple[bool,str]:
    if event.get("type")!=rule["type"]: return False,""
    if rule["type"]=="treasury_transfer":
        amount=float(event.get("amount",0)); threshold=float(rule.get("min_amount",0)); return amount>=threshold,f"Treasury transfer {amount} meets alert threshold {threshold}."
    if rule["type"]=="contract_upgrade":
        target=str(event.get("implementation","")); allowed=set(map(str,rule.get("allowed_implementations",[])))
        return (not allowed or target not in allowed),f"Contract implementation changed to {target or 'unknown'}."
    if rule["type"]=="oracle_staleness":
        try:
            observed=datetime.fromisoformat(str(event["observed_at"]).replace("Z","+00:00")); updated=datetime.fromisoformat(str(event["updated_at"]).replace("Z","+00:00")); age=(observed-updated).total_seconds(); limit=float(rule.get("max_age_seconds",3600))
        except (KeyError,ValueError,TypeError) as exc: return True,f"Oracle event timestamps are invalid: {exc}"
        return age>limit,f"Oracle update age is {age:.0f}s (limit {limit:.0f}s)."
    return True,f"Governance proposal {event.get('proposal_id','unknown')} executed."


def replay_events(rules: list[dict],events: list[dict]) -> dict:
    alerts=[]; previous=None
    for index,event in enumerate(events):
        for rule in rules:
            matched,message=_matches(rule,event)
            if not matched: continue
            alert={"id":hashlib.sha256(f"{rule['id']}:{index}:{json.dumps(event,sort_keys=True)}".encode()).hexdigest()[:20],"rule_id":rule["id"],"type":rule["type"],"severity":rule["severity"],"message":message,"event_index":index,"event":event,"previous_hash":previous}
            alert["event_hash"]=hashlib.sha256(json.dumps(alert,sort_keys=True,separators=(",",":")).encode()).hexdigest(); previous=alert["event_hash"]; alerts.append(alert)
    return {"schema_version":"1.0","provider":"jsonl-replay","events_processed":len(events),"rules_evaluated":len(rules),"alerts":alerts,"summary":{"total":len(alerts),"by_severity":{severity:sum(a["severity"]==severity for a in alerts) for severity in ("critical","high","medium","low","informational")}},"limitations":["Replay input is caller-supplied and is not independently verified against a blockchain node."]}


def read_jsonl(path: Path) -> list[dict]:
    events=[]
    for number,line in enumerate(path.read_text(encoding="utf-8").splitlines(),1):
        if not line.strip(): continue
        try: value=json.loads(line)
        except json.JSONDecodeError as exc: raise ValueError(f"Invalid JSON event at line {number}: {exc}") from exc
        if not isinstance(value,dict): raise ValueError(f"Event at line {number} must be an object")
        events.append(value)
    return events


def monitoring_plan(project: Path, filename: str) -> dict:
    rules,path=load_monitoring_rules(project,filename)
    return {"schema_version":"1.0","status":"configured" if rules else "not_configured","rules_file":path,"rule_count":len(rules),"rules":rules,"providers":[{"id":"jsonl-replay","status":"available"},{"id":"rpc","status":"not_configured"},{"id":"block-explorer","status":"not_configured"}],"limitations":["Live RPC and explorer ingestion are not configured in this phase."]}


def write_monitoring_run(project_value: str,events_value: str,output_value: str,filename: str="monitoring.toml") -> tuple[dict,Path]:
    project=safe_project_path(project_value); event_path=Path(events_value).expanduser().resolve()
    if not event_path.is_file(): raise ValueError(f"Event file does not exist: {event_path}")
    rules,rules_path=load_monitoring_rules(project,filename); events=read_jsonl(event_path); result=replay_events(rules,events)
    stamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ"); event_hash=hashlib.sha256(event_path.read_bytes()).hexdigest(); run_id=f"{stamp}_{event_hash[:8]}"
    parent=Path(output_value).expanduser().resolve()/"monitoring"/re.sub(r"[^A-Za-z0-9_.-]+","-",project.name); run_dir=parent/run_id; suffix=1
    while run_dir.exists(): run_dir=parent/f"{run_id}_{suffix}"; suffix+=1
    run_id=run_dir.name; run_dir.mkdir(parents=True,exist_ok=False)
    result.update({"run_id":run_id,"created_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"project":str(project),"rules_file":rules_path,"events_file":str(event_path),"events_hash":event_hash})
    write_json(run_dir/"monitoring.json",result); write_json(run_dir/"alerts.json",result["alerts"])
    return result,run_dir
