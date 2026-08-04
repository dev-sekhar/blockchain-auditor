# Documentation

This index is the entry point for Blockchain Auditor `1.2.0` documentation.

## Use and operate the tool

- [Getting started](getting-started.md) — installation, source-only execution, audits, dashboard use, and report access
- [Instruction guide](instruction-guide.md) — installation, audits, dashboard, reports, service operation, backup, CI, and troubleshooting
- [Production runbook](production-runbook.md) — deployment gates, health checks, backup/restore, and incident response
- [Configuration example](../blockchain-auditor.example.toml)
- [Property example](../audit-properties.example.toml)
- [Simulation example](../audit-scenarios.example.toml)
- [Monitoring rules](../monitoring.example.toml) and [sample events](../monitoring-events.example.jsonl)
- [Copilot evaluation example](../copilot-evaluation.example.json)

## Scope and assurance

- [Requirements specification](../requirement) — product vision; not every enterprise requirement is implemented
- [Requirements traceability](requirements-traceability.md) — implemented, foundational, and external/unconfigured scope
- [CODEX applicability](codex-evaluation.md) — which repository guidelines are executed, adapted, deferred, or skipped
- [Delivery status](remaining-phases.md) — completed phases and remaining external production work
- [Current test status](test-report.md)

## Design history

- Phase documentation is grouped under [`docs/phases`](phases/index.md): [3](phases/phase-3.md), [4](phases/phase-4.md), [5](phases/phase-5.md), [6](phases/phase-6.md), [7](phases/phase-7.md), [8](phases/phase-8.md), [9](phases/phase-9.md), [10](phases/phase-10.md), and [11](phases/phase-11.md)
- [Plugin authoring](plugin-authoring.md)
- Historical phase test reports: [3](phases/test-report-phase-3.md), [4](phases/test-report-phase-4.md), [5](phases/test-report-phase-5.md), [6](phases/test-report-phase-6.md), [7–9](phases/test-report-phases-7-9.md), and [10–11](phases/test-report-phases-10-11.md)

Phase reports preserve what was verified when each phase landed. Use the consolidated test report for the current regression result.
