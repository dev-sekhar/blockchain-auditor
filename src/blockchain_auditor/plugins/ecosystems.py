from __future__ import annotations

import re

from .patterns import PatternPlugin, PatternRule


def _rule(rule_id, title, severity, category, pattern, description, recommendation, confidence="low"):
    return PatternRule(rule_id, title, severity, category, re.compile(pattern), description, recommendation, confidence)


RUST_SOLANA = PatternPlugin("rust-solana", {"Rust"}, {"rust", "solana"}, {".rs"}, [
    _rule("rust-unsafe-block", "Unsafe Rust block requires review", "medium", "memory-safety", r"\bunsafe\s*\{", "Unsafe Rust bypasses compiler memory-safety guarantees and expands the audit boundary.", "Document the invariant, minimize the unsafe block, and add targeted property tests.", "medium"),
    _rule("rust-production-unwrap", "Potential panic through unwrap", "low", "denial-of-service", r"\.unwrap\s*\(\s*\)", "An unexpected error or missing value can panic the program or transaction handler.", "Return and handle the error explicitly; reserve unwrap for proven invariants and tests."),
    _rule("solana-invoke-signed", "Signed program invocation requires seed review", "medium", "cross-program-invocation", r"\binvoke_signed\s*\(", "Program-derived-address signing can grant authority across a cross-program invocation if seeds or target programs are insufficiently constrained.", "Verify program IDs, account ownership, PDA seeds, bump derivation, signer and writable privileges.", "medium"),
])

MOVE = PatternPlugin("move", {"Move"}, {"move", "aptos", "sui"}, {".move"}, [
    _rule("move-friend-declaration", "Friend privilege boundary", "low", "access-control", r"^\s*friend\s+", "Friend declarations expand which modules can invoke restricted functions.", "Confirm every friend module is trusted, immutable as expected, and included in the audit scope."),
    _rule("move-public-friend", "Public friend function exposes privileged surface", "medium", "access-control", r"\bpublic\s*\(\s*friend\s*\)\s+fun\b", "A friend-visible function forms a privileged cross-module entry point.", "Validate caller modules and enforce resource/account invariants inside the function.", "medium"),
    _rule("move-vector-borrow-mut", "Mutable vector borrow requires bounds/invariant review", "low", "state-integrity", r"\bvector::borrow_mut\s*\(", "Mutable access can violate collection invariants when indices or subsequent mutations are not constrained.", "Validate indices and preserve uniqueness, accounting, and length invariants."),
])

CAIRO = PatternPlugin("cairo-starknet", {"Cairo"}, {"starknet"}, {".cairo"}, [
    _rule("cairo-library-call", "Library call executes foreign class code", "medium", "delegatecall", r"\blibrary_call(?:_syscall)?\s*\(", "A Starknet library call executes another class in the caller's context and requires a trusted class hash.", "Constrain class hashes, protect upgrade authority, and verify compatible storage assumptions.", "medium"),
    _rule("cairo-caller-auth", "Caller-address authorization boundary", "low", "access-control", r"\bget_caller_address\s*\(", "Caller identity participates in an authorization or trust decision that requires contextual review.", "Confirm zero-address behavior, account abstraction assumptions, and explicit role validation."),
    _rule("cairo-unchecked-unwrapping", "Cairo unwrap may revert execution", "low", "denial-of-service", r"\.unwrap\s*\(\s*\)", "Unexpected Option or Result values can revert the transaction.", "Handle the error branch explicitly where external input or mutable state influences the value."),
])

FABRIC = PatternPlugin("hyperledger-fabric", {"Go", "Java"}, {"fabric"}, {".go", ".java"}, [
    _rule("fabric-go-panic", "Chaincode panic path", "medium", "denial-of-service", r"\bpanic\s*\(", "A panic can abort chaincode execution and reduce availability under attacker-controlled input.", "Return deterministic chaincode errors and validate input before reaching the panic path.", "medium"),
    _rule("fabric-weak-random", "Nondeterministic or weak randomness", "high", "consensus-determinism", r"(?:math/rand|new\s+Random\s*\()", "Local randomness can be predictable and may produce nondeterministic endorsement results.", "Do not use local randomness in consensus-relevant chaincode; derive deterministic values from approved inputs.", "medium"),
    _rule("fabric-system-time", "System time can break deterministic execution", "medium", "consensus-determinism", r"(?:time\.Now\s*\(|System\.currentTimeMillis\s*\()", "Peer-local wall-clock time may differ between endorsers and cause inconsistent results.", "Use the transaction timestamp supplied by the Fabric stub and validate its acceptable range.", "medium"),
], require_ecosystem=True)

BUILTIN_PLUGINS = [RUST_SOLANA, MOVE, CAIRO, FABRIC]
