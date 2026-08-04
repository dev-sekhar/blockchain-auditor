from __future__ import annotations

import difflib
from pathlib import Path

from ..models import Finding


EXPLOITS = {
    "access-control": "An attacker may route a victim through an intermediary contract so an authorization assumption evaluates against the transaction origin instead of the immediate caller.",
    "delegatecall": "If an attacker can influence the implementation address or payload, foreign code may execute with the caller's storage and privileges.",
    "unchecked-call": "A failed external call may be ignored, or a called contract may re-enter before the caller has finalized state changes.",
    "secrets": "Anyone who obtains the committed credential may impersonate its owner and authorize blockchain transactions.",
    "dangerous-operation": "An authorized or compromised caller may trigger lifecycle behavior that disrupts integrations or strands assets.",
}


def _patch(project: Path, finding: Finding) -> dict | None:
    if finding.rule_id != "solidity-tx-origin" or not finding.locations: return None
    location = finding.locations[0]; path = project / location.file
    try: original = path.read_text(encoding="utf-8").splitlines(keepends=True)
    except OSError: return None
    index = location.start_line - 1
    if index < 0 or index >= len(original) or "tx.origin" not in original[index]: return None
    modified = original.copy(); modified[index] = modified[index].replace("tx.origin", "msg.sender")
    normalized="".join(modified[index].split())
    if "msg.sender==msg.sender" in normalized or "msg.sender!=msg.sender" in normalized: return None
    diff = "".join(difflib.unified_diff(original, modified, fromfile=f"a/{location.file}", tofile=f"b/{location.file}"))
    return {
        "finding_id": finding.id, "status": "proposal", "confidence": "medium", "diff": diff,
        "rationale": "Replace transaction-origin identity with the immediate caller identity.",
        "guardrails": ["Not applied automatically", "Review intended caller flow and authorization subject", "Reject tautological authorization conditions", "Run the full test suite", "Require human approval before applying"],
    }


def build_assistance(project: Path, findings: list[Finding], architecture: dict) -> dict:
    explanations, patches = [], []
    for finding in findings:
        explanations.append({
            "finding_id": finding.id, "summary": finding.description,
            "why_it_matters": EXPLOITS.get(finding.category, "The identified pattern can violate the protocol's intended security assumptions."),
            "exploit_scenario": EXPLOITS.get(finding.category, "An attacker may reach the affected code path under conditions the implementation did not anticipate."),
            "recommended_action": finding.recommendation,
            "confidence": finding.confidence,
            "basis": "Deterministic rule and source evidence; no generative model was used.",
        })
        proposal = _patch(project, finding)
        if proposal: patches.append(proposal)
    return {
        "schema_version": "1.0", "explanations": explanations, "patch_proposals": patches,
        "architecture_summary": architecture["risk_indicators"],
        "disclaimer": "Assisted output supports human review and is not proof of security. Patch proposals are never applied automatically.",
    }
