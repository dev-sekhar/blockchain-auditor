from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Protocol

from .models import EngineResult, Finding, Location
from .provenance import IGNORED_PARTS
from .config import AuditConfig

RULE_ROOT = Path(__file__).with_name("rules")


def finding_id(rule_id: str, relative_file: str, line: int, evidence: str) -> str:
    normalized = " ".join(evidence.split())[:200]
    value = f"{rule_id}\0{relative_file}\0{line}\0{normalized}".encode()
    return hashlib.sha256(value).hexdigest()[:20]


class AuditEngine(Protocol):
    name: str

    def available(self) -> bool: ...
    def run(self, project: Path) -> EngineResult: ...


RULES = [
    {
        "id": "solidity-tx-origin",
        "title": "Authorization uses tx.origin",
        "severity": "high",
        "category": "access-control",
        "pattern": re.compile(r"\btx\.origin\b"),
        "description": "tx.origin authorization can be bypassed through a malicious intermediary contract.",
        "recommendation": "Use msg.sender with explicit role or ownership checks.",
    },
    {
        "id": "solidity-selfdestruct",
        "title": "Contract contains selfdestruct",
        "severity": "medium",
        "category": "dangerous-operation",
        "pattern": re.compile(r"\bselfdestruct\s*\("),
        "description": "Destructive lifecycle behavior can make assets or integrations unavailable.",
        "recommendation": "Remove selfdestruct or strictly constrain and document the lifecycle operation.",
    },
    {
        "id": "solidity-delegatecall",
        "title": "Low-level delegatecall detected",
        "severity": "medium",
        "category": "delegatecall",
        "pattern": re.compile(r"\.delegatecall\s*\("),
        "description": "delegatecall executes foreign code in the caller's storage context.",
        "recommendation": "Allow only trusted implementations and validate upgrade/storage invariants.",
    },
    {
        "id": "solidity-unchecked-call",
        "title": "Low-level call requires return-value review",
        "severity": "low",
        "category": "unchecked-call",
        "pattern": re.compile(r"\.call\s*\{"),
        "description": "Low-level calls expose explicit success values and reentrancy risk.",
        "recommendation": "Check the success value and follow checks-effects-interactions or use a reentrancy guard.",
    },
    {
        "id": "secret-private-key",
        "title": "Possible private key in source",
        "severity": "critical",
        "category": "secrets",
        "pattern": re.compile(r"(?i)(private[_-]?key|mnemonic)\s*[:=]\s*['\"][0-9a-f ]{32,}['\"]"),
        "description": "A credential resembling a private key or mnemonic is stored in source code.",
        "recommendation": "Revoke the credential, remove it from history, and load secrets from an approved vault.",
    },
]


class BuiltinEngine:
    name = "builtin"

    def available(self) -> bool:
        return True

    def run(self, project: Path) -> EngineResult:
        started = time.monotonic()
        findings: list[Finding] = []
        scanned = 0
        allowed = {".sol", ".vy", ".rs", ".move", ".cairo", ".go", ".java", ".js", ".ts", ".env"}
        for path in project.rglob("*"):
            if not path.is_file() or (path.suffix.lower() not in allowed and path.name != ".env"):
                continue
            relative = path.relative_to(project)
            if any(part in IGNORED_PARTS for part in relative.parts):
                continue
            try:
                if path.stat().st_size > 2_000_000:
                    continue
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            scanned += 1
            for line_number, line in enumerate(lines, 1):
                for rule in RULES:
                    if rule["pattern"].search(line):
                        rel = relative.as_posix()
                        findings.append(Finding(
                            id=finding_id(rule["id"], rel, line_number, line),
                            rule_id=rule["id"], title=rule["title"], severity=rule["severity"],
                            confidence="medium", category=rule["category"], description=rule["description"],
                            locations=[Location(rel, line_number)], evidence=line.strip()[:500],
                            recommendation=rule["recommendation"], source_engine=self.name,
                        ))
        return EngineResult(
            name=self.name, version="1", status="completed", findings=findings,
            duration_ms=int((time.monotonic() - started) * 1000), raw_output={"files_scanned": scanned},
        )


