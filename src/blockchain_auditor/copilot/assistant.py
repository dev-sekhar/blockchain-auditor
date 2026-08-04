from __future__ import annotations

import hashlib
from pathlib import Path

from .retrieval import build_evidence,retrieve
from .safety import detect_injection,redact
from ..storage import load_json


class ModelProvider:
    """Provider-neutral extension contract. Implementations must preserve supplied citations."""
    provider_id="unconfigured"
    def generate(self,question: str,evidence: list[dict]) -> str: raise NotImplementedError


def _proposal_is_safe(proposal: dict) -> bool:
    diff=str(proposal.get("diff","")); normalized="".join(diff.split())
    forbidden=("+require(msg.sender==msg.sender)","+require(msg.sender!=msg.sender)","+assert(true)","+require(true)")
    return bool(diff.startswith("--- ") and "\n+++ " in diff and not any(item in normalized for item in forbidden))


def answer_question(run_dir: Path,question: str,provider: ModelProvider|None=None) -> dict:
    question=question.strip()
    if not question or len(question)>4000: raise ValueError("Question must contain between 1 and 4000 characters")
    injection=detect_injection(question); evidence=retrieve(question,build_evidence(run_dir))
    citations=[{"id":item["id"],"artifact":item["artifact"],"pointer":item["pointer"]} for item in evidence]
    if injection:
        answer="I ignored instruction-like text that attempted to override the audit workflow. I can only answer from recorded audit evidence."
    elif not evidence: answer="No relevant evidence is available in this audit run. Run the applicable analyzer or verification stage before drawing a conclusion."
    elif provider:
        answer=redact(provider.generate(question,evidence))
    else:
        findings=[item for item in evidence if item["kind"]=="finding"]
        if findings: answer="Relevant recorded issues:\n"+"\n".join(f"- {item['text']} [{item['id']}]" for item in findings)
        else: answer="Relevant audit evidence:\n"+"\n".join(f"- {item['text']} [{item['id']}]" for item in evidence)
    assistance_path=run_dir/"assistance.json"; proposals=[]
    if assistance_path.exists() and not injection:
        assistance=load_json(assistance_path); finding_ids={item.get("finding_id") for item in evidence}
        proposals=[{**item,"runtime_safety_validated":True} for item in assistance.get("patch_proposals",[]) if item.get("finding_id") in finding_ids and _proposal_is_safe(item)]
    return {"schema_version":"1.0","interaction_id":hashlib.sha256((question+str(run_dir)).encode()).hexdigest()[:20],"mode":"provider" if provider else "deterministic","provider":provider.provider_id if provider else None,"answer":redact(answer),"citations":citations,"safety":{"prompt_injection_detected":bool(injection),"matched_controls":injection,"secrets_redacted":True},"remediation_proposals":proposals,"guardrail":"Proposals are read-only and require human review; this endpoint never modifies source or opens pull requests."}
