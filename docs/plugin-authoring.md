# Ecosystem Plugin Authoring

This is an internal trusted-extension contract for version 1.2.0. Read the [instruction guide](instruction-guide.md) for operator configuration and [requirements traceability](requirements-traceability.md) before describing plugin coverage.

An ecosystem plugin implements the contract in `plugins/contracts.py`:

- globally unique `plugin_id`
- version, languages, and ecosystem identifiers
- explicit capability states
- `matches(project)` for deterministic selection
- `analyze(root)` returning normalized `Finding` objects
- `coverage(detected)` describing assurance and limitations

Register a trusted plugin explicitly:

```python
from blockchain_auditor.plugins.registry import PluginRegistry

registry = PluginRegistry()
registry.register(my_reviewed_plugin)
results, coverage = registry.run(project_root, detected_project)
```

Rules must use stable IDs, source-relative locations, clear evidence, calibrated severity/confidence, and actionable remediation. A plugin must not label a capability implemented unless it actually executes and records that capability. Errors should return a failed plugin result without preventing other compatible plugins from completing.

Third-party automatic discovery is intentionally unavailable because plugins currently share the auditor process and filesystem permissions.

Add unit tests, a phase or feature note, capability limitations, and an update to the current test report for every plugin change, as required by `CODEX.md`.