class JsonCommandEngine:
    def __init__(self, name: str, executable: str, args: list[str], parser):
        self.name, self.executable, self.args, self.parser = name, executable, args, parser

    def available(self) -> bool:
        return shutil.which(self.executable) is not None

    def run(self, project: Path) -> EngineResult:
        started = time.monotonic()
        try:
            version_run = subprocess.run([self.executable, "--version"], capture_output=True, text=True, timeout=10)
            version_lines = (version_run.stdout or version_run.stderr).strip().splitlines()
            version = version_lines[0][:100] if version_lines else "unknown"
            result = subprocess.run(
                [self.executable, *self.args], cwd=project, capture_output=True, text=True, timeout=300
            )
            raw = json.loads(result.stdout) if result.stdout.strip() else {}
            findings = self.parser(raw, project)
            status = "completed" if result.returncode in (0, 1) else "failed"
            error = None if status == "completed" else (result.stderr.strip()[:2000] or "Analyzer failed")
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            version, raw, findings, status, error = "unknown", None, [], "failed", str(exc)
        return EngineResult(self.name, version, status, findings, error, int((time.monotonic()-started)*1000), raw)


def parse_semgrep(raw: dict, project: Path) -> list[Finding]:
    findings = []
    severity_map = {"ERROR": "high", "WARNING": "medium", "INFO": "low"}
    for item in raw.get("results", []):
        extra = item.get("extra", {})
        rel = str(item.get("path", "unknown"))
        line = int(item.get("start", {}).get("line", 1))
        rule = str(item.get("check_id", "semgrep"))
        evidence = str(extra.get("lines", ""))
        findings.append(Finding(
            finding_id(rule, rel, line, evidence), rule, extra.get("message", rule),
            severity_map.get(extra.get("severity", "WARNING"), "medium"), "medium", "static-analysis",
            extra.get("message", "Semgrep finding"), [Location(rel, line, item.get("end", {}).get("line"))],
            evidence[:500], "Review the referenced rule and remediate the unsafe pattern.", "semgrep",
            list(extra.get("metadata", {}).get("references", [])),
        ))
    return findings


def parse_slither(raw: dict, project: Path) -> list[Finding]:
    findings = []
    impact = {"High": "high", "Medium": "medium", "Low": "low", "Informational": "informational", "Optimization": "informational"}
    for detector in raw.get("results", {}).get("detectors", []):
        elements = detector.get("elements", [])
        mapping = elements[0].get("source_mapping", {}) if elements else {}
        filename = mapping.get("filename_relative") or mapping.get("filename_short") or "unknown"
        lines = mapping.get("lines", [1])
        line = int(lines[0]) if lines else 1
        rule = str(detector.get("check", "slither"))
        description = str(detector.get("description", detector.get("markdown", "Slither finding"))).strip()
        findings.append(Finding(
            finding_id(rule, filename, line, description), rule, rule.replace("-", " ").title(),
            impact.get(detector.get("impact"), "medium"), str(detector.get("confidence", "Medium")).lower(),
            "static-analysis", description, [Location(filename, line, int(lines[-1]) if lines else line)],
            description[:500], "Review the detector guidance and remediate the affected data/control flow.", "slither",
            [f"https://github.com/crytic/slither/wiki/Detector-Documentation#{rule}"],
        ))
    return findings


class ContainerJsonEngine:
    def __init__(self, name: str, image: str, command: list[str], parser, config: AuditConfig):
        self.name, self.image, self.command, self.parser, self.config = name, image, command, parser, config
        self.unavailable_reason = "Docker or the configured image is unavailable locally"

    def available(self) -> bool:
        if not shutil.which("docker"):
            return False
        try:
            check = subprocess.run(["docker", "image", "inspect", self.image], capture_output=True, timeout=10)
            return check.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    def run(self, project: Path) -> EngineResult:
        started = time.monotonic()
        command = [
            "docker", "run", "--rm", "--network", "none", "--read-only",
            "--security-opt", "no-new-privileges", "--cap-drop", "ALL",
            "--memory", self.config.max_memory, "--cpus", self.config.max_cpus,
            "--pids-limit", "256", "--tmpfs", "/tmp:rw,noexec,nosuid,size=256m",
            "-v", f"{project}:/src:ro",
        ]
        if self.name == "semgrep":
            command.extend(["-v", f"{RULE_ROOT}:/rules:ro"])
        command.extend(["-w", "/src", self.image, *self.command])
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=self.config.timeout_seconds)
            raw = json.loads(result.stdout) if result.stdout.strip() else {}
            findings = self.parser(raw, project)
            status = "completed" if result.returncode in (0, 1) else "failed"
            error = None if status == "completed" else (result.stderr.strip()[:2000] or "Container analyzer failed")
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            raw, findings, status, error = None, [], "failed", str(exc)
        return EngineResult(self.name, self.image, status, findings, error, int((time.monotonic()-started)*1000), raw)


