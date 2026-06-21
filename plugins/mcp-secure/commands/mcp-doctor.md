---
description: Health-check the MCP secret chain for this repo
---

**How to talk to the user:** plain, friendly language (same tone as
`/mcp-secure:setup`). Translate the results — don't paste the raw ✔/✘ lines; tell
them in plain words what's working and what (if anything) needs fixing.

Run the `mcp-doctor` helper (on PATH) to check the setup for the current project:

```
mcp-doctor
```

It checks that `mcp-secret`/`mcp-launch` are reachable, the configured secret
backend is installed + authenticated, and every secret reference in `./.mcp.json`
(and `~/.claude.json`) actually resolves. To check specific files: `mcp-doctor path/to/.mcp.json`.

Read the output and, for each `✘`, explain in plain terms what's wrong and propose the concrete fix — e.g.:
- backend not authed → `op signin`, `bw unlock` (+ export `BW_SESSION`), or set up the age key.
- a reference fails to resolve → the secret is missing/misnamed in the backend, or the ref path is wrong.
- `mcp-launch` not on PATH → run the marketplace `install.sh`.

Never print resolved secret values; `mcp-doctor` already keeps them out of output.
