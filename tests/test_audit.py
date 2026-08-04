import json
import tempfile
import unittest
import os
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from blockchain_auditor.audit import compare_findings, run_audit
from blockchain_auditor.provenance import safe_project_path, tree_hash
from blockchain_auditor.config import load_config
from blockchain_auditor.integrity import verify_manifest
from blockchain_auditor.storage import load_json
from blockchain_auditor.services.repositories import RepositoryService


class AuditTests(unittest.TestCase):
    def test_github_url_policy_and_audit_provenance(self):
        service = RepositoryService()
        self.assertEqual(service.normalize("https://github.com/example/vault.git"), "https://github.com/example/vault.git")
        for value in ("http://github.com/example/vault", "https://gitlab.com/example/vault", "https://token@github.com/example/vault", "https://github.com/example/vault?x=1"):
            with self.subTest(value=value), self.assertRaises(ValueError): service.normalize(value)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); checkout = root / "checkout"; checkout.mkdir()
            (checkout / "Vault.sol").write_text("contract Vault {}")
            @contextmanager
            def materialize(_service, value):
                self.assertEqual(value, "https://github.com/example/vault")
                yield checkout, value
            with patch.object(RepositoryService, "materialize", materialize):
                run, _ = run_audit("https://github.com/example/vault", str(root / "reports"), include_optional=False)
            self.assertEqual(run.source.repository_url, "https://github.com/example/vault")
            self.assertEqual(run.source.path, "https://github.com/example/vault")
            self.assertEqual(run.source.project_name, "vault")

    def test_audit_writes_versioned_reports_and_tracks_findings(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); project = root / "vault"; output = root / "reports"; project.mkdir()
            contract = project / "Vault.sol"
            contract.write_text("contract Vault { function bad() public { require(tx.origin == msg.sender); } }\n")
            first, first_dir = run_audit(str(project), str(output), include_optional=False)
            self.assertEqual(first.summary["total"], 1)
            self.assertEqual(first.summary["traceability"]["new"], 1)
            for name in ("manifest.json", "findings.json", "report.json", "report.html", "report.sarif", "report.junit.xml"):
                self.assertTrue((first_dir / name).is_file())
            second, second_dir = run_audit(str(project), str(output), include_optional=False)
            self.assertNotEqual(first_dir, second_dir)
            self.assertEqual(second.baseline_audit_id, first.audit_id)
            self.assertEqual(second.summary["traceability"]["existing"], 1)
            contract.write_text("contract Vault { function good() public {} }\n")
            third, _ = run_audit(str(project), str(output), include_optional=False)
            self.assertEqual(third.summary["traceability"]["resolved"], 1)

    def test_tree_hash_changes_with_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / "a.sol").write_text("a")
            before = tree_hash(root); (root / "a.sol").write_text("b")
            self.assertNotEqual(before, tree_hash(root))

    def test_compare_findings(self):
        self.assertEqual(compare_findings({"b", "c"}, {"a", "b"}), {"new": ["c"], "existing": ["b"], "resolved": ["a"]})

    def test_rejects_file_as_project(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "file"; path.write_text("x")
            with self.assertRaisesRegex(ValueError, "not a directory"):
                safe_project_path(str(path))

    def test_configuration_and_suppression_policy(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); project = root / "project"; project.mkdir()
            (project / "Unsafe.sol").write_text("contract Unsafe { function x() public { require(tx.origin == msg.sender); } }")
            (project / ".blockchain-auditor-suppressions.json").write_text(json.dumps({"suppressions": [{"rule_id": "solidity-tx-origin", "path": "*.sol", "reason": "Accepted in test fixture", "expires": "2099-01-01"}]}))
            run, run_dir = run_audit(str(project), str(root / "reports"), include_optional=False)
            self.assertEqual(run.summary["active"], 0)
            self.assertEqual(run.summary["suppressed"], 1)
            self.assertEqual(run.findings[0].status, "suppressed")
            valid, _ = verify_manifest(load_json(run_dir / "manifest.json"))
            self.assertTrue(valid)

    def test_hmac_signed_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); project = root / "project"; project.mkdir(); (project / "A.sol").write_text("contract A {}")
            previous = os.environ.get("BLOCKCHAIN_AUDITOR_SIGNING_KEY")
            os.environ["BLOCKCHAIN_AUDITOR_SIGNING_KEY"] = "test-only-key"
            try:
                _, run_dir = run_audit(str(project), str(root / "reports"), include_optional=False)
                manifest = load_json(run_dir / "manifest.json")
                self.assertIn("signature", manifest["integrity"])
                self.assertTrue(verify_manifest(manifest)[0])
            finally:
                if previous is None: os.environ.pop("BLOCKCHAIN_AUDITOR_SIGNING_KEY", None)
                else: os.environ["BLOCKCHAIN_AUDITOR_SIGNING_KEY"] = previous

    def test_native_mode_requires_explicit_permission(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.toml"
            path.write_text('[audit]\nexecution_mode="native"\n')
            with self.assertRaisesRegex(ValueError, "allow_native_execution"):
                load_config(str(path))


if __name__ == "__main__":
    unittest.main()
