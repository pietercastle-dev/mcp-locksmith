# Roadmap

Shipped work is in [CHANGELOG.md](CHANGELOG.md). This file tracks deliberate future
direction, not a backlog.

## Org-level configuration

Let a company point its employees at internal MCP conventions without each person
rediscovering them. The plugin **consumes** an optional org config; it never tries to
*be* infrastructure.

**Shipped (the pointer layer) — see [`plugins/mcp-secure/ORG.md`](plugins/mcp-secure/ORG.md):**

- ✅ An optional `org.json` (`~/.config/mcp-secret/org.json` or `$MCP_ORG_CONFIG`) that
  the `add` / `setup` flows, the SessionStart nudge, and `/mcp-secure:check` **surface**:
  org name, a link to the internal Confluence/Notion page (`docsUrl`), and `recommended`
  bundles (offered first, pairing with private bundles). Distribution is the org's job
  (onboarding / dotfiles / MDM / an internal globals plugin).
- ✅ `gateway` fields are accepted and the URL is shown as **info**, so the schema is
  forward-compatible.

**Still to do (needs a real gateway to design against):**

- **Gateway routing — point-at only.** Default new servers to route through the org
  gateway, and warn when a direct (non-gateway) server is added. **The plugin must never
  implement gateway protocol, auth brokering, or audit** — that's infra the org runs.
  Deferred until there's a concrete gateway deployment to build/test against, not a guess.
- **Policy enforcement.** `policy.*` flags (`requireVetting` / `preferGateway`) are
  accepted but not acted on. When built, this stays **advisory / best-effort** (like the
  guard), not hard enforcement — and should be explicit about that.

**Non-goals:** don't build a gateway, a policy *enforcement* engine, or org-config
*distribution* — the plugin only reads a file an org provides.
