from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from .detection import detect_project
from .config import AuditConfig, load_config
from .engines import configured_engines, TestEngine
from .integrity import sign_manifest
from .models import AuditRun, EngineResult, Finding, Location, SEVERITIES
from .provenance import identify_source, safe_project_path
from .reports import write_reports
from .storage import latest_for_project, write_json
from .suppressions import apply_suppressions, load_suppressions
from .backend.architecture import analyze_architecture, mermaid_graph
from .backend.assistance import build_assistance
from .plugins import default_registry
from .verification import run_verification
from .simulation import run_simulations
from .monitoring.runner import monitoring_plan
from .security import run_posture
from .engines import finding_id
from .services.repositories import RepositoryService


def _timestamp() -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    return now.isoformat().replace("+00:00", "Z"), now.strftime("%Y-%m-%dT%H-%M-%SZ")


def compare_findings(current: set[str], baseline: set[str]) -> dict:
    return {"new": sorted(current - baseline), "existing": sorted(current & baseline), "resolved": sorted(baseline - current)}


def _run_local_audit(
    project_value: str, output_value: str = ".audit-reports", include_optional: bool = True,
    config: AuditConfig | None = None, config_path: str | None = None, profile: str | None = None,
    repository_url: str | None = None,
) -> tuple[AuditRun, Path]:
    project = safe_project_path(project_value)
    config = config or load_config(config_path, profile)[0]
    if not include_optional:
        config = AuditConfig(profile="quick", engines=["builtin"])
    output = Path(output_value).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    source = identify_source(project)
    source.repository_url = repository_url
    if repository_url:
        source.path = repository_url
        source.project_name = Path(repository_url.removesuffix(".git")).name
    project_info = detect_project(project)
    baseline = latest_for_project(output, source.project_name)
    created_at, stamp = _timestamp()
    short_hash = source.git_commit[:8] if source.git_commit else source.tree_hash[:8]
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", source.project_name)
    base_id = f"{stamp}_{short_hash}"
    run_dir = output / safe_name / base_id
    suffix = 1
    while run_dir.exists():
        run_dir = output / safe_name / f"{base_id}_{suffix}"
        suffix += 1
    audit_id = run_dir.name
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True)

    engines = configured_engines(config)
    results = []
    for engine in engines:
        if isinstance(engine, TestEngine):
            results.append(engine.run_or_skip(project))
        elif engine.available():
            results.append(engine.run(project))
        else:
            results.append(EngineResult(
                engine.name, getattr(engine, "image", "unknown"), "skipped",
                error=getattr(engine, "unavailable_reason", "Analyzer executable is unavailable"),
            ))
    plugin_results, plugin_coverage = default_registry.run(project, project_info)
    for plugin in plugin_results:
        results.append(EngineResult(
            f"plugin:{plugin.plugin_id}", plugin.version, plugin.status, plugin.findings, plugin.error,
            raw_output={"files_scanned": plugin.files_scanned, "metadata": plugin.metadata},
        ))
    verification = run_verification(project, config)
    verification_findings=[]
    for outcome in verification["engine"]["outcomes"]:
        if outcome["status"] != "violated": continue
        source_file=outcome.get("source_file") or "unknown"; line=int(outcome.get("source_line") or 1)
        verification_findings.append(Finding(
            finding_id(f"property-{outcome['id']}",source_file,line,outcome.get("expression") or outcome["description"]),
            f"property-{outcome['id']}", f"Property violated: {outcome['id']}", outcome["severity"], "high",
            "formal-verification", outcome["description"], [Location(source_file,line)], outcome.get("expression") or outcome["description"],
            "Treat the counterexample as a release blocker; reproduce it, correct the invariant violation, and rerun verification.", "solidity-smtchecker",
        ))
    results.append(EngineResult("verification:solidity-smtchecker",verification["engine"]["version"],verification["engine"]["status"],verification_findings,verification["engine"]["error"],verification["engine"]["duration_ms"],verification["engine"]))
    simulation=run_simulations(project,config); simulation_findings=[]
    monitoring=monitoring_plan(project,config.monitoring_file)
    posture,compliance,posture_findings=run_posture(project,config.compliance_frameworks)
    results.append(EngineResult("full-stack-posture","1.0",posture["status"],posture_findings,None,raw_output=posture["summary"]))
    scenario_file=Path(config.scenarios_file).name
    for scenario in simulation["results"]:
        if scenario["status"]!="breach": continue
        simulation_findings.append(Finding(
            finding_id(f"simulation-{scenario['id']}",scenario_file,1,scenario["message"]),f"simulation-{scenario['id']}",
            f"Scenario threshold breached: {scenario['id']}",scenario["severity"],"medium","economic-simulation",scenario["message"],
            [Location(scenario_file,1)],str(scenario.get("metrics",{}))[:500],"Review the scenario assumptions, reproduce against an isolated fork, and add protocol safeguards or operating limits.","economic-simulation",
        ))
    results.append(EngineResult("simulation:economic-models","1.0",simulation["status"],simulation_findings,None,raw_output=simulation))
    findings_by_id = {}
    for result in results:
        raw_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", result.name)
        write_json(raw_dir / f"{raw_name}.json", {"status": result.status, "error": result.error, "output": result.raw_output})
        for finding in result.findings:
            findings_by_id.setdefault(finding.id, finding)

    baseline_ids = {item["id"] for item in baseline.get("findings", [])} if baseline else set()
    trace = compare_findings(set(findings_by_id), baseline_ids)
    for finding in findings_by_id.values():
        finding.traceability = "existing" if finding.id in baseline_ids else "new"
    findings = sorted(findings_by_id.values(), key=lambda f: (SEVERITIES.index(f.severity), f.id))
    suppression_result = apply_suppressions(findings, load_suppressions(project, config.suppression_file))
    counts = {severity: sum(f.severity == severity for f in findings) for severity in SEVERITIES}
    active_counts = {severity: sum(f.severity == severity and f.status != "suppressed" for f in findings) for severity in SEVERITIES}
    completed_at, _ = _timestamp()
    architecture = analyze_architecture(project)
    assistance = build_assistance(project, findings, architecture)
    unproved=sum(value for status,value in verification["summary"].items() if status!="proved")
    gate_failed=config.require_property_proofs and (verification["property_count"]==0 or unproved>0)
    verification["gate"]={"required":config.require_property_proofs,"status":"failed" if gate_failed else "passed","unproved":unproved}
    run = AuditRun(
        "1.2", audit_id, created_at, completed_at, source, project_info, config.safe_dict(), config.digest(),
        [{"name": r.name, "version": r.version, "status": r.status, "error": r.error, "duration_ms": r.duration_ms} for r in results],
        {"total": len(findings), "active": sum(active_counts.values()), "suppressed": len(suppression_result["applied"]),
         "by_severity": counts, "active_by_severity": active_counts,
         "traceability": {key: len(value) for key, value in trace.items()}, "resolved_ids": trace["resolved"],
         "suppressions": suppression_result},
        findings, baseline.get("audit_id") if baseline else None,
    )
    run.analysis = {
        "architecture": architecture["risk_indicators"],
        "explanations": len(assistance["explanations"]), "patch_proposals": len(assistance["patch_proposals"]),
        "artifacts": ["architecture.json", "architecture.mmd", "assistance.json", "coverage.json", "verification.json", "simulation.json", "monitoring.json", "posture.json", "compliance.json"],
        "verification": {"requested":verification["requested"],"engine_status":verification["engine"]["status"],"property_count":verification["property_count"],"summary":verification["summary"],"gate":verification["gate"]},
        "simulation": {"requested":simulation["requested"],"status":simulation["status"],"summary":simulation["summary"]},
        "monitoring": {"status":monitoring["status"],"rule_count":monitoring["rule_count"],"providers":monitoring["providers"]},
        "posture": posture["summary"],
        "compliance": {"frameworks":[item["framework"] for item in compliance["frameworks"]],"disclaimer":compliance["disclaimer"]},
        "ecosystem_coverage": [{
            "plugin_id": "evm-core", "version": "1.0", "detected": "evm" in project_info["ecosystems"],
            "languages": ["Solidity", "Vyper"], "ecosystems": ["evm"],
            "capabilities": {"static_analysis": "configured", "dynamic_testing": "profile_dependent", "formal_verification": ("executed" if verification["engine"]["status"]=="completed" else "not_configured" if not verification["requested"] else f"requested_{verification['engine']['status']}"), "economic_simulation": ("executed" if simulation["status"] in {"completed","completed_with_errors"} else "not_configured" if not simulation["requested"] else f"requested_{simulation['status']}"), "continuous_monitoring": "configured_replay" if monitoring["status"]=="configured" else "not_configured"},
            "assurance": "tool_and_heuristic" if "evm" in project_info["ecosystems"] else "not_applicable",
            "limitations": ["Assurance depends on which configured engines completed successfully."],
        }, *plugin_coverage],
    }
    run.integrity = sign_manifest(run.to_dict())
    write_json(run_dir / "manifest.json", run.to_dict())
    write_json(run_dir / "findings.json", [finding.to_dict() for finding in findings])
    write_json(run_dir / "architecture.json", architecture)
    (run_dir / "architecture.mmd").write_text(mermaid_graph(architecture), encoding="utf-8")
    write_json(run_dir / "assistance.json", assistance)
    write_json(run_dir / "coverage.json", run.analysis["ecosystem_coverage"])
    write_json(run_dir / "verification.json", verification)
    write_json(run_dir / "simulation.json", simulation)
    write_json(run_dir / "monitoring.json", monitoring)
    write_json(run_dir / "posture.json", posture)
    write_json(run_dir / "compliance.json", compliance)
    write_reports(run_dir, run)
    return run, run_dir


def run_audit(
    project_value: str, output_value: str = ".audit-reports", include_optional: bool = True,
    config: AuditConfig | None = None, config_path: str | None = None, profile: str | None = None,
) -> tuple[AuditRun, Path]:
    with RepositoryService().materialize(project_value) as (project, repository_url):
        return _run_local_audit(str(project), output_value, include_optional, config, config_path, profile, repository_url)
