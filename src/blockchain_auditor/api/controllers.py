from __future__ import annotations

from pathlib import Path

from .errors import not_found, validation
from .rbac import require
from ..audit import run_audit
from ..backend.reviews import load_reviews, update_review
from ..storage import list_runs
from ..db.store import Database
from ..services.repositories import RepositoryService


def find_run(output: Path, audit_id: str) -> dict:
    run = next((item for item in list_runs(output) if item.get("audit_id") == audit_id), None)
    if not run: raise not_found("Audit")
    return run


def create_audit(output: Path, body: dict, role: str) -> dict:
    require(role, "audit:run")
    if not isinstance(body.get("path"), str) or not body["path"].strip(): raise validation("A project path or GitHub repository URL is required")
    run, _ = run_audit(body["path"], str(output), profile=body.get("profile"))
    return run.to_dict()


def get_reviews(output: Path, audit_id: str, role: str) -> dict:
    require(role, "audit:read"); run = find_run(output, audit_id)
    return load_reviews(Path(run["_run_dir"]))


def put_review(output: Path, audit_id: str, finding_id: str, body: dict, role: str, actor: str) -> dict:
    require(role, "review:write"); run = find_run(output, audit_id)
    try: return update_review(Path(run["_run_dir"]), finding_id, str(body.get("status", "")), str(body.get("note", "")), actor, role)
    except ValueError as exc: raise validation(str(exc)) from exc


def create_job(database: Database, body: dict, tenant_id: str, actor: str, role: str) -> dict:
    require(role, "audit:run")
    source = body.get("source", {"type": "local", "path": body.get("path")})
    if not isinstance(source, dict): raise validation("source must be an object")
    value = source.get("url") if source.get("type") == "github" else source.get("path")
    try: project = RepositoryService().normalize(str(value or ""))
    except ValueError as exc: raise validation(str(exc)) from exc
    profile = str(body.get("profile", "solidity"))
    if profile not in {"quick", "solidity", "solidity-ci", "multi-chain", "assurance", "protocol"}: raise validation("Unknown audit profile")
    return database.create_job(tenant_id, actor, project, profile)


def list_jobs(database: Database, tenant_id: str, role: str) -> list[dict]:
    require(role, "audit:read"); return database.jobs(tenant_id)


def get_job(database: Database, tenant_id: str, job_id: str, role: str) -> dict:
    require(role, "audit:read"); job = database.job(tenant_id, job_id)
    if not job: raise not_found("Audit job")
    return job
