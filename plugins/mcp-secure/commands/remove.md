---
description: Remove a tool, unregister it, clean up its pin, and revoke its key
---

**How to talk to the user:** plain, friendly language (same tone as
`/mcp-secure:setup`): say "tool" rather than "MCP server", explain the *why* in
everyday terms, and match their technical level. The numbered steps below are for
you, not the user.

Remove a tool the user no longer wants. The important part isn't deleting the config
line. It's **not leaving a live secret behind**. A token for a tool nobody uses is a
forgotten credential waiting to leak, so the revoke step is the point of this command,
not an afterthought.

The tool to remove is in `$ARGUMENTS` (a name). If empty, list what's installed and
ask which one.

Steps:

1. **Find it and its scope.** Look in the current repo's `.mcp.json` (project scope)
   and `~/.claude.json` (user/global scope + the current project's entry). Note which
   file it lives in. That determines how you remove it.
2. **Check whether it uses a secret.** Inspect its config for a secret reference: an
   `mcp-launch --secret/--arg` ref, or an `op://` / `sops://` / `bw://` value in
   `env`/`args`. If it has one, capture the reference (e.g. `op://Work/github/token`);
   you'll need it for step 5. (Never print a resolved secret value, only the reference.)
3. **Confirm.** Tell the user plainly what you're about to remove, from which scope,
   and that it'll stop being available after a restart. Get a yes before changing anything.
4. **Unregister.** Remove the server from the right place:
   - **Project:** delete its entry from the repo's `.mcp.json` (or `claude mcp remove <name>`).
   - **User/global:** `claude mcp remove -s user <name>` (or edit `~/.claude.json`, the
     guard will ask you to confirm a global-scope edit).
   - **Always-on (globals plugin):** it lives in that plugin's `.mcp.json`. Edit there.
   Preserve every other server; only touch the one being removed.
5. **Revoke the secret, the security step.** If step 2 found a reference, tell the
   user, in plain terms, to:
   - **Revoke or rotate that token at the provider** (e.g. delete the GitHub PAT /
     rotate the API key) so it can't be used even if it leaks later.
   - **Delete the now-unused item from their vault** (1Password / Bitwarden / the SOPS
     file), *only if no other tool still references it*. Check the other configs first.
   Do **not** delete vault items or revoke tokens yourself. You can't, and shouldn't;
   guide the user to do it. If the tool had no secret, say so and skip this.
6. **Clean up the pin.** Run `mcp-pin unpin <name>` so `/mcp-secure:check` stops
   tracking a tool that's gone. (`mcp-pin prune` lists orphaned pins if they want a sweep.)
7. **Wrap up.** Remind them the change takes effect on the next session start, and give
   a one-line recap: removed from <scope>, key revoked (or "no key"), pin cleaned up.

Constraints:
- Only edit the **current repo's** `.mcp.json` or the user scope the tool actually lives
  in. Don't touch unrelated servers or other repos' configs.
- Never delete a vault item or revoke a credential on the user's behalf. That's theirs
  to do; your job is to make sure they know to.
