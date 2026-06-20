---
description: Set up always-on (global) MCP servers that load in every repo
---

Help the user manage the **global tier** — MCP servers that load in *every* repo
(e.g. Slack at work). Reserve it for genuinely cross-context servers; most belong
in a project bundle (`/mcp-secure:mcp-setup`) or a single repo (`/mcp-secure:mcp-add`).

There are two ways to run a global server. Recommend based on the situation:

**A) A profile of globals (e.g. team set at work, personal set at home) → a globals
plugin.** If a set of servers should always be on in some environment, they belong
in a dedicated plugin (see the `mcp-globals` template in the marketplace repo; copy
it per profile like `acme-globals` / `home-globals`). To add one:
1. Vet it against `VETTING.md` (provenance, pinned version, least privilege). A
   global server runs everywhere — vet it at least as hard as a project one.
2. Add it to that plugin's `.mcp.json` using `${CLAUDE_PLUGIN_ROOT}/bin/mcp-launch`
   with a fully-qualified secret ref (e.g. `op://Work/<item>/<field>`). Never inline a token.
3. Publish the plugin; teammates install it on the machines where it applies.

**B) Personal globals (home, just a few) → user scope.** For one or two personal
always-on servers, skip the plugin overhead:
1. Vet it the same way.
2. `claude mcp add -s user <name> -- mcp-launch --secret NAME=<ref> -- <server> <args>`
   (the guard will ask you to confirm the global scope). For secrets, route through
   `mcp-launch` exactly as above — never `-e TOKEN=<literal>`.

Always: keep the global set small and deliberate; project scope is the default.
Remind the user that user-scope / plugin changes load on the next session start.
