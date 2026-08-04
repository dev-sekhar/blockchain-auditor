from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..engines import finding_id
from ..models import Finding, Location
from ..provenance import IGNORED_PARTS
from .contracts import PluginResult


@dataclass(frozen=True)
class PatternRule:
    rule_id: str
    title: str
    severity: str
    category: str
    pattern: re.Pattern
    description: str
    recommendation: str
    confidence: str = "low"


class PatternPlugin:
    version = "1.0"

    def __init__(self, plugin_id: str, languages: set[str], ecosystems: set[str], extensions: set[str], rules: list[PatternRule], require_ecosystem: bool = False):
        self.plugin_id, self.languages, self.ecosystems = plugin_id, languages, ecosystems
        self.extensions, self.rules = extensions, rules
        self.require_ecosystem = require_ecosystem
        self.capabilities = {
            "static_analysis": "heuristic",
            "dynamic_testing": "not_configured",
            "formal_verification": "not_configured",
            "economic_simulation": "not_configured",
            "continuous_monitoring": "not_configured",
        }

    def matches(self, project: dict) -> bool:
        ecosystem_match = bool(self.ecosystems & set(project.get("ecosystems", [])))
        return ecosystem_match if self.require_ecosystem else bool(self.languages & set(project.get("languages", {}))) or ecosystem_match

    def analyze(self, root: Path) -> PluginResult:
        findings, scanned = [], 0
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in self.extensions: continue
            relative = path.relative_to(root)
            if any(part in IGNORED_PARTS for part in relative.parts): continue
            try:
                if path.stat().st_size > 2_000_000: continue
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError: continue
            scanned += 1; rel = relative.as_posix()
            for line_number, line in enumerate(lines, 1):
                for rule in self.rules:
                    if not rule.pattern.search(line): continue
                    findings.append(Finding(
                        finding_id(rule.rule_id, rel, line_number, line), rule.rule_id, rule.title,
                        rule.severity, rule.confidence, rule.category, rule.description,
                        [Location(rel, line_number)], line.strip()[:500], rule.recommendation, self.plugin_id,
                    ))
        return PluginResult(self.plugin_id, self.version, "completed", findings, scanned)

    def coverage(self, detected: bool) -> dict:
        return {
            "plugin_id": self.plugin_id, "version": self.version, "detected": detected,
            "languages": sorted(self.languages), "ecosystems": sorted(self.ecosystems),
            "capabilities": self.capabilities,
            "assurance": "heuristic" if detected else "not_applicable",
            "limitations": ["Pattern findings require human validation and do not establish absence of vulnerabilities."],
        }
