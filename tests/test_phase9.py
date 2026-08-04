import tempfile
import unittest
from pathlib import Path

from blockchain_auditor.audit import run_audit
from blockchain_auditor.security import run_posture


class Phase9Tests(unittest.TestCase):
    def test_full_stack_posture_detects_infrastructure_api_and_frontend_risks(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); (root/"Dockerfile").write_text("FROM python:latest\nRUN curl https://example.test/install | sh\n")
            (root/"deployment.yaml").write_text("securityContext:\n  privileged: true\n")
            (root/"api.py").write_text('allow_origins=["*"]\n')
            (root/"app.js").write_text("element.innerHTML = userInput;\n")
            posture,compliance,findings=run_posture(root,["SOC2","ISO27001"])
            rules={finding.rule_id for finding in findings}
            self.assertTrue({"container-latest-tag","shell-download-execute","container-root-default","k8s-privileged","cors-wildcard","unsafe-inner-html"}.issubset(rules))
            self.assertEqual(posture["status"],"completed")
            self.assertEqual(compliance["frameworks"][0]["status"],"evidence_mapped")
            self.assertIn("not a certification",compliance["disclaimer"])

    def test_unknown_framework_is_explicitly_unsupported(self):
        with tempfile.TemporaryDirectory() as temp:
            _,compliance,_=run_posture(Path(temp),["UNKNOWN"])
            self.assertEqual(compliance["frameworks"][0]["status"],"unsupported")

    def test_audit_writes_posture_and_compliance_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); project=root/"project"; project.mkdir(); (project/"Dockerfile").write_text("FROM python:latest\n")
            run,run_dir=run_audit(str(project),str(root/"reports"),include_optional=False)
            self.assertTrue(any(f.source_engine=="full-stack-posture" for f in run.findings))
            self.assertTrue((run_dir/"posture.json").is_file())
            self.assertTrue((run_dir/"compliance.json").is_file())


if __name__ == "__main__": unittest.main()
