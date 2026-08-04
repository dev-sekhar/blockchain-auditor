# Phase 3: Assisted Analysis and Remediation

> Historical design note. This capability remains active in 1.2.0; authenticated tenancy arrived in Phase 4 and evidence-grounded Q&A in Phase 11. See the [instruction guide](instruction-guide.md) for current operation.

## Scope

Phase 3 adds deterministic assistance around analyzer findings while preserving a human approval boundary. It implements the separation-of-concerns, RBAC, centralized-error, reusable-UI, testing, and documentation guidance in `CODEX.md`.

## Modules

- `backend/architecture.py` extracts Solidity contracts, inheritance, source-level calls, entry points, privileged operations, and upgrade indicators.
- `backend/assistance.py` correlates findings with explanations, exploit scenarios, recommendations, and guarded patch proposals.
- `backend/reviews.py` maintains remediation state and an append-only hash-chained event log.
- `api/controllers.py` validates API operations and delegates business logic.
- `api/errors.py` provides stable user-facing error codes.
- `api/rbac.py` defines roles and permissions in one source of truth.
- `services/alerts.py` provides the unified alert interface used by API errors.
- `web/api.js`, `web/state.js`, and `web/components.js` separate transport, state, and reusable presentation behavior.

## Guarded patch workflow

Patch output is a proposal, never an automatic source mutation:

1. A deterministic rule locates a supported source pattern.
2. The assistant generates a unified diff and records its rationale and confidence.
3. The dashboard displays the proposal alongside explicit guardrails.
4. An auditor records a review decision and mandatory note.
5. Applying code remains a separate, human-authorized future operation.

Only the `tx.origin` rule currently produces a mechanical proposal. Findings for which intent cannot be established safely require manual remediation.

## RBAC boundary

Roles are `admin`, `auditor`, and `viewer`. Viewers may read audits. Auditors and admins may run audits and write reviews. The local server reads `X-Audit-Role` and `X-Audit-Actor` headers.

This is an authorization-policy boundary, not an authentication system. Because the dashboard remains localhost-only and users can supply headers, it must not be exposed to untrusted networks. Phase 4 must bind roles to authenticated identities.

## Accuracy limitations

Architecture extraction is source-level and heuristic. It does not replace compiler AST, Slither call graphs, runtime traces, or formal verification. Assisted explanations are deterministic templates tied to rules and explicitly state that no generative model was used.
