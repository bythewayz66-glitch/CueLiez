"""Output-safety helpers shared by officer-facing delivery surfaces."""

from __future__ import annotations

import base64
import hashlib
import html
import json
import re
from typing import Any

_UNSAFE_CHARS = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u200e\u200f\u061c\u2028\u2029\u202a-\u202e\u2066-\u2069]")


def visible_text(value: Any) -> str:
    """Show control, terminal-escape and bidi-override characters as [U+XXXX] instead of emitting them."""
    return _UNSAFE_CHARS.sub(lambda m: f"[U+{ord(m.group(0)):04X}]", str(value))


def escape_html(value: Any) -> str:
    """HTML-escape for text and quoted attribute values, after neutralising unsafe characters."""
    return html.escape(visible_text(value), quote=True)


def json_for_script(value: Any) -> str:
    """Serialise JSON for a non-executed <script type="application/json"> block."""
    return json.dumps(value, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _digest(body: str) -> str:
    return "'sha256-" + base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode("ascii") + "'"


def csp_policy_for(page: str, *, connect_self: bool = False) -> str:
    scripts = " ".join(_digest(b) for a, b in re.findall(r"<script([^>]*)>(.*?)</script>", page, re.S) if "application/json" not in a)
    styles = " ".join(_digest(b) for b in re.findall(r"<style[^>]*>(.*?)</style>", page, re.S))
    parts = ["default-src 'none'", f"script-src {scripts}", f"style-src {styles}"]
    if connect_self:
        parts.append("connect-src 'self'")
    parts += ["base-uri 'none'", "form-action 'none'"]
    return "; ".join(parts)
