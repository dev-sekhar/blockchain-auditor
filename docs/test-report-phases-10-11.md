# Phases 10–11 Test Report

> Phase-local acceptance result. The consolidated current baseline and reproduction commands are maintained in [test-report.md](test-report.md).

Tests cover worker lease ownership and renewal, double-claim prevention, schema migration, consistent backup, webhook and repository SSRF policy, fail-closed OIDC behavior, grounded copilot citations, injection blocking, secret redaction, and evaluation recall. All prior phase regressions run in the same suite.

Final integration verification should exercise health/readiness/metrics, authenticated copilot API access, CLI Q&A, evaluation, backup creation, and the complete test suite.

## Latest result

On 2026-08-03, all 46 Phase 1–11 tests passed. Health and readiness returned success, Prometheus metrics reflected the leased job and tenant, an authenticated audit completed in one attempt, grounded copilot responses cited finding and knowledge artifacts, prompt injection was blocked, unsafe legacy remediation proposals were withheld by runtime validation, the evaluation passed, and a consistent database backup was created.
