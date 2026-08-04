# Phase 5: Ecosystem Plugin Foundation

> Historical design note. Later phases add bounded Solidity verification, offline simulation, event replay, and posture analysis. Non-EVM plugins still provide heuristic static review rather than those ecosystem-native assurance capabilities.

Phase 5 expands audits beyond Solidity through trusted in-process ecosystem plugins and explicit coverage reporting.

## Built-in plugins

| Plugin | Detection | Current analysis |
|---|---|---|
| `rust-solana` | Rust source; Solana/Anchor dependencies refine chain identification | unsafe blocks, panic-prone unwraps, signed cross-program invocations |
| `move` | Move source with Aptos/Sui manifest refinement | friend boundaries, friend-visible functions, mutable vector access |
| `cairo-starknet` | Cairo source or Scarb project | library calls, caller-address trust boundaries, unwrap reverts |
| `hyperledger-fabric` | Go/Java plus an explicit Fabric dependency | panic paths, nondeterministic randomness, peer-local system time |
| `evm-core` | Solidity/Vyper | existing built-in, Slither, Semgrep, architecture, and optional project-test pipeline |

All new plugin rules are heuristic review signals. They do not establish exploitability or prove that unreported vulnerabilities are absent.

## Capability transparency

Every report contains `coverage.json` and an ecosystem-coverage section. Each detected plugin reports separate states for:

- static analysis
- dynamic testing
- formal verification
- economic simulation
- continuous monitoring

The new plugins mark static analysis as `heuristic`; other capabilities are `not_configured`. This is deliberate. Phase 5 does not claim that pattern matching constitutes formal verification, economic simulation, or runtime monitoring.

Inspect available plugins:

```bash
blockchain-auditor capabilities
blockchain-auditor capabilities --json
```

Audit a mixed-language project:

```bash
blockchain-auditor audit /path/to/project --profile multi-chain
```

## Plugin trust model

Plugins execute inside the auditor process and are therefore trusted code. The registry currently loads built-ins explicitly; it does not discover arbitrary packages automatically. A production plugin marketplace needs signature verification, compatibility metadata, permission declarations, and isolated execution before third-party discovery is enabled.

See [plugin authoring](plugin-authoring.md) for the internal extension contract.
