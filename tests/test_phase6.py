import tempfile
import unittest
from pathlib import Path

from blockchain_auditor.audit import run_audit
from blockchain_auditor.config import AuditConfig
from blockchain_auditor.verification.properties import Property, discover_solidity_assertions, load_properties
from blockchain_auditor.verification.solidity import parse_smt_output


class Phase6Tests(unittest.TestCase):
    def test_loads_versioned_property_specification(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"audit-properties.toml").write_text('''[[properties]]
id="asset-conservation"
description="Assets cover claims"
severity="critical"
language="Solidity"
kind="design-invariant"
''')
            properties,path=load_properties(root,"audit-properties.toml")
            self.assertEqual(properties[0].id,"asset-conservation")
            self.assertEqual(properties[0].origin,"declared")
            self.assertTrue(path.endswith("audit-properties.toml"))

    def test_rejects_duplicate_property_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); entry='''[[properties]]
id="duplicate-property"
description="Test"
severity="high"
language="Solidity"
kind="design-invariant"
'''; (root/"audit-properties.toml").write_text(entry+entry)
            with self.assertRaisesRegex(ValueError,"Duplicate property"):
                load_properties(root,"audit-properties.toml")

    def test_discovers_source_assertions_as_obligations(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); (root/"Vault.sol").write_text("contract Vault { function check() external { assert(total >= claims); } }")
            properties=discover_solidity_assertions(root)
            self.assertEqual(len(properties),1)
            self.assertEqual(properties[0].expression,"total >= claims")
            self.assertEqual(properties[0].origin,"discovered")

    def test_parses_counterexample_without_overstating_other_property(self):
        violated=Property("asset-conservation","Assets cover claims","critical","Solidity","smt-assertion","Vault.sol",4,"assets >= claims",linked=True)
        safe=Property("supply-cap","Supply remains capped","high","Solidity","smt-assertion","Vault.sol",8,"supply <= cap",linked=True)
        output="Vault.sol:4:5: Warning: CHC: Assertion violation happens here.\nCounterexample: assets = 0, claims = 1"
        outcomes,diagnostics=parse_smt_output(output,[violated,safe],0)
        self.assertEqual(outcomes[0]["status"],"violated")
        self.assertEqual(outcomes[1]["status"],"no_counterexample")
        self.assertEqual(diagnostics[0]["outcome"],"violated")

    def test_assurance_audit_records_skipped_verifier_and_failed_required_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); project=root/"project"; project.mkdir()
            (project/"Vault.sol").write_text("contract Vault { function check() external { assert(total >= claims); } }")
            config=AuditConfig(profile="assurance",engines=["builtin"],formal_verification=True,require_property_proofs=True,solc_image=None)
            run,run_dir=run_audit(str(project),str(root/"reports"),config=config)
            verification=run.analysis["verification"]
            self.assertEqual(verification["engine_status"],"skipped")
            self.assertEqual(verification["gate"]["status"],"failed")
            self.assertTrue((run_dir/"verification.json").is_file())


if __name__ == "__main__": unittest.main()