class TestEngine:
    def __init__(self, name: str, executable: str, native_command: list[str], marker: str, config: AuditConfig, image: str | None):
        self.name, self.executable, self.native_command, self.marker, self.config, self.image = name, executable, native_command, marker, config, image
        self.unavailable_reason = f"{marker} not detected or execution runtime unavailable"

    def available(self) -> bool:
        return False  # project-aware check occurs in run_or_skip

    def run_or_skip(self, project: Path) -> EngineResult:
        markers = [self.marker]
        if self.name == "hardhat": markers.append("hardhat.config.ts")
        if not any((project / marker).exists() for marker in markers):
            return EngineResult(self.name, "unknown", "skipped", error=f"{self.marker} not detected")
        if not self.config.dynamic_tests:
            return EngineResult(self.name, "unknown", "skipped", error="Dynamic tests are disabled")
        if self.config.execution_mode == "native":
            if not self.config.allow_native_execution or not shutil.which(self.executable):
                return EngineResult(self.name, "unknown", "skipped", error="Native project execution is not allowed or tool is unavailable")
            command, version = self.native_command, self.executable
        else:
            if not self.image or not shutil.which("docker"):
                return EngineResult(self.name, self.image or "unconfigured", "skipped", error="Container image/runtime is unavailable")
            try:
                inspected = subprocess.run(["docker", "image", "inspect", self.image], capture_output=True, timeout=10)
                if inspected.returncode:
                    return EngineResult(self.name, self.image, "skipped", error="Container image is not present locally; images are never pulled implicitly")
            except (OSError, subprocess.TimeoutExpired):
                return EngineResult(self.name, self.image, "skipped", error="Container runtime is unavailable")
            command = ["docker", "run", "--rm", "--network", "none", "--read-only", "--security-opt", "no-new-privileges", "--cap-drop", "ALL", "--memory", self.config.max_memory, "--cpus", self.config.max_cpus, "--pids-limit", "512", "--tmpfs", "/tmp:rw,nosuid,size=512m", "--tmpfs", "/src/out:rw,nosuid,size=512m", "--tmpfs", "/src/cache:rw,nosuid,size=256m", "-v", f"{project}:/src:ro", "-w", "/src", self.image, *self.native_command]
            version = self.image
        started = time.monotonic()
        try:
            result = subprocess.run(command, cwd=project if self.config.execution_mode == "native" else None, capture_output=True, text=True, timeout=self.config.timeout_seconds)
            status, error = ("completed", None) if result.returncode == 0 else ("failed", (result.stdout + "\n" + result.stderr).strip()[-4000:])
            raw = {"exit_code": result.returncode, "stdout": result.stdout[-10000:], "stderr": result.stderr[-10000:]}
        except (OSError, subprocess.TimeoutExpired) as exc:
            status, error, raw = "failed", str(exc), None
        return EngineResult(self.name, version, status, [], error, int((time.monotonic()-started)*1000), raw)


def configured_engines(config: AuditConfig) -> list[AuditEngine]:
    result: list[AuditEngine] = []
    for name in config.engines:
        if name == "builtin": result.append(BuiltinEngine())
        elif name == "semgrep":
            result.append(ContainerJsonEngine(name, config.semgrep_image, ["semgrep", "scan", "--config", "/rules/solidity.yml", "--json", "."], parse_semgrep, config) if config.execution_mode == "container" else JsonCommandEngine(name, "semgrep", ["scan", "--config", str(RULE_ROOT / "solidity.yml"), "--json", "."], parse_semgrep))
        elif name == "slither":
            result.append(ContainerJsonEngine(name, config.slither_image, ["slither", ".", "--json", "-"], parse_slither, config) if config.execution_mode == "container" else JsonCommandEngine(name, "slither", [".", "--json", "-"], parse_slither))
        elif name == "foundry": result.append(TestEngine(name, "forge", ["forge", "test"], "foundry.toml", config, config.foundry_image))
        elif name == "hardhat": result.append(TestEngine(name, "npx", ["npx", "hardhat", "test"], "hardhat.config.js", config, config.hardhat_image))
    return result
