# Secret backends: secure setup

You only need a backend if a tool needs a password or API key. Pick **one** and
follow its section, then run `/mcp-secure:check` to confirm it's wired up.

| Backend | Best if… | CLI | Reference form |
|---------|----------|-----|----------------|
| **macOS Keychain** | you're on a Mac and want nothing to install | `security` (built in) | `keychain://service/account` |
| **1Password** | you already use 1Password | `op` | `op://Vault/item/field` |
| **Bitwarden** | you want a free hosted vault | `bw` (+ `jq`) | `bw://item/field` |
| **SOPS + age** | you prefer files in git, no SaaS | `sops`, `age` | `sops://file#/key/path` |

The Keychain is the simplest choice for one Mac. A vault (1Password/Bitwarden) is
the pick if you use more than one machine or share keys with a team: the Keychain
has no sync or sharing story. The installer suggests in that order — vault CLI if
you have one, otherwise Keychain on a Mac. SOPS is offered last on purpose: it
works well, but its root of trust is an age key sitting in plain text on disk
(a passphrase on the key would break unattended spawn-time resolution), so pick
it deliberately — typically because your secrets already live in a git repo.

**Changing your backend later** is one line: edit `MCP_SECRET_BACKEND` in
`~/.config/mcp-secret/config` (or `rm` that file and re-run `install.sh`). The
default only governs *short* refs; fully-qualified refs (`op://…`,
`keychain://…`, …) always resolve the same regardless, so existing tools keep
working through a switch.

**Install CLIs from the official source**: your OS package manager or the
vendor's signed installer, never a random `curl … | sh`.

---

## macOS Keychain (`security`)

Nothing to install: `security` ships with macOS, and your login keychain is
already encrypted and unlocked by your login password. macOS only.

Put a value in (the bare `-w` **prompts** for it, so the secret never lands in
argv or your shell history, where `-w <value>` would put it):

```sh
security add-generic-password -s cloudflare -a mcp -w
# Password data for new item: <paste the value, press return>
```

`-s` is the *service* (name it after the tool), `-a` the *account* (any label;
`mcp` is a fine convention). Config:

```sh
MCP_SECRET_BACKEND=keychain
```

References: `keychain://cloudflare/mcp` (service/account), or `keychain://cloudflare`
to match on the service alone, or the short form `cloudflare/mcp`. `mcp-secret`
only ever **reads** (`security find-generic-password -w`); it never creates or
changes an item, so the keychain stays yours to manage.

Store **plain text** values: `security` hex-encodes anything with non-ASCII or
control bytes, and the resolver does not decode that. Updating a value later:
`security add-generic-password -U -s cloudflare -a mcp -w`. Deleting one:
`security delete-generic-password -s cloudflare -a mcp`. macOS may show a
"wants to access your keychain" prompt the first time a tool launches; allow it
(choose *Always Allow* if you don't want to be asked again).

---

## 1Password (`op`)

```sh
brew install 1password-cli   # others: developer.1password.com/docs/cli/get-started
```

Sign in via desktop-app integration (1Password app, then Settings, then Developer, then
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
