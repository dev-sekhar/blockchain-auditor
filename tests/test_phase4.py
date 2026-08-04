import tempfile
import time
import unittest
from pathlib import Path

from blockchain_auditor.backend.worker import AuditWorker
from blockchain_auditor.db.store import Database
from blockchain_auditor.services.auth import AuthService


class Phase4Tests(unittest.TestCase):
    def test_token_authentication_and_tenant_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            database = Database(Path(temp) / "service.db")
            database.bootstrap("tenant-a", "Tenant A", "a-secure-token-value-123456", "alice", "admin")
            identity = AuthService(database, True).authenticate("Bearer a-secure-token-value-123456")
            self.assertEqual((identity.tenant_id, identity.actor, identity.role), ("tenant-a", "alice", "admin"))
            with self.assertRaisesRegex(Exception, "invalid or revoked"):
                AuthService(database, True).authenticate("Bearer invalid-token-value-123456")

    def test_jobs_and_events_are_tenant_isolated(self):
        with tempfile.TemporaryDirectory() as temp:
            database = Database(Path(temp) / "service.db")
            database.bootstrap("a", "A", "tenant-a-token-value-123456")
            database.bootstrap("b", "B", "tenant-b-token-value-123456")
            job_a = database.create_job("a", "alice", "/project/a", "quick")
            database.create_job("b", "bob", "/project/b", "quick")
            self.assertEqual([job["id"] for job in database.jobs("a")], [job_a["id"]])
            self.assertTrue(all(event["tenant_id"] == "a" for event in database.events("a")))
            self.assertIsNone(database.job("b", job_a["id"]))

    def test_worker_completes_persistent_job_and_writes_tenant_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); project = root / "project"; project.mkdir()
            (project / "Vault.sol").write_text("contract Vault { function bad() external { require(tx.origin == msg.sender); } }")
            database = Database(root / "service.db")
            database.bootstrap("tenant-a", "Tenant A", "a-secure-token-value-123456")
            job = database.create_job("tenant-a", "alice", str(project), "quick")
            worker = AuditWorker(database, root / "reports", interval=0.01); worker.start()
            try:
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    stored = database.job("tenant-a", job["id"])
                    if stored["status"] in {"completed", "failed"}: break
                    time.sleep(0.02)
                self.assertEqual(stored["status"], "completed", stored.get("error_message"))
                manifests = list((root / "reports" / "tenants" / "tenant-a").glob("*/*/manifest.json"))
                self.assertEqual(len(manifests), 1)
                self.assertTrue(any(event["action"] == "job.complete" for event in database.events("tenant-a")))
            finally: worker.stop()

    def test_claim_is_single_consumer_transition(self):
        with tempfile.TemporaryDirectory() as temp:
            database = Database(Path(temp) / "service.db")
            database.bootstrap("a", "A", "tenant-a-token-value-123456")
            database.create_job("a", "alice", "/project", "quick")
            self.assertIsNotNone(database.claim_job())
            self.assertIsNone(database.claim_job())
            self.assertEqual(database.requeue_interrupted(), 1)
            self.assertIsNotNone(database.claim_job())
            self.assertTrue(any(event["action"] == "job.requeue" for event in database.events("a")))

    def test_rejects_unsafe_tenant_identifier(self):
        with tempfile.TemporaryDirectory() as temp:
            database = Database(Path(temp) / "service.db")
            with self.assertRaisesRegex(ValueError, "path-safe"):
                database.bootstrap("../escape", "Unsafe", "unsafe-tenant-token-value-123456")


if __name__ == "__main__": unittest.main()
