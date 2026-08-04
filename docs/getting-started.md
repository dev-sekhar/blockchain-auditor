# Getting Started

This guide takes you from a fresh checkout to an audit report. Blockchain Auditor requires Python 3.11 or newer. Git is also required when the audit target is a public GitHub repository.

## Download the project

The current development branch is `dev`:

```bash
git clone --branch dev https://github.com/dev-sekhar/blockchain-auditor.git
cd blockchain-auditor
```

## Option A: run without installation

Set `PYTHONPATH=src` for each command. Audit a local project:

```bash
PYTHONPATH=src python3 -m blockchain_auditor audit /absolute/path/to/project
```

Or audit the default branch of a public GitHub repository:

```bash
PYTHONPATH=src python3 -m blockchain_auditor audit https://github.com/owner/repository
```

To run only the bundled analyzer and avoid optional external tools:

```bash
PYTHONPATH=src python3 -m blockchain_auditor audit https://github.com/owner/repository --no-optional-engines
```

## Option B: install the command locally

An isolated virtual environment is recommended:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
blockchain-auditor --version
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

Then audit a local path or public GitHub repository:

```bash
blockchain-auditor audit /absolute/path/to/project
blockchain-auditor audit https://github.com/owner/repository
```

The command prints the audit ID, finding count, and exact HTML report path when it completes.

## Access a command-line audit report

Reports use this structure by default:

```text
.audit-reports/<project>/<UTC timestamp>_<commit-or-source-hash>/
```

List stored audit IDs:

```bash
blockchain-auditor list
```

Without installation, use:

```bash
PYTHONPATH=src python3 -m blockchain_auditor list
```

Open the `report.html` path printed by the audit command in a browser. For example, serve the report store locally:

```bash
python3 -m http.server 8080 --directory .audit-reports
```

Then open <http://127.0.0.1:8080>, select the project and timestamped run, and open `report.html`. Stop the temporary server with `Ctrl+C`.

Other useful artifacts in the same directory include:

- `findings.json` for normalized issue data and fingerprints
- `manifest.json` for source, commit, configuration, and integrity provenance
- `report.json` for the complete machine-readable report
- `report.sarif` and `report.junit.xml` for CI integrations
- `architecture.json`, `verification.json`, `simulation.json`, `monitoring.json`, `posture.json`, and `compliance.json` for specialized evidence

Verify that a stored report has not changed:

```bash
blockchain-auditor verify AUDIT_ID
```

Compare issue traceability between two audits:

```bash
blockchain-auditor compare BASELINE_AUDIT_ID CURRENT_AUDIT_ID
```

Pass `--output /another/report/store` to `audit`, `list`, `verify`, and `compare` when using a non-default report directory.

## Run audits and access reports through the dashboard

Without installation:

```bash
PYTHONPATH=src python3 -m blockchain_auditor serve
```

After installation:

```bash
blockchain-auditor serve
```

Open <http://127.0.0.1:8765>. Paste a local project path or public GitHub URL into the source field and select **Queue audit**. The **Jobs** section shows progress. When the job completes, select the audit from the top menu and use:

- **Overview** for statistics and analyzer status
- **Findings** for issue evidence and severity
- **Reports** to view or download generated artifacts
- **Architecture**, **Verification**, **Simulation**, **Monitoring**, and **Posture** for specialized analysis
- **Remediation** for guarded suggestions and review history

Dashboard-created reports are tenant-scoped. In local mode they are stored beneath:

```text
.audit-reports/tenants/local/<project>/<timestamp>_<hash>/
```

The dashboard is the simplest way to browse dashboard-created reports. A report created directly by the `audit` CLI is stored in `.audit-reports/<project>/...`; open its printed HTML path or use the temporary report server described above.

## Authenticated dashboard mode

For a locally authenticated service:

```bash
export BLOCKCHAIN_AUDITOR_BOOTSTRAP_TOKEN='replace-with-at-least-24-random-characters'
export BLOCKCHAIN_AUDITOR_TENANT_ID='acme'
export BLOCKCHAIN_AUDITOR_TENANT_NAME='Acme Protocol'
blockchain-auditor serve --require-auth --database .audit-reports/service.db
```

Open <http://127.0.0.1:8765> and enter the bootstrap token in the session field. Reports are stored beneath `.audit-reports/tenants/acme/`. Do not expose this development server directly to an untrusted network; follow the [production runbook](production-runbook.md) for deployment controls.

## Common problems

- `No module named blockchain_auditor`: run from the repository root with `PYTHONPATH=src`, or install with `python3 -m pip install -e .`.
- `Git is required`: install Git and ensure `git --version` succeeds.
- GitHub clone failure: confirm the repository is public and the URL is exactly `https://github.com/owner/repository`.
- Optional analyzer is skipped: preload its reviewed container image or install/configure the native tool explicitly. The bundled audit still runs.
- Port 8765 is occupied: add `--port 8766` and open <http://127.0.0.1:8766>.
- No report appears in the dashboard: confirm the audit was queued from that dashboard and tenant. Direct CLI reports are stored outside the tenant-scoped dashboard directory.

For profiles, CI gates, suppressions, signing, monitoring, copilot, backups, and security boundaries, continue to the [complete instruction guide](instruction-guide.md).
