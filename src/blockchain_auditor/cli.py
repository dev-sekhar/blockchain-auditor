from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .audit import compare_findings, run_audit
from .config import load_config
from .integrity import verify_manifest
from .server import serve
from .storage import list_runs
from .plugins import default_registry
from .monitoring import write_monitoring_run
from .db.store import Database
from .copilot import answer_question
from .copilot.evaluation import evaluate


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="blockchain-auditor", description="Audit blockchain projects and retain traceable reports")
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command", required=True)
    audit = commands.add_parser("audit", help="Audit a local project or public GitHub repository")
    audit.add_argument("project", help="Local project path or https://github.com/owner/repository URL"); audit.add_argument("--output", default=".audit-reports")
    audit.add_argument("--config", help="TOML configuration file")
    audit.add_argument("--profile", choices=["quick", "solidity", "solidity-ci", "multi-chain", "assurance", "protocol"])
    audit.add_argument("--no-optional-engines", action="store_true")
    audit.add_argument("--fail-on", choices=["critical", "high", "medium", "low"], default=None)
    audit.add_argument("--ci", action="store_true", help="Emit GitHub-compatible workflow annotations")
    dashboard = commands.add_parser("serve", help="Serve the local dashboard")
    dashboard.add_argument("--output", default=".audit-reports"); dashboard.add_argument("--host", default="127.0.0.1"); dashboard.add_argument("--port", type=int, default=8765)
    dashboard.add_argument("--database", help="SQLite service database path")
    dashboard.add_argument("--require-auth", action="store_true", help="Require bearer-token authentication")
    listing = commands.add_parser("list", help="List stored audit runs"); listing.add_argument("--output", default=".audit-reports")
    compare = commands.add_parser("compare", help="Compare two stored audit IDs")
    compare.add_argument("baseline"); compare.add_argument("current"); compare.add_argument("--output", default=".audit-reports")
    verify = commands.add_parser("verify", help="Verify a stored audit manifest")
    verify.add_argument("audit_id"); verify.add_argument("--output", default=".audit-reports")
    capabilities = commands.add_parser("capabilities", help="List ecosystem plugin coverage")
    capabilities.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    monitor = commands.add_parser("monitor", help="Replay blockchain events through monitoring rules")
    monitor.add_argument("project"); monitor.add_argument("events"); monitor.add_argument("--rules", default="monitoring.toml"); monitor.add_argument("--output", default=".audit-reports")
    backup = commands.add_parser("backup", help="Create a consistent SQLite service backup")
    backup.add_argument("database"); backup.add_argument("destination")
    ask = commands.add_parser("ask", help="Ask an evidence-grounded question about an audit")
    ask.add_argument("audit_id"); ask.add_argument("question"); ask.add_argument("--output",default=".audit-reports"); ask.add_argument("--json",action="store_true")
    evaluation = commands.add_parser("evaluate-copilot",help="Evaluate grounded retrieval against a dataset")
    evaluation.add_argument("audit_id"); evaluation.add_argument("dataset"); evaluation.add_argument("--output",default=".audit-reports")
    return root


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command in {"ask","evaluate-copilot"}:
            runs=list_runs(Path(args.output).expanduser().resolve()); run=next((item for item in runs if item.get("audit_id")==args.audit_id),None)
            if not run: raise ValueError("Audit ID does not exist in the audit store")
            run_dir=Path(run["_run_dir"])
            if args.command=="ask":
                response=answer_question(run_dir,args.question); print(json.dumps(response,indent=2) if args.json else response["answer"]+"\n\nCitations: "+", ".join(item["id"] for item in response["citations"])); return 0
            result=evaluate(run_dir,Path(args.dataset).expanduser().resolve()); print(json.dumps(result,indent=2)); return 0 if result["summary"]["passed"]==result["summary"]["total"] else 1
        if args.command == "backup":
            path=Database(Path(args.database)).backup(Path(args.destination)); print(f"Backup: {path}"); return 0
        if args.command == "monitor":
            result,path=write_monitoring_run(args.project,args.events,args.output,args.rules)
            print(f"Monitoring run: {result['run_id']}\nEvents: {result['events_processed']}\nAlerts: {result['summary']['total']}\nReport: {path/'monitoring.json'}")
            return 1 if result["summary"]["by_severity"]["critical"] else 0
        if args.command == "capabilities":
            capabilities = default_registry.capabilities()
            if args.json: print(json.dumps(capabilities, indent=2)); return 0
            for item in capabilities:
                static = item["capabilities"]["static_analysis"]
                print(f"{item['plugin_id']:<22} static={static:<12} ecosystems={','.join(item['ecosystems'])}")
            return 0
        if args.command == "audit":
            config, _ = load_config(args.config, args.profile)
            run, path = run_audit(args.project, args.output, not args.no_optional_engines, config=config)
            print(f"Audit: {run.audit_id}\nFindings: {run.summary['total']}\nReport: {path / 'report.html'}")
            if args.ci:
                for finding in run.findings:
                    if finding.status == "suppressed": continue
                    location = finding.locations[0] if finding.locations else None
                    level = "error" if finding.severity in ("critical", "high") else "warning" if finding.severity == "medium" else "notice"
                    location_text = f" file={location.file},line={location.start_line}," if location else " "
                    message = finding.title.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
                    print(f"::{level}{location_text}title={finding.rule_id}::{message}")
            threshold = args.fail_on or config.fail_on
            if threshold:
                order = ["critical", "high", "medium", "low", "informational"]
                if any(run.summary["active_by_severity"][s] for s in order[:order.index(threshold)+1]): return 1
            if run.analysis.get("verification", {}).get("gate", {}).get("status") == "failed": return 1
            return 0
        if args.command == "serve": serve(args.output, args.host, args.port, args.database, args.require_auth); return 0
        runs = list_runs(Path(args.output).expanduser().resolve())
        if args.command == "list":
            for run in runs: print(f"{run['audit_id']}  {run['source']['project_name']}  findings={run['summary']['total']}")
            return 0
        by_id = {run["audit_id"]: run for run in runs}
        if args.command == "verify":
            if args.audit_id not in by_id: raise ValueError("Audit ID does not exist in the audit store")
            valid, message = verify_manifest(by_id[args.audit_id])
            print(message); return 0 if valid else 1
        if args.baseline not in by_id or args.current not in by_id: raise ValueError("Both audit IDs must exist in the audit store")
        result = compare_findings({f["id"] for f in by_id[args.current]["findings"]}, {f["id"] for f in by_id[args.baseline]["findings"]})
        print(json.dumps(result, indent=2)); return 0
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr); return 3
    except Exception as exc:
        print(f"audit failed: {exc}", file=sys.stderr); return 2


if __name__ == "__main__": raise SystemExit(main())
