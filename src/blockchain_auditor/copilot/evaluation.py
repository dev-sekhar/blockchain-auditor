from __future__ import annotations

import json
from pathlib import Path

from .assistant import answer_question


def evaluate(run_dir: Path,dataset_path: Path) -> dict:
    data=json.loads(dataset_path.read_text(encoding="utf-8")); cases=data.get("cases",data)
    if not isinstance(cases,list): raise ValueError("Evaluation dataset must be a list or contain a cases list")
    results=[]
    for case in cases:
        response=answer_question(run_dir,str(case.get("question",""))); expected=set(case.get("expected_finding_ids",[])); cited={citation["id"].removeprefix("finding:") for citation in response["citations"] if citation["id"].startswith("finding:")}
        recall=len(expected&cited)/len(expected) if expected else 1.0; grounded=bool(response["citations"]) or not expected
        results.append({"id":case.get("id"),"recall":recall,"grounded":grounded,"passed":recall>=float(case.get("minimum_recall",1.0)) and grounded})
    return {"schema_version":"1.0","cases":results,"summary":{"total":len(results),"passed":sum(item["passed"] for item in results),"average_recall":sum(item["recall"] for item in results)/len(results) if results else 1.0}}
