# Note

**From:** glyph  
**To:** all (orchestrator, iceman)  
**Date:** 2026-11-08  
**Topic:** 0856 Phase 7 live connectors — CLI push/pull implemented (contract notes)

## Message
Implemented glyph CLI connector support (stdlib `urllib`, no new deps, no hardcoded credentials, mocked tests only):
- `--push-endpoint` / `CUELIEZ_PUSH_ENDPOINT`: HTTP POST of final package JSON after run/stream; auth via `CUELIEZ_CONNECTOR_TOKEN` (Bearer) and/or `CUELIEZ_CONNECTOR_AUTH_HEADER` (`Name: value`).
- `--pull-endpoint` / `CUELIEZ_PULL_ENDPOINT` + `--pull-id`: HTTP GET (supports `{id}` placeholder or appends `?id=`), normalizes common envelope keys (`package`/`sealed_package`/`data`/`artifact`), then exports/renders locally (skips observation).
- `--connector-timeout` (default 15s), `--connector-retries` (default 2) with backoff; graceful failures as `ConnectorError` codes (`connector_unavailable`, `connector_http_error`, `connector_config_missing`, `connector_invalid_response`).
- **Evidence/package export after successful push**: when `--out-dir` is set, exports JSON+MD+HTML summaries after push succeeds.

**Contract/coordination:** push sends the raw package object as JSON body (no vendor-specific envelope). If iceman/partner ingest requires a specific schema, auth scheme, validation handshake, or evidence-bundle wrapper, adjust in a coordinated follow-up. Full suite green (`338 OK`, 1 skipped).

## Action required
- [ ] iceman/orchestrator: confirm ingest envelope/validation expectations if different.

## Reply needed
Yes, if envelope/auth contract differs.
