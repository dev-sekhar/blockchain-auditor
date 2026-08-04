# CODEX.md Applicability Evaluation

This matrix distinguishes architectural rules that apply to version 1.2.0 from organizational or infrastructure activities that cannot be executed solely in this workspace. It is the decision record for which `CODEX.md` instructions must be executed, adapted, deferred, or skipped.

## Execute now

| Guideline | Decision and implementation |
|---|---|
| Separation of concerns | Required. Python modules are separated into `backend`, `api`, `db`, and `services`; browser code separates API, state, components, and feature rendering. |
| Reusability | Required. Analyzer adapters, repository providers, alerts, authentication, database queries, and UI components expose reusable boundaries. |
| Centralized errors | Required. API failures use `ApiError` with stable codes and the server has a single error response path. |
| Notifications and alerts | Required at the applicable local level. Server alerts go through `AlertService`; user messages use the reusable accessible notification component. |
| RBAC and least privilege | Required. Roles and permissions have one source of truth and APIs enforce them. Phase 4 binds roles to hashed bearer tokens. |
| Scalability/modularity | Required. Audit jobs persist in SQLite and execute through a worker boundary that can later be replaced by distributed workers. |
| Unit and integration tests | Required. The aggregate Phase 1–11 suite covers core audits, service boundaries, assurance modules, operations, and copilot safety. |
| Test reports and coverage | Required. Phase reports and the current aggregate report live in `docs`; CI enforces its configured coverage gate. |
| Feature documentation | Required. Each phase has design and test documentation under `docs`. |
| Accessible UI | Required. Navigation and form controls use semantic elements, labels, ARIA live status, and keyboard-operable native controls. |
| Centralized state | Required in proportion to the UI. A small shared ES module is used instead of adding Redux to a zero-dependency application. |

## Adapt rather than execute literally

| Guideline | Adaptation |
|---|---|
| Root `/ui`, `/backend`, `/api`, `/db`, `/services` directories | The same boundaries live below `src/blockchain_auditor/`, which is the conventional installable Python package root. Moving them to repository-root import packages would make packaging less coherent without improving separation. Documentation and tests remain at repository root as prescribed. |
| Redux/Vuex examples | These are examples, not mandatory frameworks. The UI uses `state.js`; adding a framework would violate the current zero-dependency constraint and is not justified by its state complexity. |
| Admin/User/Guest role examples | Adapted to the SRS roles currently exercised by the tool: `admin`, `auditor`, and `viewer`. More enterprise roles can be added to the same permission map. |
| Notifications by email/SMS/in-app | The unified boundary and in-app channel are implemented. Email and SMS transports require providers, credentials, retention policy, and user consent, so they remain provider plugins. |
| Automated deployment pipeline | Build/test/audit CI plus container and Compose foundations are implemented. Automated release/deployment remains deferred until a target, registry, secret model, and release authority are defined. |

## Defer until external process or infrastructure exists

| Guideline | Reason |
|---|---|
| Feature branches and conventional commits | This workspace is not a Git repository. Initializing a repository or committing was not requested. The naming/conventional-commit policy should be applied once version control exists. |
| Pull-request review and test-report gate | Requires a hosted Git repository, branch protection, reviewers, and organizational policy. The test report and CI building blocks are present. |
| Email/SMS delivery | Requires approved providers and secrets plus operational and privacy decisions. |
| Production deployment automation | Requires a selected environment, artifact registry, network model, secret manager, and approval process. The supplied deployment files are examples, not evidence of a live deployment. |
| Browser end-to-end suite | The UI currently has no package/toolchain dependency. Add Playwright or an equivalent when browser dependency installation is authorized; API workflows are integration-tested meanwhile. |

## Skip for the current product stage

No architectural or security principle is skipped. Illustrative technology choices that do not fit the stack—such as Redux specifically—are non-binding examples and use smaller equivalents. Organizational actions are deferred, not falsely marked complete. See the [instruction guide](instruction-guide.md) and [requirements traceability](requirements-traceability.md).
