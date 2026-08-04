import json
import tempfile
import unittest
from pathlib import Path

from blockchain_auditor.audit import run_audit
from blockchain_auditor.detection import detect_project
from blockchain_auditor.plugins import default_registry
from blockchain_auditor.plugins.registry import PluginRegistry


class Phase5Tests(unittest.TestCase):
    def test_detects_specific_ecosystems_from_manifests(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "Cargo.toml").write_text('[dependencies]\nanchor-lang="0.30"')
            (root / "lib.rs").write_text("pub fn x() {}")
            project = detect_project(root)
            self.assertIn("solana", project["ecosystems"])
            self.assertNotIn("rust", project["ecosystems"])

    def test_registry_rejects_duplicate_plugin_ids(self):
        registry = PluginRegistry()
        plugin = default_registry.plugins()[0]
        registry.register(plugin)
        with self.assertRaisesRegex(ValueError, "Duplicate plugin"):
            registry.register(plugin)

    def test_rust_plugin_generates_findings_and_explicit_coverage(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / "Cargo.toml").write_text('[dependencies]\nsolana-program="2"')
            (root / "lib.rs").write_text("fn process() { let x = value.unwrap(); unsafe { call(); } invoke_signed(); }")
            project = detect_project(root); results, coverage = default_registry.run(root, project)
            rust = next(result for result in results if result.plugin_id == "rust-solana")
            self.assertEqual({finding.rule_id for finding in rust.findings}, {"rust-production-unwrap", "rust-unsafe-block", "solana-invoke-signed"})
            matrix = next(item for item in coverage if item["plugin_id"] == "rust-solana")
            self.assertTrue(matrix["detected"])
            self.assertEqual(matrix["capabilities"]["formal_verification"], "not_configured")

    def test_multichain_audit_combines_plugins_and_writes_coverage(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); project = root / "protocol"; project.mkdir()
            (project / "Move.toml").write_text('[package]\nname="Demo"')
            (project / "module.move").write_text("module demo::m { friend demo::trusted; public(friend) fun admin() {} }")
            run, run_dir = run_audit(str(project), str(root / "reports"), profile="multi-chain")
            self.assertTrue(any(tool["name"] == "plugin:move" for tool in run.tools))
            self.assertTrue(any(finding.source_engine == "move" for finding in run.findings))
            coverage = json.loads((run_dir / "coverage.json").read_text())
            self.assertTrue(next(item for item in coverage if item["plugin_id"] == "move")["detected"])

    def test_fabric_plugin_requires_fabric_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / "main.go").write_text("package main\nfunc main(){ panic(\"x\") }")
            self.assertNotIn("hyperledger-fabric", [plugin.plugin_id for plugin in default_registry.plan(detect_project(root))])
            (root / "go.mod").write_text("module chaincode\nrequire github.com/hyperledger/fabric-chaincode-go v1.0.0")
            self.assertIn("hyperledger-fabric", [plugin.plugin_id for plugin in default_registry.plan(detect_project(root))])


if __name__ == "__main__": unittest.main()
