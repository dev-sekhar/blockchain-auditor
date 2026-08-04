from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from ..storage import load_json, write_json


REVIEW_STATUSES = {"open", "acknowledged", "false_positive", "remediation_planned", "resolved"}


def review_path(run_dir: Path) -> Path:
    return run_dir / "reviews.json"


def load_reviews(run_dir: Path) -> dict:
    path = review_path(run_dir)
    return load_json(path) if path.exists() else {"schema_version": "1.0", "findings": {}, "events": []}


def update_review(run_dir: Path, finding_id: str, status: str, note: str, actor: str, role: str) -> dict:
    if status not in REVIEW_STATUSES:
        raise ValueError(f"Invalid review status: {status}")
    if not note.strip():
        raise ValueError("A review note is required")
    manifest = load_json(run_dir / "manifest.json")
    if finding_id not in {item["id"] for item in manifest.get("findings", [])}:
        raise ValueError("Finding does not exist in this audit")
    reviews = load_reviews(run_dir)
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    review = {"status": status, "note": note.strip()[:2000], "actor": actor[:100], "role": role, "updated_at": timestamp}
    reviews["findings"][finding_id] = review
    previous_hash = reviews["events"][-1]["event_hash"] if reviews["events"] else None
    event = {"finding_id": finding_id, **review, "previous_hash": previous_hash}
    event["event_hash"] = hashlib.sha256(json.dumps(event, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    reviews["events"].append(event)
    write_json(review_path(run_dir), reviews)
    return review
