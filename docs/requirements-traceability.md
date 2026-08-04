# Requirements Traceability

The root `requirement` file is an enterprise product vision. This matrix records the implemented `1.2.0` boundary without treating a foundation, heuristic, or adapter as a completed external capability.

| Requirement area | Status | Current evidence and boundary |
|---|---|---|
| Project-path audit and detection | Implemented | CLI accepts a local path; language/framework detection and source provenance are recorded. |
| Timestamped, versioned reports | Implemented | Immutable UTC/source-hash directories, manifests, fingerprints, comparison, JSON/HTML/SARIF/JUnit artifacts. |
| Statistics, analysis, traceability UI | Implemented | Local dashboard covers findings, reports, architecture, coverage, remediation, jobs, events, and copilot evidence. |
| Solidity/Vyper analysis | Implemented with configuration | Bundled rules plus optional Slither/Semgrep and isolated project-test adapters. Tool availability remains explicit. |
| Solana, Move, Cairo, Fabric | Foundation | Deterministic detection and heuristic plugins; ecosystem-native dynamic/formal tooling is not configured. |
| Formal verification | Partial | Solidity assertions and SMTChecker adapter with conservative outcomes; broader language/protocol proving is pending. |
| Economic simulation | Foundation | Deterministic offline scenarios; no live liquidity, mempool, bytecode, or fork execution. |
| Continuous monitoring | Foundation | Rule validation and replayable JSONL alerts; no live RPC/explorer ingestion. |
| Full-stack and compliance | Implemented as evidence mapping | Source/configuration posture and control mapping; not certification or legal advice. |
| AI explanations and fixes | Implemented with guardrails | Deterministic assistance and evidence-grounded copilot; cited, read-only proposals; no external model configured. |
| Authentication, RBAC, tenancy | Service foundation | Hashed bearer tokens, roles, tenant scoping, audit events; OIDC/MFA contract fails closed until configured. |
| Job processing | Service foundation | Durable SQLite queue and leased workers; managed database/queue and isolated pools are required for multi-host scale. |
| Repository integrations | Public GitHub implemented | Local paths and public HTTPS GitHub default-branch clones work with captured commit provenance and limits. Private credentials and other SCM providers are disabled. |
| Notifications/integrations | Partial | In-app alerts and safe webhook policy/dry run; email, SMS, Jira, Slack, SIEM, and hosted SCM require providers. |
| Production operations | Foundation | Health, readiness, metrics, backup, container and Compose examples; TLS, secrets, restore drills, load tests, and ownership are external. |
| Licensing, billing, enterprise administration | Not implemented | Requires product, legal, identity, payment, and organizational decisions outside the current local tool. |

## Acceptance baseline

The minimum requested workflow is complete when a caller can run `blockchain-auditor audit PROJECT`, receive a timestamped report directory, verify its manifest, compare finding fingerprints across runs, and inspect statistics and issue evidence in the dashboard. The automated regression suite and current integration evidence are recorded in [test-report.md](test-report.md).

Items marked foundation, partial, or not implemented must not be marketed as completed enterprise functions. See [remaining-phases.md](remaining-phases.md) for the external work needed before public multi-tenant production use.
