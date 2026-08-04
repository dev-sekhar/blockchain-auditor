from __future__ import annotations

import ipaddress
import json
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class WebhookPolicy:
    allowed_hosts: frozenset[str]
    enabled: bool = False
    timeout_seconds: int = 5

    def validate(self,url: str) -> str:
        parsed=urllib.parse.urlparse(url)
        if parsed.scheme!="https" or not parsed.hostname: raise ValueError("Webhook URL must use HTTPS and include a hostname")
        host=parsed.hostname.lower()
        if host not in self.allowed_hosts: raise ValueError("Webhook host is not allowlisted")
        try: address=ipaddress.ip_address(host)
        except ValueError: address=None
        if address and (address.is_private or address.is_loopback or address.is_link_local): raise ValueError("Private and loopback webhook targets are forbidden")
        return url


class WebhookNotifier:
    def __init__(self,policy: WebhookPolicy): self.policy=policy
    def send(self,url: str,payload: dict) -> dict:
        self.policy.validate(url)
        if not self.policy.enabled: return {"status":"dry_run","url":url,"payload":payload}
        request=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"},method="POST")
        with urllib.request.urlopen(request,timeout=self.policy.timeout_seconds) as response: return {"status":"delivered","http_status":response.status}


class OidcProvider:
    """Extension contract. Production JWT validation requires a configured provider implementation."""
    def authenticate(self,bearer_token: str): raise NotImplementedError("OIDC provider is not configured")


@dataclass(frozen=True)
class RemoteRepositoryPolicy:
    allowed_hosts: frozenset[str]
    def validate(self,url: str,ref: str) -> dict:
        parsed=urllib.parse.urlparse(url)
        if parsed.scheme!="https" or not parsed.hostname: raise ValueError("Remote repository URL must use HTTPS")
        if parsed.username or parsed.password: raise ValueError("Credentials must not be embedded in repository URLs")
        if parsed.hostname.lower() not in self.allowed_hosts: raise ValueError("Repository host is not allowlisted")
        if not __import__("re").fullmatch(r"[0-9a-fA-F]{40}",ref): raise ValueError("Remote repository ref must be an immutable 40-character commit SHA")
        return {"url":url,"ref":ref,"host":parsed.hostname.lower()}
