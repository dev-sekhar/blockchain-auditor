from __future__ import annotations

import json
import mimetypes
import os
import re
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .api.controllers import create_audit, create_job, get_job, get_reviews, list_jobs, put_review
from .api.errors import ApiError, not_found
from .api.rbac import require
from .backend.worker import AuditWorker
from .db.store import Database
from .services.alerts import Alert, alerts
from .services.auth import AuthService
from .storage import list_runs
from .copilot import answer_question


WEB_ROOT = Path(__file__).with_name("web")


def handler_factory(output: Path, database: Database, auth: AuthService):
    class Handler(BaseHTTPRequestHandler):
        def _json(self, value, status=200):
            payload = json.dumps(value).encode(); self.send_response(status)
            self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(payload)))
            self.send_header("X-Content-Type-Options", "nosniff"); self.end_headers(); self.wfile.write(payload)

        def _text(self,value,status=200,content_type="text/plain; charset=utf-8"):
            payload=value.encode(); self.send_response(status); self.send_header("Content-Type",content_type); self.send_header("Content-Length",str(len(payload))); self.end_headers(); self.wfile.write(payload)

        def _file(self, path: Path):
            if not path.is_file(): return self._json(not_found("File").payload(), 404)
            payload = path.read_bytes(); mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            self.send_response(200); self.send_header("Content-Type", mime); self.send_header("Content-Length", str(len(payload)))
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'")
            self.send_header("X-Content-Type-Options", "nosniff"); self.end_headers(); self.wfile.write(payload)

        def _identity(self):
            if not hasattr(self, "_identity_cache"):
                self._identity_cache = auth.authenticate(self.headers.get("Authorization"), self.headers.get("X-Audit-Role", "viewer").lower(), self.headers.get("X-Audit-Actor", "local-user"))
            return self._identity_cache

        def _tenant_output(self): return output / "tenants" / self._identity().tenant_id
        def _body(self):
            length = int(self.headers.get("Content-Length", "0"))
            if length > 32_768: raise ApiError("AUDIT-API-413", "Request is too large", 413)
            try: return json.loads(self.rfile.read(length))
            except json.JSONDecodeError as exc: raise ApiError("AUDIT-API-400", "The request body is not valid JSON", 400) from exc

        def _api_error(self, exc: ApiError):
            alerts.publish(Alert(exc.code, "warning" if exc.status < 500 else "error", exc.message, {"path": self.path}))
            return self._json(exc.payload(), exc.status)

        def do_GET(self):
            path = unquote(urlparse(self.path).path)
            if path == "/": return self._file(WEB_ROOT / "index.html")
            if path == "/healthz": return self._json({"status":"ok"})
            if path == "/readyz":
                try: metrics=database.service_metrics(); return self._json({"status":"ready","database":True,"jobs":metrics["jobs"]})
                except Exception: return self._json({"status":"not_ready","database":False},503)
            if path == "/metrics":
                metrics=database.service_metrics(); lines=[f'blockchain_auditor_jobs{{status="{status}"}} {count}' for status,count in sorted(metrics["jobs"].items())]; lines.extend([f"blockchain_auditor_tenants {metrics['tenants']}",f"blockchain_auditor_audit_events {metrics['events']}"])
                return self._text("\n".join(lines)+"\n",content_type="text/plain; version=0.0.4; charset=utf-8")
            if path.startswith("/static/"):
                candidate = (WEB_ROOT / path.removeprefix("/static/")).resolve()
                return self._file(candidate) if candidate.parent == WEB_ROOT.resolve() else self._api_error(not_found("Static asset"))
            try:
                identity = self._identity(); tenant_output = self._tenant_output(); runs = list_runs(tenant_output)
                if path == "/api/session": return self._json({"tenant_id": identity.tenant_id, "actor": identity.actor, "role": identity.role, "authenticated": auth.required})
                if path == "/api/jobs": return self._json(list_jobs(database, identity.tenant_id, identity.role))
                if path == "/api/events": require(identity.role, "audit:log"); return self._json(database.events(identity.tenant_id))
                if path == "/api/runs":
                    require(identity.role, "audit:read")
                    return self._json([{k:v for k,v in run.items() if k not in ("findings","_run_dir")} for run in runs])
                parts = path.strip("/").split("/")
                if len(parts) == 3 and parts[:2] == ["api","jobs"]: return self._json(get_job(database, identity.tenant_id, parts[2], identity.role))
                if len(parts) >= 3 and parts[:2] == ["api","runs"]:
                    require(identity.role, "audit:read"); run = next((r for r in runs if r.get("audit_id") == parts[2]), None)
                    if not run: raise not_found("Audit")
                    if len(parts) == 3: run.pop("_run_dir",None); return self._json(run)
                    if len(parts) == 4 and parts[3] == "reviews": return self._json(get_reviews(tenant_output, parts[2], identity.role))
                    if len(parts) == 5 and parts[3] == "files":
                        allowed={"report.html","report.json","report.sarif","report.junit.xml","manifest.json","findings.json","architecture.json","architecture.mmd","assistance.json","coverage.json","verification.json","simulation.json","monitoring.json","posture.json","compliance.json","reviews.json"}
                        if parts[4] not in allowed: raise not_found("Report artifact")
                        return self._file(Path(run["_run_dir"])/parts[4])
                raise not_found("Endpoint")
            except ApiError as exc: return self._api_error(exc)

        def do_POST(self):
            try:
                identity=self._identity(); path=urlparse(self.path).path
                parts=unquote(path).strip("/").split("/")
                if len(parts)==4 and parts[:2]==["api","runs"] and parts[3]=="copilot":
                    require(identity.role,"audit:read"); runs=list_runs(self._tenant_output()); run=next((item for item in runs if item.get("audit_id")==parts[2]),None)
                    if not run: raise not_found("Audit")
                    body=self._body(); response=answer_question(Path(run["_run_dir"]),str(body.get("question","")))
                    database.event(identity.tenant_id,identity.actor,"copilot.query","audit",parts[2],"success",{"interaction_id":response["interaction_id"],"question_hash":hashlib.sha256(str(body.get("question","")).encode()).hexdigest()})
                    return self._json(response)
                if path == "/api/jobs": return self._json(create_job(database,self._body(),identity.tenant_id,identity.actor,identity.role),202)
                if path == "/api/audits":
                    result=create_audit(self._tenant_output(),self._body(),identity.role)
                    database.event(identity.tenant_id,identity.actor,"audit.create","audit",result["audit_id"],"success",{"mode":"synchronous"})
                    return self._json(result,201)
                raise not_found("Endpoint")
            except ApiError as exc: return self._api_error(exc)
            except Exception as exc:
                alerts.publish(Alert("AUDIT-API-500","error","Unhandled API error",{"error":str(exc)}))
                return self._api_error(ApiError("AUDIT-API-500","The operation could not be completed",500))

        def do_PATCH(self):
            parts=unquote(urlparse(self.path).path).strip("/").split("/")
            try:
                identity=self._identity()
                if len(parts)!=6 or parts[:2]!=["api","runs"] or parts[3]!="findings" or parts[5]!="review": raise not_found("Endpoint")
                review=put_review(self._tenant_output(),parts[2],parts[4],self._body(),identity.role,identity.actor)
                database.event(identity.tenant_id,identity.actor,"finding.review","finding",parts[4],"success",{"audit_id":parts[2],"status":review["status"]})
                return self._json(review)
            except ApiError as exc: return self._api_error(exc)

        def log_message(self, format, *args): print(f"[dashboard] {format % args}")
    return Handler


