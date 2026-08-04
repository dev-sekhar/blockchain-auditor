from __future__ import annotations

import re


SECRET_PATTERNS=[
    re.compile(r"(?i)(api[_-]?key|private[_-]?key|secret|token|password)\s*[:=]\s*['\"]?([^\s'\"]{8,})"),
    re.compile(r"\b0x[0-9a-fA-F]{64}\b"),
]
INJECTION_PATTERNS=[re.compile(pattern,re.I) for pattern in (r"ignore (?:all|any|the) previous",r"reveal (?:the )?system prompt",r"exfiltrat",r"override (?:your|the) instructions")]


def redact(text: str) -> str:
    result=text
    for pattern in SECRET_PATTERNS:
        result=pattern.sub(lambda match: f"{match.group(1)}=[REDACTED]" if match.lastindex and match.lastindex>=1 else "[REDACTED]",result)
    return result


def detect_injection(text: str) -> list[str]: return [pattern.pattern for pattern in INJECTION_PATTERNS if pattern.search(text)]
