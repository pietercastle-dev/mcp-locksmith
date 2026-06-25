# Org configuration (optional)

For teams: point everyone at your internal MCP conventions without each person
rediscovering them. mcp-secure reads an optional **`org.json`** and *surfaces* it in
the flows — it never enforces policy or routes traffic. The plugin only **consumes**
this file; getting it onto machines is the org's job (onboarding script, dotfiles,
MDM, or bundling it in an internal plugin).

## Location

- `~/.config/mcp-secret/org.json` (default), or
- the path in `$MCP_ORG_CONFIG`.

## Schema

```json
{
  "org": "Acme",
  "docsUrl": "https://acme.example.com/wiki/mcp-patterns",
  "recommended": ["frontend", "acme-internal"],
  "gateway": { "url": "https://mcp-gw.acme.internal", "authRef": "op://Acme/mcp-gateway/token" },
  "policy": { "requireVetting": true, "preferGateway": true }
}
```

| Field | Used in v1 | Meaning |
|-------|-----------|---------|
| `org` | ✅ surfaced | Display name, shown in `/mcp-secure:check`. |
| `docsUrl` | ✅ surfaced | Your internal page (Confluence/Notion). Shown in `check`, the nudge, `add`, `setup`. |
| `recommended` | ✅ surfaced | Bundle names to suggest first in `/mcp-secure:add`. Pair with **private bundles** (`~/.config/mcp-secret/bundles/`) so your vetted sets are actually present. |
| `gateway.url` / `gateway.authRef` | ℹ️ info only | Shown as information. Routing/defaulting through the gateway is **not** built yet (see [ROADMAP.md](../../ROADMAP.md)). |
| `policy.*` | 🔒 reserved | Accepted but not enforced yet. The plugin's guard is advisory/defense-in-depth — org policy will be too. |

## What it does (and doesn't)

- **Does:** show your org name + internal docs link in the flows, and surface your
  recommended bundles so `add` offers them first.
- **Does not (yet):** route servers through a gateway, warn on direct servers, or
  enforce `policy`. Those need a real gateway to design against — deliberately deferred.

## Distributing it

Ship `org.json` however you already manage machine config — an onboarding step, a
dotfiles repo, your MDM, or inside a company **globals plugin** (see the `mcp-globals`
template). Keep your team's vetted server sets in private bundles
(`~/.config/mcp-secret/bundles/`, `mcp-bundles --user`) referenced from `recommended`.
