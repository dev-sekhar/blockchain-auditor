from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any


SIGNING_ENV = "BLOCKCHAIN_AUDITOR_SIGNING_KEY"


def canonical_payload(manifest: dict[str, Any]) -> bytes:
    unsigned = {key: value for key, value in manifest.items() if key != "integrity" and not key.startswith("_")}
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sign_manifest(manifest: dict[str, Any]) -> dict[str, str]:
    payload = canonical_payload(manifest)
    result = {"algorithm": "sha256", "digest": hashlib.sha256(payload).hexdigest()}
    key = os.environ.get(SIGNING_ENV)
    if key:
        result.update({"signature_algorithm": "hmac-sha256", "signature": hmac.new(key.encode(), payload, hashlib.sha256).hexdigest()})
    return result


def verify_manifest(manifest: dict[str, Any]) -> tuple[bool, str]:
    integrity = manifest.get("integrity", {})
    expected = hashlib.sha256(canonical_payload(manifest)).hexdigest()
    if not hmac.compare_digest(str(integrity.get("digest", "")), expected):
        return False, "Manifest digest does not match"
    signature = integrity.get("signature")
    if signature:
        key = os.environ.get(SIGNING_ENV)
        if not key:
            return False, f"A signature exists; set {SIGNING_ENV} to authenticate it"
        actual = hmac.new(key.encode(), canonical_payload(manifest), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, actual):
            return False, "Manifest signature does not match"
        return True, "Digest and HMAC signature are valid"
    return True, "Digest is valid (unsigned manifest)"
