# Phase 7: Economic and DeFi Simulation

> Current in 1.2.0 as deterministic offline scenario analysis; it does not claim fork-based or live-market execution. See the [instruction guide](../instruction-guide.md).

Phase 7 adds deterministic, version-controlled offline scenario models:

- constant-product AMM swap and price-impact analysis
- collateral/oracle shock health-factor analysis
- governance voting-concentration analysis
- bridge validator-quorum compromise analysis

Scenarios live in `audit-scenarios.toml`; copy [the example](../../audit-scenarios.example.toml). Use the protocol profile:

```bash
blockchain-auditor audit /path/to/project --profile protocol
```

Threshold breaches become normalized findings and all inputs, assumptions, metrics, and limitations are written to `simulation.json`.

These models do not execute bytecode, reproduce mempool behavior, or query live liquidity. A scenario result must be reproduced against an isolated fork before it is treated as an exploit demonstration.
