from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


SEVERITIES = ("critical", "high", "medium", "low", "informational")


@dataclass
class Location:
    file: str
    start_line: int
    end_line: int | None = None


@dataclass
class Finding:
    id: str
    rule_id: str
    title: str
    severity: str
    confidence: str
    category: str
    description: str
    locations: list[Location]
    evidence: str
    recommendation: str
    source_engine: str
    references: list[str] = field(default_factory=list)
    status: str = "open"
    traceability: str = "new"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EngineResult:
    name: str
    version: str
    status: str
    findings: list[Finding] = field(default_factory=list)
    error: str | None = None
    duration_ms: int = 0
    raw_output: Any = None


@dataclass
class SourceIdentity:
    path: str
    project_name: str
    tree_hash: str
    git_commit: str | None = None
    git_branch: str | None = None
    git_dirty: bool | None = None
    repository_url: str | None = None


@dataclass
class AuditRun:
    schema_version: str
    audit_id: str
    created_at: str
    completed_at: str
    source: SourceIdentity
    project: dict[str, Any]
    configuration: dict[str, Any]
    configuration_hash: str
    tools: list[dict[str, Any]]
    summary: dict[str, Any]
    findings: list[Finding]
    baseline_audit_id: str | None = None
    integrity: dict[str, str] = field(default_factory=dict)
    analysis: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
