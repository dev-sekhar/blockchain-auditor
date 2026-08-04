# Phase 5 Test Report

> Historical phase-local result. See the [current aggregate baseline](test-report.md).

Phase 5 tests cover:

- manifest-based Solana detection
- Fabric detection only when Fabric dependencies are present
- duplicate plugin-ID rejection
- Rust/Solana rule normalization
- Move plugin selection and findings
- mixed-language audit integration
- explicit unconfigured formal-verification coverage
- generation of `coverage.json`
- all Phase 1–4 regression behavior

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m blockchain_auditor capabilities --json
node --check src/blockchain_auditor/web/app.js
```

## Latest result

On 2026-08-03, all 22 Phase 1–5 tests passed. Four browser modules passed JavaScript syntax validation, the `multi-chain` CLI smoke audit completed, `coverage.json` was generated, and the timestamped manifest integrity digest verified successfully.
