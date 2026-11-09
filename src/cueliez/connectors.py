"""HTTP connector helpers for pushing/pulling sealed CueLiez packages.

Observation/cue artifacts only. No live vendor integrations are bundled; callers
configure endpoints via CLI flags or environment variables. No credentials are
hardcoded. Tests should use mocked/local endpoints.

Security (Phase 9 hardening): URL scheme validation, DNS resolution with
restricted egress (blocks link-local/multicast/unspecified/reserved/metadata
targets; blocks RFC1918/CGNAT/private ranges by default except loopback),
response size limits, and redirect revalidation. For approved on-prem/private
network targets, set CUELIEZ_CONNECTOR_ALLOW_PRIVATE_NETWORK=1 explicitly.
"""

from __future__ import annotations

import ipaddress
import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterable, Mapping, Optional, Set, Tuple

from .audit import audit_event

DEFAULT_TIMEOUT_S = 15.0
DEFAULT_RETRIES = 2
DEFAULT_BACKOFF_S = 0.5
DEFAULT_MAX_RESPONSE_BYTES = 10 * 1024 * 1024  # 10 MiB sealed-package safety cap
DEFAULT_MAX_REQUEST_BYTES = 10 * 1024 * 1024
DEFAULT_MAX_REDIRECTS = 5
ALLOWED_SCHEMES = {"http", "https"}


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


def _allow_private_network() -> bool:
    v = os.environ.get("CUELIEZ_CONNECTOR_ALLOW_PRIVATE_NETWORK", "").strip().lower()
    return v in {"1", "true", "yes", "on"}


def _parse_allowlist() -> Tuple[Set[str], list]:
    """Return (allowed_hostnames_lower, allowed_networks). Empty config means no allowlist restriction."""
    raw = os.environ.get("CUELIEZ_CONNECTOR_HOST_ALLOWLIST", "").strip()
    hosts: Set[str] = set()
    nets = []
    if not raw:
        return hosts, nets
    for item in (x.strip() for x in raw.split(",") if x.strip()):
        low = item.lower()
        try:
            if "/" in item:
                nets.append(ipaddress.ip_network(item, strict=False))
            else:
                ipaddress.ip_address(item)
                hosts.add(low)
                nets.append(ipaddress.ip_network(item if "/" in item else f"{item}/32", strict=False))
        except ValueError:
            hosts.add(low)
    return hosts, nets


def _is_loopback_ip(ip: ipaddress._BaseAddress) -> bool:
    return bool(getattr(ip, "is_loopback", False))


def _ip_is_restricted(ip: ipaddress._BaseAddress, *, allow_private: bool) -> Optional[str]:
    # Allow loopback explicitly (common for local/test/on-host tooling).
    if _is_loopback_ip(ip):
        return None
    # Always block obviously dangerous targets.
    if getattr(ip, "is_multicast", False):
        return "multicast"
    if getattr(ip, "is_unspecified", False):
        return "unspecified"
    if getattr(ip, "is_link_local", False):
        # Covers IPv4 169.254/16 (incl. metadata patterns) and IPv6 fe80::/10.
        return "link_local"
    if getattr(ip, "is_reserved", False):
        return "reserved"
    # Private/RFC1918/CGNAT/etc.: blocked unless explicitly allowed for on-prem.
    if not allow_private and (
        getattr(ip, "is_private", False)
        or (isinstance(ip, ipaddress.IPv4Address) and ip in ipaddress.ip_network("100.64.0.0/10"))
    ):
        return "private_network"
    return None


def _resolve_host_ips(hostname: str) -> Set[ipaddress._BaseAddress]:
    ips: Set[ipaddress._BaseAddress] = set()
    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise ConnectorError("connector_url_rejected", f"Connector host could not be resolved: {hostname}: {e}")
    for _family, _type, _proto, _canon, sockaddr in infos:
        addr = sockaddr[0]
        try:
            ips.add(ipaddress.ip_address(addr))
        except ValueError:
            continue
    if not ips:
        raise ConnectorError("connector_url_rejected", f"Connector host resolved to no valid IPs: {hostname}")
    return ips


def _host_allowlisted(hostname: str, resolved_ips: Iterable[ipaddress._BaseAddress]) -> bool:
    hosts, nets = _parse_allowlist()
    if not hosts and not nets:
        return True  # no allowlist configured
    if hostname.lower() in hosts:
        return True
    for ip in resolved_ips:
        for net in nets:
            if ip in net:
                return True
    return False


