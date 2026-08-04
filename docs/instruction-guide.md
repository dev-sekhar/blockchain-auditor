# Blockchain Auditor Instruction Guide

This guide covers the supported `1.2.0` workflow: provide a local project path or public GitHub repository URL, run an audit, inspect the dashboard, trace issues, and retain timestamped reports. Commands assume Python 3.11 or newer and are run from this repository.

For the shortest end-to-end setup, including exact report-access steps, start with [Getting Started](getting-started.md).

## 1. Install or run from source

Run without installing:

```bash
PYTHONPATH=src python3 -m blockchain_auditor --version
```

Or install an editable command:

```bash
python3 -m pip install -e .
blockchain-auditor --version
```

The examples below use `blockchain-auditor`. Replace it with `PYTHONPATH=src python3 -m blockchain_auditor` when running directly from source.

## 2. Run an audit

```bash
blockchain-auditor audit /absolute/path/to/project
blockchain-auditor audit https://github.com/owner/repository
```

The default report store is `.audit-reports`. Each run is immutable and stored under a project directory using a UTC timestamp and source hash:

```text
.audit-reports/<project>/<UTC timestamp>_<source hash>/
```

The auditor reads project source and metadata. It does not modify the target project or commit reports. Optional analyzers and project tests only run under the execution policy described below.

Public GitHub URLs must use `https://github.com/owner/repository` (an optional `.git` suffix is accepted). The auditor performs a shallow clone of the default branch without tags or submodules, disables prompts and Git LFS smudging, rejects symbolic links, enforces a 120-second clone timeout and checkout limits of 50,000 files/250 MiB, records the exact resulting commit SHA, and deletes the temporary checkout after reporting. Private repositories, embedded credentials, alternate hosts, URL query strings, and fragments are rejected.

### Profiles

| Profile | Intended use |
|---|---|
| `quick` | Built-in static checks with minimal dependencies |
| `solidity` | Solidity analyzers where configured |
| `solidity-ci` | Solidity analysis and CI-oriented gates |
| `multi-chain` | EVM, Rust/Solana, Move, Cairo/Starknet, and Fabric plugin planning |
| `assurance` | Solidity property discovery and SMT verification adapter |
| `protocol` | Assurance plus economic scenarios, monitoring plan, posture, and compliance evidence |

```bash
blockchain-auditor audit ./protocol --profile protocol
blockchain-auditor audit ./protocol --config blockchain-auditor.toml --ci --fail-on high
```

Copy `blockchain-auditor.example.toml` before customizing execution, images, limits, suppressions, or CI gates. Use `blockchain-auditor capabilities --json` to inspect ecosystem coverage.

### External analyzers and untrusted code

Container execution is the default for external analyzers. Images are never pulled implicitly. Preload reviewed, preferably digest-pinned images. Analyzer containers use a read-only project mount, no network, dropped capabilities, `no-new-privileges`, resource limits, and temporary storage.

Native execution requires both:

```toml
execution_mode = "native"
allow_native_execution = true
```

Foundry or Hardhat execution also requires `dynamic_tests = true`. A missing executable or image is recorded as skipped/unconfigured; it is not reported as successful analysis. Use `--no-optional-engines` when only bundled checks should run.

## 3. Inspect reports and issue traceability

```bash
blockchain-auditor list
blockchain-auditor verify AUDIT_ID
blockchain-auditor compare BASELINE_ID CURRENT_ID
```

Stable finding fingerprints connect the same issue across audits. Comparison classifies findings as new, existing, or resolved. Each report directory can contain:

| Artifact | Purpose |
|---|---|
| `manifest.json` | Source provenance, configuration, artifact hashes, and optional signature |
| `findings.json` | Normalized issues, fingerprints, evidence, severity, and location |
| `report.html`, `report.json` | Human- and machine-readable audit reports |
| `report.sarif`, `report.junit.xml` | CI and code-scanning integrations |
| `architecture.json`, `architecture.mmd` | Solidity structure and trust-boundary evidence |
| `assistance.json` | Explanations and guarded remediation proposals |
| `coverage.json` | Per-ecosystem capability states and limitations |
| `verification.json` | Property and verifier outcomes |
| `simulation.json` | Economic scenario inputs, assumptions, and breaches |
| `monitoring.json` | Configured monitoring plan |
| `posture.json`, `compliance.json` | Full-stack signals and non-certifying control mapping |
| `raw/` | Captured analyzer output |

Set `BLOCKCHAIN_AUDITOR_SIGNING_KEY` before an audit to authenticate its manifest with HMAC. Without it, the manifest still has a SHA-256 integrity digest. Keep the signing key in a secret manager; never put it in TOML or reports.

Suppressions belong in `.blockchain-auditor-suppressions.json`, require a reason, and should expire. Suppressed findings remain traceable. Remediation diffs are proposals only: review them against the exact source and run project tests before applying. The tool deliberately withholds unsafe or tautological legacy proposals.

## 4. Use the dashboard

```bash
blockchain-auditor serve --output .audit-reports --host 127.0.0.1 --port 8765
```

