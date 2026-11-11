"""Run an inline page script under Node against a recording fake DOM.

The fake DOM records every raw-HTML sink and every element the script creates,
so tests can assert that data never becomes markup.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

NODE = shutil.which("node")

_RUNNER = r"""
const vm = require('vm');
const fs = require('fs');
const cfg = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const sinks = [];
const created = [];
const INTERNAL = new Set(['tag','attrs','children','_text','dataset','value','props','isFake']);

function makeEl(tag, track) {
  const el = {
    isFake: true, tag, attrs: {}, children: [], _text: '', dataset: {}, value: '', props: {},
    append(...nodes) { for (const n of nodes) this.children.push(typeof n === 'string' ? {isText: true, text: n} : n); },
    appendChild(n) { this.children.push(n); return n; },
    replaceChildren(...nodes) { this.children = []; this.append(...nodes); },
    setAttribute(k, v) { this.attrs[k] = String(v); },
    getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; },
    addEventListener() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
    click() { if (typeof this.props.onclick === 'function') return this.props.onclick(); },
  };
  const proxy = new Proxy(el, {
    get(t, k) {
      if (k === 'textContent') return t._text + t.children.map(c => c.isText ? c.text : (c.textContent || '')).join('');
      if (k === 'className') return t.attrs['class'] || '';
      if (k === 'onclick' || k in t) return k in t ? t[k] : t.props[k];
      return t.props[k];
    },
    set(t, k, v) {
      if (k === 'textContent') { t._text = String(v); t.children = []; return true; }
      if (k === 'innerHTML' || k === 'outerHTML') { sinks.push({sink: k, value: String(v)}); t.children = []; return true; }
      if (k === 'className') { t.attrs['class'] = String(v); return true; }
      if (k === 'value') { t.value = v; return true; }
      if (INTERNAL.has(k)) { t[k] = v; return true; }
      t.props[k] = v; return true;
    },
  });
  if (track) created.push(proxy);
  return proxy;
}

const byId = {};
for (const id of cfg.ids) byId[id] = makeEl('static', false);
for (const [id, v] of Object.entries(cfg.values || {})) byId[id].value = v;

const document = {
  getElementById: id => byId[id] || null,
  createElement: tag => makeEl(String(tag).toLowerCase(), true),
  createTextNode: s => ({isText: true, text: String(s)}),
  querySelector: () => null,
  querySelectorAll: () => [],
  write(s) { sinks.push({sink: 'document.write', value: String(s)}); },
  body: makeEl('body', false),
};

const ctx = {
  document,
  console,
  setInterval: () => 0,
  setTimeout,
  fetch: async () => ({ ok: true, status: 200, json: async () => cfg.fetchJson, text: async () => JSON.stringify(cfg.fetchJson) }),
  eval: undefined,
};
ctx.window = ctx;
vm.createContext(ctx);
const result = {errors: []};
try { vm.runInContext(cfg.script, ctx, {timeout: 5000}); } catch (e) { result.errors.push(String(e && e.stack || e)); }

(async () => {
  await new Promise(r => setTimeout(r, 50));
  for (const step of cfg.steps || []) {
    try {
      const el = byId[step.id];
      const fn = el.props[step.call];
      const r = fn.call(el);
      if (r && typeof r.then === 'function') await r;
    } catch (e) { result.errors.push(String(e && e.stack || e)); }
    await new Promise(r => setTimeout(r, 50));
  }
  const dump = n => n.isText ? {text: n.text} : {tag: n.tag, attrs: n.attrs, text: n._text, children: n.children.map(dump)};
  result.sinks = sinks;
  result.created = created.map(e => ({tag: e.tag, attrs: e.attrs, props: Object.keys(e.props)}));
  result.roots = {};
  for (const id of cfg.ids) result.roots[id] = dump(byId[id]);
  result.pwned = ctx.__pwned || null;
  process.stdout.write(JSON.stringify(result));
})();
"""


def extract_inline_scripts(html_text: str) -> List[str]:
    out = []
    for m in re.finditer(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script\s*>", html_text, re.S | re.I):
        if "application/json" in m.group("attrs"):
            continue
        out.append(m.group("body"))
    return out


def run_script(
    script: str,
    *,
    ids: List[str],
    fetch_json: Any = None,
    values: Optional[Dict[str, str]] = None,
    steps: Optional[List[Dict[str, str]]] = None,
    tmp_dir: Path,
) -> Dict[str, Any]:
    if NODE is None:
        raise RuntimeError("node is not available")
    runner = tmp_dir / "runner.js"
    cfg = tmp_dir / "cfg.json"
    runner.write_text(_RUNNER, encoding="utf-8")
    cfg.write_text(json.dumps({"script": script, "ids": ids, "fetchJson": fetch_json, "values": values or {}, "steps": steps or []}), encoding="utf-8")
    p = subprocess.run([NODE, str(runner), str(cfg)], capture_output=True, text=True, timeout=30)
    if p.returncode != 0:
        raise RuntimeError(f"node failed: {p.stderr}")
    return json.loads(p.stdout)


class _Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: List[Tuple[str, List[Tuple[str, Optional[str]]]]] = []
        self.text: List[str] = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, attrs))

    def handle_startendtag(self, tag, attrs):
        self.tags.append((tag, attrs))

    def handle_data(self, data):
        self.text.append(data)


def parse_markup(markup: str) -> _Collector:
    c = _Collector()
    c.feed(markup)
    c.close()
    return c


FORBIDDEN_ATTRS = {"src", "href", "srcdoc", "style", "action", "formaction", "xlink:href", "data", "srcset"}


def markup_violations(tags: List[Tuple[str, List[Tuple[str, Optional[str]]]]], allowed_tags: Set[str]) -> List[str]:
    bad = []
    for tag, attrs in tags:
        if tag not in allowed_tags:
            bad.append(f"unexpected element <{tag}>")
        for name, _ in attrs:
            n = (name or "").lower()
            if n.startswith("on") or n in FORBIDDEN_ATTRS:
                bad.append(f"unexpected attribute {n} on <{tag}>")
    return bad


def tree_text(node: Dict[str, Any]) -> str:
    if "text" in node and "tag" not in node:
        return node["text"]
    return node.get("text", "") + "".join(tree_text(c) for c in node.get("children", []))


def analyse(result: Dict[str, Any], allowed_tags: Set[str]) -> Tuple[List[str], str]:
    """Return (violations, all visible text) across raw-HTML sinks and created elements."""
    violations: List[str] = []
    text_parts: List[str] = []
    for s in result["sinks"]:
        col = parse_markup(s["value"])
        violations += [f"{s['sink']}: {v}" for v in markup_violations(col.tags, allowed_tags)]
        text_parts.append("".join(col.text))
    for el in result["created"]:
        if el["tag"] not in allowed_tags:
            violations.append(f"created element <{el['tag']}>")
        for name in el["attrs"]:
            n = name.lower()
            if n.startswith("on") or n in FORBIDDEN_ATTRS:
                violations.append(f"created element attribute {n}")
        if el["props"]:
            violations.append(f"created element props set: {el['props']}")
    for root in result["roots"].values():
        text_parts.append(tree_text(root))
    return violations, "\n".join(text_parts)
