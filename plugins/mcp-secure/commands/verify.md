---
description: Pin MCP servers' tools and detect drift (rug-pull defense)
---

**How to talk to the user:** plain, friendly language (same tone as
`/mcp-secure:setup`). Say "tool" rather than "MCP server", and explain results in
everyday terms rather than pasting raw output.

Use the `mcp-pin` helper (on PATH) to record an approved baseline of each
tool's capabilities and detect when a tool changes them after approval (a "rug-pull").
It auto-discovers servers wherever they live: `~/.claude.json` (user scope + this
project) and `./.mcp.json`, so it works with or without a repo. Pins are stored
per-user; no committed file required.

How it works: `mcp-pin` speaks the MCP protocol to each server, launching stdio
servers briefly, or POSTing to streamable-HTTP ones (honoring the config's
`headers`/`headersHelper`), reads its `tools/list`, and hashes each tool's
name/description/schema.

Commands:
- `mcp-pin` (or `mcp-pin verify`): check all discovered servers against the baseline.
- `mcp-pin pin [name…]`: record/update the baseline (do this after vetting a server).
- `mcp-pin list`: show what's pinned.

Run `mcp-pin verify` and interpret the output for the user:
- **DRIFT** (a pinned tool changed): tell the user plainly: "this tool changed since
  you approved it. That can just be a normal update, but it can also be tampering,
  so it's worth a look before trusting it again." Re-vet (see VETTING.md), then
  `mcp-pin pin <name>` to re-approve.
- **not pinned**: review the server's tools for hidden instructions, then pin it.
- **unchanged**: all good.

Notes: verifying contacts each server briefly (resolving its secrets via mcp-launch),
so it's an on-demand check, not something that runs every session. A clean verify
stamps `lastVerified`, and the session nudge reminds the user when pinned tools
haven't been checked in `MCP_PIN_MAX_AGE` days (default 14). The known gap: a
remote server that authenticates via Claude Code's OAuth store can't be pinned
(that token isn't readable from outside). `mcp-pin` says so on a 401 rather than
pretending; explain it as "this tool signs in with OAuth, so the drift check
can't reach it yet". Legacy `type: "sse"` servers are skipped with a note.
Never print resolved secret values.
