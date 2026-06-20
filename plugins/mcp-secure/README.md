# mcp-secure

A Claude Code plugin that makes MCP servers **secret-safe by default**: credentials
are resolved at spawn from your vault, never stored in config, never reach the
model's context. It adds a vetting flow for new servers and guard hooks that stop
the common leak vectors.

## What it provides

| Component | Purpose |
|-----------|---------|
| `bin/mcp-secret` | Resolves a secret *reference* to plaintext from 1Password / SOPS / Bitwarden. |
| `bin/mcp-launch` | Generic launcher: injects resolved secrets into a server at spawn (env or CLI flag), then execs it. Replaces per-server wrapper scripts. |
| `bin/mcp-bundles` | Prints the path to the shipped bundles dir (used by `/mcp-setup`). |
| `bin/mcp-doctor` | Health-checks the chain: backend auth + every config reference resolves. |
| `bin/mcp-pin` | Pins each server's tool definitions and detects drift (rug-pull defense). |
| `commands/` | `/mcp-secure:mcp-setup`, `:mcp-add` (vetting), `:mcp-global`, `:mcp-doctor`, `:mcp-pin`. |
| `hooks/` | Guard (blocks literal secrets + confirms global scope) + nudge. |
| `bundles/` | Vetted, ready-to-add server sets (e.g. `frontend`). |
| `VETTING.md` | The security checklist `/mcp-add` enforces. |

## Install

```
/plugin marketplace add <this-repo>
/plugin install mcp-secure@mcp-locksmith
```

Then run the one-time machine setup (puts the resolver on PATH + picks your default
backend) — needed only if you use secret-backed servers in a repo's `.mcp.json`:

```
bash <this-repo>/install.sh
```

## How secrets work

You never put a secret in config — you put a **reference**, resolved at launch.

```jsonc
// in a server's .mcp.json entry
{
  "command": "mcp-launch",
  "args": ["--secret", "GITHUB_TOKEN=op://Work/github/token",
           "--", "github-mcp-server", "--read-only"]
}
```

`mcp-launch` resolves each `--secret NAME=ref` (or `--arg FLAG=ref` for flag-only
servers) via `mcp-secret`, injects it, and execs the server.

**Reference forms**

```
cloudflare/token            # short ref → machine default backend
op://Work/cloudflare/token  # 1Password (explicit)
sops://~/secrets.sops.yaml#/cloudflare/token
bw://cloudflare/token       # Bitwarden
```

**Machine default** (`~/.config/mcp-secret/config`) lets short refs resolve per
environment, so one config is portable across work/home:

```sh
# work laptop                 # home laptop
MCP_SECRET_BACKEND=op         MCP_SECRET_BACKEND=sops
MCP_OP_VAULT=Work             MCP_SOPS_FILE=~/secrets.sops.yaml
```

**HTTP servers:** prefer OAuth where supported (no static secret at all). If a
remote server needs a header, use a `headersHelper` that prints the header as JSON,
e.g. `printf '{"Authorization":"Bearer %s"}\n' "$(mcp-secret op://Work/x/token)"`.

## Adding servers — the priority order

1. **OAuth-capable?** Use it. No static secret. (`/mcp-secure:mcp-add` checks this first.)
2. **Token-only?** `mcp-launch` + a backend ref.
3. **Guard hook** is the backstop — it denies literal secrets in any `.mcp.json`
   and asks before a global (`-s user`) add.

Commands:
- `/mcp-secure:mcp-setup` — add a vetted bundle to this repo.
- `/mcp-secure:mcp-add` — vet + add a brand-new server (runs `VETTING.md`).
- `/mcp-secure:mcp-global` — set up an always-on server (team plugin or user scope).

## Tool pinning (rug-pull defense)

Vetting checks a server when you add it — but a server can change its tool
descriptions *after* you approve it (a "rug-pull"; tool descriptions are injected
into the model's context, so a changed one can carry new hidden instructions).
`mcp-pin` defends against that, locally and with no repo required:

```sh
mcp-pin pin       # record the approved tool baseline (after vetting)
mcp-pin verify    # re-check; flags DRIFT if a server's tools changed
mcp-pin list      # show what's pinned
```

It auto-discovers servers from `~/.claude.json` (user scope + current project) and
`./.mcp.json`, launches each stdio server, reads its `tools/list` over the MCP
protocol, and hashes each tool's name/description/schema. Pins are stored per-user
at `~/.config/mcp-secret/pins.json`, keyed by server identity (name + command +
args) — a version bump reads as "new, re-pin". `verify` launches servers briefly,
so it's an on-demand check, not a per-session cost. (stdio only for now.)

## Optional: package-install firewall (personal hardening)

MCP servers usually launch via `npx`/`uvx`, which pull packages at install — a
supply-chain surface. [Socket Firewall](https://github.com/SocketDev/sfw-free)
(`sfw`) blocks confirmed-malicious packages, free and tokenless. The harness
recommends running a new server's first install under it (`/mcp-add` reminds you):

```sh
npm i -g sfw
sfw npx -y some-mcp@1.2.3   # the first fetch is the exposure window
```

If you want it for **all** your installs, that's a personal choice — opt in yourself
rather than having a tool rewrite your shell. Paste into your shell rc only if you
accept the caveats below:

```sh
# ~/.zshrc — wrap interactive package installs with Socket Firewall
for pm in npm pnpm yarn pip uv; do alias $pm="sfw $pm"; done
```

Caveats, so you're not surprised: aliases fire only in **interactive** shells (not
scripts/CI/`npx` called by other tools), and `sfw` doesn't support **custom/private
registries** — it'll break installs that need one. The harness deliberately does
**not** edit your rc for you.

## Security model

- **At rest:** config holds references and `mcp-launch` invocations — no secrets.
- **In context:** secrets resolve in a subprocess; values never return to the model.
  The guard denies literal secrets written into MCP config.
- **Scope:** project by default; global is opt-in and confirmed.
- **Residual risk:** while a server runs, a secret passed as an argv flag (`--arg`)
  is visible in `ps` for that process. Prefer `--secret` (env) where the server
  supports it. Local-process exposure only — never on disk, never in context.

## Backends

| Backend | CLI | Reference | Notes |
|---------|-----|-----------|-------|
| 1Password | `op` | `op://vault/item/field` | `op signin` |
| SOPS+age | `sops` | `sops://file#/key/path` | age key configured |
| Bitwarden | `bw` (+`jq`) | `bw://item/field` | `bw unlock` + `BW_SESSION` |
