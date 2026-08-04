# Phase 6: Formal Verification and Property Assurance

> Current in 1.2.0 as a bounded Solidity SMT foundation. See the [instruction guide](../instruction-guide.md) for configuration and [requirements traceability](../requirements-traceability.md) for unsupported proof scope.

Phase 6 adds a conservative property-assurance pipeline for Solidity.

## Features

- version-controlled `audit-properties.toml` specifications
- automatic discovery of Solidity `assert(...)` proof obligations
- isolated Solidity SMTChecker adapter
- normalized outcomes: `proved`, `no_counterexample`, `violated`, `inconclusive`, `unverified`, and `declared_unlinked`
- counterexamples normalized into security findings
- optional CI gate requiring explicit proofs
- `verification.json`, HTML report, capability matrix, and dashboard integration

Use the assurance profile:

```bash
blockchain-auditor audit /path/to/project --profile assurance
```

Container execution requires a reviewed `solc_image` already present locally. Images are never pulled implicitly. Native `solc` requires both `execution_mode = "native"` and `allow_native_execution = true`.

Copy [the example property file](../../audit-properties.example.toml) into a project as `audit-properties.toml` and link SMT assertions to their source file and line. Design invariants without a source assertion are reported as `declared_unlinked`; the tool does not pretend they were verified.

## Interpretation

`proved` is reserved for an explicit verifier proof message. `no_counterexample` means the configured run produced no matching counterexample for that assertion; it is not labeled a mathematical proof. A skipped, failed, or solver-limited run remains visible in the report and capability matrix.

The current verifier covers Solidity assertion obligations only. Move Prover, Cairo proof tooling, Rust property checking, theorem provers, and protocol-level state-machine models remain future work.
