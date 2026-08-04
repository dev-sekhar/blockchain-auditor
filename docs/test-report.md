# Current Test Report

## Baseline

On 2026-08-03, the full regression suite passed: **47 Python unit/integration tests**. JavaScript modules passed syntax validation.

The integration verification covered health, readiness, Prometheus metrics, authenticated queued auditing, lease ownership, tenant report visibility, GitHub URL policy and source provenance, grounded copilot citations, prompt-injection blocking, secret redaction, unsafe-remediation filtering, evaluation recall, manifest integrity, and consistent SQLite backup.

## Reproduce

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
node --check src/blockchain_auditor/web/app.js
node --check src/blockchain_auditor/web/api.js
node --check src/blockchain_auditor/web/components.js
node --check src/blockchain_auditor/web/state.js
```

Optional analyzer execution depends on locally available or preloaded tools and images. A passing core suite does not prove external analyzer, live RPC, OIDC, webhook, remote repository, model-provider, or production infrastructure configuration.

Historical reports remain available for the feature-specific acceptance evidence from each phase. This document is the current aggregate result.
