from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import uuid
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


SCHEMA = """
CREATE TABLE IF NOT EXISTS tenants (id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS api_tokens (
  token_hash TEXT PRIMARY KEY, tenant_id TEXT NOT NULL REFERENCES tenants(id), actor TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('admin','auditor','viewer')), created_at TEXT NOT NULL, revoked_at TEXT
);
CREATE TABLE IF NOT EXISTS audit_jobs (
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL REFERENCES tenants(id), actor TEXT NOT NULL,
  project_path TEXT NOT NULL, profile TEXT NOT NULL, status TEXT NOT NULL,
  audit_id TEXT, error_code TEXT, error_message TEXT, created_at TEXT NOT NULL, started_at TEXT, completed_at TEXT
);
CREATE INDEX IF NOT EXISTS audit_jobs_tenant_created ON audit_jobs(tenant_id, created_at DESC);
CREATE TABLE IF NOT EXISTS audit_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL,
  resource_type TEXT NOT NULL, resource_id TEXT NOT NULL, outcome TEXT NOT NULL, metadata_json TEXT NOT NULL,
  created_at TEXT NOT NULL, previous_hash TEXT, event_hash TEXT NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS audit_events_tenant_id ON audit_events(tenant_id, id DESC);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path.expanduser().resolve(); self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock(); self.migrate()

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=30); connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON"); connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def migrate(self):
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            columns={row[1] for row in connection.execute("PRAGMA table_info(audit_jobs)")}
            for name,definition in (("lease_owner","TEXT"),("lease_expires_at","TEXT"),("attempts","INTEGER NOT NULL DEFAULT 0")):
                if name not in columns: connection.execute(f"ALTER TABLE audit_jobs ADD COLUMN {name} {definition}")

    def bootstrap(self, tenant_id: str, tenant_name: str, token: str, actor: str = "bootstrap-admin", role: str = "admin"):
        if len(token) < 24: raise ValueError("Bootstrap API token must contain at least 24 characters")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", tenant_id): raise ValueError("Tenant ID must be path-safe and contain at most 64 characters")
        now = utc_now(); digest = hashlib.sha256(token.encode()).hexdigest()
        with self.connect() as connection:
            connection.execute("INSERT OR IGNORE INTO tenants(id,name,created_at) VALUES(?,?,?)", (tenant_id, tenant_name, now))
            connection.execute("INSERT OR IGNORE INTO api_tokens(token_hash,tenant_id,actor,role,created_at) VALUES(?,?,?,?,?)", (digest, tenant_id, actor, role, now))

    def identity_for_token(self, token: str) -> dict | None:
        digest = hashlib.sha256(token.encode()).hexdigest()
        with self.connect() as connection:
            row = connection.execute("SELECT tenant_id,actor,role FROM api_tokens WHERE token_hash=? AND revoked_at IS NULL", (digest,)).fetchone()
        return dict(row) if row else None

    def create_job(self, tenant_id: str, actor: str, project_path: str, profile: str) -> dict:
        job = {"id": uuid.uuid4().hex, "tenant_id": tenant_id, "actor": actor, "project_path": project_path, "profile": profile, "status": "queued", "created_at": utc_now()}
        with self._lock, self.connect() as connection:
            connection.execute("INSERT INTO audit_jobs(id,tenant_id,actor,project_path,profile,status,created_at) VALUES(:id,:tenant_id,:actor,:project_path,:profile,:status,:created_at)", job)
            self._append_event(connection, tenant_id, actor, "job.create", "audit_job", job["id"], "success", {"profile": profile})
        return job

    def claim_job(self, worker_id: str = "local-worker", lease_seconds: int = 900) -> dict | None:
        with self._lock, self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            now=utc_now(); row=connection.execute("SELECT * FROM audit_jobs WHERE status='queued' OR (status='running' AND (lease_expires_at IS NULL OR lease_expires_at<?)) ORDER BY created_at LIMIT 1",(now,)).fetchone()
            if not row: connection.commit(); return None
            expires=(datetime.now(timezone.utc)+timedelta(seconds=max(30,lease_seconds))).isoformat().replace("+00:00","Z")
            connection.execute("UPDATE audit_jobs SET status='running',started_at=COALESCE(started_at,?),lease_owner=?,lease_expires_at=?,attempts=attempts+1 WHERE id=?",(now,worker_id,expires,row["id"])); connection.commit()
            result=dict(row); result.update(status="running",started_at=row["started_at"] or now,lease_owner=worker_id,lease_expires_at=expires,attempts=int(row["attempts"] or 0)+1); return result

    def renew_lease(self, job_id: str, worker_id: str, lease_seconds: int = 900) -> bool:
        expires=(datetime.now(timezone.utc)+timedelta(seconds=max(30,lease_seconds))).isoformat().replace("+00:00","Z")
        with self.connect() as connection: cursor=connection.execute("UPDATE audit_jobs SET lease_expires_at=? WHERE id=? AND status='running' AND lease_owner=?",(expires,job_id,worker_id))
        return cursor.rowcount==1

    def requeue_interrupted(self) -> int:
        with self._lock, self.connect() as connection:
            rows = connection.execute("SELECT id,tenant_id,actor FROM audit_jobs WHERE status='running'").fetchall()
            for row in rows:
                connection.execute("UPDATE audit_jobs SET status='queued',started_at=NULL WHERE id=?", (row["id"],))
                self._append_event(connection, row["tenant_id"], row["actor"], "job.requeue", "audit_job", row["id"], "success", {"reason": "service_restart"})
        return len(rows)

    def complete_job(self, job_id: str, audit_id: str, worker_id: str | None = None) -> bool:
        with self._lock, self.connect() as connection:
            row = connection.execute("SELECT tenant_id,actor FROM audit_jobs WHERE id=? AND status='running' AND (? IS NULL OR lease_owner=?)", (job_id,worker_id,worker_id)).fetchone()
            if not row: return False
            connection.execute("UPDATE audit_jobs SET status='completed',audit_id=?,completed_at=?,lease_owner=NULL,lease_expires_at=NULL WHERE id=?", (audit_id, utc_now(), job_id))
            if row: self._append_event(connection, row["tenant_id"], row["actor"], "job.complete", "audit_job", job_id, "success", {"audit_id": audit_id})
        return True

    def fail_job(self, job_id: str, code: str, message: str, worker_id: str | None = None) -> bool:
        with self._lock, self.connect() as connection:
            row = connection.execute("SELECT tenant_id,actor FROM audit_jobs WHERE id=? AND status='running' AND (? IS NULL OR lease_owner=?)", (job_id,worker_id,worker_id)).fetchone()
            if not row: return False
            connection.execute("UPDATE audit_jobs SET status='failed',error_code=?,error_message=?,completed_at=?,lease_owner=NULL,lease_expires_at=NULL WHERE id=?", (code, message[:2000], utc_now(), job_id))
            if row: self._append_event(connection, row["tenant_id"], row["actor"], "job.complete", "audit_job", job_id, "failure", {"code": code})
        return True

    def jobs(self, tenant_id: str) -> list[dict]:
        with self.connect() as connection: rows = connection.execute("SELECT * FROM audit_jobs WHERE tenant_id=? ORDER BY created_at DESC", (tenant_id,)).fetchall()
        return [dict(row) for row in rows]

    def job(self, tenant_id: str, job_id: str) -> dict | None:
        with self.connect() as connection: row = connection.execute("SELECT * FROM audit_jobs WHERE tenant_id=? AND id=?", (tenant_id, job_id)).fetchone()
        return dict(row) if row else None

    def event(self, tenant_id: str, actor: str, action: str, resource_type: str, resource_id: str, outcome: str, metadata: dict):
        with self._lock, self.connect() as connection:
            self._append_event(connection, tenant_id, actor, action, resource_type, resource_id, outcome, metadata)

    def _append_event(self, connection, tenant_id: str, actor: str, action: str, resource_type: str, resource_id: str, outcome: str, metadata: dict):
        previous = connection.execute("SELECT event_hash FROM audit_events WHERE tenant_id=? ORDER BY id DESC LIMIT 1", (tenant_id,)).fetchone()
        previous_hash = previous[0] if previous else None; created = utc_now()
        material = {"tenant_id": tenant_id, "actor": actor, "action": action, "resource_type": resource_type, "resource_id": resource_id, "outcome": outcome, "metadata": metadata, "created_at": created, "previous_hash": previous_hash}
        event_hash = hashlib.sha256(json.dumps(material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        connection.execute("INSERT INTO audit_events(tenant_id,actor,action,resource_type,resource_id,outcome,metadata_json,created_at,previous_hash,event_hash) VALUES(?,?,?,?,?,?,?,?,?,?)", (tenant_id, actor, action, resource_type, resource_id, outcome, json.dumps(metadata, sort_keys=True), created, previous_hash, event_hash))

    def events(self, tenant_id: str, limit: int = 100) -> list[dict]:
        with self.connect() as connection: rows = connection.execute("SELECT * FROM audit_events WHERE tenant_id=? ORDER BY id DESC LIMIT ?", (tenant_id, min(max(limit, 1), 500))).fetchall()
        result=[]
        for row in rows:
            item=dict(row); item["metadata"]=json.loads(item.pop("metadata_json")); result.append(item)
        return result

    def service_metrics(self) -> dict:
        with self.connect() as connection:
            jobs={row["status"]:row["count"] for row in connection.execute("SELECT status,COUNT(*) AS count FROM audit_jobs GROUP BY status")}; tenants=connection.execute("SELECT COUNT(*) FROM tenants").fetchone()[0]; events=connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
        return {"jobs":jobs,"tenants":tenants,"events":events}

    def backup(self, destination: Path) -> Path:
        destination=destination.expanduser().resolve(); destination.parent.mkdir(parents=True,exist_ok=True)
        if destination.exists(): raise ValueError(f"Backup destination already exists: {destination}")
        source=self.connect(); target=sqlite3.connect(destination)
        try: source.backup(target)
        finally: target.close(); source.close()
        return destination
