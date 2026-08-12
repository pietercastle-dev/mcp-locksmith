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

**Requires BuildKit.** The Dockerfile uses `COPY --chmod=755`, which the classic
builder rejects outright. Docker Desktop and modern Docker Engine (23.0+) default
to BuildKit already; if `docker build` errors on `--chmod`, either upgrade Docker
or run with `DOCKER_BUILDKIT=1 docker build -t mcp-dogfood tests/dogfood`.

## What it proves

- `install.sh` survives the no-backend-CLI path (a real v1.0-dogfood
  regression) and writes the right config when sops+age are present.
- The full secret chain from nothing: age keygen → sops encrypt → `mcp-secret`
  resolves full and short refs → `mcp-launch` injects into the child process
  env only.
- The rug-pull tripwire: pin the env-driven fixture, clean verify, grow its
  tool surface, and `mcp-pin verify` must exit non-zero AND print the literal
  `DRIFT` token — a crash or unreadable config alone doesn't count as caught.
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

The sops binary is pinned in the Dockerfile (`SOPS_VER`) and its download is
verified against the sha256 checksums getsops publishes for the release, for
both amd64 and arm64 (selected by `dpkg --print-architecture`); bump the
version and both hashes together. The base image (`node:22-bookworm`) is
pinned by digest for the same reason — bump consciously, per the comment
above the `FROM` line. `git config --system --add safe.directory /repo` runs
before `USER dog` so the fresh-clone step is deterministic regardless of which
uid Docker Desktop's backend has bind-mount `/repo` owned by.

Trigger-looking strings in `dogfood.sh` are built by concatenation on purpose —
the plugin's own guard scans shell commands in sessions that run it live.
