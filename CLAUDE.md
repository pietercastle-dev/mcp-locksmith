# CLAUDE.md: working on mcp-locksmith

This repo IS the mcp-secure plugin (a Claude Code plugin marketplace). Current
status and next actions live at the top of **[PLAN.md](PLAN.md)**; shipped work
in [CHANGELOG.md](CHANGELOG.md) (release-pending items under `[Unreleased]`).

## Map

```
plugins/mcp-secure/
  bin/        mcp-secret (vault resolver), mcp-launch (spawn-time injection),
              mcp-doctor (health + --launch diagnostics), mcp-pin (tool pinning,
              drift, `tools` plumbing), mcp-bundles
  hooks/      mcp-guard.py (config writes), mcp-call-guard.py (runtime calls),
              mcp-nudge.py (SessionStart), hooks.json, tests/
  commands/   the flows (setup/add/update/fix/remove/audit/check/verify/always-on)
  skills/     plain-language routers → the commands (add-tool, update-tool, …)
  tests/      bin-script tests + fake_mcp_server.py fixture (env-driven toolset)
  templates/  globals-profile scaffold, copied by the always-on flow
```

## Run the checks (what CI runs, ubuntu + macos)

```sh
for t in plugins/mcp-secure/hooks/tests/test_*.py plugins/mcp-secure/tests/test_*.py; do python3 "$t" || break; done
shellcheck --severity=warning plugins/mcp-secure/bin/mcp-{secret,launch,bundles} install.sh
```

## Conventions (load-bearing)

- **Design stance:** hooks fail OPEN; runtime interventions `ask`, never `deny`;
  hooks do local file reads only (no network, no server launches); command docs
  speak plain language ("tool", not "MCP server"); never duplicate native
  Claude Code features (permission system, OAuth store).
- **Keep-in-sync (no shared lib, scripts are standalone by design):** the
  credential regexes (`SECRET_VAL`/`SECRET_KEY`/`SAFE_VAL`) and the server
  `identity()` hash are duplicated across mcp-guard.py, mcp-call-guard.py,
  mcp-nudge.py, mcp-doctor, and mcp-pin. Changing one means changing all.
  Each copy has a "keep in sync" comment.
- **Bash targets 3.2** (macOS default): empty-array expansion under `set -u`
  needs `${arr+"${arr[@]}"}`; no bash-4isms.
- **Every behavior change ships with tests**: the suites have caught four real
  bugs pre-merge. Simulate tool drift via the fixture's env vars (`FAKE_TOOLS`/
  `FAKE_DESC`/`FAKE_DIE`), never by changing args (args change = new identity).
- **Test secrets** must be obviously fake (`ghp_EXAMPLEONLYnotarealtoken00`
  style), and test_guard.py builds trigger phrases by concatenation.

## Gotchas

- **The plugin runs live from this repo** (hooks + symlinked bin/). Edits to
  hooks take effect in this very session, and the guard scans YOUR commands:
  a commit message quoting a trigger pattern (the lowercase claude/mcp/add
  sequence, an auth header with a value, a token shape) will be blocked.
  Capitalize or paraphrase; this has happened.
- A blocked compound command (`git add … && git commit`) executed nothing.
  Re-run the whole thing, not just the tail.
- `~/.claude.json` is large and live. Never edit it in tests; every test
  redirects `HOME`/`MCP_PINS_FILE`/`MCP_ORG_CONFIG`/`MCP_SECRET_CONFIG`.

## Releasing

Pattern: "Stage vX.Y.Z release" commit: bump
`plugins/mcp-secure/.claude-plugin/plugin.json`, date the CHANGELOG
`[Unreleased]` section (+ link at bottom), tag `vX.Y.Z`, GitHub release.
Users are told to pin tags, so never rewrite a published tag. Commit as
**pietercastle-dev**.
