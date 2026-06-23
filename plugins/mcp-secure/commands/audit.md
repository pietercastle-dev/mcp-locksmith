---
description: Review tools you already have and bring them into the safe setup
---

**How to talk to the user:** plain, friendly language (same tone as
`/mcp-secure:setup`) — say "tool" rather than "MCP server", explain the *why* in
everyday terms, don't dump raw output, and match their technical level. The numbered
steps below are for you, not the user.

Installing this plugin does **not** automatically touch tools the user already had.
This command is the catch-up pass: review the **already-installed** servers and bring
them into the safe setup.

**Scope — stay in your lane.** This is *config hygiene and adoption into this harness*,
**not** a security scanner. Do **not** try to deep-scan for tool-poisoning, provenance,
or CVEs — that's what Cisco `mcp-scanner` and Snyk `agent-scan` do (see `VETTING.md`).
For anything beyond the checks below, point the user at those tools rather than
reinventing them.

What to check, across the current repo's `.mcp.json` and `~/.claude.json` (user scope
+ this project's entry):

1. **Inline secrets → references.** Run `mcp-doctor`; it now flags any literal secret
   sitting in `env`/`args`. For each, offer to migrate it: move the value into the
   user's vault and rewrite the entry to launch via `mcp-launch` with a reference
   (`op://…` / `sops://…` / `bw://…`). This is the highest-value fix and the thing this
   harness uniquely does — lead with it. (Never print the resolved secret value.)
2. **Unpinned versions.** Flag servers launched with `@latest`, a bare `npx -y <pkg>`
   (no `@version`), or `uvx <pkg>` without a version. Offer to pin the current exact
   version — it's both reproducibility and the rug-pull defense.
3. **Plaintext transport.** Flag any `http://` (non-TLS) URL to a non-local host.
4. **Unpinned baselines.** Run `mcp-pin verify`; for each "not pinned" server, offer to
   review its tools and `mcp-pin pin <name>` so future `/mcp-secure:check` runs catch drift.
5. **Hand off the deep stuff.** If the user wants real provenance / tool-poisoning /
   vulnerability analysis, point them to `VETTING.md` and the optional scanners it
   names (Cisco `mcp-scanner` local-first, or Snyk `agent-scan`). Don't attempt it here.

How to run it:

- Present findings **per server**, in plain terms, worst-first (inline secrets before
  cosmetic stuff). Summarize: "3 tools look fine; 1 has a key in plain text I can move
  to your vault; 1 isn't version-pinned."
- Fix **with confirmation**, one change at a time. Migrating a secret edits config and
  needs the value put in the user's backend — walk them through it like `/mcp-secure:add` does.
- If everything's already clean, say so plainly and stop — don't invent work.

Constraints:
- Only edit the **current repo's** `.mcp.json` or the user scope a server actually
  lives in. Never delete a vault item or revoke a token yourself.
- Read-only by default until the user approves a specific fix.
