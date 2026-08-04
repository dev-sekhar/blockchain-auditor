from __future__ import annotations

from dataclasses import dataclass

from ..api.errors import ApiError
from ..db.store import Database


@dataclass(frozen=True)
class Identity:
    tenant_id: str
    actor: str
    role: str


class AuthService:
    def __init__(self, database: Database | None, required: bool): self.database, self.required = database, required

    def authenticate(self, authorization: str | None, local_role: str = "viewer", local_actor: str = "local-user") -> Identity:
        if not self.required: return Identity("local", local_actor, local_role)
        if not authorization or not authorization.startswith("Bearer "):
            raise ApiError("AUDIT-AUTH-401", "A bearer API token is required", 401)
        token = authorization.removeprefix("Bearer ").strip()
        record = self.database.identity_for_token(token) if self.database else None
        if not record: raise ApiError("AUDIT-AUTH-401", "The API token is invalid or revoked", 401)
        return Identity(**record)
