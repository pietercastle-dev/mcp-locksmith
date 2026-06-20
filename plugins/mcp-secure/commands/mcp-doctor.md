---
description: Health-check the MCP secret chain for this repo
---

Run the `mcp-doctor` helper (on PATH) to verify the MCP setup for the current repo:

```
mcp-doctor
```

It checks that `mcp-secret`/`mcp-launch` are reachable, the configured secret
backend is installed + authenticated, and every secret reference in `./.mcp.json`
(and `~/.claude.json`) actually resolves. To check specific files: `mcp-doctor path/to/.mcp.json`.

Read the output and, for each `✘`, propose the concrete fix — e.g.:
- backend not authed → `op signin`, `bw unlock` (+ export `BW_SESSION`), or set up the age key.
- a reference fails to resolve → the secret is missing/misnamed in the backend, or the ref path is wrong.
- `mcp-launch` not on PATH → run the marketplace `install.sh`.

Never print resolved secret values; `mcp-doctor` already keeps them out of output.
