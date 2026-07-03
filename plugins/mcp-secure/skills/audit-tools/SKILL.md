---
name: audit-tools
description: Review the MCP tools / servers a user ALREADY has and bring them into the safe setup, e.g. "check my existing MCP servers", "are my tool API keys safe?", "I already have some tools set up", "review my mcp config for plaintext secrets". Use when the user wants to assess or clean up tools that predate this plugin. Config hygiene (migrate inline secrets to vault references, pin versions/baselines), not a deep vulnerability scanner.
---

The user wants to review tools they already have. Installing the plugin does not touch
pre-existing servers, so this is the catch-up pass. Run the mcp-secure *audit* flow.

Authoritative steps: read and follow `${CLAUDE_PLUGIN_ROOT}/commands/audit.md` in this
plugin (or find `commands/audit.md` under the mcp-secure plugin).

The essentials (apply even if you can't read the file):
- Run `mcp-doctor` (it flags literal secrets already in config) and `mcp-pin verify`
  (unpinned servers), across the repo's `.mcp.json` and `~/.claude.json`.
- **Lead with inline secrets:** for any literal key in `env`/`args`, offer to migrate it
  into the user's vault and relaunch via `mcp-launch` with a reference.
- Also flag unpinned versions (`@latest` / bare `npx -y`), `http://` to non-local hosts,
  and unpinned tool baselines (offer to `mcp-pin pin` after review).
- **Stay in your lane:** this is config hygiene, NOT a security scanner. For real
  provenance / tool-poisoning / CVE analysis, point the user to the scanners named in
  `VETTING.md` (Cisco `mcp-scanner`, Snyk `agent-scan`), don't reinvent them.
- Present findings per server, worst-first; fix only with confirmation. If everything's
  clean, say so and stop.
