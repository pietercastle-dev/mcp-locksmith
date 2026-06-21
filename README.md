# mcp-locksmith

**Safely connect tools to Claude — without leaking your keys into the chat.**

Claude Code can use external **tools** (called "MCP servers") — a web browser,
Slack, your notes, a database, and more. Wiring them up by hand is fiddly, and it's
easy to accidentally leave an API key or password somewhere it shouldn't be — in a
config file, or even pasted into the chat. mcp-locksmith makes adding tools **safe
and simple**:

- 🔑 **Your keys stay in your vault** — never written into config, never shown to Claude.
- ✅ **New tools get vetted** — a quick safety check before you trust one.
- 🛡️ **Automatic guardrails** — blocks secrets from leaking, and warns you if a tool changes after you approved it.
- 🧰 **Guided setup** — Claude walks you through it; you don't need to be technical.

## Start here (about 2 minutes)

**1. Install it** — paste these into Claude Code:

```
/plugin marketplace add <your-github>/mcp-locksmith
/plugin install mcp-secure@mcp-locksmith
```

**2. Let Claude set up the rest:**

```
/mcp-secure:setup
```

That's it. The setup walks you through everything in plain language and gets a
first tool working. You only need a key vault if a tool you add requires a password
or API key — and setup will guide you if so.

## What you can do

| Command | What it does |
|---------|--------------|
| `/mcp-secure:setup` | **Start here** — guided first-time setup |
| `/mcp-secure:add` | Add a tool to the current project — a ready-made one (e.g. a browser), or a brand-new one it safety-checks first |
| `/mcp-secure:check` | Check that everything's healthy |
| `/mcp-secure:verify` | Detect if a tool changed since you approved it |
| `/mcp-secure:always-on` | Set up an always-on tool (e.g. Slack everywhere) |

## How it keeps your keys safe (in one paragraph)

You never put a password in a config file. You store it once in a vault you already
trust — **1Password, Bitwarden, or SOPS** — and mcp-locksmith fetches it only at the
moment a tool starts up. So the key never lands on disk and never reaches the chat.
If anything tries to write a raw secret into your config, a built-in guard blocks
it automatically.

## For technical users

The full design — the `mcp-secret` resolver and reference syntax, `mcp-launch`
secret injection, the project-vs-global scoping model, tool-pinning (rug-pull
detection), and the complete security model — lives in
**[`plugins/mcp-secure/README.md`](plugins/mcp-secure/README.md)**.

## What's in this repo

A Claude Code **plugin marketplace** with two plugins:

| Plugin | Install where | What it is |
|--------|---------------|------------|
| **mcp-secure** | everywhere | The toolkit above: safe tool setup, vetting, guardrails. |
| **mcp-globals** | where you want them (template) | Your always-on tools (e.g. Slack at work, a personal set at home). Copy per profile. |

```
.claude-plugin/marketplace.json   # lists the plugins
plugins/mcp-secure/               # the toolkit (commands, hooks, helpers, bundles)
plugins/mcp-globals/              # template for always-on tools
install.sh                        # one-time: puts the helpers on PATH + saves your vault choice
```

## License

MIT — see [LICENSE](LICENSE).
