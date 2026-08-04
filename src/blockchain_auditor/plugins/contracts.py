from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from ..models import Finding


CAPABILITIES = ("static_analysis", "dynamic_testing", "formal_verification", "economic_simulation", "continuous_monitoring")


@dataclass
class PluginResult:
    plugin_id: str
    version: str
    status: str
    findings: list[Finding] = field(default_factory=list)
    files_scanned: int = 0
    error: str | None = None
    metadata: dict = field(default_factory=dict)


class EcosystemPlugin(Protocol):
    plugin_id: str
    version: str
    languages: set[str]
    ecosystems: set[str]
    capabilities: dict[str, str]

    def matches(self, project: dict) -> bool: ...
    def analyze(self, root: Path) -> PluginResult: ...
    def coverage(self, detected: bool) -> dict: ...
