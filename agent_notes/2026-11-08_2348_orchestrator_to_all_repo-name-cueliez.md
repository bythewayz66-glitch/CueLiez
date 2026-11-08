# Note

**From:** orchestrator  
**To:** all  
**Date:** 2026-11-08  
**Topic:** Repository name update — use **cueliez**

## Message

The repository name is now **`cueliez`** (lowercase). Update your local git remotes, docs links, and any hard-coded paths accordingly.

### Canonical references

| What | Value |
|------|--------|
| GitHub repo | `bythewayz66-glitch/cueliez` |
| Clone URL | `https://github.com/bythewayz66-glitch/cueliez.git` |
| Package (Python) | `cueliez` (unchanged) |
| Product display name | **CueLiez** (Cue + Legal Interview Engine) — unchanged |
| Pages (if enabled) | `https://bythewayz66-glitch.github.io/cueliez/` |

### What does **not** change
- Product name **CueLiez** and language rules
- Python import path `cueliez` / `src/cueliez/`
- Agent roles, `agent_notes/`, `PROGRESS.md`, Sprint 3 assignments
- No public AI / Pollinations test-only rules

### Actions required (each agent)
1. Point your local remote at `cueliez` if it still says `CueLiez`:
   ```bash
   git remote -v
   git remote set-url origin https://github.com/bythewayz66-glitch/cueliez.git
   git fetch origin
   git checkout main
   git pull origin main
   ```
2. Prefer lowercase `cueliez` in new links, clone instructions, and ops URLs.
3. Do not rename the product to “cueliez” in user-facing copy — keep **CueLiez**.
4. Continue Sprint 3 work on the updated remote; commit/push to `cueliez`.
5. Note in `PROGRESS.md` that remote was updated (one line is enough).

### GitHub case note
GitHub repo names are case-insensitive in URLs; `CueLiez` and `cueliez` often resolve to the same repo. Treat **`cueliez`** as the name you write in instructions and remotes from now on.

## Reply needed
One-line PROGRESS note after remote is verified.
