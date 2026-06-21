---
description: One health check — secret chain resolves, and no tool changed since approval
---

**How to talk to the user:** plain, friendly language (same tone as
`/mcp-secure:setup`). Translate the results — don't paste the raw ✔/✘ lines; tell
them in plain words what's working and what (if anything) needs fixing. Give them
**one** plain verdict at the end ("everything's healthy" / "one thing to look at: …").

This is the single "is everything OK?" command. It runs two checks and reports them
together:

**1. Secret chain** — run the `mcp-doctor` helper (on PATH):

```
mcp-doctor
```

It checks that `mcp-secret`/`mcp-launch` are reachable, the configured secret
backend is installed + authenticated, and every secret reference in `./.mcp.json`
(and `~/.claude.json`) actually resolves. To check specific files: `mcp-doctor path/to/.mcp.json`.

For each `✘`, explain in plain terms what's wrong and propose the concrete fix — e.g.:
- backend not authed → `op signin`, `bw unlock` (+ export `BW_SESSION`), or set up the age key.
- a reference fails to resolve → the secret is missing/misnamed in the backend, or the ref path is wrong.
- `mcp-launch` not on PATH → run the marketplace `install.sh`.

**2. Tool drift** — run `mcp-pin verify` to confirm no approved tool changed its
capabilities since you pinned it (the rug-pull defense):

```
mcp-pin verify
```

Fold the result into the same verdict:
- **DRIFT** (a pinned tool changed) → flag it plainly: "one tool changed since you
  approved it — could be a normal update, could be tampering, worth a look before
  trusting it again." Re-vet (VETTING.md), then `mcp-pin pin <name>` to re-approve.
  For a focused drift-only run, point them at `/mcp-secure:verify`.
- **not pinned** → mention they can pin approved tools so future checks catch changes.
- **unchanged** → just roll it into "everything's healthy".

Never print resolved secret values; both helpers already keep them out of output.
