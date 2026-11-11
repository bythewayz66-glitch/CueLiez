# Delivery output safety

Officer-facing surfaces show transcript-derived text (cue text, source quotes, labels, notes). That text is untrusted. These rules apply to `src/cueliez/delivery/*` and `docs/site/review.html`.

## Rules

- Server-rendered HTML: every inserted value goes through `delivery.safe.escape_html` (HTML-escape for text and quoted attributes, after control and bidi characters are shown as `[U+XXXX]`).
- Inline JSON in a script block: `delivery.safe.json_for_script` (ASCII-only JSON with `<`, `>` and `&` escaped). The block is `type="application/json"` and is never executed.
- Client-side JS (live dashboard, review page): build nodes with `createElement` and `textContent`. No `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval` or `new Function`. Values are coerced to text; non-object cues and non-numeric scores are displayed, not trusted.
- Terminal text (`render_text`): control, escape-sequence and bidi characters are shown as `[U+XXXX]`.
- Quote content is displayed as received. Only unsafe characters are made visible, so the record is not rewritten.

## Content-Security-Policy

- Live dashboard: sent as a response header on `/`. Inline script and style are allowed by SHA-256 hash only; `default-src 'none'`, `connect-src 'self'`, no `unsafe-inline`, no framing.
- Officer HTML (`render_officer_html`) and `docs/site/review.html`: `<meta http-equiv="Content-Security-Policy">` with the hashes of their inline script and style. Editing either inline block changes its hash. `tests/test_delivery_escaping.py` fails until the meta is regenerated (`delivery.safe.csp_policy_for` for the officer page; the review page hash is computed over the exact script and style text).

## Dashboard transport

- Responses carry `X-Content-Type-Options: nosniff`, `Cache-Control: no-store` and `Referrer-Policy: no-referrer`.
- An `Origin` header is accepted only when its scheme is http or https and its host is exactly `127.0.0.1`, `localhost` or `[::1]` (any port), or it is listed in `CUELIEZ_DASHBOARD_ALLOWED_ORIGINS`.

## Tests

`tests/test_delivery_escaping.py` runs the real inline scripts under Node against a recording fake DOM (`tests/js_dom_harness.py`) and parses server-rendered HTML with the standard HTML parser. Node is required in CI; locally the client-side tests skip when Node is absent.
