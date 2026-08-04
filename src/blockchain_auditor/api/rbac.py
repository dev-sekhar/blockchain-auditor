from __future__ import annotations

from .errors import forbidden


ROLES = {
    "admin": {"audit:run", "review:write", "audit:read", "audit:log"},
    "auditor": {"audit:run", "review:write", "audit:read", "audit:log"},
    "viewer": {"audit:read"},
}


def require(role: str, permission: str) -> None:
    if permission not in ROLES.get(role, set()):
        raise forbidden()
