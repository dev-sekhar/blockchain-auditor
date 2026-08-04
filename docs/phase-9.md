# Phase 9: Full-Stack Security and Compliance Evidence

> Current in 1.2.0 as repository-evidence analysis, not certification. See [requirements traceability](requirements-traceability.md).

Phase 9 reviews repository evidence beyond contracts:

- container images, root execution, and download-to-shell patterns
- Kubernetes privileged and host-network configuration
- CI token permissions and mutable action references
- wildcard CORS
- frontend HTML injection sinks
- unlimited wallet approvals

Results are normalized into findings and `posture.json`.

`compliance.json` maps available evidence to OWASP Smart Contract, SOC 2, ISO 27001, PCI DSS, GDPR, and FATF labels. Controls are `observed`, `gap`, or `not_assessed`. Unknown frameworks are `unsupported`.

This is evidence mapping only. It is not certification, legal advice, or a determination of compliance; organizational processes and runtime evidence remain outside source analysis.
