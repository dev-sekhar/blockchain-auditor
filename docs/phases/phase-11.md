# Phase 11: Evidence-Grounded Auditor Copilot

> Implemented in 1.2.0 with deterministic fallback and no external model by default. See the [instruction guide](../instruction-guide.md) for use and safety boundaries.

Phase 11 adds a provider-neutral, citation-first copilot:

- retrieval over findings, architecture, verification, simulation, monitoring, and compliance artifacts
- a small bundled security knowledge collection
- deterministic answers when no model provider is configured
- stable citations containing artifact and pointer
- prompt-injection detection
- secret redaction on provider output
- guarded read-only remediation proposals
- evaluation datasets measuring expected-finding recall and grounding
- API and dashboard interaction with privacy-preserving query hashes in the operational audit log

Ask from the CLI:

```bash
blockchain-auditor ask AUDIT_ID "Explain the highest access-control risk" --output .audit-reports
```

Evaluate retrieval:

```bash
blockchain-auditor evaluate-copilot AUDIT_ID evaluation.json --output .audit-reports
```

No external model is configured by default. The deterministic mode does not pretend to be a generative model. A future model implementation must preserve citations, enforce tenant boundaries, redact secrets, define retention, and pass the evaluation gate before use.
