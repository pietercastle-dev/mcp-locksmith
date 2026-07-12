#!/usr/bin/env python3
"""install.sh must succeed on a machine with no vault CLI (a supported state:
"you only need a vault if a tool requires a key") and on a config missing its
backend line. Regression for the pipefail-killed grep found in the v1.0
fresh-machine dogfood: the no-vault path exited 2 after linking, and a config
without MCP_SECRET_BACKEND would have died instead of warning.
Run: python3 test_install.py
"""
import os
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
INSTALL = os.path.join(REPO, "install.sh")

# System dirs only: excludes Homebrew/user paths, so op/sops/bw are absent no
# matter what the host has installed.
BARE_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"
HELPERS = ("mcp-secret", "mcp-launch", "mcp-bundles", "mcp-doctor", "mcp-pin")


def run_install(home):
    return subprocess.run(
        ["bash", INSTALL, "--non-interactive"],
        env={"HOME": home, "PATH": BARE_PATH},
        capture_output=True,
        text=True,
    )


class TestInstall(unittest.TestCase):
    def test_no_vault_cli_still_succeeds(self):
        with tempfile.TemporaryDirectory() as home:
            r = run_install(home)
            self.assertEqual(
                r.returncode, 0,
                "no-vault install must exit 0\nstdout: %s\nstderr: %s"
                % (r.stdout, r.stderr),
            )
            self.assertIn("no secret backend CLI found", r.stderr)
            for b in HELPERS:
                link = os.path.join(home, ".local", "bin", b)
                self.assertTrue(os.path.islink(link), "%s not linked" % b)
            self.assertFalse(
                os.path.exists(os.path.join(home, ".config", "mcp-secret", "config")),
                "no config should be written without a backend",
            )

    def test_config_without_backend_warns_not_dies(self):
        with tempfile.TemporaryDirectory() as home:
            cfg_dir = os.path.join(home, ".config", "mcp-secret")
            os.makedirs(cfg_dir)
            with open(os.path.join(cfg_dir, "config"), "w") as fh:
                fh.write("# hand-rolled config with no backend line\n")
            r = run_install(home)
            self.assertEqual(
                r.returncode, 0,
                "backend-less config must warn, not abort\nstdout: %s\nstderr: %s"
                % (r.stdout, r.stderr),
            )
            self.assertIn("no MCP_SECRET_BACKEND", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
