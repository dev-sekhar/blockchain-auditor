import json
import tempfile
import unittest
from pathlib import Path

from blockchain_auditor.monitoring.runner import load_monitoring_rules,replay_events,write_monitoring_run


RULES='''[[rules]]
id="upgrade"
type="contract_upgrade"
severity="critical"
allowed_implementations=["0xGood"]
[[rules]]
id="transfer"
type="treasury_transfer"
severity="high"
min_amount=1000
'''


class Phase8Tests(unittest.TestCase):
    def test_replay_generates_hash_chained_alerts(self):
        rules=[{"id":"upgrade","type":"contract_upgrade","severity":"critical","allowed_implementations":["0xGood"]},{"id":"transfer","type":"treasury_transfer","severity":"high","min_amount":1000}]
        result=replay_events(rules,[{"type":"contract_upgrade","implementation":"0xBad"},{"type":"treasury_transfer","amount":2000}])
        self.assertEqual(result["summary"]["total"],2)
        self.assertEqual(result["alerts"][1]["previous_hash"],result["alerts"][0]["event_hash"])

    def test_monitoring_run_is_timestamped_and_replayable(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); project=root/"project"; project.mkdir(); (project/"monitoring.toml").write_text(RULES)
            events=root/"events.jsonl"; events.write_text('{"type":"contract_upgrade","implementation":"0xBad"}\n')
            result,run_dir=write_monitoring_run(str(project),str(events),str(root/"reports"))
            self.assertEqual(result["summary"]["total"],1)
            self.assertTrue((run_dir/"monitoring.json").is_file())
            self.assertTrue((run_dir/"alerts.json").is_file())
            _,second_dir=write_monitoring_run(str(project),str(events),str(root/"reports"))
            self.assertNotEqual(run_dir,second_dir)

    def test_invalid_event_line_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); project=root/"project"; project.mkdir(); (project/"monitoring.toml").write_text(RULES); events=root/"events.jsonl"; events.write_text("not-json\n")
            with self.assertRaisesRegex(ValueError,"line 1"):
                write_monitoring_run(str(project),str(events),str(root/"reports"))


if __name__ == "__main__": unittest.main()
