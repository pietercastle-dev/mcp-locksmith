# mcp-locksmith

**The easiest way to give Claude new tools, safe by default.**

Claude Code can use external **tools** (called "MCP servers"): a web browser,
Slack, your notes, a database. Adding one normally means editing JSON by hand and
pasting an API key into a config file. mcp-locksmith lets you just ask: say
*"add a Slack tool"* and Claude sets it up. Your key goes into the vault you
already use, never into config and never shown to Claude. New tools get a quick
safety check, and built-in guards catch leaks and warn you if a tool changes
after you approved it.

Other ways to lock down MCP tools ask you to run something extra: a cloud
scanner your config uploads to, a Docker runtime wrapped around every server, or
a proxy gateway to route through. mcp-locksmith is just local scripts and hooks
that run inside Claude Code. No cloud account, no containers, no gateway, and
nothing phones home.

## Install (about 2 minutes)

```
/plugin marketplace add pietercastle-dev/mcp-locksmith
/plugin install mcp-secure@mcp-locksmith
/mcp-secure:setup
```

That's the whole install. `/mcp-secure:setup` gets your first tool working and
handles the rest. You only need a vault if a tool requires a key.

## Requirements

**Claude Code** on **macOS or Linux** (Windows via WSL; the helpers are
bash/python scripts). Then, only as you need them:

- **To run most tools:** Node.js (`npx`) and/or Python (`uvx`). `python3` also
  runs the secret-leak guard hook, so without it that guard silently won't run.
- **Only if a tool needs a key:** one vault CLI, either **1Password** (`op`),
  **Bitwarden** (`bw`), or **SOPS** (`sops`). Setup helps you pick; secure
  step-by-step for each is in **[`BACKENDS.md`](plugins/mcp-secure/BACKENDS.md)**.

## What you can do

You usually **don't need to type these**. Just ask in plain language ("add a
Slack tool", "remove the GitHub server", "are my tool keys safe?") and the
matching flow runs automatically.

| Command | What it does |
|---------|--------------|
| `/mcp-secure:setup` | **Start here.** Guided first-time setup |
| `/mcp-secure:add` | Add a tool to this project, ready-made or safety-checked first |
| `/mcp-secure:update` | Update tools; preview what a new version changes before taking it |
| `/mcp-secure:fix` | Diagnose and fix a tool that isn't working |
| `/mcp-secure:remove` | Remove a tool and revoke its key |
| `/mcp-secure:audit` | Review tools you **already** had and bring them into the safe setup |
| `/mcp-secure:check` | One health check: secrets resolve, no tool changed since approval |
| `/mcp-secure:verify` | Focused drift-only check (also rolled into `check`) |
| `/mcp-secure:always-on` | Set up an always-on tool (e.g. Slack everywhere) |

> **Already have tools set up?** Installing this plugin doesn't change or inspect
> them. Run `/mcp-secure:audit` once to review and adopt them.

## How it keeps your keys safe

You store a key once in a vault you already trust; config holds only a
*reference*, resolved at the moment the tool starts. The key never lands on disk
and never reaches the chat. Around that sit several checks, so a gap in one is
covered by another:

1. **Add-time vetting.** Provenance, pinned version, least privilege, and a
   tool-poisoning check. See **[`VETTING.md`](plugins/mcp-secure/VETTING.md)**.
2. **Config guard.** A hook blocks literal secrets from being written into
   config and flags global-scope changes. A best-effort safety net, not a sandbox.
3. **Call guard.** A hook watches outbound tool calls and checks with you if a
   credential-shaped value is about to leave through one (the classic
   poisoned-tool move), or on first use of a tool that was never pinned. It asks,
   never blocks.
4. **Drift detection.** `/mcp-secure:check` warns if an approved tool changes
   its capabilities later (a "rug-pull"). When a check is due, the reminder
   appears inside Claude's first reply of the session, not as a separate popup.
5. *Optional:* [Socket Firewall](https://github.com/SocketDev/sfw-free) (`sfw`)
   for install-time supply chain, and deeper scanners on demand (see `VETTING.md`).

## How it compares

Other MCP security tools are good at what they do, and most add a piece of
infrastructure to do it. mcp-locksmith deliberately adds none: it runs as local
scripts and hooks inside Claude Code. The honest trade is that it's
defense-in-depth and secret hygiene, not a scanner or a sandbox, so it pairs
well with the tools below rather than replacing them.

| Tool | Approach | What it needs | Strongest at |
|------|----------|---------------|--------------|
| **[mcp-scan](https://github.com/invariantlabs-ai/mcp-scan)** (Invariant Labs / Snyk) | Scans tool descriptions for poisoning and injection; can proxy traffic at runtime | A Snyk account and API token; shares tool names and descriptions with the cloud | Deep tool-poisoning and prompt-injection analysis |
| **[ToolHive](https://github.com/stacklok/toolhive)** (Stacklok) | Runs each server in an isolated container with scoped permissions and network isolation | Docker or Podman (Kubernetes for teams) | Real sandbox isolation and network egress control |
| **MCP gateways** ([IBM ContextForge](https://github.com/IBM/mcp-context-forge), Docker MCP Gateway, Lasso) | A proxy in front of every server for aggregation, guardrails, and central policy | A deployed, self-hosted gateway service | Org-wide policy enforcement and aggregation |
| **mcp-locksmith** | Vault-reference secrets, local tool pinning, runtime leak guards, plain-language flows | Nothing beyond Claude Code (a vault CLI only if a tool needs a key) | Zero-setup adoption; keys never in config or context |

They aren't mutually exclusive: run mcp-locksmith for everyday tool adoption and
secret hygiene, and reach for a scanner or a sandbox when you need deep analysis
or hard isolation.

## For teams

An optional `org.json` points everyone at your internal MCP docs and recommended
tools, surfaced in the flows but never enforced. Keep your vetted sets as private
bundles. See **[`ORG.md`](plugins/mcp-secure/ORG.md)**.

## For technical users

The full design (the `mcp-secret` resolver, `mcp-launch` injection, scoping
model, tool pinning, and the complete security model) lives in
**[`plugins/mcp-secure/README.md`](plugins/mcp-secure/README.md)**.

## What's in this repo

A Claude Code **plugin marketplace** with one plugin, **`plugins/mcp-secure/`**
(the toolkit). Always-on team tools are scaffolded from a bundled template
(`plugins/mcp-secure/templates/globals-profile/`) by the `always-on` flow.
`install.sh` is a one-time step that puts the helpers on PATH and saves your
vault choice.

## Releases, trust & updates

Installing this plugin lets its code run as a hook and resolve your vault
secrets, so treat updates as a trust decision: **pin to a tagged release** and
review changes (especially `hooks/` and `bin/`) before updating. `install.sh`
symlinks the helpers, so checking out a tag pins the executed code too. Threat
model and vulnerability reporting: **[SECURITY.md](SECURITY.md)**. What's
shipped: [CHANGELOG.md](CHANGELOG.md). Where it's headed: [ROADMAP.md](ROADMAP.md)
and the detailed [PLAN.md](PLAN.md).

## License

MIT. See [LICENSE](LICENSE).
