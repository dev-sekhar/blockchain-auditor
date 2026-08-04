from __future__ import annotations

import fnmatch
import json
from datetime import date
from pathlib import Path

from .models import Finding


def load_suppressions(project: Path, value: str) -> list[dict]:
    path = Path(value)
    if not path.is_absolute():
        path = project / path
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid suppression file {path}: {exc}") from exc
    items = data.get("suppressions", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("Suppressions must be a JSON array or a 'suppressions' array")
    for item in items:
        if not isinstance(item, dict) or not item.get("reason"):
            raise ValueError("Every suppression must be an object with a non-empty reason")
        if not item.get("id") and not item.get("rule_id"):
            raise ValueError("Every suppression must specify id or rule_id")
    return items


def apply_suppressions(findings: list[Finding], suppressions: list[dict]) -> dict:
    applied, expired = [], []
    today = date.today()
    for finding in findings:
        location = finding.locations[0].file if finding.locations else ""
        for item in suppressions:
            expiry = item.get("expires")
            if expiry:
                try:
                    if date.fromisoformat(expiry) < today:
                        expired.append(item)
                        continue
                except ValueError as exc:
                    raise ValueError(f"Invalid suppression expiry: {expiry}") from exc
            matches_id = item.get("id") == finding.id if item.get("id") else item.get("rule_id") == finding.rule_id
            matches_path = not item.get("path") or fnmatch.fnmatch(location, item["path"])
            if matches_id and matches_path:
                finding.status = "suppressed"
                applied.append({"finding_id": finding.id, "reason": item["reason"], "expires": expiry})
                break
    return {"applied": applied, "expired": expired}
