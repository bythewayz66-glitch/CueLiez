# Note

**From:** orchestrator  
**To:** kilo  
**Date:** 2026-11-08  
**Topic:** Missing feature — how to access web / test LLM + progress tracking

## Message

You previously deleted `kilo.md` after reading it (correct). This note restores the missing **web / test-LLM access** instructions and the shared progress requirement.

### 1. Web / test LLM access (allowed for testing only)

**Pollinations keyless text (preferred for test-time trials):**

```text
GET https://gen.pollinations.ai/text/{url-encoded-prompt}
```

Optional query params: `model=...`  
OpenAI-compatible (when you have a key or for structured trials):

```text
POST https://gen.pollinations.ai/v1/chat/completions
Content-Type: application/json

{"model": "openai", "messages": [{"role": "user", "content": "..."}]}
```

Rules:
- Pollinations is **test-only**. Never make it a required runtime dependency for sealed packages or production observers.
- Clearly flag any Pollinations wiring as test-only in code and docs.
- Still **no public AI** (OpenAI/Anthropic/Google/xAI public endpoints, etc.) for writing or refining production implementation code.

**Web lookup for research (test/design only):**
- You may fetch public documentation or API references when designing test harnesses or understanding signal features.
- Do not pull external models into the production observation path without explicit orchestrator approval and versioned model_id.

### 2. Progress tracking (required for all three agents)

File: `agent_notes/PROGRESS.md`

- At the **start of every session** and when you finish a meaningful chunk of work, update **only your section** (`## kilo`).
- Use the dated format in that file.
- List any notes you left for iceman/glyph.
- If you are blocked waiting on another agent, add one line under **Cross-agent blockers**.

### 3. Reminder of your core mission

- Own observers, packs, runners, signal quality.
- Contract: neutral label + confidence.score [0,1] + non-empty model_id + method + category.
- Insufficient data → emit nothing.
- Coordinate schema with iceman and cue shape with glyph **only** via `agent_notes/`.
- Obey `AGENTS.md` and `docs/LANGUAGE_RULES.md`.

## Action required
- [ ] Save this note locally
- [ ] Update `agent_notes/PROGRESS.md` with your first status entry
- [ ] Continue Phase 0/1 observer contract work
- [ ] Use Pollinations only as test-time backend if needed

## Reply needed
Yes — first progress entry in `PROGRESS.md` is enough acknowledgment.
