#!/usr/bin/env python3
"""Every script the plugin runtime invokes directly must be executable, on
disk AND in the git index (a file chmod'd locally but committed 644 ships
broken to every installed copy). Regression for the dead call guard found in
the 2026-07-12 transcript dogfood: mcp-call-guard.py was committed 100644, so
hooks.json's direct invocation failed with 'Permission denied' in every
installed session and the fail-open design hid it for the hook's whole life.
Run: python3 test_executable.py
"""
import json
import os
import re
import subprocess
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
HOOKS = os.path.dirname(HERE)
MCP = os.path.dirname(HOOKS)
BIN = os.path.join(MCP, "bin")


def hook_scripts():
    """Script paths referenced by hooks.json via ${CLAUDE_PLUGIN_ROOT}."""
    with open(os.path.join(HOOKS, "hooks.json")) as fh:
        blob = json.dumps(json.load(fh))
    # Commands quote the variable: "${CLAUDE_PLUGIN_ROOT}"/hooks/x.py — allow
    # (escaped) quotes between the closing brace and the path.
    rels = set(re.findall(r'\$\{CLAUDE_PLUGIN_ROOT\}[\\"]*/([\w./-]+)', blob))
    assert rels, "no CLAUDE_PLUGIN_ROOT script refs found in hooks.json"
    return sorted(os.path.join(MCP, r) for r in rels)


def runtime_scripts():
    return hook_scripts() + sorted(
        os.path.join(BIN, b)
        for b in os.listdir(BIN)
        if not b.startswith(".")
        and os.path.isfile(os.path.join(BIN, b))
        and b != "__pycache__"
    )


class TestExecutable(unittest.TestCase):
    def test_scripts_exist(self):
        for path in runtime_scripts():
            self.assertTrue(os.path.isfile(path), "%s missing" % path)

    def test_executable_on_disk(self):
        for path in runtime_scripts():
            self.assertTrue(
                os.access(path, os.X_OK),
                "%s is not executable; direct invocation fails with "
                "'Permission denied' and the hooks fail open (silently)"
                % os.path.relpath(path, MCP),
            )

    def test_executable_in_git_index(self):
        """Disk mode can lie (local chmod, uncommitted). The index mode is
        what clones and plugin caches receive."""
        try:
            out = subprocess.run(
                ["git", "ls-files", "-s", "--"] + runtime_scripts(),
                capture_output=True, text=True, cwd=MCP, check=True,
            ).stdout
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("not a git checkout")
        lines = [l for l in out.splitlines() if l.strip()]
        if not lines:
            self.skipTest("scripts not tracked by git here")
        for line in lines:
            mode, rest = line.split(" ", 1)
            path = rest.split("\t", 1)[1]
            self.assertEqual(
                mode, "100755",
                "%s is committed with mode %s; every installed copy gets a "
                "non-executable script" % (path, mode),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
