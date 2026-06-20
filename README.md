# mcp-locksmith

A Claude Code **plugin marketplace** for managing MCP servers securely across a
team. The core problem it solves: the default ways of installing MCP servers tend
to leak secrets into config files and into the model's context. This keeps
credentials in your vault, resolved only at spawn.

## Plugins in this marketplace

| Plugin | Install where | What it does |
|--------|---------------|--------------|
| **mcp-secure** | everywhere | The machinery: secret resolver + `mcp-launch`, a vetting flow for new servers, and guard hooks. Secrets never hit disk-config or context. |
| **mcp-globals** | where the profile applies (template) | A profile of always-on servers (e.g. Slack at work, or a personal home set), loaded in every repo. Copy/rename per profile. |

## Quick start

```
/plugin marketplace add <this-repo-url>      # or a local path
/plugin install mcp-secure@mcp-locksmith
bash <this-repo>/install.sh                   # one-time: resolver on PATH + backend
```

Also publish & install a filled-in globals profile where you want always-on
servers (see `plugins/mcp-globals/README.md`) — e.g. an `acme-globals` at work or a
`home-globals` at home. Or skip it and add the odd personal always-on at user scope.

## The model

- **Project tier (default):** per-repo `.mcp.json`, populated from vetted bundles
  via `/mcp-secure:mcp-setup` or new servers via `/mcp-secure:mcp-add`.
- **Global tier (curated):** always-on servers. Team-shared → a globals plugin;
  personal → user scope. Managed via `/mcp-secure:mcp-global`.
- **Secrets:** never inlined. OAuth where possible; otherwise `mcp-launch` resolves
  a reference (`op://` / `sops://` / `bw://`) at spawn. A guard hook blocks literal
  secrets in any MCP config and confirms global-scope additions.

See [`plugins/mcp-secure/README.md`](plugins/mcp-secure/README.md) for the full
secret model, reference syntax, and security notes.

## Why a plugin (not an installer)

Earlier this was a hand-rolled `install.sh` that symlinked hooks and merged
settings. Claude Code plugins do that natively — versioned, installable via
`/plugin install`, updatable via `/plugin update` — so the harness rides that
instead of reinventing it. `install.sh` survives only for the one thing a plugin
can't do: put the resolver on your PATH and configure your backend.

## Repo layout

```
.claude-plugin/marketplace.json   # lists the plugins
plugins/
  mcp-secure/                     # the machinery plugin
    .claude-plugin/plugin.json
    bin/        mcp-secret, mcp-launch, mcp-bundles
    hooks/      hooks.json + mcp-guard.py, mcp-nudge.py
    commands/   mcp-setup, mcp-add, mcp-global
    bundles/    frontend, example-secret
    VETTING.md, README.md
  mcp-globals/                    # template for an always-on server profile
install.sh                        # one-time machine setup (PATH + backend)
CLAUDE.snippet.md                 # paste into your CLAUDE.md
```
