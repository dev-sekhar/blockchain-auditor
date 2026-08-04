from __future__ import annotations

import dataclasses
import hashlib
import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AuditConfig:
    profile: str = "solidity"
    execution_mode: str = "container"
    engines: list[str] = field(default_factory=lambda: ["builtin", "semgrep", "slither"])
    dynamic_tests: bool = False
    allow_native_execution: bool = False
    timeout_seconds: int = 300
    max_memory: str = "2g"
    max_cpus: str = "2"
    suppression_file: str = ".blockchain-auditor-suppressions.json"
    fail_on: str | None = None
    semgrep_image: str = "semgrep/semgrep:1.128.0"
    slither_image: str = "trailofbits/eth-security-toolbox:0.12.0"
    foundry_image: str = "ghcr.io/foundry-rs/foundry:v1.3.1"
    hardhat_image: str | None = None
    formal_verification: bool = False
    properties_file: str = "audit-properties.toml"
    require_property_proofs: bool = False
    solc_image: str | None = None
    economic_simulation: bool = False
    scenarios_file: str = "audit-scenarios.toml"
    monitoring_file: str = "monitoring.toml"
    compliance_frameworks: list[str] = field(default_factory=lambda: ["OWASP-SC", "SOC2", "ISO27001"])

    def validate(self) -> None:
        if self.execution_mode not in {"container", "native"}:
            raise ValueError("execution_mode must be 'container' or 'native'")
        if self.execution_mode == "native" and not self.allow_native_execution:
            raise ValueError("Native execution requires allow_native_execution = true")
        if not 1 <= self.timeout_seconds <= 3600:
            raise ValueError("timeout_seconds must be between 1 and 3600")
        allowed = {"builtin", "semgrep", "slither", "foundry", "hardhat"}
        unknown = set(self.engines) - allowed
        if unknown:
            raise ValueError(f"Unknown audit engines: {', '.join(sorted(unknown))}")
        if not isinstance(self.compliance_frameworks,list) or not all(isinstance(item,str) for item in self.compliance_frameworks):
            raise ValueError("compliance_frameworks must be a list of framework names")

    def safe_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    def digest(self) -> str:
        encoded = json.dumps(self.safe_dict(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


PROFILES: dict[str, dict[str, Any]] = {
    "solidity": {"engines": ["builtin", "semgrep", "slither"], "dynamic_tests": False},
    "solidity-ci": {"engines": ["builtin", "semgrep", "slither", "foundry", "hardhat"], "dynamic_tests": True, "fail_on": "high"},
    "quick": {"engines": ["builtin"], "dynamic_tests": False, "execution_mode": "container"},
    "multi-chain": {"engines": ["builtin"], "dynamic_tests": False, "execution_mode": "container"},
    "assurance": {"engines": ["builtin", "semgrep", "slither"], "dynamic_tests": False, "formal_verification": True, "require_property_proofs": False},
    "protocol": {"engines": ["builtin", "semgrep", "slither"], "dynamic_tests": False, "formal_verification": True, "economic_simulation": True},
}


def load_config(path_value: str | None = None, profile: str | None = None) -> tuple[AuditConfig, Path | None]:
    path = Path(path_value).expanduser().resolve() if path_value else None
    raw: dict[str, Any] = {}
    if path:
        if not path.is_file():
            raise ValueError(f"Configuration file does not exist: {path}")
        with path.open("rb") as stream:
            document = tomllib.load(stream)
        raw = document.get("audit", document)
        if not isinstance(raw, dict):
            raise ValueError("Configuration must contain an [audit] table")
    selected = profile or raw.pop("profile", "solidity")
    if selected not in PROFILES:
        raise ValueError(f"Unknown profile: {selected}")
    values = {**PROFILES[selected], **raw, "profile": selected}
    known = {item.name for item in dataclasses.fields(AuditConfig)}
    unknown = set(values) - known
    if unknown:
        raise ValueError(f"Unknown configuration keys: {', '.join(sorted(unknown))}")
    config = AuditConfig(**values)
    config.validate()
    return config, path
