---
description: Diagnose and fix a tool that isn't working
---

**How to talk to the user:** plain, friendly language: say "tool" rather than
"MCP server", translate raw output, one problem and one fix at a time. The steps
below are for you, not the user.

A tool is broken ("the Slack tool stopped working", errors, not connecting).
Diagnose from evidence, then walk the fix.

1. **Scope it.** Which tool (`$ARGUMENTS`, or ask), and what changed recently if
   they know (new machine, update, new repo)?

2. **Run the diagnostics.** Both are read-only and never print secret values:
   ```sh
   mcp-doctor            # secret chain: helpers on PATH, backend authed, refs resolve
   mcp-doctor --launch   # actually spawns each stdio tool and speaks MCP to it
   ```
   `--launch` reports the server's own stderr on failure. Read it; that's
   usually the answer.

3. **Match the failure to its fix** (most common first):
   - **Backend not authenticated**: `op signin` / `export BW_SESSION="$(bw unlock --raw)"` /
     age key missing (see BACKENDS.md).
   - **A reference doesn't resolve**: the item/field name in the vault doesn't
     match the ref, or the secret was never stored. Fix the ref or the vault item.
   - **`mcp-launch`/`mcp-secret` not found**: run the marketplace repo's
     `install.sh` (symlinks them into `~/.local/bin`).
   - **Command not found / runtime missing**: the tool's runtime isn't
     installed (node/`npx`, `uvx`): install it, or the pinned package name is wrong.
   - **Package/version not found on the registry**: the pinned version may have
     been yanked. Offer `/mcp-secure:update` to move to a current version safely.
   - **`unresolved ${…}`**: plugin-scope config being run outside its plugin;
     that server is managed by a plugin, not this repo's config.
   - **Remote (http) tool failing**: launch checks don't apply; usually an
     expired OAuth session. Reconnect via `/mcp`, or re-add. If it needs a
     header, confirm the `headersHelper` command runs cleanly by itself.
   - **Timeout on first launch**: often the package download on first run;
     re-try, or run the fetch manually under `sfw` to watch it.

4. **Verify the fix**: re-run `mcp-doctor --launch` (or the failing flow) and
   confirm green. If the tool works but `mcp-pin verify` now reports DRIFT, its
   tools changed while it was broken. Re-vet before re-pinning (VETTING.md
   step 7), or use `/mcp-secure:update` if it was a version change.

5. If nothing above matches, gather the evidence (exact stderr, the config
   entry with any secret refs left as-is) and help debug from there. Never
   guess-edit config, and never inline a secret to "test".
