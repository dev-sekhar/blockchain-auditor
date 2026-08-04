import tempfile
import unittest
from pathlib import Path

from blockchain_auditor.audit import run_audit
from blockchain_auditor.simulation.runner import load_scenarios, run_simulations
from blockchain_auditor.config import AuditConfig


SCENARIOS='''[[scenarios]]
id="swap"
type="amm_swap"
reserve_in=1000
reserve_out=1000
amount_in=500
max_price_impact_pct=10
[[scenarios]]
id="crash"
type="oracle_shock"
collateral_value=100
debt=70
liquidation_threshold=0.8
shock_pct=30
'''


class Phase7Tests(unittest.TestCase):
    def test_simulation_models_report_threshold_breaches(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); (root/"audit-scenarios.toml").write_text(SCENARIOS)
            config=AuditConfig(economic_simulation=True)
            result=run_simulations(root,config)
            self.assertEqual(result["status"],"completed")
            self.assertEqual(result["summary"]["breaches"],2)
            self.assertTrue(all(item["status"]=="breach" for item in result["results"]))

    def test_rejects_duplicate_scenarios(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); entry='''[[scenarios]]\nid="same"\ntype="bridge_quorum"\nvalidators=3\nsignature_threshold=2\ncompromised_validators=1\n'''; (root/"audit-scenarios.toml").write_text(entry+entry)
            with self.assertRaisesRegex(ValueError,"Duplicate scenario"):
                load_scenarios(root,"audit-scenarios.toml")

    def test_protocol_audit_normalizes_simulation_findings(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); project=root/"project"; project.mkdir(); (project/"audit-scenarios.toml").write_text(SCENARIOS)
            run,run_dir=run_audit(str(project),str(root/"reports"),profile="protocol")
            self.assertEqual(run.analysis["simulation"]["summary"]["breaches"],2)
            self.assertEqual(sum(f.category=="economic-simulation" for f in run.findings),2)
            self.assertTrue((run_dir/"simulation.json").is_file())


if __name__ == "__main__": unittest.main()
