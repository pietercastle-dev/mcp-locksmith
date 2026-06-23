# Roadmap

Shipped work is in [CHANGELOG.md](CHANGELOG.md). This file tracks deliberate future
direction, not a backlog.

## v0.2 — org-level configuration

Let a company point its employees at internal MCP conventions without each person
rediscovering them. The plugin **consumes** an optional org policy; it never tries to
*be* infrastructure.

**Scope decided:**

- **Org pointer (do).** An optional `org.json` (well-known path like
  `~/.config/mcp-secret/org.json`, an `$MCP_ORG_CONFIG` path/URL, or bundled in a
  company's internal globals plugin — distribution is the org's job, via onboarding /
  dotfiles / MDM). The `add` / `audit` flows and the SessionStart nudge surface it:
  recommended bundles, and a link to the internal Confluence/Notion page.
- **Default gateway — point-at only (do, lightly).** If `org.json` names a gateway,
  store its URL + auth reference, default new servers to route through it, and
  optionally warn when a direct (non-gateway) server is added. **The plugin must never
  implement gateway protocol, auth brokering, or audit** — that's infra the org runs.
- **Policy surfacing (do, advisory).** Flags like `requireVetting` / `preferGateway`
  shape what the flows recommend. Like the guard, this is **advisory / best-effort**,
  not enforcement — be explicit about that.

Proposed shape (illustrative, not final — design against a real internal page first):

```json
{
  "org": "Acme",
  "docsUrl": "https://acme.atlassian.net/wiki/mcp-patterns",
  "recommended": ["frontend", "acme-internal-tools"],
  "gateway": { "url": "https://mcp-gw.acme.internal", "authRef": "op://Acme/mcp-gateway/token" },
  "policy": { "requireVetting": true, "preferGateway": true }
}
```

**Deliberately deferred / non-goals:**

- Don't build a gateway, a policy *enforcement* engine, or org config *distribution* —
  the plugin only reads a file an org provides.
- Don't commit to a gateway integration shape while MCP gateway standards are still
  emerging; design v0.2 against a concrete internal deployment, not a guess.

A small forward-compatible seam (flows surface `org.json` if present, shipping nothing
by default) can land earlier than the full feature if there's demand.
