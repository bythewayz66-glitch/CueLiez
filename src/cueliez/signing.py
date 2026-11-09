"""Package signing/verification workflow (Phase 9.5 / 9.6).

Real HMAC-SHA256 signing over the canonical package hash (stdlib only).
`package_signature` is excluded from the canonical hash. Key custody is an
operator responsibility; see docs/deployment/KEY_CUSTODY.md.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional

from .gates import compute_package_hash


def load_signing_key() -> Optional[bytes]:
    key = os.environ.get("CUELIEZ_SIGNING_KEY", "")
    if key:
        return key.encode("utf-8")
    path = os.environ.get("CUELIEZ_SIGNING_KEY_FILE", "").strip()
    if path:
        p = Path(path)
        if p.exists() and p.is_file():
            return p.read_bytes().strip()
    return None


def load_verification_keys() -> list[bytes]:
    """Keys for signature verification: current key plus CUELIEZ_SIGNING_VERIFY_KEYS (comma-separated, rotation)."""
    keys: list[bytes] = []
    cur = load_signing_key()
    if cur:
        keys.append(cur)
    extra = os.environ.get("CUELIEZ_SIGNING_VERIFY_KEYS", "")
    for part in (x.strip() for x in extra.split(",") if x.strip()):
        keys.append(part.encode("utf-8"))
    # de-dup preserving order
    out = []
    seen = set()
    for k in keys:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def key_id_for_key(key: bytes) -> str:
    return hashlib.sha256(key).hexdigest()[:16]


def hmac_sign_package(package: Mapping[str, Any], *, key: Optional[bytes] = None, key_id: Optional[str] = None) -> Dict[str, Any]:
    k = load_signing_key() if key is None else key
    if not k:
        raise ValueError("signing_key_missing: set CUELIEZ_SIGNING_KEY or CUELIEZ_SIGNING_KEY_FILE")
    pkg_hash = compute_package_hash(package)
    sig = hmac.new(k, pkg_hash.encode("utf-8"), hashlib.sha256).hexdigest()
    return {
        "type": "hmac-sha256",
        "alg": "HMAC-SHA256",
        "hash_alg": "sha256",
        "key_id": key_id or key_id_for_key(k),
        "signed_hash": pkg_hash,
        "sig": sig,
    }


def verify_hmac_signature(package: Mapping[str, Any], *, key: Optional[bytes] = None, keys: Optional[list[bytes]] = None) -> Dict[str, Any]:
    candidates = list(keys) if keys is not None else ([key] if key is not None else load_verification_keys())
    sig_obj = package.get("package_signature") if isinstance(package, Mapping) else None
    if not isinstance(sig_obj, Mapping):
        return {"ok": False, "reason": "missing_signature"}
    if sig_obj.get("type") != "hmac-sha256":
        return {"ok": False, "reason": "unsupported_signature_type", "type": sig_obj.get("type")}
    if not candidates:
        return {"ok": False, "reason": "signing_key_missing"}
    expected_hash = compute_package_hash(package)
    signed_hash = sig_obj.get("signed_hash")
    if signed_hash != expected_hash:
        return {"ok": False, "reason": "signed_hash_mismatch"}
    provided = str(sig_obj.get("sig") or "")
    for k in candidates:
        if not k:
            continue
        expected_sig = hmac.new(k, expected_hash.encode("utf-8"), hashlib.sha256).hexdigest()
        if hmac.compare_digest(provided, expected_sig):
            return {"ok": True, "type": "hmac-sha256", "key_id": sig_obj.get("key_id"), "signed_hash": signed_hash}
    return {"ok": False, "reason": "signature_invalid"}


def hmac_signer(*, key: Optional[bytes] = None, key_id: Optional[str] = None) -> Callable[[Mapping[str, Any]], Dict[str, Any]]:
    def _sign(package: Mapping[str, Any]) -> Dict[str, Any]:
        return hmac_sign_package(package, key=key, key_id=key_id)
    return _sign


def auto_signer_from_env() -> Optional[Callable[[Mapping[str, Any]], Dict[str, Any]]]:
    if load_signing_key() is None:
        return None
    return hmac_signer()
