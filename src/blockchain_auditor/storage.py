from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def list_runs(output: Path) -> list[dict]:
    runs = []
    if not output.exists():
        return runs
    for manifest in output.glob("*/*/manifest.json"):
        try:
            data = load_json(manifest)
            data["_run_dir"] = str(manifest.parent)
            runs.append(data)
        except (OSError, json.JSONDecodeError):
            continue
    return sorted(runs, key=lambda run: run.get("created_at", ""), reverse=True)


def latest_for_project(output: Path, project_name: str) -> dict | None:
    return next((r for r in list_runs(output) if r.get("source", {}).get("project_name") == project_name), None)
