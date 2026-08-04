# Blockchain Auditor

A local-first audit orchestrator for blockchain projects. Version 1.2.0 accepts a local project path or public GitHub repository URL, fingerprints its source, runs compatible analysis engines, normalizes issues, and writes timestamped reports with issue traceability. Start with [Getting Started](docs/getting-started.md), the [complete instruction guide](docs/instruction-guide.md), or the [documentation index](docs/index.md).

## Current capabilities

- Local project and language/framework detection
- Git commit, dirty-state, and deterministic source-tree provenance
- Built-in rules for an immediately usable scan
- Optional Semgrep execution when `semgrep` is installed
- Stable finding fingerprints and new/existing/resolved comparison
- Immutable timestamped JSON, HTML, and SARIF reports
- Local dashboard for statistics, analysis results, traceability, and report access
- CI severity threshold and deterministic exit codes
- TOML audit profiles with validated execution policy
- Container isolation for Slither, Semgrep, and opted-in project tests
- Reasoned, expiring suppressions and active/suppressed issue counts
- Manifest/configuration integrity verification and optional HMAC signatures
- JUnit, SARIF, and GitHub workflow annotations for CI
- Solidity architecture, inheritance, trust-boundary, and upgrade indicators
- Deterministic exploit explanations and guarded patch proposals
- Auditor remediation decisions with a hash-chained review history
- Centralized API error codes, role policy, and alert boundary
- Modular accessible dashboard sections for architecture and remediation
- SQLite-backed tenant identities, queued jobs, and operational audit events
- Bearer-token authenticated service mode with tenant-isolated report stores
- Interrupted-job recovery and persistent worker lifecycle
- Automatic Rust/Solana, Move, Cairo/Starknet, and Fabric plugin planning
- Explicit per-ecosystem capability and assurance reporting
- Versioned properties, Solidity SMT verification adapter, and proof gates
- Deterministic DeFi scenario models and normalized economic breaches
- Replayable monitoring rules with hash-chained alerts
- Infrastructure/API/frontend posture and non-certifying compliance evidence
- Leased worker jobs, operational endpoints, backup, and production integration policies
- Evidence-grounded copilot with citations, safety controls, and evaluation

The bundled quick scan does not execute project build scripts or tests. Optional dynamic adapters require explicit configuration and must run untrusted project code in an isolated container unless native execution is deliberately enabled.

## Run without installation

```bash
PYTHONPATH=src python3 -m blockchain_auditor audit /path/to/project
PYTHONPATH=src python3 -m blockchain_auditor audit https://github.com/owner/repository
PYTHONPATH=src python3 -m blockchain_auditor audit /path/to/project --config blockchain-auditor.toml --ci
PYTHONPATH=src python3 -m blockchain_auditor serve
```

Open <http://127.0.0.1:8765>. The dashboard binds only to localhost by default. It can launch an audit from a project path accessible to the local process.

See [Getting Started](docs/getting-started.md) for the complete source-only workflow and report-access instructions.

## Install locally

```bash
python3 -m pip install -e .
blockchain-auditor audit /path/to/project
blockchain-auditor serve --output .audit-reports --port 8765
```

## Commands

```text
blockchain-auditor audit PROJECT [--output PATH] [--fail-on high]
blockchain-auditor audit PROJECT [--config PATH] [--profile PROFILE] [--ci]
blockchain-auditor serve [--output PATH] [--host 127.0.0.1] [--port 8765] [--database PATH] [--require-auth]
blockchain-auditor list [--output PATH]
blockchain-auditor compare BASELINE_ID CURRENT_ID [--output PATH]
blockchain-auditor verify AUDIT_ID [--output PATH]
blockchain-auditor capabilities [--json]
blockchain-auditor monitor PROJECT EVENTS [--rules PATH] [--output PATH]
blockchain-auditor backup DATABASE DESTINATION
blockchain-auditor ask AUDIT_ID QUESTION [--json]
blockchain-auditor evaluate-copilot AUDIT_ID DATASET
```

Reports are stored as:

```text
.audit-reports/<project>/<UTC timestamp>_<source hash>/
├── manifest.json
├── findings.json
├── report.html
├── report.json
├── report.sarif
├── report.junit.xml
├── architecture.json
├── assistance.json
├── coverage.json
├── verification.json
├── simulation.json
├── monitoring.json
├── posture.json
├── compliance.json
└── raw/
```

The tool never commits reports or modifies the audited project. Teams may version the report store separately or intentionally commit it to their repository.

The audit command prints the exact `report.html` path. You can open it directly or browse the report store with:

```bash
python3 -m http.server 8080 --directory .audit-reports
```

Then open <http://127.0.0.1:8080>. Reports created through the dashboard are available from its **Reports** section and stored under `.audit-reports/tenants/<tenant>/`.

GitHub URL audits support public repositories on `github.com` over HTTPS. The default branch is shallow-cloned without submodules into a disposable checkout. Reports retain the URL and exact audited commit SHA; the checkout is removed after the run. Private repositories and embedded credentials are not accepted.

## Test

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Phase 2 configuration and execution safety

Copy [blockchain-auditor.example.toml](blockchain-auditor.example.toml) and select `quick`, `solidity`, or `solidity-ci`. Container execution is the default. Each analyzer receives:

