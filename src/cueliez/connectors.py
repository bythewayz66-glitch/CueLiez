"""HTTP connector helpers for pushing/pulling sealed CueLiez packages.

Observation/cue artifacts only. No live vendor integrations are bundled; callers
configure endpoints via CLI flags or environment variables. No credentials are
hardcoded. Tests should use mocked/local endpoints.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Mapping, Optional, Tuple

DEFAULT_TIMEOUT_S = 15.0
DEFAULT_RETRIES = 2
DEFAULT_BACKOFF_S = 0.5


class ConnectorError(Exception):
    """Raised for connector configuration/transport failures (handled gracefully by CLI)."""

    def __init__(self, code: str, message: str, *, status: Optional[int] = None):
        super().__init__(message)
        self.code = code
        self.status = status


def _auth_headers() -> Dict[str, str]:
    headers: Dict[str, str] = {}
    token = os.environ.get("CUELIEZ_CONNECTOR_TOKEN", "").strip()
    if token:
        # Standard bearer auth; endpoints may ignore if not required.
        headers["Authorization"] = f"Bearer {token}"
    extra = os.environ.get("CUELIEZ_CONNECTOR_AUTH_HEADER", "").strip()
    if extra and ":" in extra:
        k, v = extra.split(":", 1)
        if k.strip():
            headers[k.strip()] = v.strip()
    return headers


def push_endpoint(cli_value: Optional[str] = None) -> Optional[str]:
    v = (cli_value or os.environ.get("CUELIEZ_PUSH_ENDPOINT") or "").strip()
    return v or None


def pull_endpoint(cli_value: Optional[str] = None) -> Optional[str]:
    v = (cli_value or os.environ.get("CUELIEZ_PULL_ENDPOINT") or "").strip()
    return v or None


def _request_json(method: str, url: str, payload: Optional[Mapping[str, Any]] = None, *, timeout: float = DEFAULT_TIMEOUT_S, retries: int = DEFAULT_RETRIES) -> Tuple[int, Any]:
    body = None
    headers = {"Accept": "application/json", **_auth_headers()}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                status = getattr(resp, "status", 200)
            if not raw:
                return status, None
            try:
                return status, json.loads(raw.decode("utf-8"))
            except Exception:
                return status, {"raw": raw.decode("utf-8", "replace")}
        except urllib.error.HTTPError as e:
            raw = e.read() if hasattr(e, "read") else b""
            detail = None
            try:
                detail = json.loads(raw.decode("utf-8")) if raw else None
            except Exception:
                detail = raw.decode("utf-8", "replace") if raw else str(e)
            raise ConnectorError("connector_http_error", f"Connector HTTP {e.code}: {detail}", status=int(e.code))
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            last_err = e
            if attempt < retries:
                time.sleep(DEFAULT_BACKOFF_S * (2 ** attempt))
                continue
            raise ConnectorError("connector_unavailable", f"Connector unavailable/offline: {e}")
        except Exception as e:
            last_err = e
            break
    raise ConnectorError("connector_error", f"Connector request failed: {last_err}")


def push_package(endpoint: str, package: Mapping[str, Any], *, timeout: float = DEFAULT_TIMEOUT_S, retries: int = DEFAULT_RETRIES) -> Dict[str, Any]:
    if not endpoint:
        raise ConnectorError("connector_config_missing", "Push endpoint is required (--push-endpoint or CUELIEZ_PUSH_ENDPOINT).")
    status, data = _request_json("POST", endpoint, dict(package), timeout=timeout, retries=retries)
    return {"ok": True, "status": status, "response": data, "endpoint": endpoint}


def pull_package(endpoint: str, package_id: str, *, timeout: float = DEFAULT_TIMEOUT_S, retries: int = DEFAULT_RETRIES) -> Dict[str, Any]:
    if not endpoint:
        raise ConnectorError("connector_config_missing", "Pull endpoint is required (--pull-endpoint or CUELIEZ_PULL_ENDPOINT).")
    if not package_id:
        raise ConnectorError("connector_config_missing", "Pull ID is required (--pull-id).")
    # Support {id} placeholder or append as query/path.
    if "{id}" in endpoint:
        url = endpoint.replace("{id}", urllib.parse.quote(package_id, safe=""))
    elif endpoint.endswith("/"):
        url = endpoint + urllib.parse.quote(package_id, safe="")
    else:
        sep = "&" if "?" in endpoint else "?"
        url = endpoint + f"{sep}id={urllib.parse.quote(package_id, safe='')}"
    status, data = _request_json("GET", url, None, timeout=timeout, retries=retries)
    # Normalize: if endpoint returns envelope, try common keys.
    pkg = data
    if isinstance(data, dict):
        for k in ("package", "sealed_package", "data", "artifact"):
            if isinstance(data.get(k), dict):
                pkg = data[k]
                break
    return {"ok": True, "status": status, "package": pkg, "response": data, "endpoint": url}
