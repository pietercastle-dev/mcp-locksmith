# Fresh-machine dogfood (Docker)

The automatable slice of the release-gate dogfood, on a genuinely clean Linux
box: empty HOME, nothing preinstalled, the repo mounted read-only and cloned
inside. **Local-only by design** — it needs Docker and exists to be run by a
human before tagging a release, not on every push (CI already runs the unit
suites on ubuntu + macOS).

```sh
docker build -t mcp-dogfood tests/dogfood
docker run --rm -v "$PWD":/repo:ro mcp-dogfood
```

Exit 0 = every check passed. The run prints PASS/FAIL per check and a summary.

## What it proves

- `install.sh` survives the no-backend-CLI path (a real v1.0-dogfood
  regression) and writes the right config when sops+age are present.
- The full secret chain from nothing: age keygen → sops encrypt → `mcp-secret`
  resolves full and short refs → `mcp-launch` injects into the child process
  env only.
- The rug-pull tripwire: pin the env-driven fixture, clean verify, grow its
  tool surface, and `mcp-pin verify` must flag DRIFT and exit non-zero.
- Hooks work from a plain clone: `mcp-guard.py` is executable (the
  dead-call-guard regression class), denies a literal token headed into
  config, allows vault/keychain references.
- The Claude Code CLI slice: `plugin validate --strict`, marketplace add from
  the local clone, plugin install, and that the **installed cache copy** of
  the hook keeps its executable bit (where the 644 bug actually lived).

## What it cannot prove

- The macOS Keychain backend (`security` is macOS-only) — cover that with a
  live resolve on a Mac.
- The conversational flows (setup/add/fix) — they need an authed interactive
  Claude session; never bake credentials into this image.
- The marketplace-over-GitHub install UX and the human half of the
  "fresh machine to working tool in under 5 minutes" metric.

The sops binary is pinned in the Dockerfile (`SOPS_VER`); bump it consciously.
Trigger-looking strings in `dogfood.sh` are built by concatenation on purpose —
the plugin's own guard scans shell commands in sessions that run it live.
