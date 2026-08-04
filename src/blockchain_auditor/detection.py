from __future__ import annotations

from pathlib import Path

from .provenance import IGNORED_PARTS


EXTENSIONS = {
    ".sol": ("Solidity", "evm"),
    ".vy": ("Vyper", "evm"),
    ".rs": ("Rust", "rust"),
    ".move": ("Move", "move"),
    ".cairo": ("Cairo", "starknet"),
    ".go": ("Go", "go"),
    ".java": ("Java", "jvm"),
}


def detect_project(project: Path) -> dict:
    counts: dict[str, int] = {}
    ecosystems: set[str] = set()
    source_files = 0
    for path in project.rglob("*"):
        if not path.is_file() or any(part in IGNORED_PARTS for part in path.relative_to(project).parts):
            continue
        detected = EXTENSIONS.get(path.suffix.lower())
        if detected:
            language, ecosystem = detected
            counts[language] = counts.get(language, 0) + 1
            ecosystems.add(ecosystem)
            source_files += 1

    frameworks = []
    markers = {
        "foundry.toml": "Foundry",
        "hardhat.config.js": "Hardhat",
        "hardhat.config.ts": "Hardhat",
        "Anchor.toml": "Anchor",
        "Move.toml": "Move",
        "Scarb.toml": "Scarb",
    }
    for marker, framework in markers.items():
        if (project / marker).exists() and framework not in frameworks:
            frameworks.append(framework)
    def contains(name: str, needles: tuple[str, ...]) -> bool:
        path = project / name
        if not path.is_file(): return False
        try: content = path.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError: return False
        return any(needle.lower() in content for needle in needles)
    if contains("Cargo.toml", ("solana-program", "anchor-lang")):
        ecosystems.discard("rust"); ecosystems.add("solana")
    if contains("Move.toml", ("aptosframework", "aptos-framework")):
        ecosystems.discard("move"); ecosystems.add("aptos")
    elif contains("Move.toml", ("suiframework", "sui-framework")):
        ecosystems.discard("move"); ecosystems.add("sui")
    if contains("go.mod", ("fabric-chaincode-go", "hyperledger/fabric")) or contains("pom.xml", ("fabric-chaincode-shim",)):
        ecosystems.add("fabric")
    return {
        "languages": counts,
        "ecosystems": sorted(ecosystems),
        "frameworks": frameworks,
        "source_file_count": source_files,
    }
