# Owner instruction 2026-11-11: real connectors, signing, accessibility, retention

Source of truth for tickets ENG-009 to ENG-013. Written by the lead dev. Status and results go in `DIARY.md`, not here.

Owner instruction relayed by the Independent Reviewer: finish everything that code can finish in four areas. Verified at HEAD `7b1c8e1` before assigning (read and run):
- `signing.py` is HMAC-SHA256 only; a third party cannot verify without the secret [read]. `--verify-package` on a CLI-exported package returns `hash_ok: false`, exit 2 (ENG-001) [ran]; signed export verification builds on that, so ENG-001 comes first.
- `connectors.py` is a generic HTTP push/pull with SSRF hardening; no vendor code in `src/` [read, grep].
- `retention.py` computes a derived policy and redacts for sharing; nothing imports it, no test covers it, the 3/5/7-year defaults have no source, and no deletion exists [read, grep].
- Accessibility: only `lang="en"` in the three HTML surfaces; no ARIA, no keyboard handling, no checks [grep].
- Stale text: TODO.md Phase 3.3 "signature not yet implemented" and the Admissibility "signature optional hook" are wrong against `signing.py` [read].

CLI seam (landed in `a891e05`): `cli.py` has a `SUBCOMMANDS` table, name to `module:function`. The handler receives the remaining argv and returns an exit code; an existing file with the same name is still treated as a transcript; errors print the standard JSON with `error_code`. Tests: `tests/test_cli_subcommands.py`. No subcommand is registered yet; ENG-009, 010 and 013 each register theirs in their own commit. Do not add new top-level flags to `cli.py` for these features.

## Boundaries binding on all tickets

- No document, string or help text may claim a signature, package or process is "legally accepted", "admissible" or "court-ready". Legal weight depends on the signer's certificate, the jurisdiction and counsel. Docs say that plainly and say what the operator must supply (certificate, HSM or KMS, TSA).
- No vendor endpoint, field or auth flow may be invented. If it is not in documentation you cite, it is not built; it is listed in DIARY as not completed, with the exact document or credential needed.
- Language rules, the never-claim paragraph, observation-only wording and the subject-not-shown default are unchanged.
- Core stays zero runtime dependencies. Anything needing a library goes in an optional extra, imported lazily, with a clear error code when missing. The verifier must run on stdlib alone.
- Full GAMUT.md check set run and observed before every push. Push directly to main. Pull before every edit; `DIARY.md` and `export.py` are shared, never push a stale copy.
- What cannot be finished is stated in DIARY as not completed, with the reason. No placeholders.

## ENG-009 Signing: asymmetric signatures, trusted timestamps, standalone verifier (Export and Integrity Engineer)

**Order:** ENG-001 first (the exported file must pass `--verify-package`, signed too; test through the real CLI export path). Then this.

**Why:** HMAC cannot be verified by a third party. Evidentiary use needs a signature anyone can check from a public key, a time attestation, and a verifier that does not need CueLiez installed.