def serve(output_value: str, host: str, port: int, database_value: str | None = None, require_auth: bool = False) -> None:
    output=Path(output_value).expanduser().resolve(); output.mkdir(parents=True,exist_ok=True)
    database=Database(Path(database_value).expanduser() if database_value else output/"service.db")
    if require_auth:
        token=os.environ.get("BLOCKCHAIN_AUDITOR_BOOTSTRAP_TOKEN","")
        tenant_id=os.environ.get("BLOCKCHAIN_AUDITOR_TENANT_ID","default")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}",tenant_id): raise ValueError("BLOCKCHAIN_AUDITOR_TENANT_ID has an invalid format")
        if not token: raise ValueError("BLOCKCHAIN_AUDITOR_BOOTSTRAP_TOKEN is required when authentication is enabled")
        database.bootstrap(tenant_id,os.environ.get("BLOCKCHAIN_AUDITOR_TENANT_NAME",tenant_id),token)
    auth=AuthService(database,require_auth); worker=AuditWorker(database,output); worker.start()
    server=ThreadingHTTPServer((host,port),handler_factory(output,database,auth))
    print(f"Dashboard: http://{host}:{port}"); print(f"Audit store: {output}"); print(f"Authentication: {'required' if require_auth else 'local development mode'}")
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close(); worker.stop()
