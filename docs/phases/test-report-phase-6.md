# Phase 6 Test Report

> Historical phase-local result. See the [current aggregate baseline](../test-report.md).

Phase 6 tests cover property parsing and validation, duplicate IDs, automatic assertion discovery, counterexample parsing, conservative no-counterexample labeling, skipped-verifier reporting, required-proof CI gates, artifact creation, and all Phase 1–5 regression behavior.

The environment does not currently contain `solc`, `forge`, Move, or Scarb. The real adapter therefore correctly reports `skipped`; parser behavior is verified with representative SMTChecker diagnostics. A reviewed verifier image or explicitly approved native tool is required for an executed proof run.

## Latest result

On 2026-08-03, all 27 Phase 1–6 tests passed and all browser modules passed JavaScript syntax validation. The assurance-profile smoke run generated `verification.json`, reported the unavailable verifier transparently, and preserved a valid timestamped manifest digest.
