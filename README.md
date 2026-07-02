# mcp-locksmith

**Safely connect tools to Claude — without leaking your keys into the chat.**

Claude Code can use external **tools** (called "MCP servers") — a web browser,
Slack, your notes, a database. mcp-locksmith makes adding them safe and simple:
your keys stay in your vault (never in config, never shown to Claude), new tools
get a quick safety check, and built-in guardrails block leaks and warn you if a
tool changes after you approved it. Claude walks you through everything in plain
language.

## Before you start

You need **Claude Code**, plus:

- **To run most tools:** Node.js (`npx`) and/or Python (`uvx`). `python3` also
  runs the secret-leak guard hook — without it, that guard silently won't run.
- **Only if a tool needs a key:** one vault CLI — **1Password** (`op`),
  **Bitwarden** (`bw`), or **SOPS** (`sops`). Setup helps you pick; secure
  step-by-step for each is in **[`BACKENDS.md`](plugins/mcp-secure/BACKENDS.md)**.

## Start here (about 2 minutes)

```
/plugin marketplace add pietercastle-dev/mcp-locksmith
/plugin install mcp-secure@mcp-locksmith
/mcp-secure:setup
```

Setup walks you through the rest and gets a first tool working. You only need a
vault if a tool requires a key — setup will guide you if so.

## What you can do

You usually **don't need to type these** — just ask in plain language ("add a
Slack tool", "remove the GitHub server", "are my tool keys safe?") and the
matching flow runs automatically.

| Command | What it does |
|---------|--------------|
| `/mcp-secure:setup` | **Start here** — guided first-time setup |
| `/mcp-secure:add` | Add a tool to this project — ready-made, or safety-checked first |
| `/mcp-secure:update` | Update tools — preview what a new version changes before taking it |
| `/mcp-secure:remove` | Remove a tool and revoke its key |
| `/mcp-secure:audit` | Review tools you **already** had and bring them into the safe setup |
| `/mcp-secure:check` | One health check — secrets resolve, no tool changed since approval |
| `/mcp-secure:verify` | Focused drift-only check (also rolled into `check`) |
| `/mcp-secure:always-on` | Set up an always-on tool (e.g. Slack everywhere) |

> **Already have tools set up?** Installing this plugin doesn't change or inspect
> them. Run `/mcp-secure:audit` once to review and adopt them.

## How it keeps your keys safe

You store a key once in a vault you already trust; config holds only a
*reference*, resolved at the moment the tool starts. The key never lands on disk
and never reaches the chat. Around that, layered defenses — a miss in one is
caught by another:

1. **Add-time vetting** — provenance, pinned version, least privilege, a
   tool-poisoning check. See **[`VETTING.md`](plugins/mcp-secure/VETTING.md)**.
2. **Runtime guard** — a hook blocks literal secrets from being written into
   config and flags global-scope changes. A best-effort safety net, not a sandbox.
3. **Drift detection** — `/mcp-secure:check` warns if an approved tool changes
   its capabilities later (a "rug-pull").
4. *Optional:* [Socket Firewall](https://github.com/SocketDev/sfw-free) (`sfw`)
   for install-time supply chain, and deeper scanners on demand (see `VETTING.md`).

## For teams

An optional `org.json` points everyone at your internal MCP docs and recommended
tools, surfaced in the flows — never enforced. Keep your vetted sets as private
bundles. See **[`ORG.md`](plugins/mcp-secure/ORG.md)**.

## For technical users

The full design — the `mcp-secret` resolver, `mcp-launch` injection, scoping
model, tool pinning, and the complete security model — lives in
**[`plugins/mcp-secure/README.md`](plugins/mcp-secure/README.md)**.

## What's in this repo

A Claude Code **plugin marketplace**: **`plugins/mcp-secure/`** (the toolkit) and
**`plugins/mcp-globals/`** (a template for your always-on tools, copied per
profile). `install.sh` is a one-time step that puts the helpers on PATH and saves
your vault choice.

## Releases, trust & updates

Installing this plugin lets its code run as a hook and resolve your vault
secrets, so treat updates as a trust decision: **pin to a tagged release** and
review changes (especially `hooks/` and `bin/`) before updating. `install.sh`
symlinks the helpers, so checking out a tag pins the executed code too. Threat
model and vulnerability reporting: **[SECURITY.md](SECURITY.md)**. What's
shipped: [CHANGELOG.md](CHANGELOG.md). Where it's headed: [ROADMAP.md](ROADMAP.md)
and the detailed [PLAN.md](PLAN.md).

## License

MIT — see [LICENSE](LICENSE).