Open <http://127.0.0.1:8765>. The UI shows audit statistics, findings, architecture, analysis coverage, remediation history, jobs, operational events, reports, and grounded copilot answers. Local mode should remain bound to loopback because user-supplied identity headers are a policy aid, not authentication.

For authenticated service mode:

```bash
export BLOCKCHAIN_AUDITOR_BOOTSTRAP_TOKEN='replace-with-at-least-24-random-characters'
export BLOCKCHAIN_AUDITOR_TENANT_ID='acme'
export BLOCKCHAIN_AUDITOR_TENANT_NAME='Acme Protocol'
blockchain-auditor serve --require-auth --database .audit-reports/service.db
```

Enter the bootstrap token in the dashboard session field or send it as `Authorization: Bearer <token>`. Tokens are stored as hashes server-side. Tenant report stores, queued jobs, and operational events are isolated by tenant. Roles are `admin`, `auditor`, and `viewer`; mutations require the applicable permission.

## 5. Assurance, simulation, and monitoring

Copy `audit-properties.example.toml` to the target as `audit-properties.toml`, then run the `assurance` profile. `proved` requires an explicit proof result; `no_counterexample` is not represented as a proof. Unavailable or bounded tooling remains visible.

Copy `audit-scenarios.example.toml` to `audit-scenarios.toml` and use `protocol` for deterministic AMM, oracle/collateral, governance, and bridge scenarios. These offline models are not fork-based exploit demonstrations.

Replay monitoring evidence with:

```bash
blockchain-auditor monitor ./protocol monitoring-events.example.jsonl --rules monitoring.example.toml
```

Replay output is timestamped under `.audit-reports/monitoring/` with stable, hash-chained alert IDs. Events are caller-supplied; no live RPC or explorer provider is configured.

## 6. Use the evidence-grounded copilot

```bash
blockchain-auditor ask AUDIT_ID "Explain the highest access-control risk"
blockchain-auditor ask AUDIT_ID "What evidence supports this?" --json
blockchain-auditor evaluate-copilot AUDIT_ID copilot-evaluation.example.json
```

The default deterministic mode retrieves report and bundled knowledge evidence and cites artifact pointers. Prompt-injection-like queries are rejected, provider output is secret-redacted, and remediation stays read-only. No external model is configured by default. Any future provider must preserve tenant boundaries, citations, retention policy, redaction, and evaluation gates.

## 7. CI and exit behavior

```bash
blockchain-auditor audit . --profile solidity-ci --ci --fail-on high
```

`--ci` emits GitHub-compatible annotations. `--fail-on` returns a failing process status when an active finding meets or exceeds the selected severity. Verification proof gates can add failures when configured. Archive the entire timestamped directory so its manifest continues to cover the referenced artifacts.

The repository workflow in `.github/workflows/audit.yml` is a starting point; adapt paths, analyzer images, permissions, and artifact retention to the hosting organization.

## 8. Operate and back up the service

Operational endpoints are:

- `GET /healthz` for liveness
- `GET /readyz` for readiness
- `GET /metrics` for Prometheus text metrics

Create a consistent SQLite snapshot:

```bash
blockchain-auditor backup .audit-reports/service.db backups/service-2026-08-03.db
```

Restore only into a stopped, separate validation environment first; verify tenant records, jobs, events, and report object availability before cutover. The supplied `Dockerfile` and `deploy/docker-compose.production.yml` are deployment foundations. Compose requires `BLOCKCHAIN_AUDITOR_BOOTSTRAP_TOKEN`, `BLOCKCHAIN_AUDITOR_TENANT_ID`, and `AUDIT_PROJECTS_PATH`. Follow the production runbook before exposing a service.

## 9. Troubleshooting and security boundaries

- Run `blockchain-auditor COMMAND --help` for the authoritative local options.
- A skipped analyzer normally means its executable or pre-approved image is absent; inspect `coverage.json`, `verification.json`, and `raw/`.
- A readiness failure indicates a service dependency or database problem; check service logs and `/metrics`.
- A manifest verification failure means an artifact, configuration record, or signature no longer matches. Preserve the directory and investigate instead of regenerating in place.
- Authentication failures use centralized API error codes. Confirm bearer token length, tenant bootstrap settings, and role permissions without logging secrets.
- Do not expose the development server directly to untrusted networks. Production needs TLS ingress, network policy, managed secrets, retention, monitoring, and tested recovery.
- SQLite plus in-process workers is not a multi-host distributed architecture. Public GitHub cloning is enabled with strict limits; private repository credentials and other providers remain unconfigured. OIDC/MFA, outbound integrations, live chain monitoring, and an external AI model remain fail-closed, dry-run, or unconfigured until an operator supplies approved infrastructure.

## 10. Validate this repository

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
node --check src/blockchain_auditor/web/app.js
node --check src/blockchain_auditor/web/api.js
node --check src/blockchain_auditor/web/components.js
node --check src/blockchain_auditor/web/state.js
```

See the [current test report](test-report.md), [requirements traceability](requirements-traceability.md), and [CODEX applicability evaluation](codex-evaluation.md) for the exact assurance boundary.
