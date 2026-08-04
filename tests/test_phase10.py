import sqlite3
import tempfile
import unittest
from pathlib import Path

from blockchain_auditor.db.store import Database
from blockchain_auditor.services.production import OidcProvider,RemoteRepositoryPolicy,WebhookNotifier,WebhookPolicy


class Phase10Tests(unittest.TestCase):
    def test_job_leases_prevent_double_claim_and_track_attempts(self):
        with tempfile.TemporaryDirectory() as temp:
            database=Database(Path(temp)/"service.db"); database.bootstrap("tenant","Tenant","phase10-secure-token-value-123456")
            job=database.create_job("tenant","alice","/project","quick")
            first=database.claim_job("worker-a",60)
            self.assertEqual(first["lease_owner"],"worker-a"); self.assertEqual(first["attempts"],1)
            self.assertIsNone(database.claim_job("worker-b",60))
            self.assertFalse(database.renew_lease(job["id"],"worker-b",60)); self.assertTrue(database.renew_lease(job["id"],"worker-a",60))
            self.assertFalse(database.complete_job(job["id"],"audit","worker-b"))
            self.assertTrue(database.complete_job(job["id"],"audit","worker-a"))

    def test_migration_and_consistent_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); database=Database(root/"service.db"); database.bootstrap("tenant","Tenant","phase10-secure-token-value-123456")
            backup=database.backup(root/"backup.db")
            with sqlite3.connect(backup) as connection: self.assertEqual(connection.execute("SELECT COUNT(*) FROM tenants").fetchone()[0],1)
            with self.assertRaisesRegex(ValueError,"already exists"): database.backup(backup)

    def test_webhook_and_repository_ssrf_policies(self):
        webhook=WebhookNotifier(WebhookPolicy(frozenset({"hooks.example.com"}),enabled=False))
        self.assertEqual(webhook.send("https://hooks.example.com/a",{"ok":True})["status"],"dry_run")
        with self.assertRaisesRegex(ValueError,"HTTPS"): webhook.send("http://hooks.example.com/a",{})
        with self.assertRaisesRegex(ValueError,"allowlisted"): webhook.send("https://localhost/a",{})
        repositories=RemoteRepositoryPolicy(frozenset({"github.com"}))
        valid=repositories.validate("https://github.com/example/project.git","a"*40); self.assertEqual(valid["host"],"github.com")
        with self.assertRaisesRegex(ValueError,"immutable"): repositories.validate("https://github.com/example/project.git","main")
        with self.assertRaisesRegex(ValueError,"embedded"): repositories.validate("https://token@github.com/example/project.git","a"*40)

    def test_oidc_adapter_never_fakes_authentication(self):
        with self.assertRaises(NotImplementedError): OidcProvider().authenticate("token")


if __name__ == "__main__": unittest.main()
