# Phase 4: Persistent Multi-Tenant Service Foundation

> Historical design note. Phase 10 later added leased jobs, operational endpoints, backups, and production policies. SQLite/in-process workers remain a single-host foundation; see the [production runbook](../production-runbook.md).

Phase 4 turns the local dashboard into a persistent queued service while retaining local development mode.

## Capabilities

- SQLite schema and automatic idempotent migration
- tenant and API-token records; only SHA-256 token digests are stored
- bearer authentication in `--require-auth` mode
- tenant-scoped job, report, and event queries
- durable queued/running/completed/failed job lifecycle
- background audit worker that automatically re-queues interrupted `running` jobs after restart
- hash-chained operational audit events
- local repository provider interface
- queued-job and operational-event dashboard

Start authenticated mode:

```bash
export BLOCKCHAIN_AUDITOR_BOOTSTRAP_TOKEN='replace-with-at-least-24-random-characters'
export BLOCKCHAIN_AUDITOR_TENANT_ID='acme'
export BLOCKCHAIN_AUDITOR_TENANT_NAME='Acme Protocol'
PYTHONPATH=src python3 -m blockchain_auditor serve --require-auth
```

The bootstrap token is hashed before storage. Enter the original token in the dashboard session field; it is kept in browser session storage, not persistent local storage.

## Security boundary

SQLite and the in-process worker are appropriate for the initial service foundation, not 100 concurrent distributed jobs. Production scale should replace the claim operation with a managed queue/database and run workers in isolated infrastructure. TLS must terminate in a trusted reverse proxy. Remote Git providers are represented by a provider interface but are intentionally rejected until credential, host allowlist, and clone-isolation policies are defined.