**In scope:**
- Design note first (`docs/design/SIGNING_DESIGN.md`, short): algorithm choice and why; how signing works with zero runtime dependencies (the stdlib has no asymmetric signing; evaluate an optional `cryptography` extra and an external signer command for HSM, KMS or PKCS#11 so the private key never enters CueLiez); signature object format; key-status records. State the constant-time and key-handling limits of any pure-Python path honestly. Push the design before the code; the lead dev reviews it.
- Ed25519 signature type alongside `hmac-sha256` (HMAC stays, labelled symmetric, not suitable for third-party verification). The signature object carries `key_id`, `alg`, `signed_hash` and a public key or certificate reference.
- Pluggable signer: operator supplies a key file, certificate chain, or external command. ECDSA or RSA where a CA or HSM requires it, if the design supports it.
- Key rotation and revocation: signed key-status records (valid-from, valid-until, revoked-at, reason). The verifier reports key status at `signed_at` and at verification time.
- RFC 3161 timestamping against an operator-configured TSA URL, going through the existing connector egress rules and audit events. Token stored in the package signature block. The verifier checks the message imprint equals the package hash, reports `genTime`, and verifies the TSA signature against an operator-supplied trust file. If any part cannot be verified on stdlib, the verifier says which part it did not do and prints the exact `openssl ts -verify` command; it never reports `ok` for a part it skipped.
- Standalone dependency-free verifier: a single file runnable as `python cueliez_verify.py package.json [--pubkey ...] [--key-status ...] [--tsa-trust ...]`, plus a `cueliez verify` subcommand using the same code. Documented offline procedure in `docs/deployment/KEY_CUSTODY.md` or a new verification doc.
- Published JSON Schema for the sealed package (`docs/schemas/`), a schema validator in the verifier, and a conformance suite with fixed vectors (RFC 8032 test vectors for Ed25519; at least one sealed fixture per signature type, including tampered, wrong-key, revoked-key and wrong-timestamp negatives).
- Docs state the legal boundary above. Do not edit TODO.md (PM does).

**Acceptance criteria:**
- AC1 [behavior] An Ed25519-signed export verifies with only the public key and the standalone verifier on a machine with no CueLiez install and no private key. Verify: a test runs the verifier file in a subprocess with `-I` and an empty `PYTHONPATH`.
- AC2 [failure-path] Tampered content, tampered `signed_hash`, wrong public key, key revoked before `signed_at`, expired key, unsupported algorithm, and an HMAC package presented as third-party-verifiable each fail with a distinct reason code.
- AC3 [behavior] A timestamp token from a locally generated test TSA verifies; a token for a different hash, a tampered token and an untrusted TSA certificate each fail with distinct codes.
- AC4 [behavior] RFC 8032 vectors pass in the pure verifier.
- AC5 [behavior] The schema validates every exported fixture and rejects a package missing `package_hash`.
- AC6 [failure-path] A missing optional library, an unreachable TSA and a failing external signer each produce a named error and no sealed file (this also closes the reviewer finding that `sign_package` swallows signer errors).

## ENG-010 Vendor connectors: Axon, CaseCracker, RMS, case and evidence systems (Ingest and Connectors Engineer)

**Why:** The owner wants real adapters, not only the generic HTTP connector. This supersedes the "integrations are post-pilot" lines in the roadmap (PM records the dated decision).

**In scope:**
1. Evidence table first: `docs/design/VENDOR_CONNECTORS.md`. One section per vendor and system class (Axon Evidence, CaseCracker, RMS, case and evidence management; the PM supplies named RMS and case systems, start with whatever you can find documented). For each: what the vendor publicly documents (URL, access date, quoted endpoint or field names), what sits behind a partner agreement and is not visible to us, what credentials or sandbox access are needed, and a `verified` status. Use web search and fetch. Do not infer from other vendors.
2. Adapter framework: adapters are classes with a validated config schema (secrets from env or file, never argv), the auth flow as documented (API key, OAuth 2 client credentials, whichever the vendor documents), idempotency keys, retry and backoff honouring `Retry-After`, payload limits, audit events, secret redaction in logs, and the egress rules inherited from `connectors.py`. Keep `cueliez.connectors` imports working.
3. For each vendor with public documentation: an adapter built only from that documentation, tested against fixtures whose provenance (doc URL and section) is recorded next to the fixture. For each vendor without it: no adapter code; an entry in DIARY under "not completed" naming the document or credential needed. Adapter metadata carries `verified: false` where any part is untested against the live system, and CLI output shows it.
4. Direction in: vendor transcript export to ingest (use the `ingest.py` strict path and the vendor normaliser already in the repo). Direction out: sealed package attached as an original artifact with hash, signature and chain-of-custody metadata mapped to the vendor's documented fields (TODO 9.7).
5. CLI: `cueliez connector {list,validate-config,push,pull}` registered in `SUBCOMMANDS`.
6. Live calls only when the operator sets an explicit opt-in env var and the target host is allowlisted; the default test suite never touches the network.

**Acceptance criteria:**
- AC1 [behavior] For each implemented adapter, push and pull against a local server that replays the documented contract (headers, auth, body shape, status codes) succeed and the sealed package round-trips with `hash_ok: true`.
- AC2 [failure-path] 401, 403, 404, 409 (duplicate idempotency key), 429 with `Retry-After`, 5xx, oversize body, malformed JSON and a redirect to a blocked host each map to a named `ConnectorError` code; secrets never appear in audit output (a test greps the audit log).
- AC3 [failure-path] Invalid or incomplete config fails at `validate-config` with the missing field named, before any request.
- AC4 [behavior] A retried POST sends the same idempotency key; a replay does not create a second attachment on the replay server.
- AC5 [process] Every adapter and fixture cites its documentation; DIARY lists each vendor as done or not completed with the missing item.

## ENG-011 Accessibility: officer surfaces and exports (Officer UI Engineer)

**Why:** The owner wants accessibility features. Officers and reviewers use these pages under time pressure; keyboard-only and screen-reader use has to work, and nothing may rely on colour alone.

**In scope:**
- Shared checks in `tests/a11y_checks.py` (stdlib `html.parser`, plus the existing `tests/js_dom_harness.py` for live behaviour): `lang`, landmarks, skip link, heading order, form labels, accessible names for buttons, `aria-live` politeness, priority never conveyed by colour alone, computed colour contrast from the CSS values (WCAG AA ratios), visible focus, `prefers-reduced-motion`, relative text units and no clipping at 200 percent zoom (CSS check), tab order. Land this harness first and say so in DIARY; ENG-012 uses it.
- Apply to: live dashboard, onscreen cue renderer, officer notes and review page, export HTML summaries (`export.py` is also being edited for ENG-001 and ENG-009: pull before every edit, keep commits small).
- Live cue region: polite, batched, does not re-announce unchanged cues, has a pause control; keyboard shortcuts to pause and to dismiss; documented in `docs/ACCESSIBILITY.md`.
- Subject-not-shown default and observation-only wording unchanged; priority shown as text plus shape, not colour only.
- `docs/ACCESSIBILITY.md`: what is checked automatically, which WCAG 2.2 criteria that covers, and what is not tested (no manual screen-reader pass has been done; say so). Do not claim conformance.

**Acceptance criteria:**
- AC1 [behavior] Every surface passes every check in the harness. Verify: `tests/test_accessibility.py`.
- AC2 [failure-path] The harness fails on seeded defects: missing label, colour-only priority, low contrast, unlabelled button, assertive live region. Verify: tests that feed broken HTML.
- AC3 [behavior] With the DOM harness, a burst of 50 cues produces bounded live-region updates and no repeat announcement of an unchanged cue.
- AC4 [behavior] Every control on the dashboard is reachable and operable by keyboard events alone.

## ENG-012 Accessibility: Training GUI (Training and Certification Engineer)

Same requirements and the same harness as ENG-011, applied to `training_gui.py` (module pages, assessment forms, media, captions). Training videos need captions or a transcript link; the page must not print server paths (open reviewer finding) and must not show "no media" for the optional webm. Wait for `tests/a11y_checks.py` from ENG-011; until it lands on main, fix the semantics and the reviewer findings. Acceptance: the harness passes on every Training GUI page; keyboard-only completion of an assessment is tested; seeded-defect failure tests are included.

## ENG-013 Retention: policy, legal hold, sweep, deletion with receipts, redaction (Gates and Seal Engineer)

**Why:** `retention.py` computes a policy and nothing enforces it. The owner wants a real implementation.

**Order:** design note first (`docs/design/RETENTION_DESIGN.md`, short), pushed before code. It must settle the open conflict between a tamper-evident sealed record and erasure: sealed packages stay immutable; erasure produces a tombstone plus a signed deletion receipt that keeps `package_hash`, what was removed, when, under which policy, the hold check result and the operator ID, but not the content. If field-level redaction needs per-field commitments in the sealed package (salted digests of redactable fields so a redacted derivative can still be tied to the original hash), say so; that is a seal-format change and needs the Export and Integrity Engineer (ENG-009) and a schema version bump. State what a verifier can and cannot conclude from a redacted derivative.

**In scope:**
- Operator policy file (per mode and jurisdiction: retention period, hold rules). The 3/5/7-year table in `retention.py` has no source: remove it as a default. With no policy configured, nothing is marked expired. The PM decides example values (PRODUCT QUESTION below).
- Legal-hold registry: add, release, list; each record has an ID, reason, placed-by and timestamps; a held package cannot be deleted or redacted-for-expiry; every change audited.
- Sweep: scans a package store directory, evaluates policy and holds, prints a report. Dry run is the default; `--execute` deletes. Idempotent so cron or a systemd timer can run it; ship real example timer and cron units in `docs/deployment/` and test the command they call.
- Secure deletion: delete package files plus their exports; state honestly in docs what overwrite can and cannot achieve on SSD, journaling and copy-on-write storage and what the operator must do (encrypted volume, key destruction). The receipt records what was done, no more.
- Deletion receipt: JSON, hash-chained to the previous receipt, signed through `signing.py` when a key is configured; `cueliez retention verify-receipts` checks the chain.
- Redaction of the redactable fields for secondary sharing with a redaction record; keep `redact_for_secondary_sharing` behaviour or replace it with the new tested path.
- CLI `cueliez retention {check,sweep,hold,release,redact,verify-receipts}` registered in `SUBCOMMANDS`; audit events for every action.

**Acceptance criteria:**
- AC1 [behavior] Sweep dry run changes nothing on disk and lists the right candidates; `--execute` deletes only expired, unheld packages and writes one receipt each.
- AC2 [failure-path] A held package is never deleted by sweep or by direct delete; releasing the hold allows it; deleting with no policy configured is refused.
- AC3 [failure-path] A tampered receipt, a removed receipt (chain gap) and a reordered chain each fail `verify-receipts` with distinct codes.
- AC4 [behavior] A redacted derivative carries a record naming the original `package_hash` and the removed fields, and `verify` reports it as a redacted derivative, never as the original.
- AC5 [behavior] `retention.py` is imported by the CLI path; no dead code remains; no hard-coded retention defaults.
- AC6 [process] DIARY states the tamper-evidence versus erasure position and what is left to counsel and the operator.

## Product manager: do and answer

- Record the owner decision (dated) in `docs/OWNER_DECISIONS.md`: vendor adapters, asymmetric signing and timestamps, accessibility and retention enforcement are now in scope, superseding the "post-pilot" wording.
- Fix `TODO.md`: Phase 3.3 and Admissibility signature text (signing exists; HMAC only until ENG-009 lands), Phase 7 connector items, the retention item, the accessibility item (L234), 9.6 and 9.7. Items stay `[ ]` or `[~]` until code, tests and checks land; the lead dev confirms each.
- PRODUCT QUESTION: Which RMS and case or evidence systems, by name, are pilot-relevant after Axon and CaseCracker? The connector engineer researches in that order.
- PRODUCT QUESTION: Retention example values per mode, and who confirms them (counsel or the pilot agency). Engineering ships no defaults.
- PRODUCT QUESTION: Multilingual scope. Observers and the banned-language scan are English only. Non-English cue text would bypass the language gate unless the scan is extended per language. Options: (a) multilingual interface strings and documentation only; cue wording stays English; non-English transcripts are ingested but observers report insufficient data with a language flag; (b) per-language cue templates, each reviewed by the Language Auditor. The lead dev recommends (a) now. Decide before any engineering starts on it.
- PRODUCT QUESTION: Default TSA policy. None configured by default; the operator supplies the TSA URL and trust file? The lead dev recommends yes: CueLiez must not send package hashes to a third party unless the operator configured it.
