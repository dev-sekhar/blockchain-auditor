import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from blockchain_auditor.api.controllers import create_audit, put_review
from blockchain_auditor.api.errors import ApiError
from blockchain_auditor.audit import run_audit
from blockchain_auditor.backend.architecture import analyze_architecture, mermaid_graph
from blockchain_auditor.backend.assistance import build_assistance
from blockchain_auditor.backend.reviews import load_reviews, update_review
from blockchain_auditor.integrity import verify_manifest
from blockchain_auditor.storage import load_json


CONTRACT = """pragma solidity ^0.8.20;
contract Owned {
    function adminAction() external onlyOwner {}
}
contract Vault is Owned {
    function authorize() external { require(tx.origin == msg.sender); }
    function upgradeTo(address implementation) external onlyOwner {}
}
"""


class Phase3Tests(unittest.TestCase):
    def test_architecture_extracts_contracts_boundaries_and_edges(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp); (project / "Vault.sol").write_text(CONTRACT)
            result = analyze_architecture(project)
            self.assertEqual({node["id"] for node in result["nodes"]}, {"Owned", "Vault"})
            self.assertTrue(any(edge["type"] == "inheritance" and edge["target"] == "Owned" for edge in result["edges"]))
            self.assertEqual(result["risk_indicators"]["privileged_operations"], 2)
            self.assertGreaterEqual(result["risk_indicators"]["upgrade_signals"], 1)
            self.assertIn("flowchart LR", mermaid_graph(result))

    def test_audit_generates_assistance_and_guarded_patch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); project = root / "project"; project.mkdir(); (project / "Vault.sol").write_text(CONTRACT)
            run, run_dir = run_audit(str(project), str(root / "reports"), include_optional=False)
            assistance = load_json(run_dir / "assistance.json")
            self.assertEqual(len(assistance["explanations"]), 1)
            self.assertEqual(len(assistance["patch_proposals"]), 0)
            self.assertIn("architecture.json", run.analysis["artifacts"])
            self.assertTrue(verify_manifest(load_json(run_dir / "manifest.json"))[0])

    def test_guarded_patch_rejects_tautology_but_allows_owner_substitution(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); project=root/"project"; project.mkdir(); source=project/"Auth.sol"; source.write_text("contract Auth { address owner; function x() external { require(tx.origin == owner); } }")
            run,run_dir=run_audit(str(project),str(root/"reports"),include_optional=False)
            assistance=load_json(run_dir/"assistance.json"); self.assertEqual(len(assistance["patch_proposals"]),1)
            self.assertIn("msg.sender == owner",assistance["patch_proposals"][0]["diff"])

    def test_review_log_is_hash_chained(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); project = root / "project"; project.mkdir(); (project / "Vault.sol").write_text(CONTRACT)
            run, run_dir = run_audit(str(project), str(root / "reports"), include_optional=False)
            finding_id = run.findings[0].id
            update_review(run_dir, finding_id, "acknowledged", "Confirmed by auditor", "alice", "auditor")
            update_review(run_dir, finding_id, "remediation_planned", "Fix scheduled", "alice", "auditor")
            reviews = load_reviews(run_dir)
            self.assertEqual(reviews["events"][1]["previous_hash"], reviews["events"][0]["event_hash"])
            for event in reviews["events"]:
                recorded = event["event_hash"]
                unsigned = {key: value for key, value in event.items() if key != "event_hash"}
                actual = hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                self.assertEqual(recorded, actual)

    def test_rbac_blocks_viewer_mutations(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); project = root / "project"; project.mkdir()
            with self.assertRaises(ApiError) as context:
                create_audit(root / "reports", {"path": str(project)}, "viewer")
            self.assertEqual(context.exception.code, "AUDIT-AUTH-403")

    def test_review_requires_note_and_known_status(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); project = root / "project"; project.mkdir(); (project / "Vault.sol").write_text(CONTRACT)
            run, run_dir = run_audit(str(project), str(root / "reports"), include_optional=False)
            with self.assertRaisesRegex(ValueError, "note is required"):
                update_review(run_dir, run.findings[0].id, "resolved", "", "alice", "auditor")


if __name__ == "__main__": unittest.main()