- no network
- a read-only project mount
- dropped Linux capabilities
- `no-new-privileges`
- CPU, memory, PID, and timeout limits
- isolated temporary storage

Images are never pulled implicitly. Pull and approve the configured, preferably digest-pinned images before auditing. Native external-tool or project execution requires both:

```toml
execution_mode = "native"
allow_native_execution = true
```

Dynamic Foundry/Hardhat tests must also set `dynamic_tests = true`. Hardhat has no default container image because projects vary materially by Node and dependency version; set a reviewed project-specific image.

Suppressions live in `.blockchain-auditor-suppressions.json` by default:

```json
{
  "suppressions": [
    {
      "rule_id": "solidity-tx-origin",
      "path": "test/fixtures/*.sol",
      "reason": "Deliberately vulnerable training fixture",
      "expires": "2026-12-31"
    }
  ]
}
```

For authenticated manifests, provide a secret only through the environment:

```bash
export BLOCKCHAIN_AUDITOR_SIGNING_KEY='managed-secret-value'
blockchain-auditor audit .
blockchain-auditor verify <audit-id>
```

The secret itself is never written into a report. Without it, manifests still receive a SHA-256 integrity digest but are not authenticated.

## Phase 3 assisted review

Every audit now writes `architecture.json`, `architecture.mmd`, and `assistance.json`. The dashboard exposes architecture and remediation sections. Supported mechanical fixes are displayed as unified-diff proposals with explicit review guardrails; the tool does not apply them.

Review actions require an `auditor` or `admin` role and a note. Review events are append-only and hash chained. See [the Phase 3 design](docs/phase-3.md) and [test report](docs/test-report-phase-3.md).

## Phase 4 service mode

```bash
export BLOCKCHAIN_AUDITOR_BOOTSTRAP_TOKEN='at-least-24-random-characters'
export BLOCKCHAIN_AUDITOR_TENANT_ID='acme'
PYTHONPATH=src python3 -m blockchain_auditor serve --require-auth
```

Audits submitted in the dashboard use a durable queue and tenant-scoped report directory. See [the Phase 4 design](docs/phase-4.md), [CODEX evaluation](docs/codex-evaluation.md), and [Phase 4 test report](docs/test-report-phase-4.md).

## Phase 5 ecosystem plugins

```bash
PYTHONPATH=src python3 -m blockchain_auditor capabilities
PYTHONPATH=src python3 -m blockchain_auditor audit /path/to/project --profile multi-chain
```

Each run writes `coverage.json` so unsupported or unconfigured analysis stages remain visible. See [the Phase 5 design](docs/phase-5.md), [plugin authoring guide](docs/plugin-authoring.md), and [test report](docs/test-report-phase-5.md).

## Phase 6 property assurance

```bash
PYTHONPATH=src python3 -m blockchain_auditor audit /path/to/project --profile assurance
```

Phase 6 writes `verification.json` and can convert SMT counterexamples into release-blocking findings. See [the Phase 6 design](docs/phase-6.md), [example properties](audit-properties.example.toml), [test report](docs/test-report-phase-6.md), and [remaining delivery phases](docs/remaining-phases.md).

## Phases 7–9

```bash
PYTHONPATH=src python3 -m blockchain_auditor audit /path/to/project --profile protocol
PYTHONPATH=src python3 -m blockchain_auditor monitor /path/to/project events.jsonl
```

The audit now emits `simulation.json`, `monitoring.json`, `posture.json`, and `compliance.json`. See [Phase 7](docs/phase-7.md), [Phase 8](docs/phase-8.md), [Phase 9](docs/phase-9.md), and the [combined test report](docs/test-report-phases-7-9.md).

## Phases 10–11

Production operations and the evidence-grounded copilot are documented in [Phase 10](docs/phase-10.md), [Phase 11](docs/phase-11.md), the [production runbook](docs/production-runbook.md), and the [combined test report](docs/test-report-phases-10-11.md).

## Phase roadmap

1. **Local audit core and dashboard** — implemented in this initial slice.
2. **Reproducible analyzers and CI** — implemented: containerized Slither/Semgrep, Foundry/Hardhat adapters, suppressions, configuration, integrity signatures, and CI formats.
3. **Assisted analysis** — implemented: architecture graphs, deterministic explanations, remediation review, and guarded patch suggestions.
4. **Enterprise service foundation** — implemented: persistent queue worker, API authentication, tenancy, audit logging, and a repository-provider boundary.
5. **Expanded ecosystem foundation** — implemented: Rust/Solana, Move, Cairo, and Fabric static-review plugins plus explicit extension states for formal verification, simulation, and monitoring.
6. **Property assurance** — implemented as a conservative Solidity SMT foundation with explicit proof states.
7. **Economic simulation** — implemented as deterministic, version-controlled offline scenarios.
8. **Monitoring** — implemented as provider-neutral rules and replayable, hash-chained alerts.
9. **Full-stack and compliance evidence** — implemented as source/configuration posture and non-certifying mappings.
10. **Production service foundation** — implemented: leases, operational endpoints, backups, integration policies, container, and Compose example; managed infrastructure remains external.
11. **Evidence-grounded copilot** — implemented: cited retrieval, deterministic fallback, safety filters, API/UI/CLI access, and evaluation.

See [requirements traceability](docs/requirements-traceability.md) for limitations and [the current test report](docs/test-report.md) for the latest aggregate verification.