def validate_connector_url(url: str, *, allow_private: Optional[bool] = None) -> str:
    """Validate connector URL and fail closed on unsafe egress targets."""
    if not isinstance(url, str) or not url.strip():
        raise ConnectorError("connector_config_missing", "Connector URL is required.")
    parsed = urllib.parse.urlparse(url.strip())
    scheme = (parsed.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        audit_event("connector.url_rejected", outcome="blocked", details={"reason": "scheme", "scheme": parsed.scheme})
        raise ConnectorError("connector_url_rejected", f"Connector URL scheme must be http/https, got: {parsed.scheme!r}")
    if not parsed.hostname:
        raise ConnectorError("connector_url_rejected", "Connector URL must include a hostname.")
    if parsed.username or parsed.password:
        audit_event("connector.url_rejected", outcome="blocked", details={"reason": "embedded_credentials", "host": parsed.hostname})
        raise ConnectorError("connector_url_rejected", "Connector URL must not include embedded credentials.")
    allow = _allow_private_network() if allow_private is None else bool(allow_private)
    # Literal IPs: validate directly. Hostnames: resolve and validate all answers.
    resolved: Set[ipaddress._BaseAddress] = set()
    try:
        literal = ipaddress.ip_address(parsed.hostname)
        resolved.add(literal)
        reason = _ip_is_restricted(literal, allow_private=allow)
        if reason:
            audit_event("connector.egress_blocked", outcome="blocked", details={"host": parsed.hostname, "reason": reason, "ip": str(literal)})
            raise ConnectorError(
                "connector_egress_blocked",
                f"Connector target IP blocked ({reason}): {parsed.hostname}. "
                "Set CUELIEZ_CONNECTOR_ALLOW_PRIVATE_NETWORK=1 only for approved on-prem/private targets.",
            )
    except ValueError:
        resolved = _resolve_host_ips(parsed.hostname)
        for ip in resolved:
            reason = _ip_is_restricted(ip, allow_private=allow)
            if reason:
                audit_event("connector.egress_blocked", outcome="blocked", details={"host": parsed.hostname, "ip": str(ip), "reason": reason})
                raise ConnectorError(
                    "connector_egress_blocked",
                    f"Connector target resolves to blocked IP ({reason}): {parsed.hostname} -> {ip}. "
                    "Set CUELIEZ_CONNECTOR_ALLOW_PRIVATE_NETWORK=1 only for approved on-prem/private targets.",
                )
    if not _host_allowlisted(parsed.hostname, resolved):
        audit_event("connector.url_rejected", outcome="blocked", details={"reason": "allowlist", "host": parsed.hostname})
        raise ConnectorError("connector_url_rejected", f"Connector host not in CUELIEZ_CONNECTOR_HOST_ALLOWLIST: {parsed.hostname}")
    return url.strip()


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, max_redirects: int = DEFAULT_MAX_REDIRECTS):
        super().__init__()
        self.max_redirects = max_redirects
        self._count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        self._count += 1
        if self._count > self.max_redirects:
            raise ConnectorError("connector_url_rejected", f"Connector redirect limit exceeded ({self.max_redirects}).")
        validate_connector_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _read_limited(resp: Any, max_bytes: int = DEFAULT_MAX_RESPONSE_BYTES) -> bytes:
    chunks = []
    total = 0
    while True:
        chunk = resp.read(min(65536, max_bytes - total + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ConnectorError("connector_response_too_large", f"Connector response exceeded {max_bytes} bytes.")
        chunks.append(chunk)
    return b"".join(chunks)


def _request_json(method: str, url: str, payload: Optional[Mapping[str, Any]] = None, *, timeout: float = DEFAULT_TIMEOUT_S, retries: int = DEFAULT_RETRIES, max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES, max_request_bytes: int = DEFAULT_MAX_REQUEST_BYTES, max_redirects: int = DEFAULT_MAX_REDIRECTS, correlation_id: Optional[str] = None) -> Tuple[int, Any]:
    url = validate_connector_url(url)
    body = None
    headers = {"Accept": "application/json", **_auth_headers()}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        if len(body) > max_request_bytes:
            raise ConnectorError("connector_request_too_large", f"Connector request body exceeded {max_request_bytes} bytes.")
        headers["Content-Type"] = "application/json"
    opener = urllib.request.build_opener(_SafeRedirectHandler(max_redirects=max_redirects))
    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            audit_event("connector.request", correlation_id=correlation_id, details={"method": method, "host": urllib.parse.urlparse(url).hostname, "has_body": body is not None})
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            with opener.open(req, timeout=timeout) as resp:
                raw = _read_limited(resp, max_bytes=max_response_bytes)
                status = getattr(resp, "status", 200)
            if not raw:
                audit_event("connector.response", details={"method": method, "status": status, "bytes": 0})
                return status, None
            try:
                audit_event("connector.response", details={"method": method, "status": status, "bytes": len(raw)})
                return status, json.loads(raw.decode("utf-8"))
            except Exception:
                audit_event("connector.response", details={"method": method, "status": status, "bytes": len(raw), "parse": "raw"})
                return status, {"raw": raw.decode("utf-8", "replace")}
        except urllib.error.HTTPError as e:
            raw = b""
            try:
                raw = _read_limited(e, max_bytes=max_response_bytes) if hasattr(e, "read") else b""
            except ConnectorError:
                raw = b""
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
        except ConnectorError:
            raise
        except Exception as e:
            last_err = e
            break
    raise ConnectorError("connector_error", f"Connector request failed: {last_err}")


def push_package(endpoint: str, package: Mapping[str, Any], *, timeout: float = DEFAULT_TIMEOUT_S, retries: int = DEFAULT_RETRIES, correlation_id: Optional[str] = None) -> Dict[str, Any]:
    if not endpoint:
        raise ConnectorError("connector_config_missing", "Push endpoint is required (--push-endpoint or CUELIEZ_PUSH_ENDPOINT).")
    status, data = _request_json("POST", endpoint, dict(package), timeout=timeout, retries=retries, correlation_id=correlation_id)
    return {"ok": True, "status": status, "response": data, "endpoint": endpoint}


def pull_package(endpoint: str, package_id: str, *, timeout: float = DEFAULT_TIMEOUT_S, retries: int = DEFAULT_RETRIES, correlation_id: Optional[str] = None) -> Dict[str, Any]:
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
    status, data = _request_json("GET", url, None, timeout=timeout, retries=retries, correlation_id=correlation_id)
    # Normalize: if endpoint returns envelope, try common keys.
    pkg = data
    if isinstance(data, dict):
        for k in ("package", "sealed_package", "data", "artifact"):
            if isinstance(data.get(k), dict):
                pkg = data[k]
                break
    return {"ok": True, "status": status, "package": pkg, "response": data, "endpoint": url}
