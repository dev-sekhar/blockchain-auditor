# Phase 3 Test Report

> Historical phase-local result. See the [current aggregate baseline](test-report.md).

## Automated coverage

The Phase 3 suite covers:

- Solidity contract, inheritance, trust-boundary, and upgrade-signal extraction
- Mermaid graph generation
- Finding explanation and guarded patch generation
- Manifest integrity after assisted-analysis metadata is added
- Required remediation notes and controlled statuses
- Hash chaining of remediation review events
- RBAC denial for viewer mutations
- Phase 1 and Phase 2 regression behavior

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
node --check src/blockchain_auditor/web/app.js
node --check src/blockchain_auditor/web/api.js
node --check src/blockchain_auditor/web/components.js
```

The CI workflow executes the Python audit. A later UI toolchain can add browser-level accessibility and end-to-end tests; the current zero-dependency UI is syntax-checked and its API is integration-tested locally.

## Latest result

On 2026-08-03, all 12 Python unit/integration tests passed. JavaScript syntax checks passed for the state, API, components, and application modules. A localhost integration run confirmed:

- assisted audit creation returned HTTP 201
- architecture output contained two contracts and the expected trust indicators
- an auditor remediation review was recorded
- a viewer remediation mutation was denied with `AUDIT-AUTH-403`

CI installs the development extra and enforces 70% coverage across the Phase 3 backend and API packages.
