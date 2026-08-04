# Phase 10: Production Service and Integration Boundaries

> Implemented as a production-oriented foundation in 1.2.0. Complete the external gates in the [production runbook](../production-runbook.md) before public or untrusted-tenant exposure.

Phase 10 adds production-oriented operational controls:

- migration-compatible worker leases, ownership, attempts, and renewal
- atomic claim behavior suitable for multiple workers sharing the same database
- health (`/healthz`), readiness (`/readyz`), and Prometheus (`/metrics`) endpoints
- consistent SQLite online backups through `blockchain-auditor backup`
- HTTPS webhook allowlists, dry-run default, and private-target rejection
- remote repository policy requiring allowlisted HTTPS hosts and immutable commit SHAs
- explicit OIDC provider contract that fails closed when not configured
- non-root container image and a restricted Compose deployment example

## Important boundary

This is a production service foundation, not a claim that SQLite is a distributed database. Multi-host deployments should replace SQLite and the in-process worker with managed transactional storage, a durable queue, and isolated worker pools. Version 1.2.0 enables bounded disposable clones for public GitHub repositories only; private credentials, arbitrary hosts, submodules, and other SCM providers remain disabled. OIDC/MFA is not enabled merely by the existence of an adapter.

Create a backup:

```bash
blockchain-auditor backup .audit-reports/service.db backups/service-2026-08-03.db
```

The Compose example requires `BLOCKCHAIN_AUDITOR_BOOTSTRAP_TOKEN`, `BLOCKCHAIN_AUDITOR_TENANT_ID`, and `AUDIT_PROJECTS_PATH`. TLS should terminate at an approved reverse proxy.
