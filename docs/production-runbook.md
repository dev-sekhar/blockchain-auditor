# Production Runbook

This runbook supplements the [instruction guide](instruction-guide.md). The Docker and Compose files are a deployment foundation, not authorization to expose the development server publicly.

## Pre-deployment gates

- Replace SQLite/in-process workers for multi-host scale.
- Configure TLS, OIDC/MFA, vault-backed secrets, backups, retention, and restore drills.
- Pin the application base image and every analyzer image to reviewed digests.
- Mount customer source read-only and keep analyzer containers network-disabled.
- Restrict `/metrics` and service administration endpoints at the network layer.
- Configure outbound hosts explicitly; webhook delivery is dry-run by default.
- Run unit, coverage, audit, load, restore, and tenant-isolation tests.

## Health

- Liveness: `GET /healthz`
- Readiness: `GET /readyz`
- Metrics: `GET /metrics`

## Backup and restore

Use `blockchain-auditor backup DATABASE DESTINATION` for a consistent SQLite snapshot. Validate restore into a stopped, separate environment before replacing any database. Managed deployments should use provider-native point-in-time recovery and periodically test full report-object restoration.

Record the backup timestamp, source database identity, destination checksum, restore-test result, report-object reconciliation, operator, and approval. A database-only backup is incomplete if the report store is not preserved.

## Incident response

Revoke affected API tokens, isolate workers, preserve hash-chained event logs and report manifests, rotate secrets, inspect outbound delivery records, and rebuild from reviewed artifacts.

## Release evidence

Before each release, attach the [current test report](test-report.md), dependency and image digests, configuration review, migration/rollback plan, recovery result, and approval record. OIDC, remote repositories, webhooks, and model providers must remain disabled or dry-run unless their own threat model and retention policy are approved.
