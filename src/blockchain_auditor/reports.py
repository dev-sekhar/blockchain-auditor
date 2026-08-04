from __future__ import annotations

import html
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from .models import AuditRun


COLORS = {"critical": "#b91c1c", "high": "#dc2626", "medium": "#d97706", "low": "#2563eb", "informational": "#64748b"}


def render_html(run: AuditRun) -> str:
    rows = []
    for finding in run.findings:
        location = finding.locations[0] if finding.locations else None
        where = f"{location.file}:{location.start_line}" if location else "—"
        rows.append(f"""
        <tr><td><span class="severity" style="background:{COLORS.get(finding.severity, '#64748b')}">{html.escape(finding.severity)}</span></td>
        <td><strong>{html.escape(finding.title)}</strong><br><small>{html.escape(finding.rule_id)} · {html.escape(finding.source_engine)}</small></td>
        <td>{html.escape(where)}</td><td>{html.escape(finding.traceability)}</td></tr>
        <tr class="detail"><td></td><td colspan="3">{html.escape(finding.description)}<br><strong>Recommendation:</strong> {html.escape(finding.recommendation)}</td></tr>""")
    counts = run.summary["by_severity"]
    stats = "".join(f'<div class="stat"><b>{counts.get(s, 0)}</b><span>{s}</span></div>' for s in COLORS)
    architecture = run.analysis.get("architecture", {})
    architecture_html = "".join(f"<li><strong>{html.escape(str(key).replace('_', ' ').title())}:</strong> {html.escape(str(value))}</li>" for key, value in architecture.items())
    coverage = run.analysis.get("ecosystem_coverage", [])
    coverage_rows = "".join(f"<tr><td>{html.escape(item['plugin_id'])}</td><td>{'yes' if item['detected'] else 'no'}</td><td>{html.escape(item['capabilities']['static_analysis'])}</td><td>{html.escape(item['capabilities']['formal_verification'])}</td><td>{html.escape(item['assurance'])}</td></tr>" for item in coverage)
    verification = run.analysis.get("verification", {})
    verification_summary = verification.get("summary", {})
    verification_html = "".join(f"<li><strong>{html.escape(status.replace('_',' ').title())}:</strong> {count}</li>" for status,count in verification_summary.items())
    simulation=run.analysis.get("simulation",{}); monitoring=run.analysis.get("monitoring",{}); posture=run.analysis.get("posture",{}); compliance=run.analysis.get("compliance",{})
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Audit {html.escape(run.audit_id)}</title><style>
body{{font:14px system-ui;margin:0;background:#f5f7fb;color:#172033}}main{{max-width:1100px;margin:auto;padding:40px 24px}}
h1{{margin-bottom:4px}}.muted,small{{color:#68758a}}.stats{{display:flex;gap:12px;flex-wrap:wrap;margin:28px 0}}.stat{{background:white;padding:18px 24px;border-radius:10px;box-shadow:0 1px 4px #ccd3df;min-width:110px}}.stat b{{font-size:28px;display:block}}.stat span{{text-transform:capitalize}}table{{width:100%;border-collapse:collapse;background:white}}th,td{{text-align:left;padding:12px;border-bottom:1px solid #e5e9f0}}.severity{{color:white;border-radius:12px;padding:3px 9px;text-transform:uppercase;font-size:11px}}.detail td{{padding-top:0;color:#4b5563}}code{{background:#e8edf4;padding:2px 5px}}</style></head><body><main>
<h1>Blockchain Security Audit</h1><div class="muted">{html.escape(run.source.project_name)} · {html.escape(run.audit_id)}</div>
<p>Created {html.escape(run.created_at)} · source <code>{html.escape(run.source.tree_hash[:12])}</code></p>
<div class="stats">{stats}</div><h2>Architecture indicators</h2><ul>{architecture_html or '<li>No Solidity architecture data detected.</li>'}</ul><p class="muted">Architecture and assisted findings are heuristic and require human review. Patch proposals are never applied automatically.</p><h2>Formal verification</h2><p>Engine status: <strong>{html.escape(str(verification.get('engine_status','not requested')))}</strong> · Properties: {verification.get('property_count',0)} · Gate: <strong>{html.escape(str(verification.get('gate',{}).get('status','not configured')))}</strong></p><ul>{verification_html or '<li>No proof obligations recorded.</li>'}</ul><h2>Simulation and monitoring</h2><p>Simulation: <strong>{html.escape(str(simulation.get('status','not requested')))}</strong> · Breaches: {simulation.get('summary',{}).get('breaches',0)} · Monitoring: <strong>{html.escape(str(monitoring.get('status','not configured')))}</strong> · Rules: {monitoring.get('rule_count',0)}</p><h2>Full-stack posture and compliance evidence</h2><p>Files reviewed: {posture.get('files_scanned',0)} · Posture findings: {sum(posture.get('findings_by_category',{}).values()) if posture else 0}</p><p class="muted">{html.escape(str(compliance.get('disclaimer','Compliance was not assessed.')))}</p><h2>Ecosystem coverage</h2><table><thead><tr><th>Plugin</th><th>Detected</th><th>Static analysis</th><th>Formal verification</th><th>Assurance</th></tr></thead><tbody>{coverage_rows}</tbody></table><h2>Findings</h2><table><thead><tr><th>Severity</th><th>Issue</th><th>Location</th><th>Traceability</th></tr></thead><tbody>{''.join(rows) or '<tr><td colspan="4">No findings detected.</td></tr>'}</tbody></table>
</main></body></html>"""


def write_reports(run_dir: Path, run: AuditRun) -> None:
    (run_dir / "report.html").write_text(render_html(run), encoding="utf-8")
    (run_dir / "report.json").write_text(json.dumps(run.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sarif_results = []
    for finding in run.findings:
        location = finding.locations[0] if finding.locations else None
        sarif_results.append({
            "ruleId": finding.rule_id,
            "level": {"critical": "error", "high": "error", "medium": "warning", "low": "note", "informational": "note"}.get(finding.severity, "warning"),
            "message": {"text": finding.description},
            "locations": [{"physicalLocation": {"artifactLocation": {"uri": location.file}, "region": {"startLine": location.start_line}}}] if location else [],
            "fingerprints": {"blockchainAuditor/v1": finding.id},
        })
    sarif = {"version": "2.1.0", "$schema": "https://json.schemastore.org/sarif-2.1.0.json", "runs": [{"tool": {"driver": {"name": "blockchain-auditor", "version": "1.2.0"}}, "results": sarif_results}]}
    (run_dir / "report.sarif").write_text(json.dumps(sarif, indent=2) + "\n", encoding="utf-8")
    suite = ET.Element("testsuite", name="blockchain-auditor", tests=str(len(run.findings)), failures=str(run.summary.get("active", run.summary["total"])), skipped=str(run.summary.get("suppressed", 0)))
    for finding in run.findings:
        case = ET.SubElement(suite, "testcase", classname=finding.category, name=f"{finding.rule_id}:{finding.id}")
        if finding.status == "suppressed":
            ET.SubElement(case, "skipped", message="Suppressed by audit policy")
        else:
            failure = ET.SubElement(case, "failure", type=finding.severity, message=finding.title)
            failure.text = finding.description
    ET.ElementTree(suite).write(run_dir / "report.junit.xml", encoding="unicode", xml_declaration=True)
