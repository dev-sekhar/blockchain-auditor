from __future__ import annotations

import threading
import uuid
from pathlib import Path

from ..audit import run_audit
from ..db.store import Database
from ..services.alerts import Alert, alerts
from ..services.repositories import RepositoryService


class AuditWorker:
    def __init__(self, database: Database, output: Path, interval: float = 0.5):
        self.database, self.output, self.interval = database, output, interval
        self.repositories = RepositoryService(); self.stop_event = threading.Event(); self.thread: threading.Thread | None = None; self.worker_id=f"worker-{uuid.uuid4().hex[:12]}"

    def start(self):
        if self.thread and self.thread.is_alive(): return
        self.thread = threading.Thread(target=self._loop, name="audit-worker", daemon=True); self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread: self.thread.join(timeout=5)

    def _loop(self):
        while not self.stop_event.is_set():
            job = self.database.claim_job(self.worker_id)
            if not job: self.stop_event.wait(self.interval); continue
            lease_done=threading.Event(); heartbeat=threading.Thread(target=self._heartbeat,args=(job["id"],lease_done),daemon=True); heartbeat.start()
            try:
                tenant_output = self.output / "tenants" / job["tenant_id"]
                run, _ = run_audit(job["project_path"], str(tenant_output), profile=job["profile"])
                if not self.database.complete_job(job["id"], run.audit_id, self.worker_id):
                    alerts.publish(Alert("AUDIT-WORKER-409", "warning", "Worker lost its job lease before completion", {"job_id": job["id"], "worker_id": self.worker_id}))
            except Exception as exc:
                self.database.fail_job(job["id"], "AUDIT-WORKER-500", str(exc), self.worker_id)
                alerts.publish(Alert("AUDIT-WORKER-500", "error", "Queued audit failed", {"job_id": job["id"], "error": str(exc)}))
            finally:
                lease_done.set(); heartbeat.join(timeout=2)

    def _heartbeat(self,job_id: str,done: threading.Event):
        while not done.wait(60):
            if not self.database.renew_lease(job_id,self.worker_id): return
