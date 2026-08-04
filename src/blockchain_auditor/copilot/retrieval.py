from __future__ import annotations

import json
import re
from pathlib import Path

from ..storage import load_json
from .safety import redact


def _tokens(text: str) -> set[str]: return {token for token in re.findall(r"[a-z0-9_-]{3,}",text.lower()) if token not in {"the","and","for","this","that","with"}}


def build_evidence(run_dir: Path) -> list[dict]:
    manifest=load_json(run_dir/"manifest.json"); evidence=[]
    for finding in manifest.get("findings",[]):
        location=finding.get("locations",[{}])[0] if finding.get("locations") else {}
        text=f"{finding['severity']} {finding['title']}. {finding['description']} Recommendation: {finding['recommendation']} Location: {location.get('file','unknown')}:{location.get('start_line','?')}"
        evidence.append({"id":f"finding:{finding['id']}","kind":"finding","text":redact(text),"artifact":"manifest.json","pointer":f"/findings/{finding['id']}","finding_id":finding["id"],"severity":finding["severity"]})
    artifacts=(("architecture.json","architecture"),("verification.json","verification"),("simulation.json","simulation"),("monitoring.json","monitoring"),("compliance.json","compliance"))
    for filename,kind in artifacts:
        path=run_dir/filename
        if not path.exists(): continue
        data=load_json(path); summary=data.get("summary",data.get("risk_indicators",{})); text=f"{kind.title()} status {data.get('status',data.get('engine',{}).get('status','recorded'))}. Summary: {json.dumps(summary,sort_keys=True)}. Limitations: {' '.join(data.get('limitations',[]))}"
        evidence.append({"id":f"artifact:{kind}","kind":kind,"text":redact(text),"artifact":filename,"pointer":"/","finding_id":None,"severity":"informational"})
    knowledge_path=Path(__file__).parents[1]/"knowledge"/"security.json"
    if knowledge_path.exists():
        for item in json.loads(knowledge_path.read_text(encoding="utf-8")):
            evidence.append({"id":f"knowledge:{item['id']}","kind":"knowledge","text":item["text"],"artifact":"knowledge/security.json","pointer":f"/{item['id']}","finding_id":None,"severity":"informational"})
    return evidence


def retrieve(question: str,evidence: list[dict],limit: int=6) -> list[dict]:
    query=_tokens(question); severity_order={"critical":5,"high":4,"medium":3,"low":2,"informational":1}
    scored=[]
    for item in evidence:
        overlap=len(query&_tokens(item["text"])); score=overlap*10+severity_order.get(item.get("severity"),0)
        if overlap or not query: scored.append((score,item))
    if not scored: scored=[(severity_order.get(item.get("severity"),0),item) for item in evidence]
    return [item for _,item in sorted(scored,key=lambda pair:(-pair[0],pair[1]["id"]))[:limit]]
