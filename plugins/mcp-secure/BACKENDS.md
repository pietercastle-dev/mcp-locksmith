# Secret backends — secure setup

You only need a backend if a tool you add needs a password or API key. Pick **one**
(you can add others later) and follow its section. Then run `/mcp-secure:check` to
confirm it's wired up.

| Backend | Best if… | CLI | Reference form |
|---------|----------|-----|----------------|
| **1Password** | you already use 1Password | `op` | `op://Vault/item/field` |
| **Bitwarden** | you want a free hosted vault | `bw` (+ `jq`) | `bw://item/field` |
| **SOPS + age** | you prefer files in git, no SaaS | `sops`, `age` | `sops://file#/key/path` |

**Install CLIs from the official source** — your OS package manager (Homebrew below),
or the vendor's signed installer. Don't pipe a random `curl … | sh` from an
unofficial host. Verify you're getting the real vendor (publisher, stars, docs).

---

## 1Password (`op`)

**1. Install**

```sh
brew install 1password-cli          # macOS / Linuxbrew
# others: https://developer.1password.com/docs/cli/get-started/
```

**2. Sign in.** Easiest is desktop-app integration: open the 1Password app →
Settings → Developer → "Integrate with 1Password CLI", then:

```sh
op signin
op whoami        # confirms you're authenticated
```

**3. Tell mcp-secret your default vault** (so short refs like `cloudflare/token`
resolve). `install.sh` writes this; edit `~/.config/mcp-secret/config` if needed:

```sh
MCP_SECRET_BACKEND=op
MCP_OP_VAULT=Private        # the vault short refs look in
```

**4. Reference a secret** in a tool's config:

```
op://Private/cloudflare/token       # vault / item / field
cloudflare/token                    # short ref → uses MCP_OP_VAULT
```

Store the API key as an item in that vault; scope the token to least privilege.

---

## Bitwarden (`bw`)

**1. Install**

```sh
brew install bitwarden-cli          # macOS / Linuxbrew
# or: npm install -g @bitwarden/cli
brew install jq                     # required for bw refs
```

**2. Log in, then unlock.** Login is one-time; unlocking yields a *session token*
you must export so the CLI (and mcp-secret) can read items:

```sh
bw login                            # one-time
export BW_SESSION="$(bw unlock --raw)"   # each new shell/session
bw status                           # should say "unlocked"
```

> The `BW_SESSION` export lives only in your current shell. To persist it for
> spawned MCP servers, export it in your shell rc (`~/.zshrc`) **after** unlocking,
> or re-run the unlock when `/mcp-secure:check` reports "locked". Never commit it.

**3. Config** (`~/.config/mcp-secret/config`):

```sh
MCP_SECRET_BACKEND=bw
```

**4. Reference a secret:**

```
bw://cloudflare/token       # item name / field (defaults to the password field)
```

---

## SOPS + age (`sops`, `age`)

Encrypted secrets live in a file you can commit to git; only holders of the **age
private key** can decrypt. Nothing leaves your machine.

**1. Install**

```sh
brew install sops age               # macOS / Linuxbrew
# others: https://github.com/getsops/sops  +  https://github.com/FiloSottile/age
```

**2. Generate your age key** (the private key that decrypts everything — guard it):

```sh
mkdir -p ~/.config/sops/age
age-keygen -o ~/.config/sops/age/keys.txt
chmod 600 ~/.config/sops/age/keys.txt
```

`install.sh` can do this step for you (it offers to, on the SOPS path). The command
prints your **public** key (`age1…`) — copy it for the next step.

> 🔐 **Never commit `keys.txt`** (the private key). Add it to `.gitignore`. **Do**
> back it up somewhere safe — lose it and the encrypted secrets are unrecoverable.
> Commit only the `.sops.yaml` and the encrypted secret files.

**3. Point SOPS at your public key** with a `.sops.yaml` (commit this):

```yaml
# .sops.yaml
creation_rules:
  - path_regex: \.sops\.ya?ml$
    age: age1youragepublickeyhere…
```

**4. Create / edit the encrypted secrets file:**

```sh
sops ~/secrets.sops.yaml            # opens $EDITOR; save → it's encrypted at rest
```

Put values under nested keys, e.g.:

```yaml
cloudflare:
  token: your-secret-value
```

**5. Config** (`~/.config/mcp-secret/config`):

```sh
MCP_SECRET_BACKEND=sops
MCP_SOPS_FILE=~/secrets.sops.yaml
```

**6. Reference a secret:**

```
sops://~/secrets.sops.yaml#/cloudflare/token    # file # /nested/key/path
cloudflare/token                                # short ref → uses MCP_SOPS_FILE
```

If you keep the key file somewhere non-default, set `SOPS_AGE_KEY_FILE` (or
`SOPS_AGE_KEY`) in your environment.

---

## Verify

```
/mcp-secure:check          # or: mcp-doctor
```

It confirms the CLI is installed, you're authenticated (signed in / unlocked / key
present), and that every reference in your config actually resolves — without ever
printing a secret value.

## Principles

- **One vault, referenced — never inlined.** Config holds `op://` / `bw://` /
  `sops://` references; the value is fetched only at spawn (see the README).
- **Least privilege.** Scope each API token to the minimum the tool needs.
- **Official installs only.** Package manager or signed vendor installer; verify it.
- **Protect the root of trust** — your 1Password/Bitwarden login, or the age private
  key. That single credential gates everything else.
