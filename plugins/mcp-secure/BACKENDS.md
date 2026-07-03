# Secret backends: secure setup

You only need a backend if a tool needs a password or API key. Pick **one** and
follow its section, then run `/mcp-secure:check` to confirm it's wired up.

| Backend | Best if… | CLI | Reference form |
|---------|----------|-----|----------------|
| **1Password** | you already use 1Password | `op` | `op://Vault/item/field` |
| **Bitwarden** | you want a free hosted vault | `bw` (+ `jq`) | `bw://item/field` |
| **SOPS + age** | you prefer files in git, no SaaS | `sops`, `age` | `sops://file#/key/path` |

**Install CLIs from the official source**: your OS package manager or the
vendor's signed installer, never a random `curl … | sh`.

---

## 1Password (`op`)

```sh
brew install 1password-cli   # others: developer.1password.com/docs/cli/get-started
```

Sign in via desktop-app integration (1Password app → Settings → Developer →
"Integrate with 1Password CLI"), then `op signin` and confirm with `op whoami`.

Config (`~/.config/mcp-secret/config`, written by `install.sh`):

```sh
MCP_SECRET_BACKEND=op
MCP_OP_VAULT=Private        # the vault short refs look in
```

References: `op://Private/cloudflare/token` (vault/item/field), or the short
form `cloudflare/token` via `MCP_OP_VAULT`. Scope tokens to least privilege.

---

## Bitwarden (`bw`)

```sh
brew install bitwarden-cli jq   # or: npm install -g @bitwarden/cli
```

Login is one-time; unlocking yields a session token you must export:

```sh
bw login                                  # one-time
export BW_SESSION="$(bw unlock --raw)"    # each new shell/session
bw status                                 # should say "unlocked"
```

`BW_SESSION` lives only in your current shell. Re-run the unlock when
`/mcp-secure:check` reports "locked"; never commit it.

Config: `MCP_SECRET_BACKEND=bw`. References: `bw://cloudflare/token`
(item/field; field defaults to the password field).

---

## SOPS + age (`sops`, `age`)

Encrypted secrets live in a file you can commit; only the **age private key**
decrypts. Nothing leaves your machine.

```sh
brew install sops age
mkdir -p ~/.config/sops/age
age-keygen -o ~/.config/sops/age/keys.txt   # install.sh offers to do this
chmod 600 ~/.config/sops/age/keys.txt
```

> 🔐 **Never commit `keys.txt`** (the private key), but do back it up; lose it
> and the secrets are unrecoverable. Commit only `.sops.yaml` and the encrypted
> files.

Point SOPS at the printed **public** key with a committed `.sops.yaml`:

```yaml
creation_rules:
  - path_regex: \.sops\.ya?ml$
    age: age1youragepublickeyhere…
```

Create/edit the secrets file (`sops ~/secrets.sops.yaml` opens `$EDITOR`,
encrypted on save) with nested keys:

```yaml
cloudflare:
  token: your-secret-value
```

Config:

```sh
MCP_SECRET_BACKEND=sops
MCP_SOPS_FILE=~/secrets.sops.yaml
```

References: `sops://~/secrets.sops.yaml#/cloudflare/token`, or the short form
`cloudflare/token` via `MCP_SOPS_FILE`. Non-default key location? Set
`SOPS_AGE_KEY_FILE` (or `SOPS_AGE_KEY`).

---

## Verify

`/mcp-secure:check` (or `mcp-doctor`) confirms the CLI is installed, you're
authenticated, and every reference in your config resolves, without ever
printing a secret value.

## Principles

- **One vault, referenced, never inlined.** Config holds references; values are
  fetched only at spawn.
- **Least privilege** for every API token.
- **Official installs only.**
- **Protect the root of trust**: your vault login or age private key gates
  everything else.
