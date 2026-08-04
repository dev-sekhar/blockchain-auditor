# Phase 8: Monitoring and Blockchain Intelligence Foundation

> Current in 1.2.0 as rule configuration and evidence replay; live chain providers remain unconfigured. See the [instruction guide](../instruction-guide.md).

Phase 8 implements provider-neutral monitoring rules and deterministic JSONL replay for:

- contract implementation upgrades
- large treasury transfers
- governance executions
- stale oracle updates

Rules live in `monitoring.toml`; see [the example](../../monitoring.example.toml). Replay captured events with:

```bash
blockchain-auditor monitor /path/to/project events.jsonl
```

Runs are timestamped beneath `.audit-reports/monitoring/`. Alerts contain stable IDs and a hash chain for traceability.

JSONL input is caller-supplied evidence. Live RPC and block-explorer providers remain `not_configured`; Phase 8 does not independently establish that replay events occurred on-chain.
