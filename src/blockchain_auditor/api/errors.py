from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ApiError(Exception):
    code: str
    message: str
    status: int = 400

    def payload(self) -> dict:
        return {"error": {"code": self.code, "message": self.message}}


def validation(message: str) -> ApiError:
    return ApiError("AUDIT-API-400", message, 400)


def forbidden(message: str = "Your role cannot perform this action") -> ApiError:
    return ApiError("AUDIT-AUTH-403", message, 403)


def not_found(resource: str) -> ApiError:
    return ApiError("AUDIT-API-404", f"{resource} was not found", 404)
